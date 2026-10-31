# -*- coding: utf-8 -*-
# 跑团 KP · 本地 COC 7th / DND 5e 桌面跑团工具
# https://github.com/xiangshu2026/rp-kp
"""记忆引擎：三层记忆 + 状态合并 + 滚动摘要 + 伏笔审计。无第三方依赖。"""
import json, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
WORLDS = ROOT / "worlds"
SESSIONS = ROOT / "sessions"
CONFIG = ROOT / "config.json"
NL = chr(10)
FENCE = chr(96) * 3

DEFAULT_CONFIG = {
    # ── 模型后端：ollama（本地，免费）或 openai（任意 OpenAI 兼容 API）──
    "kp_backend": "ollama",

    # 本地 Ollama
    "ollama": "http://127.0.0.1:11434",
    "model": "kp-qwen3",

    # 云端 API（kp_backend=openai 时才读）
    "kp_api_base": "",        # 例如 https://api.deepseek.com/v1
    "kp_api_key": "",         # 也可用环境变量 KP_API_KEY
    "kp_api_model": "",       # 例如 deepseek-chat

    # 通用
    "num_ctx": 24576,
    "num_predict": 1600,
    "temperature": 0.85,
    "window": 6,
    "compress_every": 8,

    # assistant 预填充引导（默认关闭，见 apply_prefill 的说明）
    "prefill_enabled": False,
    "prefill_texts": [],
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG.exists():
        try:
            cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def save_config(cfg):
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")


def safe_name(name):
    bad = set("/:*?<>|" + NL + chr(9) + chr(92))
    out = "".join("_" if c in bad else c for c in str(name)).strip().strip(".")
    return out[:60] or "untitled"


def list_worlds():
    WORLDS.mkdir(parents=True, exist_ok=True)
    return sorted(d.name for d in WORLDS.iterdir() if d.is_dir())


def world_path(name, fname):
    return WORLDS / safe_name(name) / fname


def read_world(name, fname, default=""):
    p = world_path(name, fname)
    return p.read_text(encoding="utf-8") if p.exists() else default


def write_world(name, fname, text):
    p = world_path(name, fname)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def build_fixed_layer(world):
    parts = [read_world(world, "prompt.md", "")]
    wb = read_world(world, "worldbook.md", "")
    if wb.strip():
        parts.append(NL + NL + "# 世界设定（World Book）" + NL + NL + wb)
    ch = read_world(world, "characters.md", "")
    if ch.strip():
        parts.append(NL + NL + "# 角色卡" + NL + NL + ch)
    return "".join(parts)


EMPTY_STATE = {"scene": "", "time": "", "location": "", "npcs": [], "clues": [],
               "foreshadow": [], "resolved": [], "hp": {}, "next": ""}


# ── 压缩语义边界（2026-10-31 从「大肥鱼记忆系统」修复记录学到）────────────
# 背景：那个系统曾因「压缩上下文」时调用整段 delete，把长期状态一起删了：
#   memberStats / wakeConfig / agentToken / pendingThoughts 全丢，群里的人全部不认识。
# 本项目现状：compress() 只重写 summary，不碰 state —— 所以没有那个 bug。
# 但同类风险存在两处，这里一并收口：
#   ① turns 从不裁剪，无限膨胀（压缩只是把旧对话写进 summary，原文还全在）
#   ② summary 是「覆盖式重写」不是增量 —— 40 轮后旧内容会被新摘要挤掉
# 原则：压缩只允许动「跟当前这一轮强绑定的」，长期状态一律不动。

# 压缩时绝对不能碰的字段（长期状态）
STATE_PROTECTED = ("scene", "time", "location", "npcs", "clues",
                   "foreshadow", "resolved", "hp", "next")

# 无论怎么裁，turns 至少保留最近这么多条原文
TURNS_KEEP_MIN = 20


def state_fingerprint(st):
    """给 state 做指纹，用来验证压缩前后长期状态没被动过。"""
    import hashlib
    payload = json.dumps({k: st.get(k) for k in STATE_PROTECTED},
                         ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def render_state(st):
    open_fs = [f for f in st.get("foreshadow", []) if f.get("status") == "open"]
    L2 = ["# 当前世界状态（每轮更新，必须遵守）", ""]
    L2.append("- 场景：" + str(st.get("scene", "")))
    L2.append("- 时间：" + str(st.get("time", "")))
    L2.append("- 地点：" + str(st.get("location", "")))
    L2.append("- 在场 NPC：" + ("、".join(st.get("npcs", [])) or "无"))
    L2.append("- 已掌握线索：" + ("；".join(st.get("clues", [])) or "无"))
    L2.append("- 角色状态：" + json.dumps(st.get("hp", {}), ensure_ascii=False))
    if open_fs:
        L2.append("- 未回收伏笔（必须记着，找机会自然提起）：")
        for f in open_fs:
            L2.append("  - [" + str(f.get("id")) + "] " + str(f.get("text")))
    if st.get("resolved"):
        L2.append("- 已回收伏笔：" + "、".join(st["resolved"]))
    L2.append("- 下一轮开场位置：" + str(st.get("next", "")))
    return NL.join(L2)


def render_summary(summ):
    if not summ.strip():
        return ""
    return "# 前情摘要（已压缩的历史，不是最近发生的事）" + NL + NL + summ


def assemble(fixed, state, summary, turns, window=6):
    ctx = [c for c in (render_summary(summary), render_state(state)) if c.strip()]
    msgs = [{"role": "system", "content": fixed}]
    if ctx:
        msgs.append({"role": "user", "content": (NL + NL).join(ctx) + NL + NL + "---" + NL + "以下是最近的对话。"})
        msgs.append({"role": "assistant", "content": "明白，我从这里接着写。"})
    for t in turns[-window:]:
        msgs.append({"role": t["role"], "content": t["content"]})
    return msgs


def _parse_markdown_state(text):
    """兜底：模型没吐 JSON 状态块、而是写了 Markdown 列表时的解析。

    实测常见形态：
        # 当前世界状态
        - 场景：城堡内的会客室
        - 时间：黄昏
        - 地点：灰石堡
        - 在场 NPC：哈罗德
        - 已掌握线索：无
        - 下一轮开场位置：城堡内的会客室

    解析不出来就返回 None，调用方按「无状态」处理，绝不抛异常。
    """
    import re
    if not text or not isinstance(text, str):
        return None
    # 只在这种明显是状态区的文本里找，避免把正文误当状态
    if ("当前世界状态" not in text) and ("下一轮开场位置" not in text):
        return None

    def grab(label, pattern=r"[:：]\s*(.+)"):
        m = re.search(r"^\s*[-*]?\s*" + re.escape(label) + pattern, text, re.M)
        return m.group(1).strip() if m else ""

    def grab_list(label):
        raw = grab(label)
        if not raw or raw in ("无", "暂无", "没有", "-"):
            return []
        parts = re.split(r"[、,，;；]", raw)
        return [p.strip() for p in parts if p.strip()]

    st = {}
    scene = grab("场景")
    if scene:
        st["scene"] = scene
    tm = grab("时间")
    if tm:
        st["time"] = tm
    loc = grab("地点")
    if loc:
        st["location"] = loc
    npcs = grab_list("在场 NPC") or grab_list("在场NPC") or grab_list("在场人物")
    if npcs:
        st["npcs"] = npcs
    clues = grab_list("已掌握线索") or grab_list("线索")
    if clues:
        st["clues"] = clues
    nxt = grab("下一轮开场位置") or grab("下一轮位置")
    if nxt:
        st["next"] = nxt

    return st or None


def split_state(reply):
    i = reply.find(FENCE)
    if i < 0:
        # 没有三反引号：先试 Markdown 状态块兜底
        md = _parse_markdown_state(reply)
        if md:
            # 把状态区从正文里切掉（从「当前世界状态」那行起）
            cut = reply.find("# 当前世界状态")
            if cut < 0:
                cut = reply.find("当前世界状态")
            prose = reply[:cut].strip() if cut > 0 else reply.strip()
            return prose, md
        return reply.strip(), None
    j = reply.find(FENCE, i + 3)
    if j < 0:
        return reply.strip(), None
    inner = reply[i + 3:j].strip()
    if inner.startswith("json"):
        inner = inner[4:].strip()
    try:
        st = json.loads(inner)
        if not isinstance(st, dict):
            raise ValueError("not a dict")
    except Exception:
        # JSON 解析失败也试一次 Markdown 兜底
        md = _parse_markdown_state(reply)
        if md:
            return reply.strip(), md
        return reply.strip(), None
    prose = (reply[:i] + reply[j + 3:]).strip()
    return prose, st


STATE_EXTRACT_SYS = (
    "你是跑团记录员。给你此前的状态和 KP 刚写的这一段剧情，输出本轮结束后的新状态，只输出 JSON。" + NL +
    "字段：scene / time / location / npcs(数组) / clues(数组) / foreshadow(数组，[{\"text\":\"…\"}]) / hp(对象) / next" + NL + NL +
    "【最重要的两条，违反即失败】" + NL +
    "1. next 必须是「这一段剧情结束时玩家所在的位置或正要面对的东西」，" + NL +
    "   不能照抄上一轮的 next。如果剧情里玩家移动了、场景变了、或者出现了新的焦点，next 就必须跟着变。" + NL +
    "2. scene 必须是「这一段里实际发生的事」，用一句话概括，不能重复上一轮的 scene。" + NL + NL +
    "其余规则：" + NL +
    "- 只写事实，不写形容词和气氛描写" + NL +
    "- 拿不准的字段留空字符串或空数组，绝对不要照抄旧值充数" + NL +
    "- clues 只放玩家在剧情里实际获得的线索，不要放过场描写" + NL +
    "- 只输出 JSON 对象本身，前后不要任何解释文字"
)


def extract_state(prose, prev_state, cfg):
    """单独发一次轻量请求提取状态，不依赖模型在正文里吐状态块。

    为什么要单独一次：实测 glm-4-flash 这类模型即使提示词写死了格式，
    也只有 0/3 概率吐 JSON 状态块——正文和状态混在一次输出里太容易被忽略。
    拆成两次调用后，状态这次只让它填 JSON，成功率高得多。

    失败时返回 None，调用方保持原状态不变。
    """
    if not prose or not str(prose).strip():
        return None
    prev = json.dumps({k: prev_state.get(k) for k in STATE_PROTECTED}, ensure_ascii=False)
    msgs = [
        {"role": "system", "content": STATE_EXTRACT_SYS},
        {"role": "user", "content": "此前状态：" + NL + prev + NL + NL + "本轮剧情：" + NL + str(prose)[:3000]},
    ]
    try:
        r = chat(msgs, cfg, temperature=0.1, num_predict=400)
        raw = (r.get("message") or {}).get("content", "").strip()
    except Exception:
        return None
    if not raw:
        return None
    # 剥掉可能的代码围栏
    if raw.startswith(FENCE):
        raw = raw[3:]
        if raw.startswith("json"):
            raw = raw[4:]
    if raw.endswith(FENCE):
        raw = raw[:-3]
    raw = raw.strip()
    # 只取第一个 { 到最后一个 } 之间
    a = raw.find("{")
    b = raw.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        st = json.loads(raw[a:b + 1])
    except Exception:
        return None
    return st if isinstance(st, dict) else None


def merge_state(old, new):
    st = dict(old)
    if not isinstance(new, dict):
        # 模型没按格式吐状态块时，保持原状态不动，绝不让调用链崩掉
        return dict(old)
    for k in ("scene", "time", "location", "next"):
        if new.get(k):
            st[k] = new[k]
    if new.get("npcs"):
        st["npcs"] = new["npcs"]
    if new.get("clues"):
        merged = []
        for c in list(old.get("clues", [])) + list(new["clues"]):
            c = str(c).strip()
            if c and c not in merged:
                merged.append(c)
        st["clues"] = merged[-20:]
    if new.get("hp"):
        st["hp"] = dict(old.get("hp", {}), **new["hp"])
    existing = list(old.get("foreshadow", []))
    nums = [int(str(f.get("id"))[1:]) for f in existing
            if str(f.get("id", "")).startswith("f") and str(f.get("id"))[1:].isdigit()]
    nxt = 1 + (max(nums) if nums else 0)
    texts = {str(f.get("text", "")).strip() for f in existing}
    for f in new.get("foreshadow", []):
        t = str(f.get("text", "")).strip()
        if not t or t in texts:
            continue
        existing.append({"id": "f" + str(nxt).zfill(3), "text": t, "status": "open"})
        texts.add(t)
        nxt += 1
    for rid in new.get("resolved", []):
        for f in existing:
            if f.get("id") == rid:
                f["status"] = "closed"
    st["foreshadow"] = existing
    st["resolved"] = sorted({f["id"] for f in existing if f.get("status") == "closed"})
    return st

# ── assistant 预填充引导（可选）────────────────────────────────────────────
# 有些模型（尤其是对齐较严的）在特定题材上会反复「重新判断该不该拒绝」，
# 表现为回复空转、只说教不推进剧情。一个通用缓解办法是在 messages 末尾
# 补一条不闭合的 assistant 引导句，让模型接着写而不是从头决策。
#
# 这里只做「结构」：预填充内容由 config.json 的 prefill_texts 提供，
# 默认空数组 = 完全关闭。仓库不内置任何具体文本。
PREFILL_KEYS = (
    "战斗", "攻击", "挥剑", "开枪", "追击", "逃亡", "谈判", "逼问",
)


def _wants_prefill(text, keys):
    """玩家输入是否命中预填充触发词。"""
    t = str(text or "")
    return any(k in t for k in keys)


def _last_user(msgs):
    for m in reversed(msgs):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def apply_prefill(msgs, cfg):
    """按配置在末尾追加一条 assistant 引导句（不闭合句子）。

    默认关闭。要启用需在 config.json 里同时给出：
      "prefill_enabled": true
      "prefill_texts": ["……", "……"]
      "prefill_keys": ["关键词1", "关键词2"]   （可选，缺省用 PREFILL_KEYS）

    只在最后一轮是 user 时追加；已经有 assistant 结尾就不加。
    """
    if not cfg.get("prefill_enabled", False):
        return msgs
    texts = cfg.get("prefill_texts") or []
    if not texts:
        return msgs
    if not msgs or msgs[-1].get("role") != "user":
        return msgs
    keys = tuple(cfg.get("prefill_keys") or PREFILL_KEYS)
    if not _wants_prefill(_last_user(msgs), keys):
        return msgs
    idx = len(_last_user(msgs)) % len(texts)
    out = list(msgs)
    out.append({"role": "assistant", "content": texts[idx]})
    return out


# ── 模型后端：本地 Ollama 或任意 OpenAI 兼容 API ─────────────────────────
#
# config.json 里用 kp_backend 切换：
#   "kp_backend": "ollama"        （默认）走本地 Ollama，免费、离线
#   "kp_backend": "openai"        走任意 OpenAI 兼容 API，需要 base + key + model
#
# 云端配置（只有 kp_backend=openai 时才读）：
#   "kp_api_base": "https://api.deepseek.com/v1"
#   "kp_api_key":  "sk-..."         也可以用环境变量 KP_API_KEY
#   "kp_api_model": "deepseek-chat"
#
# 常见服务商的 base 地址见 README。都是 /chat/completions 接口，填对 base 就行。


def _cloud_call(msgs, cfg, temperature=None, num_predict=None):
    """OpenAI 兼容接口调用。返回与 Ollama 同形的 dict，方便上层不改。"""
    base = str(cfg.get("kp_api_base") or "").rstrip("/")
    if not base:
        raise ValueError("kp_api_base 没填。填服务商的 API 地址，例如 https://api.deepseek.com/v1")
    key = str(cfg.get("kp_api_key") or "")
    if not key:
        import os as _os
        key = _os.environ.get("KP_API_KEY", "")
    if not key:
        raise ValueError("kp_api_key 没填，也没设环境变量 KP_API_KEY")
    model = str(cfg.get("kp_api_model") or cfg.get("model") or "")
    if not model:
        raise ValueError("kp_api_model 没填")
    body = json.dumps({
        "model": model,
        "messages": msgs,
        "temperature": float(temperature if temperature is not None else cfg.get("temperature", 0.85)),
        "max_tokens": int(num_predict or cfg.get("num_predict", 1600)),
        "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base + "/chat/completions", data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    })
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            obj = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise ValueError("HTTP " + str(e.code) + "：" + detail)
    choices = obj.get("choices") or []
    if not choices:
        raise ValueError("返回里没有 choices：" + json.dumps(obj, ensure_ascii=False)[:200])
    msg = choices[0].get("message") or {}
    # 包成 Ollama 的形状，上层代码不用改
    return {"message": {"content": msg.get("content", "")}}


def chat(msgs, cfg, temperature=None, num_predict=None):
    msgs = apply_prefill(msgs, cfg)
    backend = str(cfg.get("kp_backend") or "ollama").lower()
    if backend == "openai":
        return _cloud_call(msgs, cfg, temperature, num_predict)
    body = json.dumps({
        "model": cfg["model"], "stream": False, "think": False,
        "options": {
            "num_ctx": int(cfg["num_ctx"]),
            "num_predict": int(num_predict or cfg["num_predict"]),
            "temperature": float(temperature if temperature is not None else cfg["temperature"]),
        },
        "messages": msgs,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(cfg["ollama"] + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(r.read().decode("utf-8"))


SUMMARY_SYS = ("你在为一场长篇跑团做记忆压缩。把「已有摘要」和「本轮新对话」合并成一份不超过 600 字的摘要。" + NL + NL +
               "规则：" + NL +
               "1. 只写事实：谁做了什么、去了哪、得到了什么、失去了什么、谁死了、谁反目了。" + NL +
               "2. 保留所有专有名词（人名、地名、物品名），一个字都不许改。" + NL +
               "3. 凡是玩家表现出强烈情绪或立下誓言的时刻，用一句话原样保留。" + NL +
               "4. 不要形容词，不要气氛描写，不要心理描写。" + NL +
               "5. 输出纯文本，不要标题，不要列表符号。" + NL +
               "6. 【重要】已有摘要里的事实必须全部保留，只允许压缩措辞，不允许丢弃事件。" + NL +
               "7. 如果已有摘要 + 新对话超过 600 字，优先压缩早期的场景描写，保留人物、事件、承诺、伏笔。")


AUDIT_SYS = ("你在为跑团做伏笔审计。下面是所有未回收的伏笔。" + NL + NL +
             "任务：从里面挑 1 到 2 条，写一句它现在应该如何自然地出现在下一幕。" + NL +
             "要求：必须具体（谁的什么东西、在哪个场景、以什么形态出现），不要空话。" + NL +
             "输出格式：每行一条，以伏笔 id 开头，冒号后接做法。")


class Session:
    def __init__(self, name, world):
        self.name = safe_name(name)
        self.world = safe_name(world)
        self.dir = SESSIONS / self.name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.dir / "meta.json"
        self.turns_file = self.dir / "turns.jsonl"
        self.state_file = self.dir / "state.json"
        self.summary_file = self.dir / "summary.md"
        self.archive = self.dir / "archive.md"
        # 已落盘的世界绑定优先；没有落盘且本次传了具体世界，就把绑定写死
        if self.meta_file.exists():
            self.meta = self._load(self.meta_file, {})
            if self.meta.get("world"):
                self.world = self.meta["world"]
        else:
            self.meta = {"created": time.time()}
            if self.world and self.world != "default":
                self.meta["world"] = self.world
                self.save_meta()
            else:
                self.meta["world"] = ""
        self.state = self._load(self.state_file, dict(EMPTY_STATE))
        self.summary = self.summary_file.read_text(encoding="utf-8") if self.summary_file.exists() else ""
        if self.turns_file.exists():
            raw = self.turns_file.read_text(encoding="utf-8").splitlines()
            self.turns = [json.loads(l) for l in raw if l.strip()]
        else:
            self.turns = []

    @staticmethod
    def _load(p, default):
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return default
        return default

    def append_turn(self, role, content):
        self.turns.append({"role": role, "content": content})
        with self.turns_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"role": role, "content": content}, ensure_ascii=False) + NL)

    def save_state(self):
        self.state_file.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")

    def save_summary(self):
        self.summary_file.write_text(self.summary, encoding="utf-8")

    def save_meta(self):
        self.meta_file.write_text(json.dumps(self.meta, ensure_ascii=False, indent=1), encoding="utf-8")

    def archive_turn(self, prose):
        n = len([t for t in self.turns if t["role"] == "assistant"])
        with self.archive.open("a", encoding="utf-8") as f:
            f.write(NL + "## 第 " + str(n) + " 轮" + NL + NL + prose + NL)

    def compress(self, cfg):
        w = int(cfg["window"])
        if len(self.turns) <= w * 2:
            return None

        # ── 语义边界：压缩前给长期状态拍指纹 ──────────────────────────
        fp_before = state_fingerprint(self.state)

        batch = self.turns[:-w]
        payload = (NL + NL).join("【" + t["role"] + "】" + t["content"] for t in batch)
        msgs = [{"role": "system", "content": SUMMARY_SYS},
                {"role": "user", "content": "已有摘要：" + NL + (self.summary or "（无）") +
                 NL + NL + "本轮要压缩的对话：" + NL + payload}]
        r = chat(msgs, cfg, temperature=0.2, num_predict=700)
        self.summary = r["message"]["content"].strip()
        self.save_summary()

        # ── 裁剪 turns：只丢已经写进 summary 的旧对话，保留最近原文 ────
        # 原来 turns 从不裁剪，长局会无限膨胀；这里按 window 裁剪，
        # 但至少留 TURNS_KEEP_MIN 条，避免把「刚刚发生的事」也压掉。
        keep = max(w, TURNS_KEEP_MIN)
        if len(self.turns) > keep * 2:
            dropped = len(self.turns) - keep
            self.turns = self.turns[-keep:]
            self._rewrite_turns()
            self.last_trim = {"dropped": dropped, "kept": keep}

        # ── 语义边界：压缩后校验长期状态没被动过 ──────────────────────
        fp_after = state_fingerprint(self.state)
        if fp_after != fp_before:
            # 不该发生。真发生了说明有代码路径动了 state，必须报出来。
            print("[engine] ⚠️ 压缩后长期状态指纹变了：" + fp_before + " → " + fp_after)
        return self.summary

    def _rewrite_turns(self):
        """turns 裁剪后重写文件（原来是 append-only，裁完必须整体重写）。"""
        tmp = self.turns_file.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for t in self.turns:
                f.write(json.dumps(t, ensure_ascii=False) + NL)
        tmp.replace(self.turns_file)

    def audit(self, cfg):
        open_fs = [f for f in self.state.get("foreshadow", []) if f.get("status") == "open"]
        if not open_fs:
            return ""
        listing = NL.join("[" + str(f["id"]) + "] " + str(f["text"]) for f in open_fs)
        msgs = [{"role": "system", "content": AUDIT_SYS},
                {"role": "user", "content": "当前场景：" + str(self.state.get("scene", "")) +
                 NL + NL + "未回收伏笔：" + NL + listing}]
        r = chat(msgs, cfg, temperature=0.6, num_predict=300)
        return r["message"]["content"].strip()


def list_sessions():
    SESSIONS.mkdir(parents=True, exist_ok=True)
    out = []
    for d in sorted(SESSIONS.iterdir()):
        if not d.is_dir():
            continue
        meta = {}
        mp = d / "meta.json"
        if mp.exists():
            try:
                meta = json.loads(mp.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        tf = d / "turns.jsonl"
        n = 0
        if tf.exists():
            n = sum(1 for l in tf.read_text(encoding="utf-8").splitlines() if l.strip()) // 2
        out.append({"name": d.name, "world": meta.get("world", ""),
                    "turns": n, "mtime": d.stat().st_mtime})
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out