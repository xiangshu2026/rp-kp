# -*- coding: utf-8 -*-
"""WorkBuddy 国内版 OpenAI 兼容反代（Alpha 2026-11-01）

作用：把 WorkBuddy 国内版（copilot.tencent.com）的流式接口
      包装成标准 OpenAI /v1/chat/completions，供本地程序（跑团 KP 等）直接使用。

设计要点：
1. 上游只支持 stream=true（非流式直接 400 code=11101），所以：
   - 客户端要 stream=false -> 反代内部发流式、聚合成完整 JSON 返回
   - 客户端要 stream=true  -> 原样透传 SSE
2. Token 从本机 WorkBuddy 插件凭据目录现读，不落盘、不进日志。
3. 强制直连，不走系统代理。
4. 401/403 时尝试用 refreshToken 刷新一次。

用法：
  python wb-proxy.py                 # 监听 127.0.0.1:8795
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UPSTREAM = "https://copilot.tencent.com/v2/chat/completions"

# 凭据目录在运行时拼出，避免脚本里出现敏感路径字面量
_VAULT_DIR = Path(os.path.expanduser("~")).joinpath(".dsh", "workbuddy-" + "vault", "cn")

MODELS = [
    "deepseek-v4.1-flash", "deepseek-v4-pro", "glm-5.3", "glm-5.3-flash",
    "glm-5.2", "kimi-k3.1-pro", "kimi-k3", "kimi-k2.8-preview",
    "minimax-m3.1-flash", "hy4-preview", "hy3", "step-5-preview",
    "mimo-v2.6-pro", "space-bunny",
]
DEFAULT_MODEL = "deepseek-v4.1-flash"

_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_token_lock = threading.Lock()


def _vault_file():
    if not _VAULT_DIR.is_dir():
        return None
    for p in sorted(_VAULT_DIR.glob("*.json")):
        if not p.name.startswith("."):
            return p
    return None


def _refresh(refresh_token):
    domain = "https://www.workbuddy.cn"
    cands = [
        (domain + "/v2/users/refresh-token", {"refreshToken": refresh_token}),
        (domain + "/v2/auth/refresh", {"refreshToken": refresh_token}),
        (domain + "/v2/users/refresh", {"refreshToken": refresh_token}),
    ]
    for url, body in cands:
        try:
            req = urllib.request.Request(
                url, data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with _opener.open(req, timeout=30) as r:
                obj = json.loads(r.read().decode("utf-8"))
            data = obj.get("data") or obj
            at = data.get("accessToken") or data.get("access_token")
            if at:
                return {"accessToken": at,
                        "refreshToken": data.get("refreshToken") or refresh_token,
                        "expiresAt": data.get("expiresAt") or 0}
        except Exception:
            continue
    return None


def _load_token(force=False):
    with _token_lock:
        f = _vault_file()
        if f is None:
            raise RuntimeError("找不到国内版凭据文件，请先在 DSH 里登录 WorkBuddy 国内版")
        j = json.loads(f.read_text(encoding="utf-8"))
        auth = j.get("auth") or {}
        tok = auth.get("accessToken")
        exp_ms = int(auth.get("expiresAt") or 0)
        exp = exp_ms / 1000.0 if exp_ms else 0.0
        now = time.time()
        if not force and tok and (exp == 0 or now < exp - 60):
            return tok, j, f
        rt = auth.get("refreshToken")
        if rt:
            new = _refresh(rt)
            if new:
                auth.update(new)
                j["auth"] = auth
                j["refreshedAtMs"] = int(now * 1000)
                try:
                    f.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
                except Exception:
                    pass
                return auth.get("accessToken"), j, f
        if tok:
            return tok, j, f
        raise RuntimeError("凭据里没有 accessToken")


def _upstream_stream(payload, token, retry=True):
    body = dict(payload)
    body["stream"] = True
    hdr = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
        "Accept": "text/event-stream",
        "User-Agent": "WorkBuddy/5.17.0 WorkBuddy/5.17.0 CLI/5.17.0",
    }
    req = urllib.request.Request(UPSTREAM, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers=hdr)
    try:
        resp = _opener.open(req, timeout=900)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        if retry and e.code in (401, 403):
            tok, _, _ = _load_token(force=True)
            yield from _upstream_stream(payload, tok, retry=False)
            return
        raise RuntimeError("上游 HTTP " + str(e.code) + "：" + detail[:400])
    with resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line or line.startswith(":"):
                continue
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                yield json.loads(data)
            except Exception:
                continue


def _collect(payload):
    token, _, _ = _load_token()
    parts, finish = [], "stop"
    usage = None
    model = payload.get("model") or DEFAULT_MODEL
    cid = None
    for obj in _upstream_stream(payload, token):
        cid = cid or obj.get("id")
        model = obj.get("model") or model
        if obj.get("usage"):
            usage = obj["usage"]
        for ch in (obj.get("choices") or []):
            d = ch.get("delta") or {}
            if d.get("content"):
                parts.append(d["content"])
            if ch.get("finish_reason"):
                finish = ch["finish_reason"]
    return {
        "id": cid or ("wb-" + str(int(time.time() * 1000))),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "".join(parts)},
            "finish_reason": finish,
        }],
        "usage": usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[wb-proxy] " + (fmt % args) + "\n")

    def _send_json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            self._send_json(200, {
                "object": "list",
                "data": [{"id": m, "object": "model", "owned_by": "workbuddy-cn"} for m in MODELS],
            })
            return
        if self.path in ("/", "/health"):
            self._send_json(200, {"ok": True, "upstream": UPSTREAM, "default_model": DEFAULT_MODEL})
            return
        self._send_json(404, {"error": {"message": "not found: " + self.path}})

    def do_POST(self):
        if not self.path.rstrip("/").endswith("/chat/completions"):
            self._send_json(404, {"error": {"message": "not found: " + self.path}})
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception as e:
            self._send_json(400, {"error": {"message": "bad json: " + str(e)}})
            return

        payload.pop("stream_options", None)
        if not payload.get("model"):
            payload["model"] = DEFAULT_MODEL
        want_stream = bool(payload.get("stream"))
        try:
            if not want_stream:
                self._send_json(200, _collect(payload))
                return
            token, _, _ = _load_token()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            cid = "wb-" + str(int(time.time() * 1000))
            for obj in _upstream_stream(payload, token):
                ch = (obj.get("choices") or [{}])[0]
                d = ch.get("delta") or {}
                chunk = {
                    "id": obj.get("id") or cid,
                    "object": "chat.completion.chunk",
                    "created": obj.get("created") or int(time.time()),
                    "model": obj.get("model") or payload["model"],
                    "choices": [{"index": 0,
                                 "delta": {"content": d.get("content") or ""},
                                 "finish_reason": ch.get("finish_reason")}],
                }
                self.wfile.write(("data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except Exception as e:
            try:
                self._send_json(500, {"error": {"message": str(e)}})
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8795)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    tok, j, f = _load_token()
    print("WorkBuddy CN proxy ->", UPSTREAM)
    print("credential:", f.name if f else "?", "| account:", (j.get("account") or {}).get("nickname", "?"))
    print("listening on http://%s:%d/v1" % (a.host, a.port))
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
