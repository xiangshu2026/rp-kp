import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import teammates as tm, coc7

# 先清空，避免残留数据干扰
for _x in tm.load_all():
    tm.delete(_x['id'])

a = tm.blank("哈罗德")
a["role"] = "独臂副官"
a["persona"] = "话少，说话像钉子"
a["enabled"] = True
tm.upsert(a)
b = tm.blank("贝尔纳")
b["provider"] = "cloud"
b["api_base"] = "https://api.deepseek.com/v1"
b["api_key"] = "YOUR_API_KEY_HERE"
tm.upsert(b)
items = tm.load_all()
print("队友数:", len(items))

pv = tm.public_view(items[1])
print("脱敏:", pv["api_key_masked"], "| has_key:", pv["has_key"], "| 明文key字段:", repr(pv["api_key"]))
assert pv["api_key"] == "" and pv["has_key"] is True

# 消息构造
card = coc7.random_card("记者")
msgs = tm.build_teammate_messages(items[0], card, "灰石堡城头，狼烟起", [
    {"role":"user","content":"我要下井。"},
    {"role":"assistant","content":"井口黑得像张开的嘴。"}
])
print("消息数:", len(msgs), "| system 字数:", len(msgs[0]["content"]))
assert "哈罗德" in msgs[0]["content"]
assert "独臂副官" in msgs[0]["content"]
assert "我要下井" in msgs[1]["content"]
assert "世界状态" not in msgs[1]["content"]

print("active:", [x["name"] for x in tm.active_teammates()])

# 云端缺 key 的报错
try:
    tm.call_cloud({"api_base":"https://x/v1","api_key":"","model":"m"}, [])
except ValueError as e:
    print("缺key报错:", e)

# 清理
for x in tm.load_all():
    tm.delete(x["id"])
print("ALL PASS")