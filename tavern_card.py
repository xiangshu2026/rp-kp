# -*- coding: utf-8 -*-
# 跑团 KP · 本地 COC 7th / DND 5e 桌面跑团工具
# https://github.com/xiangshu2026/rp-kp
"""酒馆(SillyTavern)角色卡：只取性格与外形。"""
import base64, json, struct, zlib
from pathlib import Path
NL = chr(10)
PNG_MAGIC = b'\x89PNG'
NUL = b'\x00'
ONE = b'\x01'


def read_png_chara(path):
    try:
        raw = Path(path).read_bytes()
    except Exception as e:
        return None, "读文件失败：" + str(e)[:80]
    if not raw.startswith(PNG_MAGIC):
        return None, "不是 PNG 文件"
    pos = 8
    found = []
    while pos + 8 <= len(raw):
        try:
            length = struct.unpack(">I", raw[pos:pos + 4])[0]
            ctype = raw[pos + 4:pos + 8]
        except Exception:
            break
        data = raw[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"tEXt":
            k, sep, v = data.partition(NUL)
            key = k.decode("latin-1", "ignore")
            if sep and key in ("chara", "ccv3"):
                found.append((key, v))
        elif ctype == b"iTXt":
            # 结构：keyword NUL compression_flag compression_method
            #       language_tag NUL translated_keyword NUL text
            p1 = data.find(NUL)
            if p1 > 0:
                key = data[:p1].decode("latin-1", "ignore")
                rest = data[p1 + 1:]
                if len(rest) >= 2:
                    comp_flag = rest[0:1]
                    rest2 = rest[2:]           # 跳过 flag + method
                    p2 = rest2.find(NUL)       # language_tag 结束
                    rest3 = rest2[p2 + 1:] if p2 >= 0 else rest2
                    p3 = rest3.find(NUL)       # translated_keyword 结束
                    body = rest3[p3 + 1:] if p3 >= 0 else rest3
                    if comp_flag == ONE:
                        try:
                            body = zlib.decompress(body)
                        except Exception:
                            pass
                    if key in ("chara", "ccv3"):
                        found.append((key, body))
        if ctype == b"IEND":
            break
    if not found:
        return None, "这张 PNG 里没有酒馆角色数据（不是酒馆导出的卡）"
    found.sort(key=lambda x: 0 if x[0] == "chara" else 1)
    for key, val in found:
        obj, err = decode_payload(val)
        if obj:
            return obj, None
    return None, "chara 数据解不出来"


def decode_payload(val):
    if isinstance(val, bytes):
        s = ""
        for enc in ("utf-8", "latin-1"):
            try:
                s = val.decode(enc)
                break
            except Exception:
                continue
    else:
        s = str(val)
    s = s.strip()
    try:
        raw = base64.b64decode(s)
        obj = json.loads(raw.decode("utf-8"))
        if isinstance(obj, dict):
            return obj, None
    except Exception:
        pass
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj, None
    except Exception:
        pass
    return None, "不是合法 JSON"


def read_json_card(path):
    try:
        raw = Path(path).read_text(encoding="utf-8-sig")
    except Exception as e:
        return None, "读文件失败：" + str(e)[:80]
    try:
        obj = json.loads(raw)
    except Exception as e:
        return None, "JSON 解析失败：" + str(e)[:80]
    if isinstance(obj, dict):
        return obj, None
    return None, "JSON 顶层不是对象"


def normalize(obj):
    if not isinstance(obj, dict):
        return {}
    if isinstance(obj.get("data"), dict):
        return obj["data"]
    return obj


APPEAR_KEYS = ["外貌", "外形", "长相", "容貌", "体型", "身高", "发色", "瞳色",
               "长发", "短发", "头发", "发丝", "辫", "疤痕", "伤疤", "眼睛", "眼眸",
               "皮肤", "肤色", "身材", "穿", "披", "戴", "甲", "袍", "靴", "斗篷",
               "appearance", "looks", "hair", "eyes", "skin", "tall", "wears"]


def clean_text(t):
    """去掉酒馆卡里常见的格式噪音：残留括号、字段前缀、多余空白。"""
    import re
    if not t:
        return ""
    s = str(t)
    s = s.replace(chr(13), "")
    # 去掉开头的 "Appearance:" / "外貌：" 这类字段名
    s = re.sub(r"^" + chr(92) + "s*(appearance|looks|外貌|外形|长相|容貌)" + chr(92) + "s*[:" + chr(65306) + "]" + chr(92) + "s*",
               "", s, flags=re.I)
    # 去掉整段最外层包裹的括号
    s = s.strip()
    while s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    # 去掉行首孤立的右括号/左括号残渣
    lines = []
    for ln in s.split(NL):
        x = ln.strip()
        if x in (")", "(", "（", "）"):
            continue
        x = re.sub(r"^[" + chr(65288) + chr(65289) + r"()]" + chr(92) + "s*", "", x)
        x = re.sub(chr(92) + "s*[" + chr(65288) + chr(65289) + r"()]$", "", x)
        if x:
            lines.append(x)
    s = NL.join(lines)
    # 压掉多余空行与空格
    s = re.sub(r"[  ]{2,}", " ", s)
    s = re.sub(r"(" + NL + r"){2,}", NL, s)
    return s.strip()


def split_appearance(desc):
    """按句子切，留下命中外形关键词的句子。"""
    import re
    text = desc.replace(chr(13), "")
    sents = re.split("(?<=[" + chr(12290) + chr(65281) + chr(65311) + ".!?" + chr(59) + "])", text)
    hit = []
    for s in sents:
        s = s.strip()
        if not s:
            continue
        low = s.lower()
        if any(k.lower() in low for k in APPEAR_KEYS):
            hit.append(s)
    return clean_text("".join(hit[:8]))

def extract_persona(obj):
    d = normalize(obj)
    name = str(d.get("name") or "").strip()
    personality = str(d.get("personality") or "").strip()
    desc = str(d.get("description") or "").strip()
    appearance = str(d.get("appearance") or "").strip()
    looks = appearance
    if not looks and desc:
        looks = split_appearance(desc)
    # 有些卡把外形写进 personality，这里做一次纠正
    if personality and looks and personality.strip() == looks.strip():
        personality = ""
    if personality and len(personality) > 200 and not looks:
        # 性格字段过长且像外形描写，挪去外形
        looks = clean_text(personality)
        personality = ""
    personality = clean_text(personality)
    looks = clean_text(looks)
    parts = []
    if personality:
        parts.append("性格：" + personality)
    if looks:
        parts.append("外形：" + looks)
    merged = NL.join(parts)
    return {"name": name, "personality": personality, "appearance": looks,
            "merged": merged, "has_any": bool(merged)}


def load_any(path):
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".png":
        return read_png_chara(p)
    if ext == ".json":
        return read_json_card(p)
    try:
        if p.read_bytes()[:8].startswith(PNG_MAGIC):
            return read_png_chara(p)
    except Exception:
        pass
    return read_json_card(p)