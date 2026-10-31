import sys
sys.path.insert(0, r"E:/deepseek工作区/rp-kp-app")
import tavern_card as tc

# 复现截图里的那张卡（Jolyne）
desc = ("Appearance: (Jolyne is a young woman of above-average height, with a build that sits between slender and athletic, shaped by the hardness of prison life."
        "Her skin is a warm, golden, lightly bronzed tone that contrasts sharply with the colors of her two-toned hair."
        "Her gaze is the first thing that hits: piercing eyes, large, lime green, with a permanent expression somewhere between defiance and vigilance."
        "Her hair is entirely two-toned and organized into two clearly distinct layers: the base layer, which includes the roots and most of the volume, is a dark green."
        ")")
card = {"name": "Jolyne", "description": desc, "personality": ""}
p = tc.extract_persona(card)
print("=== 清洗后的外形 ===")
print(p["appearance"][:400])
print("...")
print()
print("以 ) 开头:", p["appearance"].startswith(")"))
print("含 Appearance:", "Appearance:" in p["appearance"])
print("以 ( 开头:", p["appearance"].startswith("("))
assert not p["appearance"].startswith(")"), "残留右括号"
assert not p["appearance"].startswith("("), "残留左括号"
assert "Appearance:" not in p["appearance"], "残留字段名"
print()
print("=== merged ===")
print(p["merged"][:200])
print("ALL PASS")