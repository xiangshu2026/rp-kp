# -*- coding: utf-8 -*-
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
    """识别标题行。返回 (标题文本, 层级) 或 None。

    层级规则：markdown 标题按 # 数量（1~3）；非 markdown 的编号式标题
    （第X幕 / SCENE / ACT / Chapter / 【】）一律视为幕级 = 2。
    """
    s = line.strip()
    if not s or len(s) > 60:
        return None
    # markdown 标题优先，能拿到真实层级
    m = re.match(r"^(#{1,6})\s*(.+)$", s)
    if m:
        t = m.group(2).strip()
        if 2 <= len(t) <= 50:
            return t, len(m.group(1))
        return None
    for pat in HEAD_PATTERNS:
        m = pat.match(s)
        if m:
            t = (m.group(1) if m.groups() else s).strip()
            t = t.lstrip("#").strip()
            if 2 <= len(t) <= 50:
                return t, 2
    return None


def split_module(text):
    """按标题切分。返回 [{title, level, body, chars}]，首段无标题的归为「序」。"""
    lines = text.splitlines()
    sections = []
    cur_title = "序"
    cur_level = 2
    cur_body = []
    for ln in lines:
        h = is_head(ln)
        if h:
            title, level = h
            if cur_body and any(x.strip() for x in cur_body):
                sections.append({"title": cur_title, "level": cur_level,
                                 "body": NL.join(cur_body).strip()})
            cur_title = title
            cur_level = level
            cur_body = []
        else:
            cur_body.append(ln)
    if any(x.strip() for x in cur_body):
        sections.append({"title": cur_title, "level": cur_level,
                         "body": NL.join(cur_body).strip()})

    out = []
    for s in sections:
        if len(s["body"]) < 30 and s["title"] == "序":
            continue
        s["chars"] = len(s["body"])
        out.append(s)
    return out


def merge_small(sections, min_chars=200, keep_min=3):
    """把「子级」小节合并进上一节，**幕级标题永远独立**。

    2026-11-01 修：旧版只按字数（<200）合并，不看标题层级，
    导致「## 第一幕」「## 第二幕」这种短幕被整段吞进上一幕，
    玩家会发现剧情跳幕、模组内容消失。

    新规则：
      · 先算出全篇最浅的标题层级 = 幕级基准 base（# 一级标题除外，
        那是文档大标题，不算幕）
      · 比 base 更深的是子级 → 合并进上一节
      · 等于 base 的是幕级 → 独立成幕，无论多短
    """
    if not sections:
        return []
    # 一级标题（# 文档标题）不参与基准计算
    levels = [s.get("level", 2) for s in sections if s.get("level", 2) > 1]
    base = min(levels) if levels else 2

    out = []
    for s in sections:
        lv = s.get("level", base)
        if out and lv > base:
            # 子级：合并进上一节，保留小标题作为分隔
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