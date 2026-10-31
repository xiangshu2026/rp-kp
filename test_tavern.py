import sys, json, base64, struct, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tavern_card as tc
from PIL import Image

tmp = Path(__file__).resolve().parent / "_t2"
tmp.mkdir(exist_ok=True)

# 1. 造一张真实酒馆 PNG 卡（V2 规范）
card = {
  "spec": "chara_card_v2", "spec_version": "2.0",
  "data": {
    "name": "艾琳·维斯珀",
    "description": "一位来自北方的女猎手。银白色长发，左眼有疤，惯穿深绿皮甲。",
    "personality": "冷静、寡言，但对同伴极其忠诚。讨厌说谎的人。",
    "scenario": "这段不该被导入",
    "first_mes": "这句也不该被导入",
    "mes_example": "这些对话示例不该被导入"
  }
}
payload = base64.b64encode(json.dumps(card, ensure_ascii=False).encode("utf-8"))

# 生成 1x1 PNG 并注入 tEXt
img = Image.new("RGB", (64, 64), (30, 26, 24))
img.save(str(tmp / "base.png"))
raw = (tmp / "base.png").read_bytes()
chunk_data = b"chara" + bytes([0]) + payload
chunk = struct.pack(">I", len(chunk_data)) + b"tEXt" + chunk_data
crc = struct.pack(">I", zlib.crc32(b"tEXt" + chunk_data) & 0xffffffff)
iend = raw.rfind(b"IEND") - 4
out = raw[:iend] + chunk + crc + raw[iend:]
(tmp / "tavern.png").write_bytes(out)
print("造卡完成:", len(out), "字节")

# 2. 解析
obj, err = tc.load_any(tmp / "tavern.png")
print("解析:", "OK" if obj else err)
assert obj, err
p = tc.extract_persona(obj)
print("名字:", p["name"])
print("性格:", p["personality"])
print("外形:", p["appearance"])
print("---合并---")
print(p["merged"])
assert p["name"] == "艾琳·维斯珀"
assert "冷静" in p["personality"]
assert "银白色长发" in p["appearance"]
# 关键：不该带进对话示例与开场白
assert "不该被导入" not in p["merged"], p["merged"]
assert "对话示例" not in p["merged"]
print("已排除 scenario/first_mes/mes_example")

# 3. V1 扁平结构
v1 = {"name": "老猎人", "personality": "暴躁但心软", "description": "身高六尺，独眼。"}
p2 = tc.extract_persona(v1)
print("V1:", p2["name"], "|", p2["merged"])
assert p2["name"] == "老猎人" and "暴躁" in p2["personality"]

# 4. description 里带外形关键词
v1b = {"name": "X", "personality": "温和", "description": "他是商人。" + chr(10) + "外貌：矮胖，戴圆眼镜。" + chr(10) + "背景：来自东方。"}
p3 = tc.extract_persona(v1b)
print("切外形:", p3["appearance"])
assert "矮胖" in p3["appearance"]
assert "来自东方" not in p3["appearance"]

# 5. 非酒馆 PNG
img2 = Image.new("RGB", (32, 32), (10, 10, 10))
img2.save(str(tmp / "plain.png"))
o2, e2 = tc.load_any(tmp / "plain.png")
print("普通PNG:", e2)
assert o2 is None and "没有酒馆角色数据" in e2

# 6. JSON 格式的酒馆卡
(tmp / "c.json").write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
o3, e3 = tc.load_any(tmp / "c.json")
p4 = tc.extract_persona(o3)
assert p4["name"] == "艾琳·维斯珀"
print("JSON 格式 OK")

# 7. iTXt 压缩形式
# keyword NUL flag method language_tag NUL translated_keyword NUL text
itxt_data = (b"chara" + bytes([0]) + bytes([1]) + bytes([0]) + bytes([0])
             + bytes([0]) + zlib.compress(json.dumps(card, ensure_ascii=False).encode()))
chunk2 = struct.pack(">I", len(itxt_data)) + b"iTXt" + itxt_data
crc2 = struct.pack(">I", zlib.crc32(b"iTXt" + itxt_data) & 0xffffffff)
raw2 = (tmp / "base.png").read_bytes()
iend2 = raw2.rfind(b"IEND") - 4
(tmp / "itxt.png").write_bytes(raw2[:iend2] + chunk2 + crc2 + raw2[iend2:])
o4, e4 = tc.load_any(tmp / "itxt.png")
print("iTXt:", "OK" if o4 else e4)
assert o4, e4
print("ALL PASS")