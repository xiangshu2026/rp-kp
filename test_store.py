import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import module_store as ms

parts = []
parts.append("# 灰石堡之夜" + chr(10) + chr(10) + "守秘人须知：本模组适合 3-4 名调查员。" * 20)
for i in range(1, 9):
    parts.append("## 第" + str(i) + "幕 场景" + str(i))
    parts.append("这一幕的调查员会在这里遇到线索，需要侦查检定。" * 400)
text = chr(10) + chr(10).join(parts)
print("原文", len(text), "字 =", ms.tok(text), "token")

m = ms.import_text("灰石堡之夜", text, "test")
print("切分", len(m["acts"]), "幕")

for budget in (7000, 5000, 3000):
    ctx, info = ms.build_context(m, 3, budget)
    print("预算", budget, "→ 实际", info["tokens"], "token, 截断=", info["truncated"])

ctx, info = ms.build_context(m, 3, 7000)
print("上下文含目录:", "全部目录" in ctx)
print("含当前幕:", "当前幕" in ctx)
print("含下一幕预告:", "下一幕" in ctx)
print("---前 500 字---")
print(ctx[:500])
assert info["loaded"] == 3, info
assert "全部目录" in ctx and "当前幕" in ctx
assert len(m["acts"]) >= 2
print("ALL PASS")
