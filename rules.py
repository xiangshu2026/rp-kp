# -*- coding: utf-8 -*-
# 跑团 KP · 本地 COC 7th / DND 5e 桌面跑团工具
# https://github.com/xiangshu2026/rp-kp
"""规则系统：COC 7th 与 DND 5e 双轨，各自的提示词、判定、角色卡结构。"""
import json, time
from pathlib import Path
NL = chr(10)
ROOT = Path(__file__).parent

SYSTEMS = {
    "coc7": {
        "name": "克苏鲁的呼唤 7版",
        "short": "COC 7e",
        "dice": "d100",
        "attrs": ["STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU"],
        "hp_formula": "(CON+SIZ)/10",
        "san": "POW 起始，上限 99-克苏鲁神话",
    },
    "dnd5e": {
        "name": "龙与地下城 5版",
        "short": "DND 5e",
        "dice": "d20",
        "attrs": ["STR", "DEX", "CON", "INT", "WIS", "CHA"],
        "hp_formula": "职业生命骰 + CON 调整值",
        "san": "无理智值，用 WIS 豁免对抗恐惧",
    },
}


# ---------- DND 5e 数据 ----------
DND_CLASSES = {
    "战士": {"hit": 10, "primary": "STR", "saves": ["STR", "CON"],
             "skills": ["运动", "威吓", "察觉", "生存", "历史"]},
    "法师": {"hit": 6, "primary": "INT", "saves": ["INT", "WIS"],
             "skills": ["奥秘", "历史", "调查", "洞悉", "医药"]},
    "盗贼": {"hit": 8, "primary": "DEX", "saves": ["DEX", "INT"],
             "skills": ["隐匿", "巧手", "察觉", "欺骗", "杂技", "调查"]},
    "牧师": {"hit": 8, "primary": "WIS", "saves": ["WIS", "CHA"],
             "skills": ["宗教", "洞悉", "医药", "说服", "历史"]},
    "游侠": {"hit": 10, "primary": "DEX", "saves": ["STR", "DEX"],
             "skills": ["生存", "察觉", "隐匿", "自然", "驯兽"]},
    "吟游诗人": {"hit": 8, "primary": "CHA", "saves": ["DEX", "CHA"],
             "skills": ["表演", "说服", "欺骗", "洞悉", "历史"]},
    "圣武士": {"hit": 10, "primary": "STR", "saves": ["WIS", "CHA"],
             "skills": ["威吓", "说服", "宗教", "洞悉", "运动"]},
    "野蛮人": {"hit": 12, "primary": "STR", "saves": ["STR", "CON"],
             "skills": ["运动", "威吓", "生存", "察觉", "自然"]},
}

DND_SKILLS = [
    ("运动", "STR"), ("杂技", "DEX"), ("巧手", "DEX"), ("隐匿", "DEX"),
    ("奥秘", "INT"), ("历史", "INT"), ("调查", "INT"), ("自然", "INT"), ("宗教", "INT"),
    ("驯兽", "WIS"), ("洞悉", "WIS"), ("医药", "WIS"), ("察觉", "WIS"), ("生存", "WIS"),
    ("欺骗", "CHA"), ("威吓", "CHA"), ("表演", "CHA"), ("说服", "CHA"),
]

DND_RACES = ["人类", "精灵", "矮人", "半身人", "半精灵", "半兽人", "侏儒", "龙裔", "提夫林"]


def dnd_modifier(score):
    """属性值 -> 调整值。"""
    return (int(score or 10) - 10) // 2


def dnd_prof_bonus(level):
    """熟练加值。"""
    return 2 + max(0, (int(level or 1) - 1) // 4)


def dnd_derive(attrs, level=1, cls="战士", con_bonus_extra=0):
    """DND 派生值：调整值、豁免、先攻、AC、HP、被动察觉。"""
    a = {k: int(attrs.get(k, 10)) for k in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}
    mods = {k: dnd_modifier(v) for k, v in a.items()}
    pb = dnd_prof_bonus(level)
    cd = DND_CLASSES.get(cls, DND_CLASSES["战士"])
    hit_die = cd["hit"]
    hp_max = hit_die + mods["CON"] + (int(level) - 1) * (hit_die // 2 + 1 + mods["CON"])
    hp_max = max(1, hp_max)
    ac = 10 + mods["DEX"]
    saves = {}
    for k in ("STR", "DEX", "CON", "INT", "WIS", "CHA"):
        saves[k] = mods[k] + (pb if k in cd["saves"] else 0)
    return {
        "mods": mods, "prof": pb, "hit_die": hit_die,
        "HP_max": hp_max, "AC": ac,
        "init": mods["DEX"], "saves": saves,
        "passive_perception": 10 + mods["WIS"] + (pb if "察觉" in cd.get("skills", []) else 0),
        "spell_dc": 8 + pb + mods.get(cd["primary"], 0),
    }


def dnd_blank(name="新角色"):
    attrs = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}
    d = dnd_derive(attrs, 1, "战士")
    return {
        "id": "d" + str(int(time.time() * 1000)),
        "system": "dnd5e",
        "name": name, "player": "", "race": "人类", "class": "战士",
        "level": 1, "background": "", "alignment": "",
        "attrs": attrs, "derived": d,
        "hp": d["HP_max"], "hp_max": d["HP_max"], "ac": d["AC"],
        "skills": {n: {"name": n, "attr": at, "prof": False, "bonus": 0} for n, at in DND_SKILLS},
        "equipment": [], "features": "", "spells": "", "notes": "",
        "created": time.time(), "updated": time.time(),
    }


def dnd_recalc(card):
    d = dnd_derive(card.get("attrs", {}), card.get("level", 1), card.get("class", "战士"))
    card["derived"] = d
    card["hp_max"] = d["HP_max"]
    card["ac"] = d["AC"]
    card["hp"] = min(int(card.get("hp") or d["HP_max"]), d["HP_max"])
    return card


def dnd_card_context(card):
    if not card:
        return ""
    a = card.get("attrs", {})
    d = card.get("derived", {})
    mods = d.get("mods", {})
    L2 = ["## 玩家角色：" + str(card.get("name", ""))]
    L2.append("- " + str(card.get("race", "")) + " " + str(card.get("class", "")) +
              " " + str(card.get("level", 1)) + " 级")
    L2.append("- 属性：" + " / ".join(k + " " + str(a.get(k, 10)) +
              "(" + ("+" if mods.get(k, 0) >= 0 else "") + str(mods.get(k, 0)) + ")"
              for k in ("STR", "DEX", "CON", "INT", "WIS", "CHA")))
    L2.append("- HP " + str(card.get("hp")) + "/" + str(card.get("hp_max")) +
              "　AC " + str(card.get("ac")) + "　熟练 +" + str(d.get("prof", 2)))
    if card.get("features"):
        L2.append("- 特性：" + str(card["features"])[:300])
    return NL.join(L2)

def dnd_random_card(cls=None, level=1):
    """随机 DND 角色。标准数组 15/14/13/12/10/8 分配到主属性。"""
    import random
    cls = cls or random.choice(list(DND_CLASSES.keys()))
    cd = DND_CLASSES[cls]
    std = [15, 14, 13, 12, 10, 8]
    order = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    prim = cd["primary"]
    # 主属性拿最高，CON 次高，其余递减
    rest = [k for k in order if k != prim and k != "CON"]
    random.shuffle(rest)
    assign = {prim: std[0], "CON": std[1]}
    for i, k in enumerate(rest):
        assign[k] = std[i + 2]
    card = dnd_blank("新角色")
    card["class"] = cls
    card["level"] = level
    card["race"] = random.choice(DND_RACES)
    card["attrs"] = assign
    first = random.choice(["凯尔", "莉亚", "索林", "薇拉", "格罗姆", "艾拉", "塔林", "妮莎"])
    last = random.choice(["石盾", "夜刃", "晨星", "铁锤", "银溪", "风语"])
    card["name"] = first + "·" + last
    for n in cd["skills"]:
        if n in card["skills"]:
            card["skills"][n]["prof"] = True
    return dnd_recalc(card)


def dnd_skill_bonus(card, skill_name):
    """算某个技能的检定加值。"""
    sk = (card.get("skills") or {}).get(skill_name)
    if not sk:
        return 0
    d = card.get("derived", {})
    mod = d.get("mods", {}).get(sk.get("attr", "STR"), 0)
    pb = d.get("prof", 2)
    return mod + (pb if sk.get("prof") else 0) + int(sk.get("bonus") or 0)


# ---------- 自动成长：跑完后自主更新技能 ----------
def coc_growth(card, used_skills):
    """COC 技能成长：用过的技能各掷一次 d100，超过当前值则 +1d10。
    返回 {skill_key: {old, roll, gain, new}}。"""
    import random
    sk = card.get("skills", {})
    out = {}
    for key in (used_skills or []):
        rec = sk.get(key)
        if not rec:
            continue
        old = int(rec.get("value") or 0)
        if old >= 99:
            continue
        roll = random.randint(1, 100)
        if roll > old or roll >= 96:
            gain = random.randint(1, 10)
            new = min(99, old + gain)
            rec["value"] = new
            out[key] = {"name": rec.get("name", key), "old": old, "roll": roll,
                        "gain": new - old, "new": new}
        else:
            out[key] = {"name": rec.get("name", key), "old": old, "roll": roll,
                        "gain": 0, "new": old}
    return out


def dnd_level_up(card, hp_roll=None):
    """DND 升级：等级 +1，HP 加上 (生命骰/2+1+CON调整)，重算派生值。"""
    import random
    card["level"] = int(card.get("level") or 1) + 1
    d = dnd_derive(card.get("attrs", {}), card["level"], card.get("class", "战士"))
    gain = d["hit_die"] // 2 + 1 + d["mods"].get("CON", 0)
    gain = max(1, gain)
    card["derived"] = d
    card["hp_max"] = d["HP_max"]
    card["hp"] = min(int(card.get("hp") or 0) + gain, d["HP_max"])
    card["ac"] = d["AC"]
    return {"level": card["level"], "hp_gain": gain, "hp_max": d["HP_max"],
            "prof": d["prof"]}


def dnd_skill_growth(card, used_skills):
    """DND 没有技能成长骰。改为：用过的技能累计熟练次数，达阈值时提示可专精。"""
    cnt = card.setdefault("skill_usage", {})
    out = {}
    for n in (used_skills or []):
        cnt[n] = int(cnt.get(n) or 0) + 1
        out[n] = {"name": n, "used": cnt[n],
                  "suggest_expertise": cnt[n] >= 5 and cnt[n] % 5 == 0}
    return out


def auto_grow(card, system, used_skills):
    """统一入口：按系统选成长方式，返回成长报告。"""
    if system == "dnd5e":
        return {"system": "dnd5e", "skills": dnd_skill_growth(card, used_skills)}
    return {"system": "coc7", "skills": coc_growth(card, used_skills)}