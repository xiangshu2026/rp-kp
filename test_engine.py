import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine

F = chr(96) * 3

# 1. split_state 正常
r = "正文第一段。" + chr(10) + F + "json" + chr(10) + "{\"scene\":\"井底\",\"clues\":[\"地图\"]}" + chr(10) + F + chr(10) + "尾巴"
p, st = engine.split_state(r)
assert p == "正文第一段。" + chr(10) + chr(10) + "尾巴", repr(p)
assert st["scene"] == "井底", st
print("split_state OK")

# 2. split_state 无块
p2, st2 = engine.split_state("纯文本")
assert p2 == "纯文本" and st2 is None
print("split_state-noblock OK")

# 3. split_state 坏 JSON
p3, st3 = engine.split_state("正文" + F + "{坏}" + F)
assert st3 is None, st3
print("split_state-badjson OK")

# 4. merge_state 伏笔去重与递增
old = {"foreshadow":[{"id":"f001","text":"甲","status":"open"}],"clues":[],"hp":{}}
new = {"foreshadow":[{"id":"f001","text":"甲"},{"id":"f001","text":"乙"}],"resolved":["f001"],"clues":["x"]}
m = engine.merge_state(old, new)
assert len(m["foreshadow"]) == 2, m["foreshadow"]
assert m["foreshadow"][0]["status"] == "closed"
assert m["foreshadow"][1]["id"] == "f002"
print("merge OK")

# 5. safe_name
assert engine.safe_name("a/b:c*?") == "a_b_c__", engine.safe_name("a/b:c*?")
assert engine.safe_name("") == "untitled"
print("safe_name OK")

# 6. render_state 含伏笔
txt = engine.render_state(m)
assert "[f002] 乙" in txt, txt
assert "[f001]" not in txt.split("未回收")[1] if "未回收" in txt else True
print("render_state OK")

# 7. assemble 结构
msgs = engine.assemble("SYS", m, "摘要", [{"role":"user","content":"u1"},{"role":"assistant","content":"a1"}], 6)
assert msgs[0]["role"] == "system" and msgs[0]["content"] == "SYS"
assert msgs[-1]["content"] == "a1"
print("assemble OK, msgs=", len(msgs))

print("ALL PASS")