import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import relations as rl

d = {"nodes": [], "edges": []}
rl.add_edge(d, "艾德", "哈罗德", "mentor", "哈罗德是艾德父亲的老兵", 4)
rl.add_edge(d, "艾德", "贝尔纳", "secret", "贝尔纳知道艾德父亲的死因", 5)
rl.add_edge(d, "哈罗德", "贝尔纳", "rival", "互相看不顺眼", 2)
print("节点:", len(d["nodes"]), "边:", len(d["edges"]))
assert len(d["nodes"]) == 3

# 重复边不重复添加
rl.add_edge(d, "艾德", "哈罗德", "mentor", "改了备注", 5)
assert len(d["edges"]) == 3, len(d["edges"])
print("去重 OK")

# 焦点视图
ctx = rl.to_context(d, "艾德")
print("---焦点---")
print(ctx)
assert "哈罗德" in ctx and "贝尔纳" in ctx

# 自环不建
rl.add_edge(d, "艾德", "艾德", "other")
assert len(d["edges"]) == 3

# 删节点连带删边
nid = d["nodes"][0]["id"]
rl.remove_node(d, nid)
print("删节点后 节点:", len(d["nodes"]), "边:", len(d["edges"]))
assert len(d["edges"]) == 1
print("ALL PASS")