# -*- coding: utf-8 -*-
# 跑团 KP · 本地 COC 7th / DND 5e 桌面跑团工具
# https://github.com/xiangshu2026/rp-kp
"""角色关系：节点 + 有向边，支持手工编辑与自动抽取。"""
import json, time
from pathlib import Path

ROOT = Path(__file__).parent
REL = ROOT / "relations.json"

# 关系类型（双向语义分开写，便于渲染箭头标签）
REL_TYPES = [
    ("family", "亲属"), ("lover", "恋人"), ("friend", "挚友"),
    ("colleague", "同事"), ("mentor", "师徒"), ("rival", "对手"),
    ("enemy", "仇敌"), ("debt", "债主/债务人"), ("secret", "隐瞒的秘密"),
    ("other", "其他"),
]

REL_LABEL = dict(REL_TYPES)


def load():
    if not REL.exists():
        return {"nodes": [], "edges": []}
    try:
        d = json.loads(REL.read_text(encoding="utf-8"))
        d.setdefault("nodes", [])
        d.setdefault("edges", [])
        return d
    except Exception:
        return {"nodes": [], "edges": []}


def save(d):
    REL.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def node_id(label):
    return "n" + str(abs(hash(label)) % 10 ** 9)


def ensure_node(d, label, kind="npc", card_id=""):
    label = (label or "").strip()
    if not label:
        return None
    for n in d["nodes"]:
        if n.get("label") == label:
            if card_id and not n.get("card_id"):
                n["card_id"] = card_id
            return n
    n = {"id": node_id(label), "label": label, "kind": kind, "card_id": card_id,
         "note": "", "x": None, "y": None}
    d["nodes"].append(n)
    return n


def add_edge(d, src, dst, rtype="other", note="", strength=3):
    a = ensure_node(d, src)
    b = ensure_node(d, dst)
    if not a or not b or a["id"] == b["id"]:
        return None
    for e in d["edges"]:
        if e["from"] == a["id"] and e["to"] == b["id"] and e.get("type") == rtype:
            e["note"] = note or e.get("note", "")
            e["strength"] = strength
            return e
    e = {"id": "e" + str(int(time.time() * 1000)) + str(len(d["edges"])),
         "from": a["id"], "to": b["id"], "type": rtype,
         "note": note, "strength": strength}
    d["edges"].append(e)
    return e


def remove_node(d, nid):
    d["nodes"] = [n for n in d["nodes"] if n.get("id") != nid]
    d["edges"] = [e for e in d["edges"] if e.get("from") != nid and e.get("to") != nid]


def remove_edge(d, eid):
    d["edges"] = [e for e in d["edges"] if e.get("id") != eid]


def to_context(d, focus_label=""):
    """渲染成给 KP 的关系摘要，只列和焦点角色相关的，控制 token。"""
    if not d["nodes"]:
        return ""
    idx = {n["id"]: n.get("label", "") for n in d["nodes"]}
    lines = []
    if focus_label:
        fid = None
        for n in d["nodes"]:
            if n.get("label") == focus_label:
                fid = n["id"]
                break
        if fid:
            for e in d["edges"]:
                if e["from"] == fid:
                    tgt = idx.get(e["to"], "?")
                    lab = REL_LABEL.get(e.get("type"), "其他")
                    note = ("（" + e["note"] + "）") if e.get("note") else ""
                    lines.append("- " + focus_label + " → " + tgt + "：" + lab + note)
                elif e["to"] == fid:
                    src = idx.get(e["from"], "?")
                    lab = REL_LABEL.get(e.get("type"), "其他")
                    note = ("（" + e["note"] + "）") if e.get("note") else ""
                    lines.append("- " + src + " → " + focus_label + "：" + lab + note)
    else:
        for e in d["edges"][:30]:
            a = idx.get(e["from"], "?")
            b = idx.get(e["to"], "?")
            lab = REL_LABEL.get(e.get("type"), "其他")
            lines.append("- " + a + " → " + b + "：" + lab)
    if not lines:
        return ""
    return "# 角色关系（写作时必须遵守，不能违背）" + chr(10) + chr(10).join(lines)