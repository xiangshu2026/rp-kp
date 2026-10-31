# -*- coding: utf-8 -*-
"""COC 7th 技能点系统：职业点 / 兴趣点 / 单纯加点，含上下限校验。"""
import coc7
NL = chr(10)

# 单项技能创建上限（房规可调，官方 70）
SKILL_CAP_DEFAULT = 70


def occupation_points(occ_name, attrs):
    """算职业点总数。COC 7th：EDU×2 + 指定属性×2，或 EDU×4。"""
    occ = coc7.OCCUPATIONS.get(occ_name)
    if not occ:
        return 0, ""
    formula = occ.get("points") or [("EDU", 4)]
    total = 0
    parts = []
    for key, mult in formula:
        v = int(attrs.get(key, 0) or 0)
        total += v * mult
        parts.append(key + "×" + str(mult))
    return total, " + ".join(parts)


def interest_points(attrs):
    """兴趣点 = INT × 2。"""
    return int(attrs.get("INT", 0) or 0) * 2


def analyze(card, cap=SKILL_CAP_DEFAULT):
    """分析技能点使用情况。

    返回 {
      occ_total, occ_formula, occ_used, occ_left,
      int_total, int_used, int_left,
      free_used,
      over_cap: [...],
      per_skill: [{key, name, base, occ_add, int_add, free_add, value, cap_ok}]
    }
    """
    attrs = card.get("attrs") or {}
    occ_name = card.get("occupation") or ""
    occ = coc7.OCCUPATIONS.get(occ_name) or {}
    occ_skill_names = set(occ.get("skills") or [])
    occ_total, formula = occupation_points(occ_name, attrs)
    int_total = interest_points(attrs)

    skills = card.get("skills") or {}
    # 导入卡：没有任何加点拆分字段时，说明是从外部导入的成品卡，
    # 不再用点数池校验（否则会误判超支、并吞掉技能点）
    imported = not any(
        (r.get("occ_add") or r.get("int_add") or r.get("free_add"))
        for r in skills.values()
    ) and bool(card.get("_imported") or card.get("_import_source"))
    occ_used = 0
    int_used = 0
    free_used = 0
    over_cap = []
    per = []
    for key, rec in skills.items():
        base = int(rec.get("base") or 0)
        value = int(rec.get("value") or base)
        gained = max(0, value - base)
        name = rec.get("name") or key
        in_occ = name in occ_skill_names
        # 加点归属：职业技能优先算职业点，超出职业点池的部分算兴趣
        occ_add = int(rec.get("occ_add") or 0)
        int_add = int(rec.get("int_add") or 0)
        free_add = int(rec.get("free_add") or 0)
        if occ_add == 0 and int_add == 0 and free_add == 0 and gained > 0:
            if imported:
                # 导入卡：把加点记为"自由加点"，不占任何池子
                free_add = gained
            elif in_occ:
                occ_add = gained
            else:
                int_add = gained
        occ_used += occ_add
        int_used += int_add
        free_used += free_add
        cap_ok = value <= cap or gained == 0
        if not cap_ok:
            over_cap.append({"key": key, "name": name, "value": value})
        per.append({
            "key": key, "name": name, "base": base, "value": value,
            "occ_add": occ_add, "int_add": int_add, "free_add": free_add,
            "in_occ": in_occ, "cap_ok": cap_ok,
        })

    return {
        "imported": imported,
        "occ_name": occ_name,
        "occ_total": occ_total, "occ_formula": formula,
        "occ_used": occ_used, "occ_left": occ_total - occ_used,
        "int_total": int_total,
        "int_used": int_used, "int_left": int_total - int_used,
        "free_used": free_used,
        "over_cap": over_cap,
        "cap": cap,
        "per_skill": per,
        "ok": True if imported else ((occ_total - occ_used) >= 0 and
                                     (int_total - int_used) >= 0 and not over_cap),
    }


def set_points(card, key, occ_add=None, int_add=None, free_add=None, cap=SKILL_CAP_DEFAULT):
    """设置某个技能的三类加点。value = base + occ_add + int_add + free_add。
    返回 (ok, msg)。超上限或超池子时拒绝。
    """
    sk = card.setdefault("skills", {})
    rec = sk.get(key)
    if not rec:
        return False, "技能不存在"
    base = int(rec.get("base") or 0)
    o = int(occ_add if occ_add is not None else rec.get("occ_add") or 0)
    i = int(int_add if int_add is not None else rec.get("int_add") or 0)
    f = int(free_add if free_add is not None else rec.get("free_add") or 0)
    if o < 0 or i < 0 or f < 0:
        return False, "加点不能为负"
    imported_card = bool(card.get("_imported") or card.get("_import_source"))
    if imported_card:
        # 导入卡：原有 value 就是成品值，只在此基础上加减
        old_value = int(rec.get("value") or base)
        old_f = int(rec.get("free_add") or 0)
        if free_add is not None:
            value = old_value - old_f + f
        elif occ_add is not None or int_add is not None:
            value = old_value + (o - int(rec.get("occ_add") or 0)) + (i - int(rec.get("int_add") or 0))
        else:
            value = old_value
    else:
        value = base + o + i + f
    if value > cap and (o + i + f) > 0 and not imported_card:
        return False, "超出单项上限 " + str(cap) + "（当前 " + str(value) + "）"
    # 池子校验
    attrs = card.get("attrs") or {}
    occ_name = card.get("occupation") or ""
    occ_total, _ = occupation_points(occ_name, attrs)
    int_total = interest_points(attrs)
    used_occ = 0
    used_int = 0
    for k2, r2 in sk.items():
        if k2 == key:
            used_occ += o
            used_int += i
        else:
            used_occ += int(r2.get("occ_add") or 0)
            used_int += int(r2.get("int_add") or 0)
    imported = bool(card.get("_imported") or card.get("_import_source"))
    if not imported:
        if used_occ > occ_total:
            return False, "职业点不够（" + str(used_occ) + "/" + str(occ_total) + "）"
        if used_int > int_total:
            return False, "兴趣点不够（" + str(used_int) + "/" + str(int_total) + "）"
    rec["occ_add"] = o
    rec["int_add"] = i
    rec["free_add"] = f
    rec["value"] = value
    return True, ""


def auto_fill_occ(card, cap=SKILL_CAP_DEFAULT):
    """把职业点自动填到职业技能上（优先填到 60~cap）。返回填充报告。"""
    attrs = card.get("attrs") or {}
    occ_name = card.get("occupation") or ""
    occ = coc7.OCCUPATIONS.get(occ_name) or {}
    names = occ.get("skills") or []
    occ_total, _ = occupation_points(occ_name, attrs)
    if not names or occ_total <= 0:
        return {"filled": [], "left": occ_total, "note": "没有职业或没有职业技能组"}
    sk = card.setdefault("skills", {})
    key_by_name = {}
    for k, r in sk.items():
        key_by_name[r.get("name")] = k
    left = occ_total
    filled = []
    target = min(cap, 65)
    for nm in names:
        k = key_by_name.get(nm)
        if not k or left <= 0:
            continue
        rec = sk[k]
        base = int(rec.get("base") or 0)
        cur = int(rec.get("value") or base)
        want = target - cur
        if want <= 0:
            continue
        give = min(want, left)
        rec["occ_add"] = int(rec.get("occ_add") or 0) + give
        rec["value"] = cur + give
        left -= give
        filled.append({"name": nm, "add": give, "value": rec["value"]})
    return {"filled": filled, "left": left}