# -*- coding: utf-8 -*-
"""骰子引擎：NdM+K 表达式，COC(d100) 与 DND(d20) 两种判定。"""
import random, re
NL = chr(10)

DICE_RE = re.compile("\\s*(\\d*)\\s*[dD]\\s*(\\d+)\\s*(?:([+-])\\s*(\\d+))?\\s*$")


def roll_expr(expr, rng=None):
    """掷 NdM+K，返回 rolls / mod / total / detail。"""
    rng = rng or random
    m = DICE_RE.match(str(expr))
    if not m:
        raise ValueError("看不懂的骰子表达式：" + str(expr) + "（写法如 1d100、2d6+3）")
    n = int(m.group(1) or 1)
    faces = int(m.group(2))
    sign = m.group(3)
    mod = int(m.group(4) or 0)
    if sign == "-":
        mod = -mod
    if n < 1 or n > 100:
        raise ValueError("骰子个数要在 1~100 之间")
    if faces < 2 or faces > 1000:
        raise ValueError("骰子面数要在 2~1000 之间")
    rolls = [rng.randint(1, faces) for _ in range(n)]
    total = sum(rolls) + mod
    detail = " + ".join(str(x) for x in rolls)
    if mod:
        detail += (" + " if mod > 0 else " - ") + str(abs(mod))
    return {"expr": str(expr).strip(), "rolls": rolls, "faces": faces,
            "mod": mod, "total": total, "detail": detail}


def coc_grade(roll, skill):
    """房规：01-05 大成功，<=技能/5 极难，<=技能/2 困难，<=技能 普通，96-100 大失败。"""
    skill = int(skill or 0)
    if roll <= 5:
        return "大成功"
    if roll >= 96:
        return "大失败"
    if skill <= 0:
        return "失败"
    if roll <= skill // 5:
        return "极难成功"
    if roll <= skill // 2:
        return "困难成功"
    if roll <= skill:
        return "普通成功"
    return "失败"


def coc_check(skill, label="", bonus=0, penalty=0):
    """COC 检定。bonus/penalty 为奖励/惩罚骰个数。"""
    ones = random.randint(0, 9)
    tens_list = [random.randint(0, 9) for _ in range(1 + int(bonus) + int(penalty))]
    pool = tens_list[:1 + int(bonus)]
    pen = tens_list[1 + int(bonus):]
    tens = min(pool) if pool else 0
    if pen:
        tens = max([tens] + pen)
    roll = tens * 10 + ones
    if roll == 0:
        roll = 100
    grade = coc_grade(roll, skill)
    ok = grade in ("普通成功", "困难成功", "极难成功", "大成功")
    return {"system": "coc", "label": label, "roll": roll, "skill": int(skill or 0),
            "grade": grade, "success": ok, "tens_rolls": tens_list, "ones": ones,
            "detail": "d100=" + str(roll) + " vs 技能 " + str(skill or 0)}


def dnd_check(modifier, dc, label="", advantage=False, disadvantage=False):
    """DND 5e 检定：d20 + 调整值 vs DC。"""
    times = 1
    mode = "普通"
    if advantage and not disadvantage:
        times = 2
        mode = "优势"
    elif disadvantage and not advantage:
        times = 2
        mode = "劣势"
    elif advantage and disadvantage:
        mode = "优势与劣势抵消"
    rolls = [random.randint(1, 20) for _ in range(times)]
    if times == 2:
        nat = max(rolls) if (advantage and not disadvantage) else min(rolls)
    else:
        nat = rolls[0]
    mod = int(modifier or 0)
    dcv = int(dc or 10)
    total = nat + mod
    crit = "大成功" if nat == 20 else ("大失败" if nat == 1 else "")
    if crit == "大成功":
        ok = True
    elif crit == "大失败":
        ok = False
    else:
        ok = total >= dcv
    return {"system": "dnd", "label": label, "nat": nat, "rolls": rolls,
            "modifier": mod, "dc": dcv, "total": total, "mode": mode,
            "crit": crit, "success": ok,
            "detail": "d20=" + str(nat) + " " + ("+" if mod >= 0 else "") + str(mod) +
                      " = " + str(total) + " vs DC " + str(dcv)}


def roll_damage(expr, crit=False):
    """伤害骰。crit=True 时骰子数翻倍。"""
    r = roll_expr(expr)
    if not crit:
        return r
    n2 = len(r["rolls"]) * 2
    s = str(n2) + "d" + str(r["faces"])
    if r["mod"] > 0:
        s += "+" + str(r["mod"])
    elif r["mod"] < 0:
        s += "-" + str(-r["mod"])
    doubled = roll_expr(s)
    doubled["crit"] = True
    return doubled