import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import coc7, skillpoints as sp

# 1. 职业点公式
attrs = {"STR":50,"CON":50,"SIZ":50,"DEX":60,"APP":50,"INT":70,"POW":50,"EDU":80}
t, f = sp.occupation_points("医生", attrs)
print("医生职业点:", t, "=", f)
assert t == 80*4 and f == "EDU×4"

t2, f2 = sp.occupation_points("警察", attrs)
print("警察职业点:", t2, "=", f2)
assert t2 == 80*2 + 60*2

# 2. 兴趣点
assert sp.interest_points(attrs) == 140
print("兴趣点:", sp.interest_points(attrs))

# 3. 空卡分析
c = coc7.blank_card("测试")
c["attrs"] = attrs
c["occupation"] = "医生"
c["derived"] = coc7.derive(attrs, 25, 0)
a = sp.analyze(c)
print("职业点池:", a["occ_total"], "已用:", a["occ_used"], "剩余:", a["occ_left"])
print("兴趣点池:", a["int_total"], "已用:", a["int_used"], "剩余:", a["int_left"])
assert a["occ_total"] == 320
assert a["int_total"] == 140
assert a["occ_used"] == 0 and a["int_used"] == 0
assert a["ok"] is True

# 4. 加点：职业技能用职业点
ok, msg = sp.set_points(c, "medicine", occ_add=60)
print("医学 +60 职业点:", ok, msg)
assert ok, msg
assert c["skills"]["medicine"]["value"] == 1 + 60
a2 = sp.analyze(c)
assert a2["occ_used"] == 60 and a2["occ_left"] == 260

# 5. 超池子拒绝
ok2, msg2 = sp.set_points(c, "medicine", occ_add=999)
print("超职业点:", ok2, msg2)
assert ok2 is False, msg2
assert ("上限" in msg2) or ("职业点不够" in msg2), msg2

# 6. 超单项上限拒绝
c2 = coc7.blank_card("t2")
c2["attrs"] = attrs
c2["occupation"] = "医生"
ok3, msg3 = sp.set_points(c2, "library_use", int_add=60)
print("图书馆 20+60=80 超上限70:", ok3, msg3)
assert ok3 is False and "上限" in msg3

# 7. 兴趣点加点（非职业技能）
ok4, msg4 = sp.set_points(c, "stealth", int_add=30)
print("潜行 +30 兴趣:", ok4, msg4)
assert ok4, msg4
a3 = sp.analyze(c)
assert a3["int_used"] == 30

# 8. 单纯加点不算成长
ok5, msg5 = sp.set_points(c, "listen", free_add=20)
print("聆听 +20 自由:", ok5, msg5)
assert ok5
a4 = sp.analyze(c)
assert a4["free_used"] == 20
assert a4["occ_used"] == 60 and a4["int_used"] == 30

# 9. 自动填职业点
c3 = coc7.blank_card("t3")
c3["attrs"] = attrs
c3["occupation"] = "医生"
rep = sp.auto_fill_occ(c3)
print("自动填:", [(f["name"], f["add"]) for f in rep["filled"]])
print("剩余职业点:", rep["left"])
assert len(rep["filled"]) > 0
a5 = sp.analyze(c3)
assert a5["occ_used"] <= a5["occ_total"]
print("自动填后 ok:", a5["ok"], "剩余:", a5["occ_left"])

# 10. 换职业重算
c3["occupation"] = "流浪汉"
a6 = sp.analyze(c3)
print("换流浪汉后职业点:", a6["occ_total"], "已用:", a6["occ_used"], "超了:", a6["ok"] is False)
assert a6["occ_total"] == 80*2 + 60*2
print("ALL PASS")