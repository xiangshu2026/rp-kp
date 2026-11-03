import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mapdata, map_vision as mv

# 1. 建图 + 房间 + 双向连线
m = mapdata.new_map("古堡一层")
mapdata.add_room(m, "1", "前厅", "石砌大厅，中央有一口枯井。")
mapdata.add_room(m, "2", "走廊", "两侧挂着褪色的画像。")
mapdata.add_room(m, "3", "书房", "书架上落满灰。")
ok = mapdata.link(m, "1", "2", "北")
mapdata.link(m, "2", "3", "东")
print("房间:", len(m["rooms"]), "连线:", ok)
assert len(m["rooms"]) == 3
r1 = m["rooms"][0]; r2 = m["rooms"][1]
assert r1["exits"][0]["to"] == "2" and r1["exits"][0]["dir"] == "北"
assert r2["exits"][0]["to"] == "1" and r2["exits"][0]["dir"] == "南"
print("双向连线反向方位正确")

# 2. 上下文装载
m["current"] = "1"
ctx, info = mapdata.build_context(m)
print("---地图上下文---")
print(ctx)
print("token:", info["tokens"])
assert "当前位置" in ctx and "枯井" in ctx
assert "北 → 走廊" in ctx, ctx

# 3. 视觉 JSON 抠取（模拟模型夹带解释）
fence = chr(96)*3
fake = "好的，我看到了地图。" + chr(10) + fence + "json" + chr(10) + json.dumps({"rooms":[{"id":"1","name":"入口","desc":"门厅","exits":["2"]},{"id":"2","name":"楼梯间","desc":"","exits":["1","3"]}]}, ensure_ascii=False) + chr(10) + fence + chr(10) + "以上。"
data, err = mv.parse_vision_json(fake)
print("解析结果:", len(data["rooms"]) if data else err)
assert data and len(data["rooms"]) == 2

# 4. 无代码块也能抠
fake2 = "这是结果：" + json.dumps({"rooms":[{"id":"A","name":"大厅","exits":[]}]}, ensure_ascii=False) + " 完毕"
d2, e2 = mv.parse_vision_json(fake2)
assert d2 and d2["rooms"][0]["id"] == "A"
print("无代码块也抠出来了")

# 5. 坏 JSON
d3, e3 = mv.parse_vision_json("完全没有 json 的一段话")
assert d3 is None and "没找到合法 JSON" in e3
print("坏 JSON 正确报错")

# 6. 文字描述解析
desc = "1: 前厅，中央有枯井。通往 2、3" + chr(10) + "2: 走廊，挂满画像。通往 1、4" + chr(10) + "3: 书房。通往 1"
td = mv.from_text_desc(desc)
print("文字解析房间:", [(r["id"], [e["to"] for e in r["exits"]]) for r in td["rooms"]])
assert len(td["rooms"]) == 3
assert [e["to"] for e in td["rooms"][0]["exits"]] == ["2", "3"]

# 7. 应用到地图并补反向
m2 = mapdata.new_map("测试")
n = mv.apply_to_map(m2, td)
print("新增房间:", n, "总数:", len(m2["rooms"]))
assert n == 3
r2a = next(r for r in m2["rooms"] if r["id"] == "2")
assert any(e["to"] == "1" for e in r2a["exits"]), r2a
print("反向连线已补")

# 8. 引用不存在的房间会自动建
m3 = mapdata.new_map("x")
mv.apply_to_map(m3, {"rooms": [{"id": "1", "name": "厅", "exits": ["9"]}]})
assert any(r["id"] == "9" for r in m3["rooms"])
print("自动补建缺失房间")
print("ALL PASS")