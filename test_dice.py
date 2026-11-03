import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dice

# 1. 基础表达式
r = dice.roll_expr("1d100")
print("1d100:", r["total"], r["detail"])
assert 1 <= r["total"] <= 100 and len(r["rolls"]) == 1

r2 = dice.roll_expr("2d6+3")
print("2d6+3:", r2["total"], r2["detail"])
assert 6 <= r2["total"] <= 15, r2["total"]
assert r2["mod"] == 3

r3 = dice.roll_expr("3d8-2")
print("3d8-2:", r3["total"], r3["detail"])
assert 1 <= r3["total"] <= 22
assert r3["mod"] == -2

# 2. 缺省个数 = 1
r4 = dice.roll_expr("d20")
assert len(r4["rolls"]) == 1 and 1 <= r4["total"] <= 20
print("d20 缺省:", r4["total"])

# 3. 非法表达式
for bad in ["abc", "1d", "d", "1d1", "0d6"]:
    try:
        dice.roll_expr(bad)
        raise AssertionError("应该报错: " + bad)
    except ValueError:
        pass
print("非法表达式拦截 OK")

# 4. COC 成功等级（用固定骰子）
class Fixed:
    def __init__(self, v): self.v = v
    def randint(self, a, b): return self.v
print("1 vs 50:", dice.coc_grade(1, 50))
assert dice.coc_grade(1, 50) == "大成功"
assert dice.coc_grade(5, 50) == "大成功"
assert dice.coc_grade(6, 50) == "极难成功"
assert dice.coc_grade(10, 50) == "极难成功"
assert dice.coc_grade(11, 50) == "困难成功"
assert dice.coc_grade(25, 50) == "困难成功"
assert dice.coc_grade(26, 50) == "普通成功"
assert dice.coc_grade(50, 50) == "普通成功"
assert dice.coc_grade(51, 50) == "失败"
assert dice.coc_grade(95, 50) == "失败"
assert dice.coc_grade(96, 50) == "大失败"
assert dice.coc_grade(100, 50) == "大失败"
print("COC 成功等级全对")

# 5. COC 检定结构
for _ in range(50):
    c = dice.coc_check(50, "侦查")
    assert 1 <= c["roll"] <= 100
    assert c["system"] == "coc" and c["label"] == "侦查"
print("COC 检定 50 次 OK")

# 6. DND 检定
d = dice.dnd_check(5, 15, "力量")
print("DND:", d["detail"], "| 成功:", d["success"])
assert 1 <= d["nat"] <= 20
assert d["total"] == d["nat"] + 5

# 7. DND 优势取高
hi = [dice.dnd_check(0, 10, advantage=True) for _ in range(30)]
assert all(x["mode"] == "优势" for x in hi)
assert all(x["nat"] == max(x["rolls"]) for x in hi)
print("DND 优势取高 OK")

lo = [dice.dnd_check(0, 10, disadvantage=True) for _ in range(30)]
assert all(x["nat"] == min(x["rolls"]) for x in lo)
print("DND 劣势取低 OK")

# 8. 大成功大失败
nat20 = [x for x in (dice.dnd_check(0, 99) for _ in range(400)) if x["nat"] == 20]
if nat20:
    assert nat20[0]["crit"] == "大成功" and nat20[0]["success"] is True
    print("d20=20 -> 大成功且必定成功 OK")

# 9. 伤害骰重击翻倍
dmg = dice.roll_damage("1d8+2")
crit = dice.roll_damage("1d8+2", crit=True)
print("普通伤害:", dmg["detail"], "| 重击:", crit["detail"])
assert len(crit["rolls"]) == 2 and crit["mod"] == 2
print("ALL PASS")