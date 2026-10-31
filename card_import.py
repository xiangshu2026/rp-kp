# -*- coding: utf-8 -*-
"""角色卡导入：JSON / 文本解析 / 从任意文本里抽属性。"""
import json, re, time
import coc7
NL = chr(10)
B = chr(92)   # 反斜杠

ATTR_ALIASES = {
    "STR": ["STR", "力量"], "CON": ["CON", "体质"], "SIZ": ["SIZ", "体型"],
    "DEX": ["DEX", "敏捷"], "APP": ["APP", "外貌"], "INT": ["INT", "智力"],
    "POW": ["POW", "意志"], "EDU": ["EDU", "教育", "知识"],
    "LUCK": ["LUCK", "幸运"],
}

DERIVED_ALIASES = {
    "HP": ["HP", "体力", "生命值"], "MP": ["MP", "魔法值"],
    "SAN": ["SAN", "理智值", "理智"],
}

NUM = "[^0-9]{0,14}([0-9]{1,3})"


def _find(text, name, lo, hi):
    pat = re.compile(re.escape(name) + NUM, re.I)
    m = pat.search(text)
    if not m:
        return None
    v = int(m.group(1))
    if lo <= v <= hi:
        return v
    return None


def parse_attrs(text):
    found = {}
    for key, names in ATTR_ALIASES.items():
        for nm in names:
            v = _find(text, nm, 1, 99)
            if v is not None:
                found[key] = v
                break
    return found


def parse_derived(text):
    out = {}
    for key, names in DERIVED_ALIASES.items():
        for nm in names:
            v = _find(text, nm, 0, 999)
            if v is not None:
                out[key] = v
                break
    return out


def parse_skills(text):
    found = {}
    for cn, key, base, cat in coc7.SKILLS:
        v = _find(text, cn, 0, 99)
        if v is not None:
            found[key] = v
    return found


def parse_name(text):
    for lab in ("姓名", "角色名", "调查员", "名字"):
        pat = re.compile(re.escape(lab) + "[" + chr(65306) + ": ]" + B + "s*([^" + B + "n]{1,20})")
        m = pat.search(text)
        if m:
            n = m.group(1).strip(" " + chr(12288) + ":：")
            if n:
                return n
    return ""


def parse_age(text):
    for lab in ("年龄", "年岁"):
        v = _find(text, lab, 1, 120)
        if v is not None:
            return v
    return None


def parse_occupation(text):
    for lab in ("职业", "身份", "职业/身份"):
        pat = re.compile(re.escape(lab) + "[" + chr(65306) + ": ]" + B + "s*([^" + B + "n]{1,20})")
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return ""


def from_text(text, name_hint=""):
    attrs = parse_attrs(text)
    missing = [k for k, _ in coc7.ATTRS if k not in attrs]
    for k in missing:
        attrs[k] = 50
    age = parse_age(text) or 25
    nm = parse_name(text) or name_hint or "导入角色"
    card = coc7.blank_card(nm)
    card["attrs"] = attrs
    card["age"] = age
    card["occupation"] = parse_occupation(text)
    card["derived"] = coc7.derive(attrs, age, 0)

    sk = card["skills"]
    sk["language_own"]["value"] = card["derived"]["eff"]["EDU"]
    sk["dodge"]["value"] = card["derived"]["eff"]["DEX"] // 2
    for key, v in parse_skills(text).items():
        if key in sk:
            sk[key]["value"] = v

    d = parse_derived(text)
    card["hp"] = d.get("HP", card["derived"]["HP_max"])
    card["mp"] = d.get("MP", card["derived"]["MP_max"])
    card["san"] = d.get("SAN", card["derived"]["SAN_max"])
    card["luck"] = attrs.get("LUCK", 50)
    card["_import_missing"] = missing
    card["_imported"] = True
    card["_import_source"] = "text"
    return card


def from_json(text):
    data = json.loads(text)
    if isinstance(data, dict) and "attrs" in data and "skills" in data:
        card = data
        card.setdefault("id", "c" + str(int(time.time() * 1000)))
        card.setdefault("background", {})
        card.setdefault("equipment", [])
        card.setdefault("relations", [])
        card.setdefault("mythos", 0)
        card["_imported"] = True
        card["_import_source"] = "json"
        return coc7.recalc(card)
    return from_text(json.dumps(data, ensure_ascii=False))


def detect_and_import(filename, raw_text):
    low = str(filename).lower()
    if low.endswith(".json"):
        try:
            return from_json(raw_text), None
        except Exception as e:
            return None, "JSON 解析失败：" + str(e)[:100]
    card = from_text(raw_text)
    warn = None
    if card.get("_import_missing"):
        warn = "这些属性没找到，已填 50，请核对：" + "、".join(card["_import_missing"])
    return card, warn