import sys
sys.path.insert(0, r"E:/deepseek工作区/rp-kp-app")
import module_parser as mp

# 造一个典型长模组：8 幕，每幕 8000 字
parts = []
parts.append("# 灰石堡之夜" + chr(10) + chr(10) + "守秘人须知：本模组适合 3-4 名调查员。" * 30)
for i in range(1, 9):
    parts.append("## 第" + str(i) + "幕 场景标题" + str(i))
    parts.append(("这一幕的调查员会在这里遇到线索，需要侦查检定。" * 400))
text = chr(10) + chr(10).join(parts)
print("原文总字数:", len(text))

secs = mp.split_module(text)
secs = mp.merge_small(secs)
print("切出幕数:", len(secs))
for s in secs:
    print("  -", s["title"], s["chars"], "字")

idx = mp.build_index(secs)
print("索引字数:", len(idx))
print("索引 token 估算:", int(len(idx) * 0.72))
print("单幕 token 估算:", int(max(s["chars"] for s in secs) * 0.72))
print("全文 token 估算:", int(len(text) * 0.72))
assert len(secs) >= 2
assert int(max(s['chars'] for s in secs) * 0.72) < 24576
print('ALL PASS')