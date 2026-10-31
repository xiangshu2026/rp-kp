# -*- coding: utf-8 -*-
# 跑团 KP · 本地 COC 7th / DND 5e 桌面跑团工具
# https://github.com/xiangshu2026/rp-kp
"""模组切分器：把长模组切成「幕」，只把当前幕 + 索引喂进上下文。"""
import json, re, time
from pathlib import Path

ROOT = Path(__file__).parent
MODULES = ROOT / "modules"
NL = chr(10)

# 幕标题的识别模式（覆盖中英文常见模组写法）
HEAD_PATTERNS = [
    re.compile(r"^#{1,3}\s*(.+)$"),
    re.compile(r"^(第[一二三四五六七八九十百]+[章节幕部].{0,40})$"),
    re.compile(r"^(场景\s*[0-9一二三四五六七八九十]+[:：].{0,40})$"),
    re.compile(r"^(SCENE\s*[0-9]+[:.].{0,40})$", re.I),
    re.compile(r"^(ACT\s*[0-9IVX]+[:.].{0,40})$", re.I),
    re.compile(r"^(Chapter\s*[0-9]+[:.].{0,40})$", re.I),
    re.compile(r"^(【.{1,30}】)$"),
    re.compile(r"^([A-Z][A-Z 0-9]{3,40})$"),
]


def is_head(line):
    s = line.strip()
    if not s or len(s) > 60:
        return None
    for pat in HEAD_PATTERNS:
        m = pat.match(s)
        if m:
            t = (m.group(1) if m.groups() else s).strip()
            t = t.lstrip("#").strip()
            if 2 <= len(t) <= 50:
                return t
    return None


def split_module(text):
    """按标题切分。返回 [{title, body, chars}]，首段无标题的归为「序」。"""
    lines = text.splitlines()
    sections = []
    cur_title = "序"
    cur_body = []
    for ln in lines:
        h = is_head(ln)
        if h:
            if cur_body and any(x.strip() for x in cur_body):
                sections.append({"title": cur_title, "body": NL.join(cur_body).strip()})
            cur_title = h
            cur_body = []
        else:
            cur_body.append(ln)
    if any(x.strip() for x in cur_body):
        sections.append({"title": cur_title, "body": NL.join(cur_body).strip()})

    out = []
    for s in sections:
        if len(s["body"]) < 30 and s["title"] == "序":
            continue
        s["chars"] = len(s["body"])
        out.append(s)
    return out


def merge_small(sections, min_chars=200, keep_min=3):
    """太碎的段落合并到上一节。

    但保证最终幕数不少于 keep_min（模组本身够长时）——
    否则短模组会被压成一幕，失去分幕的意义。
    """
    if not sections:
        return []
    # 如果总幕数已经不多，直接原样返回，不合并
    if len(sections) <= keep_min:
        return [dict(s) for s in sections]
    out = []
    for idx, s in enumerate(sections):
        if out and s["chars"] < min_chars:
            remaining = len(sections) - idx - 1
            if len(out) + remaining >= keep_min:
                out[-1]["body"] += NL + NL + s["title"] + NL + s["body"]
                out[-1]["chars"] = len(out[-1]["body"])
                continue
        out.append(dict(s))
    return out

def build_index(sections):
    """只给模型看的目录：标题 + 字数 + 一句摘要（摘要由模型后续补）。"""
    lines = ["# 模组目录（共 " + str(len(sections)) + " 幕）"]
    for i, s in enumerate(sections):
        lines.append(str(i + 1) + ". " + s["title"] + "（" + str(s["chars"]) + " 字）")
    return NL.join(lines)