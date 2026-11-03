import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import module_parser as mp

short = "# 测试模组" + chr(10) + chr(10) + "## 第一幕 雨夜" + chr(10) + "调查员抵达宅邸。门开着。" + chr(10) + chr(10) + "## 第二幕 地下室" + chr(10) + "楼梯向下延伸。" + chr(10) + chr(10) + "## 第三幕 真相" + chr(10) + "尽头是一面镜子。"
s = mp.merge_small(mp.split_module(short))
print("短模组幕数:", len(s), [x["title"] for x in s])
assert len(s) >= 3, [x["title"] for x in s]

long = "# 长模组" + chr(10)
for i in range(1, 6):
    long += chr(10) + "## 第" + str(i) + "幕 场景" + str(i) + chr(10) + ("内容内容内容。" * 100)
    long += chr(10) + "### 小节" + chr(10) + "短小节"
s2 = mp.merge_small(mp.split_module(long))
print("长模组幕数:", len(s2), [x["title"] for x in s2][:8])
assert len(s2) >= 5, len(s2)
print("ALL PASS")