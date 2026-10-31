# -*- coding: utf-8 -*-
# 跑团 KP · 本地 COC 7th / DND 5e 桌面跑团工具
# https://github.com/xiangshu2026/rp-kp
"""地图：房间节点 + 连通关系，按当前位置装载（不整张塞进上下文）。"""
import json, re, time
from pathlib import Path
NL = chr(10)
ROOT = Path(__file__).parent
MAPS = ROOT / "maps"


def maps_dir():
    MAPS.mkdir(parents=True, exist_ok=True)
    return MAPS


def list_maps():
    out = []
    for p in sorted(maps_dir().glob("*.json")):
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
            out.append({"id": m.get("id", p.stem), "title": m.get("title", "?"),
                        "rooms": len(m.get("rooms", [])),
                        "image": bool(m.get("image_path"))})
        except Exception:
            continue
    return out


def save_map(m):
    m["updated"] = time.time()
    p = maps_dir() / (str(m["id"]) + ".json")
    p.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    return m["id"]


def load_map(mid):
    p = maps_dir() / (str(mid) + ".json")
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def delete_map(mid):
    p = maps_dir() / (str(mid) + ".json")
    if p.exists():
        p.unlink()
        return True
    return False


def new_map(title, image_path=""):
    return {
        "id": "map" + str(int(time.time() * 1000)),
        "title": title,
        "image_path": image_path,
        "rooms": [],
        "current": "",
        "notes": "",
        "created": time.time(),
    }


def add_room(m, rid, name, desc="", exits=None):
    """加房间。exits 是 [{to, dir, note}]。"""
    for r in m["rooms"]:
        if r["id"] == rid:
            if name:
                r["name"] = name
            if desc:
                r["desc"] = desc
            if exits is not None:
                r["exits"] = exits
            return r
    room = {"id": rid, "name": name or rid, "desc": desc,
            "exits": exits or [], "visited": False, "note": ""}
    m["rooms"].append(room)
    return room


def link(m, a, b, direction="", note=""):
    """双向连通。"""
    ra = None
    rb = None
    for r in m["rooms"]:
        if r["id"] == a:
            ra = r
        if r["id"] == b:
            rb = r
    if not ra or not rb:
        return False
    if not any(e.get("to") == b for e in ra["exits"]):
        ra["exits"].append({"to": b, "dir": direction, "note": note})
    back = {"北": "南", "南": "北", "东": "西", "西": "东",
            "东北": "西南", "西南": "东北", "西北": "东南", "东南": "西北",
            "上": "下", "下": "上"}
    rev = back.get(direction, "")
    if not any(e.get("to") == a for e in rb["exits"]):
        rb["exits"].append({"to": a, "dir": rev, "note": note})
    return True


def build_context(m, budget_tokens=1800):
    """只给当前位置的房间详情 + 全图目录 + 相邻房间一句话。"""
    if not m or not m.get("rooms"):
        return "", {"loaded": 0}
    cur_id = m.get("current") or m["rooms"][0]["id"]
    cur = None
    for r in m["rooms"]:
        if r["id"] == cur_id:
            cur = r
            break
    if not cur:
        cur = m["rooms"][0]
    by_id = {r["id"]: r for r in m["rooms"]}

    L2 = ["# 地图：" + str(m.get("title", ""))]
    L2.append("# 全部房间（你知道布局，但只演到当前位置）")
    for r in m["rooms"]:
        mark = " ← 当前" if r["id"] == cur["id"] else ("（去过）" if r.get("visited") else "")
        L2.append("  " + str(r["id"]) + " " + str(r["name"]) + mark)
    L2.append("")
    L2.append("# 当前位置：" + str(cur["name"]) + "（" + str(cur["id"]) + "）")
    if cur.get("desc"):
        L2.append(str(cur["desc"]))
    if cur.get("note"):
        L2.append("（备注：" + str(cur["note"]) + "）")
    L2.append("")
    if cur.get("exits"):
        L2.append("# 从这里能去哪")
        for e in cur["exits"]:
            tgt = by_id.get(e.get("to"))
            tname = tgt["name"] if tgt else str(e.get("to"))
            d = e.get("dir") or ""
            note = ("（" + e["note"] + "）") if e.get("note") else ""
            L2.append("  - " + (d + " → " if d else "") + tname + note)

    text = NL.join(L2)
    # 超预算就砍掉房间目录里的描述，只留编号与名字
    if int(len(text) * 0.72) > budget_tokens:
        L2b = [L2[0], "# 全部房间", "  " + "、".join(r["id"] + " " + r["name"] for r in m["rooms"])]
        L2b.extend(L2[L2.index("# 当前位置：" + str(cur["name"]) + "（" + str(cur["id"]) + "）"):])
        text = NL.join(L2b)
    return text, {"loaded": 1, "room": cur["id"], "tokens": int(len(text) * 0.72)}