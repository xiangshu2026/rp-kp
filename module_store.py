# -*- coding: utf-8 -*-
# 跑团 KP · 本地 COC 7th / DND 5e 桌面跑团工具
# https://github.com/xiangshu2026/rp-kp
"""模组存储 + 预算感知装载：长模组按幕装载，只喂当前需要的部分。"""
import json, time
from pathlib import Path
import module_parser as mp

ROOT = Path(__file__).parent
MODULES = ROOT / "modules"
NL = chr(10)
CHARS_PER_TOKEN = 0.72   # 中文实测


def tok(text):
    return int(len(text or "") * CHARS_PER_TOKEN)


def modules_dir():
    MODULES.mkdir(parents=True, exist_ok=True)
    return MODULES


def list_modules():
    out = []
    for p in sorted(modules_dir().glob("*.json")):
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
            out.append({"id": m.get("id", p.stem), "title": m.get("title", "?"),
                        "acts": len(m.get("acts", [])), "chars": m.get("chars", 0),
                        "tokens": m.get("tokens", 0), "source": m.get("source", "")})
        except Exception:
            continue
    return out


def save_module(mod):
    mod["updated"] = time.time()
    p = modules_dir() / (str(mod["id"]) + ".json")
    p.write_text(json.dumps(mod, ensure_ascii=False, indent=1), encoding="utf-8")
    return mod["id"]


def load_module(mid):
    p = modules_dir() / (str(mid) + ".json")
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def delete_module(mid):
    p = modules_dir() / (str(mid) + ".json")
    if p.exists():
        p.unlink()
        return True
    return False


def import_text(title, text, source=""):
    """把模组原文切分成幕并落盘。"""
    secs = mp.split_module(text)
    secs = mp.merge_small(secs)
    if not secs:
        secs = [{"title": "全文", "body": text.strip(), "chars": len(text.strip())}]
    acts = []
    for i, s in enumerate(secs):
        acts.append({
            "no": i + 1,
            "title": s["title"],
            "body": s["body"],
            "chars": s["chars"],
            "tokens": tok(s["body"]),
            "summary": "",
            "status": "todo",
        })
    mod = {
        "id": "m" + str(int(time.time() * 1000)),
        "title": title,
        "source": source,
        "chars": len(text),
        "tokens": tok(text),
        "acts": acts,
        "created": time.time(),
        "updated": time.time(),
    }
    save_module(mod)
    return mod


def shrink(text, budget_tokens):
    """超预算时按段落截断，保留开头与结尾（模组开头是背景，结尾常是线索）。"""
    if tok(text) <= budget_tokens:
        return text, False
    max_chars = int(budget_tokens / CHARS_PER_TOKEN)
    if max_chars >= len(text):
        return text, False
    paras = [p for p in text.split(NL + NL) if p.strip()]
    if len(paras) <= 2:
        return text[:max_chars], True
    keep_head = int(max_chars * 0.6)
    keep_tail = int(max_chars * 0.35)
    head = []
    used = 0
    for p in paras:
        if used + len(p) > keep_head:
            break
        head.append(p)
        used += len(p)
    tail = []
    used = 0
    for p in reversed(paras):
        if used + len(p) > keep_tail:
            break
        tail.insert(0, p)
        used += len(p)
    omitted = len(paras) - len(head) - len(tail)
    body = (NL + NL).join(head) + NL + NL + "〔此处省略约 " + str(omitted) + " 段，若调查员前往该处请用「展开细节」指令〕" + NL + NL + (NL + NL).join(tail)
    return body, True


def build_context(mod, act_no, budget_tokens=7000):
    """装载给 KP 的模组上下文：目录 + 当前幕（超预算自动压缩）+ 前后幕摘要。"""
    if not mod:
        return "", {"loaded": 0, "truncated": False}
    acts = mod.get("acts", [])
    if not acts:
        return "", {"loaded": 0, "truncated": False}
    idx = int(act_no or 1)
    idx = max(1, min(len(acts), idx))
    cur = acts[idx - 1]

    lines = ["# 模组：" + str(mod.get("title", ""))]
    lines.append("# 全部目录（你知道整体结构，但只需演到当前幕）")
    for a in acts:
        mark = " ← 当前" if a["no"] == idx else ""
        st = "" if a.get("status") != "done" else "（已演完）"
        lines.append(str(a["no"]) + ". " + str(a["title"]) + st + mark)

    if idx > 1 and acts[idx - 2].get("summary"):
        lines.append("# 上一幕回顾")
        lines.append(acts[idx - 2]["summary"])

    lines.append("# 当前幕：" + str(cur["title"]) + "（详细内容，照着演）")
    body, trunc = shrink(cur["body"], budget_tokens)
    lines.append(body)

    if idx < len(acts):
        nxt = acts[idx]
        lines.append("# 下一幕（预告，玩家还没到这里，不要提前透露）")
        lines.append(nxt["title"])
        preview = nxt["body"][:300]
        lines.append(preview + ("…" if len(nxt["body"]) > 300 else ""))

    text = NL.join(lines)
    return text, {"loaded": idx, "truncated": trunc, "tokens": tok(text),
                  "act_tokens": cur.get("tokens", 0)}


def set_act_summary(mid, act_no, summary):
    m = load_module(mid)
    if not m:
        return False
    for a in m.get("acts", []):
        if a["no"] == int(act_no):
            a["summary"] = summary
            a["status"] = "done"
            save_module(m)
            return True
    return False