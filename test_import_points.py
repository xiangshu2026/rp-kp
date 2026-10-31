import sys, json
sys.path.insert(0, r"E:/deepseek工作区/rp-kp-app")
import coc7, skillpoints as sp, card_import as ci

# 1. 导入一张高技能卡
txt = "姓名：玛戈" + chr(10) + "职业：记者" + chr(10) + "力量 45 体质 55 体型 50 敏捷 70" + chr(10) + "外貌 65 智力 80 意志 60 教育 75" + chr(10) + "侦查 85 图书馆使用 80 话术 75 聆听 70"
card, warn = ci.detect_and_import("a.txt", txt)
print("导入标记:", card.get("_imported"), card.get("_import_source"))
assert card["_imported"] is True

# 2. 分析不应判超支
a = sp.analyze(card)
print("imported:", a["imported"], "ok:", a["ok"], "职业点", a["occ_used"], "/", a["occ_total"])
assert a["imported"] is True
assert a["ok"] is True, a["over_cap"]
assert a["occ_used"] == 0 and a["int_used"] == 0, (a["occ_used"], a["int_used"])
assert a["free_used"] > 0
print("技能点没被吞")

# 3. 导入卡改技能不被池子拦
ok, msg = sp.set_points(card, "spot_hidden", free_add=5)
print("导入卡加 5:", ok, msg)
assert ok, msg
assert card["skills"]["spot_hidden"]["value"] == 85 + 5

# 4. 随机卡仍受池子约束
c2 = coc7.random_card("警察")
a2 = sp.analyze(c2)
assert a2["imported"] is False
assert a2["ok"] is True
ok2, msg2 = sp.set_points(c2, "law", occ_add=99)
print("随机卡超池子:", ok2, msg2)
assert ok2 is False
print("ALL PASS")