import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import coc7, card_import as ci

# 1. 随机卡
c = coc7.random_card("私人侦探")
print("random:", c["name"], c["occupation"], "HP", c["hp"], "SAN", c["san"], "DB", c["derived"]["DB"])
assert 1 <= c["derived"]["HP_max"] <= 30
assert c["derived"]["SAN_max"] == 99 - c["mythos"]
assert c["derived"]["SAN_start"] == c["derived"]["eff"]["POW"]
print("  技能数:", len(c["skills"]))

# 2. 派生值校验：CON50 SIZ50 -> HP10
d = coc7.derive({"STR":50,"CON":50,"SIZ":50,"DEX":50,"APP":50,"INT":50,"POW":50,"EDU":50}, 25, 0)
print("HP_max", d["HP_max"], "MP_max", d["MP_max"], "SAN_max", d["SAN_max"], "MOV", d["MOV"], "DB", d["DB"])
assert d["HP_max"] == 10 and d["MP_max"] == 10
assert d["SAN_max"] == 99 and d["SAN_start"] == 50
assert d["MOV"] == 8 and d["DB"] == "0"

# 3. 年龄修正 60 岁
d2 = coc7.derive({"STR":60,"CON":60,"SIZ":50,"DEX":60,"APP":60,"INT":60,"POW":60,"EDU":80}, 62, 0)
print("62岁 eff:", d2["eff"], "MOV", d2["MOV"])
assert d2["eff"]["STR"] == 40 and d2["eff"]["EDU"] == 60

# 4. 文本导入
txt = "姓名：玛戈·维尔" + chr(10) + "职业：记者" + chr(10) + "年龄：28" + chr(10) + "力量 45  体质 55  体型 50  敏捷 70" + chr(10) + "外貌 65  智力 80  意志 60  教育 75" + chr(10) + "侦查 65  图书馆使用 70  话术 55" + chr(10) + "HP 10  SAN 60"
card, warn = ci.detect_and_import("a.txt", txt)
print("import:", card["name"], card["occupation"], card["age"], "STR", card["attrs"]["STR"], "侦查", card["skills"]["spot_hidden"]["value"], "warn:", warn)
assert card["attrs"]["STR"] == 45
assert card["skills"]["spot_hidden"]["value"] == 65
assert card["age"] == 28

# 5. JSON 往返
c2 = coc7.random_card()
cid = coc7.save_card(c2)
back = coc7.load_card(cid)
assert back["name"] == c2["name"]
print("json roundtrip OK:", cid)
coc7.delete_card(cid)
assert coc7.load_card(cid) is None

# 6. 上下文压缩
ctx = coc7.card_to_context(c2)
print("card_to_context 字数:", len(ctx), "token:", int(len(ctx)*0.72))
print("ALL PASS")