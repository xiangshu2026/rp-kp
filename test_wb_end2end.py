# -*- coding: utf-8 -*-
"""完整验收：连续 3 轮真实跑团对话，检查正文 + 状态层 + 摘要。"""
import json, urllib.request, urllib.error, time

def post(url, body, timeout=900):
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

SESS = "_验收_wb"
inputs = [
    "我推开酒馆的门，环视一圈。",
    "我走到哈罗德对面坐下，问他最近灰石堡出了什么事。",
    "我摸了摸腰间的剑柄，压低声音问：断牙部族的人是不是又来了？",
]
for i, text in enumerate(inputs, 1):
    t0 = time.time()
    try:
        o = post("http://127.0.0.1:8760/api/chat", {"session": SESS, "world": "灰石堡", "text": text})
        st = o.get("state") or {}
        print("=== 第 %d 轮 %.1fs" % (i, time.time()-t0))
        print("  正文 %d 字：%s" % (len(o.get("prose") or ""), (o.get("prose") or "")[:100].replace("\n"," ")))
        print("  场景：%s" % st.get("scene","")[:60])
        print("  地点：%s ｜ NPC：%s" % (st.get("location",""), "、".join(st.get("npcs") or []) or "无"))
        print("  线索数：%d ｜ 伏笔数：%d ｜ next：%s" % (
            len(st.get("clues") or []), len(st.get("foreshadow") or []), st.get("next","")[:40]))
    except urllib.error.HTTPError as e:
        print("=== 第 %d 轮 HTTP %s %s" % (i, e.code, e.read().decode("utf-8","replace")[:300]))
    except Exception as e:
        print("=== 第 %d 轮 ERR %s %s" % (i, type(e).__name__, str(e)[:200]))
