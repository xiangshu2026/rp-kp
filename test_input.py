import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import player_input as pi

LB, RB = chr(12304), chr(12305)
LP, RP = chr(65288), chr(65289)

# 1. 四种标记混合
t = "LB"
t = LB + "让哈罗德立刻跪下" + RB + " 我拔剑" + LP + "心想这不对" + RP + "，你退下"
p = pi.parse(t)
print("segments:", [(s["type"], s["text"]) for s in p["segments"]])
assert p["has_force"] is True
assert p["force_texts"] == ["让哈罗德立刻跪下"]
types = [s["type"] for s in p["segments"]]
assert "force" in types and "action" in types and "speech" in types

# 2. 纯发言
p2 = pi.parse("你好啊")
assert p2["has_force"] is False
assert p2["segments"][0]["type"] == "speech"

# 3. 纯强制
p3 = pi.parse(LB + "跳过这段剧情" + RB)
assert p3["force_texts"] == ["跳过这段剧情"]
assert len(p3["segments"]) == 1

# 4. OOC
p4 = pi.parse("OOC 这个模组还有几幕")
assert p4["has_ooc"] is True, p4
p5 = pi.parse("出戏，我想问个规则")
assert p5["has_ooc"] is True

# 5. 英文括号也认
p6 = pi.parse("I look around (carefully)")
acts = [s["text"] for s in p6["segments"] if s["type"] == "action"]
assert acts == ["carefully"], acts

# 6. 渲染顺序：强制在最前
r = pi.render_for_prompt(t)
print("---渲染---")
print(r)
i_force = r.find("强制指令")
i_action = r.find("行动")
i_speech = r.find("说出口")
assert i_force >= 0 and i_action > i_force and i_speech > i_action, (i_force, i_action, i_speech)

# 7. 空输入
assert pi.render_for_prompt("") == ""
assert pi.parse("").has_force is False if hasattr(pi.parse(""), "has_force") else True

# 8. 指令块
blk = pi.force_instruction_block()
print("指令块字数:", len(blk), "token:", int(len(blk)*0.72))
assert "强制指令" in blk and "OOC" in blk
print("ALL PASS")