# -*- coding: utf-8 -*-
"""玩家输入解析：区分【强制指令】/（行动或心理）/ OOC / 普通发言。"""
import re
NL = chr(10)

L_BRACKET = chr(12304)   # 【
R_BRACKET = chr(12305)   # 】
L_PAREN = chr(65288)     # （
R_PAREN = chr(65289)     # ）
L_PAREN2 = "("
R_PAREN2 = ")"


def parse(text):
    """把玩家输入拆成四类片段。

    返回 {segments, has_force, has_ooc, force_texts, ooc_texts}
    segments: [{type, text}]，type 为 force / action / ooc / speech
    """
    text = str(text or "")
    segs = []
    i = 0
    buf = []

    def flush_speech():
        if buf:
            s = "".join(buf).strip()
            if s:
                segs.append({"type": "speech", "text": s})
            buf.clear()

    while i < len(text):
        ch = text[i]
        # 【强制指令】
        if ch == L_BRACKET:
            j = text.find(R_BRACKET, i + 1)
            if j > i:
                flush_speech()
                segs.append({"type": "force", "text": text[i + 1:j].strip()})
                i = j + 1
                continue
        # （行动或心理）
        if ch == L_PAREN or ch == L_PAREN2:
            close = R_PAREN if ch == L_PAREN else R_PAREN2
            j = text.find(close, i + 1)
            if j > i:
                flush_speech()
                segs.append({"type": "action", "text": text[i + 1:j].strip()})
                i = j + 1
                continue
        buf.append(ch)
        i += 1
    flush_speech()

    # OOC 标记：整段以 OOC / ooc / 出戏 开头，或含 (OOC:...)/【OOC】
    ooc_texts = []
    final = []
    for s in segs:
        low = s["text"].lower()
        if s["type"] == "speech" and (low.startswith("ooc") or low.startswith("出戏")
                                     or low.startswith("场外")):
            s = {"type": "ooc", "text": s["text"]}
        final.append(s)
        if s["type"] == "ooc":
            ooc_texts.append(s["text"])

    force_texts = [s["text"] for s in final if s["type"] == "force"]
    return {
        "segments": final,
        "has_force": bool(force_texts),
        "has_ooc": bool(ooc_texts),
        "force_texts": force_texts,
        "ooc_texts": ooc_texts,
    }


def render_for_prompt(text, parsed=None):
    """把玩家输入重排成带标注的文本，喂给 KP。

    强制指令放最前面并标【绝对执行】，行动/心理次之，说话最后。
    """
    p = parsed or parse(text)
    segs = p["segments"]
    if not segs:
        return ""
    forces = [s["text"] for s in segs if s["type"] == "force"]
    actions = [s["text"] for s in segs if s["type"] == "action"]
    speeches = [s["text"] for s in segs if s["type"] == "speech"]
    oocs = [s["text"] for s in segs if s["type"] == "ooc"]

    out = []
    if forces:
        out.append("【玩家给出的强制指令 —— 必须无条件执行，不得拒绝、不得打折】")
        for f in forces:
            out.append("  - " + f)
        out.append("")
    if oocs:
        out.append("【场外发言 —— 玩家在和你商量，不要写进正文】")
        for o in oocs:
            out.append("  " + o)
        out.append("")
    if actions:
        out.append("【玩家的行动 / 心理】")
        for a in actions:
            out.append("  " + a)
        out.append("")
    if speeches:
        out.append("【玩家说出口的话】")
        for s in speeches:
            out.append("  「" + s + "」")
        out.append("")
    return NL.join(out).strip()


def force_instruction_block():
    """这段会拼进系统提示词，教模型怎么读这四种标记。"""
    return NL.join([
        "## 玩家输入的四种标记（必须严格区分）",
        "",
        "1. **【方括号】里的内容是强制指令**。玩家在下命令，不是提议。",
        "   - 必须无条件执行，绝对不打折、不质疑、不「然而」。",
        "   - 哪怕它推翻了剧情、违背了设定、让 NPC 死而复生——照做。",
        "   - 执行时把它写进正文，但不要复述「玩家要求」这种元叙述。",
        "",
        "2. **（圆括号）里是玩家的行动或心理活动**。",
        "   - 不是台词，不要写成他说出口的话。",
        "   - 心理活动要写成内心独白或微表情，不要替玩家决定他真正的想法。",
        "",
        "3. **不加任何标记的裸文本** = 玩家说出口的话，或他要自主判断的行动。",
        "   - 当作台词处理，用「」括起来引用，或者顺着他说的意思推进。",
        "",
        "4. **OOC / 出戏 / 场外 开头的内容 = 玩家在和你商量**。",
        "   - 立刻跳出剧情回答他，用正常的对话口吻，不要写成小说。",
        "   - 答完可以问一句「要继续吗」，等他确认再回剧情。",
        "",
        "优先级：强制指令 > 普通发言 > 行动 > OOC 之外的一切。",
        "如果强制指令和模组冲突，**强制指令赢**。",
    ])