# -*- coding: utf-8 -*-
"""压缩语义边界 · 行为测试（2026-10-31）
验证：compress() 前后，长期状态（scene/clues/foreshadow/hp/...）必须完全不变。
不调用真实模型：把 engine.chat 打桩成固定返回，只测状态与裁剪逻辑。
"""
import sys, os, json, shutil, tempfile
sys.path.insert(0, r"E:\deepseek工作区\rp-kp-app")

import engine

# 打桩：不真的调模型
_orig_chat = engine.chat
def fake_chat(msgs, cfg, **kw):
    return {"message": {"content": "【测试摘要】亚瑟在疯狂之馆拿到了黄铜钥匙，玛戈受伤。"}}
engine.chat = fake_chat

# 用临时目录，不碰真实 sessions
tmp = tempfile.mkdtemp(prefix="kptest-")
engine.SESSIONS = __import__("pathlib").Path(tmp)

fails = []
def ck(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  → " + str(detail)) if not cond and detail else ""))
    if not cond: fails.append(name)

print("== 1. 建立会话并灌入 60 轮 ==")
s = engine.Session("test-semantic", "default")
for i in range(30):
    s.append_turn("user", "玩家行动第%d轮" % (i+1))
    s.append_turn("assistant", "KP回应第%d轮" % (i+1))

# 人工设一堆长期状态
s.state = {
    "scene": "疯狂之馆·二楼书房",
    "time": "1921年11月3日 深夜",
    "location": "书房",
    "npcs": ["玛戈", "朱利安"],
    "clues": ["黄铜钥匙", "烧焦的信", "墙上的对称图案"],
    "foreshadow": [
        {"id": "f001", "text": "亡妻戒指的来历", "status": "open"},
        {"id": "f002", "text": "詹姆森的日记缺失页", "status": "open"},
        {"id": "f003", "text": "地下室的嗡嗡声", "status": "closed"},
    ],
    "resolved": ["f003"],
    "hp": {"亚瑟": 11, "玛戈": 8, "朱利安": 9},
    "next": "书房门口",
}
s.save_state()
print("  turns=%d  clues=%d  foreshadow=%d" % (len(s.turns), len(s.state["clues"]), len(s.state["foreshadow"])))

fp_before = engine.state_fingerprint(s.state)
print("  指纹(before) = " + fp_before)

print("== 2. 执行 compress ==")
cfg = {"window": 6, "compress_every": 8}
out = s.compress(cfg)
print("  summary = " + (out or "(None)")[:60])
print("  turns after = %d" % len(s.turns))

print("== 3. 校验长期状态未被改动 ==")
fp_after = engine.state_fingerprint(s.state)
ck("指纹未变", fp_after == fp_before, fp_before + " vs " + fp_after)
ck("scene 未变", s.state["scene"] == "疯狂之馆·二楼书房", s.state["scene"])
ck("time 未变", s.state["time"] == "1921年11月3日 深夜", s.state["time"])
ck("clues 三条都在", len(s.state["clues"]) == 3, s.state["clues"])
ck("foreshadow 三条都在", len(s.state["foreshadow"]) == 3, s.state["foreshadow"])
ck("f001 仍是 open", any(f["id"]=="f001" and f["status"]=="open" for f in s.state["foreshadow"]))
ck("f003 仍是 closed", any(f["id"]=="f003" and f["status"]=="closed" for f in s.state["foreshadow"]))
ck("hp 三人都在", s.state["hp"] == {"亚瑟":11,"玛戈":8,"朱利安":9}, s.state["hp"])
ck("next 未变", s.state["next"] == "书房门口", s.state["next"])

print("== 4. 校验 turns 被裁剪但保留了最近原文 ==")
ck("turns 已裁剪", len(s.turns) < 60, len(s.turns))
ck("至少保留 TURNS_KEEP_MIN 条", len(s.turns) >= engine.TURNS_KEEP_MIN, len(s.turns))
ck("最后一条是第30轮回应", s.turns[-1]["content"] == "KP回应第30轮", s.turns[-1]["content"])

print("== 5. 校验裁剪后文件可重新加载（不丢）==")
s2 = engine.Session("test-semantic", "default")
ck("重载 turns 数一致", len(s2.turns) == len(s.turns), "%d vs %d" % (len(s2.turns), len(s.turns)))
ck("重载 state 一致", engine.state_fingerprint(s2.state) == fp_before, engine.state_fingerprint(s2.state))

print("== 6. 校验 summary 是合并式而非覆盖 ==")
ck("summary 含测试内容", "测试摘要" in (s.summary or ""), s.summary)
ck("摘要提示词要求保留旧事实", "已有摘要里的事实必须全部保留" in engine.SUMMARY_SYS)

# 清理
engine.chat = _orig_chat
shutil.rmtree(tmp, ignore_errors=True)

print("")
print("通过 %d 项，失败 %d 项" % (0 if not fails else 0, len(fails)))
sys.exit(1 if fails else 0)
