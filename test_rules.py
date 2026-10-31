import sys, json
sys.path.insert(0, r"E:/deepseek工作区/rp-kp-app")
import rules

# 1. 属性调整值
assert rules.dnd_modifier(10) == 0
assert rules.dnd_modifier(15) == 2
assert rules.dnd_modifier(8) == -1
assert rules.dnd_modifier(20) == 5
assert rules.dnd_modifier(1) == -5
print("调整值 OK")

# 2. 熟练加值
assert rules.dnd_prof_bonus(1) == 2
assert rules.dnd_prof_bonus(4) == 2
assert rules.dnd_prof_bonus(5) == 3
assert rules.dnd_prof_bonus(9) == 4
assert rules.dnd_prof_bonus(17) == 6
print("熟练加值 OK")

# 3. 派生值
a = {"STR":16,"DEX":14,"CON":15,"INT":10,"WIS":12,"CHA":8}
d = rules.dnd_derive(a, 1, "战士")
print("1级战士:", "HP", d["HP_max"], "AC", d["AC"], "先攻", d["init"], "被动察觉", d["passive_perception"])
assert d["HP_max"] == 10 + 2, d["HP_max"]
assert d["AC"] == 12
assert d["init"] == 2
assert d["saves"]["STR"] == 3 + 2
assert d["saves"]["DEX"] == 2

d5 = rules.dnd_derive(a, 5, "战士")
print("5级战士 HP:", d5["HP_max"], "熟练 +" + str(d5["prof"]))
assert d5["prof"] == 3
assert d5["HP_max"] > d["HP_max"]

# 4. 随机卡
c = rules.dnd_random_card("法师", 3)
print("随机法师:", c["name"], c["race"], c["class"], c["level"], "级 HP", c["hp"], "AC", c["ac"])
assert c["system"] == "dnd5e"
assert c["class"] == "法师" and c["level"] == 3
assert c["attrs"]["INT"] == 15, c["attrs"]
assert c["hp"] <= c["hp_max"]

# 5. 技能加值
b = rules.dnd_skill_bonus(c, "奥秘")
print("奥秘加值:", b, "(INT +2, 熟练 +2)")
assert b == 2 + 2, b
b2 = rules.dnd_skill_bonus(c, "运动")
assert b2 == 0 or b2 == rules.dnd_modifier(c["attrs"]["STR"]), b2

# 6. 升级
before = c["level"]
r = rules.dnd_level_up(c)
print("升级:", before, "->", r["level"], "HP +" + str(r["hp_gain"]))
assert r["level"] == before + 1
assert r["hp_gain"] >= 1

# 7. COC 技能成长
import coc7
cc = coc7.random_card()
before_vals = {k: v["value"] for k, v in cc["skills"].items() if k in ("spot_hidden","listen","dodge")}
g = rules.coc_growth(cc, ["spot_hidden", "listen", "dodge"])
print("COC 成长:", json.dumps({k: {"old": v["old"], "roll": v["roll"], "gain": v["gain"]} for k, v in g.items()}, ensure_ascii=False))
assert set(g.keys()) == {"spot_hidden", "listen", "dodge"}
for k, v in g.items():
    assert v["new"] == v["old"] + v["gain"]
    assert v["new"] <= 99
    assert v["new"] == cc["skills"][k]["value"]
print("COC 成长写入正确")

# 8. 统一入口
g1 = rules.auto_grow(cc, "coc7", ["listen"])
assert g1["system"] == "coc7"
g2 = rules.auto_grow(c, "dnd5e", ["察觉"])
assert g2["system"] == "dnd5e" and g2["skills"]["察觉"]["used"] == 1
print("auto_grow OK")

# 9. DND 上下文
ctx = rules.dnd_card_context(c)
print("---DND 卡上下文---")
print(ctx)
print("token:", int(len(ctx)*0.72))
print("ALL PASS")