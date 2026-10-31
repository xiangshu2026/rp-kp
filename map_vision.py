# -*- coding: utf-8 -*-
"""地图图片解析：视觉模型抽房间与连线，或从文本描述解析。"""
import base64, json, re, urllib.request
NL = chr(10)

VISION_PROMPT = (
    "你在一张桌上角色扮演游戏的地图上工作。请仔细看图，输出 JSON。" + NL + NL +
    "要求：" + NL +
    "1. 找出所有编号房间（1、2、3、A、B 或文字标签）。" + NL +
    "2. 每个房间给：id（编号或短名）、name（图上文字，没有就写 房间N）、" + NL +
    "   desc（图上能看到的陈设，一两句）、exits（通向哪些房间的 id 列表）。" + NL +
    "3. 门、楼梯、暗门在 note 里说明。" + NL +
    "4. 看不清的地方写 unknown，不要编。" + NL + NL +
    "只输出 JSON，格式：" + NL +
    chr(123) + chr(34) + "rooms" + chr(34) + ": [{" + chr(34) + "id" + chr(34) + ": " + chr(34) + "1" + chr(34) + ", " +
    chr(34) + "name" + chr(34) + ": " + chr(34) + "前厅" + chr(34) + ", " + chr(34) + "desc" + chr(34) + ": " + chr(34) + "…" + chr(34) + ", " +
    chr(34) + "exits" + chr(34) + ": [" + chr(34) + "2" + chr(34) + "]}" + chr(125)
)


def ocr_via_vision(image_path, model, cfg):
    """用 Ollama 视觉模型识别地图。返回 (data, err)。"""
    try:
        raw = open(image_path, "rb").read()
    except Exception as e:
        return None, "读图失败：" + str(e)[:100]
    b64 = base64.b64encode(raw).decode("ascii")
    body = json.dumps({
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": VISION_PROMPT, "images": [b64]}],
        "options": {"temperature": 0.2, "num_predict": 1500},
    }, ensure_ascii=False).encode("utf-8")
    url = (cfg.get("ollama") or "http://127.0.0.1:11434").rstrip("/") + "/api/chat"
    try:
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            obj = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        msg = str(e)[:200]
        if "not found" in msg.lower() or "404" in msg:
            return None, "本机没有这个视觉模型。先执行：ollama pull " + model
        return None, "视觉模型调用失败：" + msg
    text = (obj.get("message") or {}).get("content", "")
    return parse_vision_json(text)


def parse_vision_json(text):
    """从模型输出里抠出 JSON。模型经常夹带解释文字。"""
    if not text:
        return None, "模型没有返回内容"
    # 先找 ```json 代码块
    fence = chr(96) * 3
    i = text.find(fence)
    while i >= 0:
        j = text.find(fence, i + 3)
        if j > i:
            chunk = text[i + 3:j].strip()
            if chunk.startswith("json"):
                chunk = chunk[4:].strip()
            data, err = try_json(chunk)
            if data:
                return data, None
        i = text.find(fence, j + 3 if j > i else i + 3)
    # 再找第一个 { 到最后一个 }
    a = text.find("{")
    b = text.rfind("}")
    if a >= 0 and b > a:
        data, err = try_json(text[a:b + 1])
        if data:
            return data, None
    return None, "模型输出里没找到合法 JSON（原文前 200 字：" + text[:200] + "）"


def try_json(s):
    try:
        d = json.loads(s)
        if isinstance(d, dict) and "rooms" in d:
            return d, None
        if isinstance(d, list):
            return {"rooms": d}, None
        return None, "JSON 里没有 rooms"
    except Exception as e:
        return None, str(e)[:80]


def from_text_desc(text):
    """从文字描述解析房间。

    支持：
        1: 前厅，中央有枯井。通往 2、3
        2：走廊 -> 1, 4
    """
    rooms = []
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    CJK = "一-龥"
    SEP = "、，"
    id_re = re.compile("^([0-9A-Za-z" + CJK + "]{1,12})[" + ":" + ":]" + r"\s*(.*)$")
    for ln in lines:
        m = id_re.match(ln)
        if not m:
            continue
        rid = m.group(1).strip()
        rest = m.group(2).strip()
        exits = []
        em = re.search("(?:通往|通向|连接|出口是|->|→|到)" +
                       r"\s*([0-9A-Za-z" + CJK + SEP + r",\s]+)", rest)
        if em:
            raw = em.group(1)
            for part in re.split("[" + SEP + r",\s]+", raw):
                part = part.strip()
                if part and part != rid:
                    exits.append(part)
            rest = rest[:em.start()].strip()
        name = rid
        desc = rest
        nm = re.match("^([^" + "，" + "。" + r".;\s]{1,16})[" +
                      "，" + "。" + r".;\s]\s*(.*)$", rest)
        if nm:
            name = nm.group(1).strip()
            desc = nm.group(2).strip()
        elif rest:
            name = rest[:16]
            desc = ""
        rooms.append({"id": rid, "name": name, "desc": desc,
                      "exits": [{"to": e} for e in exits]})
    return {"rooms": rooms}

def apply_to_map(m, data, merge=True):
    """把解析结果写进地图。merge=True 时保留已有房间。"""
    import mapdata
    rooms = (data or {}).get("rooms") or []
    if not merge:
        m["rooms"] = []
    added = 0
    for r in rooms:
        rid = str(r.get("id") or "").strip()
        if not rid:
            continue
        exists = any(x["id"] == rid for x in m["rooms"])
        exits_raw = r.get("exits") or []
        exits = []
        for e in exits_raw:
            if isinstance(e, str):
                exits.append({"to": e, "dir": "", "note": ""})
            elif isinstance(e, dict):
                exits.append({"to": str(e.get("to") or ""),
                              "dir": e.get("dir") or "",
                              "note": e.get("note") or ""})
        mapdata.add_room(m, rid, r.get("name") or rid, r.get("desc") or "", exits)
        if not exists:
            added += 1
    # 补全反向连线
    for r in list(m["rooms"]):
        for e in list(r.get("exits") or []):
            tgt = e.get("to")
            if not tgt:
                continue
            if not any(x["id"] == tgt for x in m["rooms"]):
                mapdata.add_room(m, tgt, tgt)
            tr = next((x for x in m["rooms"] if x["id"] == tgt), None)
            if tr and not any(x.get("to") == r["id"] for x in tr.get("exits") or []):
                back = {"北": "南", "南": "北", "东": "西", "西": "东",
                        "上": "下", "下": "上"}
                tr.setdefault("exits", []).append(
                    {"to": r["id"], "dir": back.get(e.get("dir") or "", ""), "note": ""})
    if m["rooms"] and not m.get("current"):
        m["current"] = m["rooms"][0]["id"]
    return added