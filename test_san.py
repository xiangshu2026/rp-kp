import sys
sys.path.insert(0, r"E:/deepseek工作区/rp-kp-app")
import coc7

base_attrs = {"STR":50,"CON":50,"SIZ":50,"DEX":50,"APP":50,"INT":50,"POW":60,"EDU":70}

# 1. 神话 0：初始 60，上限 99
d = coc7.derive(base_attrs, 25, 0)
print("神话0 -> 初始", d["SAN_start"], "当前", d["SAN"], "上限", d["SAN_max"])
assert d["SAN_start"] == 60
assert d["SAN_max"] == 99, d["SAN_max"]
assert d["SAN"] == 60

# 2. 神话 20：上限 79，初始仍 60
d2 = coc7.derive(base_attrs, 25, 20)
print("神话20 -> 初始", d2["SAN_start"], "当前", d2["SAN"], "上限", d2["SAN_max"])
assert d2["SAN_max"] == 79, d2["SAN_max"]
assert d2["SAN"] == 60

# 3. 神话 50：上限 49，初始被压到 49
d3 = coc7.derive(base_attrs, 25, 50)
print("神话50 -> 初始", d3["SAN_start"], "当前", d3["SAN"], "上限", d3["SAN_max"])
assert d3["SAN_max"] == 49
assert d3["SAN"] == 49, d3["SAN"]

# 4. 神话 99：上限 0
d4 = coc7.derive(base_attrs, 25, 99)
print("神话99 -> 上限", d4["SAN_max"], "当前", d4["SAN"])
assert d4["SAN_max"] == 0 and d4["SAN"] == 0

# 5. 年龄不影响 POW/SAN
d5 = coc7.derive(base_attrs, 70, 0)
print("70岁 -> POW", d5["eff"]["POW"], "上限", d5["SAN_max"])
assert d5["eff"]["POW"] == 60 and d5["SAN_max"] == 99

# 6. 随机卡不超上限
c = coc7.random_card()
assert c["san"] <= c["derived"]["SAN_max"], (c["san"], c["derived"]["SAN_max"])
assert c["derived"]["SAN_max"] == 99
print("随机卡 SAN:", c["san"], "/", c["derived"]["SAN_max"])

# 7. recalc 夹紧
c["san"] = 150
coc7.recalc(c)
assert c["san"] <= 99, c["san"]
print("recalc 后 SAN:", c["san"])
print("ALL PASS")