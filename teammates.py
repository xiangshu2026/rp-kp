# -*- coding: utf-8 -*-
"""队友系统：本地 Ollama 或云端 API，各自有角色卡与立场，参与跑团对话。"""
import json, random, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).parent
TEAM = ROOT / "teammates.json"
NL = chr(10)

# 云端预设（都是 OpenAI 兼容格式）
CLOUD_PRESETS = {
    "deepseek": {"base": "https://api.deepseek.com/v1", "models": ["deepseek-chat", "deepseek-reasoner"]},
    "zhipu": {"base": "https://open.bigmodel.cn/api/paas/v4", "models": ["glm-4-plus", "glm-4-flash", "glm-4-air"]},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "models": ["anthropic/claude-3.5-sonnet", "deepseek/deepseek-chat"]},
    "moonshot": {"base": "https://api.moonshot.cn/v1", "models": ["moonshot-v1-8k", "moonshot-v1-32k"]},
    "custom": {"base": "", "models": []},
}


def load_all():
    if not TEAM.exists():
        return []
    try:
        return json.loads(TEAM.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_all(items):
    TEAM.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def new_id():
    """毫秒时间戳 + 4 位随机，避免同毫秒碰撞。"""
    return "t" + str(int(time.time() * 1000)) + str(random.randint(1000, 9999))


def blank(name="新队友"):
    return {
        "id": new_id(),
        "name": name,
        "enabled": False,
        "role": "",
        "persona": "",
        "card_id": "",
        "provider": "local",
        "model": "kp-qwen3",
        "api_base": "",
        "api_key": "",
        "temperature": 0.8,
        "max_tokens": 500,
        "speak_rounds": 1,
        "created": time.time(),
    }


def upsert(item):
    items = load_all()
    for i, old in enumerate(items):
        if old.get("id") == item.get("id"):
            items[i] = item
            break
    else:
        items.append(item)
    save_all(items)
    return item


def delete(tid):
    items = [x for x in load_all() if x.get("id") != tid]
    save_all(items)


def public_view(item):
    """给前端的版本：API Key 打码。"""
    v = dict(item)
    k = v.get("api_key") or ""
    if k:
        v["api_key_masked"] = (k[:4] + "****" + k[-4:]) if len(k) > 8 else "****"
    else:
        v["api_key_masked"] = ""
    v["has_key"] = bool(k)
    v["api_key"] = ""
    return v


# ---------- 调用 ----------
def call_local(item, messages, cfg):
    base_url = (cfg.get("ollama") or "http://127.0.0.1:11434").rstrip("/")
    body = json.dumps({
        "model": item.get("model") or cfg.get("model"),
        "stream": False,
        "think": False,
        "options": {
            "num_ctx": int(cfg.get("num_ctx") or 24576),
            "num_predict": int(item.get("max_tokens") or 500),
            "temperature": float(item.get("temperature") or 0.8),
        },
        "messages": messages,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base_url + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        obj = json.loads(r.read().decode("utf-8"))
    return (obj.get("message") or {}).get("content", "")


def call_cloud(item, messages):
    base = (item.get("api_base") or "").rstrip("/")
    if not base:
        raise ValueError("没填 API 地址")
    key = item.get("api_key") or ""
    if not key:
        raise ValueError("没填 API Key")
    url = base + "/chat/completions"
    body = json.dumps({
        "model": item.get("model"),
        "messages": messages,
        "temperature": float(item.get("temperature") or 0.8),
        "max_tokens": int(item.get("max_tokens") or 500),
        "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            obj = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        raise ValueError("HTTP " + str(e.code) + "：" + detail)
    choices = obj.get("choices") or []
    if not choices:
        raise ValueError("返回里没有 choices")
    return (choices[0].get("message") or {}).get("content", "")


def call(item, messages, cfg):
    if (item.get("provider") or "local") == "cloud":
        return call_cloud(item, messages)
    return call_local(item, messages, cfg)


def test_conn(item, cfg):
    """连通性测试：发一句短请求。"""
    msgs = [{"role": "user", "content": "回一个字：好"}]
    t0 = time.time()
    try:
        out = call(item, msgs, cfg)
        return {"ok": True, "ms": int((time.time() - t0) * 1000), "reply": (out or "")[:60]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:220], "ms": int((time.time() - t0) * 1000)}

# ---------- 队友发言 ----------
TEAMMATE_SYS_TEMPLATE = (
    "你在一场跑团里扮演一个同伴角色，不是主持人，也不是旁白。" + NL + NL +
    "你的身份：{name}" + NL +
    "你的定位：{role}" + NL +
    "你的性格与说话方式：{persona}" + NL + NL +
    "规则：" + NL +
    "1. 只用第一人称说话，可以带动作描写，但不超过三句。" + NL +
    "2. 不推进剧情、不描述玩家看不到的东西、不代替主持人做判定。" + NL +
    "3. 你有自己的判断和脾气。如果你不认同玩家的做法，就直说，但不要长篇说教。" + NL +
    "4. 你看不到「世界状态」和「模组」这些主持人的东西，你只知道你亲眼见到和听说的。" + NL +
    "5. 输出 80 到 200 字，不要标题，不要列表。"
)


def build_teammate_messages(item, card, scene_brief, recent):
    """scene_brief：给队友看的简版场景（不含模组原文）。recent：最近几轮对话。"""
    sys_text = TEAMMATE_SYS_TEMPLATE.format(
        name=item.get("name", "同伴"),
        role=item.get("role") or "同行者",
        persona=item.get("persona") or "沉默但可靠",
    )
    if card:
        import coc7, rules
        if (card.get("system") or "coc7") == "dnd5e":
            ctx = rules.dnd_card_context(card)
        else:
            ctx = coc7.card_to_context(card)
        sys_text += NL + NL + "你的角色数据（自己心里有数就行，不要念出来）：" + NL + ctx
    msgs = [{"role": "system", "content": sys_text}]
    ctx = ["# 你所在的场景", scene_brief or "（未知）"]
    if recent:
        ctx.append("")
        ctx.append("# 刚刚发生的事（按顺序）")
        for t in recent:
            who = "调查员" if t.get("role") == "user" else "主持人"
            body = (t.get("content") or "")
            if len(body) > 700:
                body = body[:700] + "…"
            ctx.append(who + "：" + body)
    ctx.append("")
    ctx.append("现在轮到你说话。只输出你这一句（含动作）。")
    msgs.append({"role": "user", "content": NL.join(ctx)})
    return msgs


def speak(item, card, scene_brief, recent, cfg):
    msgs = build_teammate_messages(item, card, scene_brief, recent)
    out = call(item, msgs, cfg)
    return (out or "").strip()


def active_teammates():
    return [x for x in load_all() if x.get("enabled")]