# -*- coding: utf-8 -*-
# 跑团 KP · 本地 COC 7th / DND 5e 桌面跑团工具
# https://github.com/xiangshu2026/rp-kp
"""本地跑团 KP —— 软件入口。只用 Python 标准库。"""
import json, sys, threading, time, webbrowser
import http.server
from urllib.parse import urlparse, parse_qs
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import engine
import coc7
import card_import
import module_store
import module_parser
import doc_import
import teammates
import relations
import dice
import rules
import player_input
import mapdata
import map_vision
import skillpoints
import tavern_card

PORT = 8760
STATIC = ROOT / "static"
NL = chr(10)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path, ctype):
        if not path.exists():
            self._json({"error": "not found"}, 404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        raw = self.rfile.read(n)
        # 容忍 UTF-8 BOM（PowerShell / 某些编辑器会加）
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        p = u.path
        cfg = engine.load_config()

        if p == "/":
            self._file(STATIC / "index.html", "text/html; charset=utf-8")
            return
        if p == "/app.js":
            self._file(STATIC / "app.js", "application/javascript; charset=utf-8")
            return
        if p == "/style.css":
            self._file(STATIC / "style.css", "text/css; charset=utf-8")
            return
        if p == "/api/config":
            self._json(cfg)
            return
        if p == "/api/worlds":
            self._json({"worlds": engine.list_worlds()})
            return
        if p == "/api/world":
            name = (q.get("name") or [""])[0]
            self._json({"name": name,
                         "prompt": engine.read_world(name, "prompt.md"),
                         "worldbook": engine.read_world(name, "worldbook.md"),
                         "characters": engine.read_world(name, "characters.md")})
            return
        if p == "/api/sessions":
            self._json({"sessions": engine.list_sessions()})
            return
        if p == "/api/session":
            name = (q.get("name") or [""])[0]
            s = engine.Session(name, "default")
            self._json({"name": s.name, "world": s.world, "turns": s.turns,
                         "state": s.state, "summary": s.summary,
                         "meta": s.meta,
                         "state_text": engine.render_state(s.state)})
            return
        if p == "/api/status":
            self._json(self._status(cfg))
            return
        if p == "/api/cards":
            self._json({"cards": coc7.list_cards()})
            return
        if p == "/api/card":
            cid = (q.get("id") or [""])[0]
            c = coc7.load_card(cid)
            if not c:
                self._json({"error": "角色卡不存在"}, 404)
                return
            # 旧卡可能用错算法存了 SAN_max，读的时候重算一遍
            c = coc7.recalc(c)
            self._json(c)
            return
        if p == "/api/card_new":
            self._json(coc7.blank_card((q.get("name") or ["新角色"])[0]))
            return
        if p == "/api/card_random":
            self._json(coc7.random_card((q.get("occupation") or [None])[0]))
            return
        if p == "/api/meta":
            self._json({"skills": [{"key": k, "name": n, "base": b, "cat": c}
                                   for n, k, b, c in coc7.SKILLS],
                        "occ_defs": self._occ_defs(),
                        "attrs": [{"key": k, "name": n} for k, n in coc7.ATTRS],
                        "occupations": list(coc7.OCCUPATIONS.keys()),
                        "rel_types": [{"key": k, "name": n} for k, n in relations.REL_TYPES],
                        "cloud_presets": {k: v for k, v in teammates.CLOUD_PRESETS.items()}})
            return
        if p == "/api/modules":
            self._json({"modules": module_store.list_modules()})
            return
        if p == "/api/module":
            mid = (q.get("id") or [""])[0]
            m = module_store.load_module(mid)
            if not m:
                self._json({"error": "模组不存在"}, 404)
                return
            self._json(m)
            return
        if p == "/api/teammates":
            self._json({"teammates": [teammates.public_view(x) for x in teammates.load_all()]})
            return
        if p == "/api/relations":
            self._json(relations.load())
            return
        if p == "/api/systems":
            self._json({"systems": [{"key": k, "name": v["name"], "short": v["short"],
                                     "dice": v["dice"]} for k, v in rules.SYSTEMS.items()],
                        "dnd_classes": {k: {"hit": v["hit"], "primary": v["primary"]}
                                        for k, v in rules.DND_CLASSES.items()},
                        "dnd_skills": [{"name": n, "attr": a} for n, a in rules.DND_SKILLS],
                        "dnd_races": rules.DND_RACES})
            return
        if p == "/api/points":
            cid = (q.get("id") or [""])[0]
            c = coc7.load_card(cid)
            if not c:
                self._json({"error": "角色卡不存在"}, 404)
                return
            cap = int((q.get("cap") or ["70"])[0] or 70)
            self._json(skillpoints.analyze(c, cap))
            return
        if p == "/api/maps":
            self._json({"maps": mapdata.list_maps()})
            return
        if p == "/api/map":
            mid = (q.get("id") or [""])[0]
            m = mapdata.load_map(mid)
            if not m:
                self._json({"error": "地图不存在"}, 404)
                return
            self._json(m)
            return
        if p == "/api/map_image":
            mid = (q.get("id") or [""])[0]
            m = mapdata.load_map(mid)
            if not m or not m.get("image_path"):
                self._json({"error": "没有图片"}, 404)
                return
            pth = Path(m["image_path"])
            if not pth.exists():
                self._json({"error": "图片文件已丢失"}, 404)
                return
            ext = pth.suffix.lower()
            ct = "image/png" if ext == ".png" else ("image/jpeg" if ext in (".jpg", ".jpeg") else "application/octet-stream")
            self._file(pth, ct)
            return
        if p == "/api/vision_models":
            self._json({"models": self._vision_models(cfg)})
            return
        if p == "/api/dnd_new":
            self._json(rules.dnd_blank((q.get("name") or ["新角色"])[0]))
            return
        if p == "/api/dnd_random":
            cls = (q.get("class") or [None])[0]
            lv = int((q.get("level") or ["1"])[0] or 1)
            self._json(rules.dnd_random_card(cls, lv))
            return
        self._json({"error": "unknown"}, 404)

    def _status(self, cfg):
        try:
            import urllib.request
            req = urllib.request.Request(cfg["ollama"] + "/api/tags")
            with urllib.request.urlopen(req, timeout=3) as r:
                tags = json.loads(r.read().decode("utf-8"))
            names = [m["name"] for m in tags.get("models", [])]
            want = cfg["model"]
            ok = want in names or (want + ":latest") in names
            return {"online": True, "models": names, "model_ready": ok}
        except Exception as e:
            return {"online": False, "error": str(e)[:120], "models": [], "model_ready": False}
    def do_POST(self):
        u = urlparse(self.path)
        p = u.path
        cfg = engine.load_config()
        try:
            body = self._body()
        except Exception as e:
            self._json({"error": "bad json: " + str(e)[:80]}, 400)
            return

        if p == "/api/config":
            cfg.update(body)
            engine.save_config(cfg)
            self._json({"ok": True, "config": cfg})
            return

        if p == "/api/world":
            name = body.get("name") or "default"
            engine.write_world(name, "prompt.md", body.get("prompt", ""))
            engine.write_world(name, "worldbook.md", body.get("worldbook", ""))
            engine.write_world(name, "characters.md", body.get("characters", ""))
            self._json({"ok": True, "name": engine.safe_name(name)})
            return

        if p == "/api/card":
            c = body.get("card") or {}
            cid = coc7.save_card(coc7.recalc(c))
            self._json({"ok": True, "id": cid})
            return
        if p == "/api/card_delete":
            ok = coc7.delete_card(body.get("id") or "")
            self._json({"ok": ok})
            return
        if p == "/api/card_import":
            self._card_import(body)
            return
        if p == "/api/module_import":
            self._module_import(body)
            return
        if p == "/api/module_delete":
            ok = module_store.delete_module(body.get("id") or "")
            self._json({"ok": ok})
            return
        if p == "/api/module_act":
            ok = module_store.set_act_summary(body.get("id"), body.get("act") or 1,
                                              body.get("summary") or "")
            self._json({"ok": ok})
            return
        if p == "/api/teammate":
            item = body.get("teammate") or {}
            if not item.get("id"):
                item = dict(teammates.blank(item.get("name") or "新队友"), **item)
            teammates.upsert(item)
            self._json({"ok": True, "teammates": [teammates.public_view(x) for x in teammates.load_all()]})
            return
        if p == "/api/teammate_delete":
            teammates.delete(body.get("id") or "")
            self._json({"ok": True})
            return
        if p == "/api/teammate_test":
            item = body.get("teammate") or {}
            self._json(teammates.test_conn(item, cfg))
            return
        if p == "/api/relations":
            d = body.get("data") or {"nodes": [], "edges": []}
            relations.save(d)
            self._json({"ok": True})
            return
        if p == "/api/map":
            m = body.get("map") or {}
            if not m.get("id"):
                m = mapdata.new_map(m.get("title") or "未命名地图")
            mapdata.save_map(m)
            self._json({"ok": True, "id": m["id"], "map": m})
            return
        if p == "/api/map_delete":
            self._json({"ok": mapdata.delete_map(body.get("id") or "")})
            return
        if p == "/api/map_import":
            self._map_import(cfg, body)
            return
        if p == "/api/points":
            cid = body.get("card_id") or ""
            c = coc7.load_card(cid)
            if not c:
                self._json({"error": "角色卡不存在"}, 404)
                return
            cap = int(body.get("cap") or 70)
            action = body.get("action") or "set"
            if action == "auto_fill":
                rep = skillpoints.auto_fill_occ(c, cap)
                coc7.save_card(c)
                self._json({"ok": True, "report": rep, "analysis": skillpoints.analyze(c, cap)})
                return
            key = body.get("skill") or ""
            ok, msg = skillpoints.set_points(c, key,
                                             body.get("occ_add"),
                                             body.get("int_add"),
                                             body.get("free_add"), cap)
            if not ok:
                self._json({"ok": False, "error": msg}, 400)
                return
            coc7.save_card(c)
            self._json({"ok": True, "analysis": skillpoints.analyze(c, cap), "card": c})
            return
        if p == "/api/tavern_import":
            self._tavern_import(body)
            return
        if p == "/api/occ_custom":
            name = (body.get("name") or "").strip()
            if not name:
                self._json({"error": "职业名不能为空"}, 400)
                return
            pts = body.get("points") or [["EDU", 4]]
            clean = []
            for p in pts:
                if isinstance(p, (list, tuple)) and len(p) == 2:
                    clean.append([str(p[0]).upper(), int(p[1])])
            if not clean:
                self._json({"error": "公式解析失败，写法如 EDU×4 或 EDU×2+DEX×2"}, 400)
                return
            d = self._load_custom_occ()
            d[name] = {"points": clean, "skills": body.get("skills") or [],
                       "credit": body.get("credit") or [0, 0], "custom": True}
            self._save_custom_occ(d)
            self._json({"ok": True, "occupations": self._occ_defs()})
            return
        if p == "/api/roll":
            self._roll(body)
            return
        if p == "/api/grow":
            self._grow(cfg, body)
            return
        if p == "/api/dnd_card":
            c = body.get("card") or {}
            c["system"] = "dnd5e"
            cid = coc7.save_card(rules.dnd_recalc(c))
            self._json({"ok": True, "id": cid})
            return
        if p == "/api/chat":
            self._chat(cfg, body)
            return

        if p == "/api/chat_stream":
            self._chat_stream(cfg, body)
            return

        if p == "/api/audit":
            s = engine.Session(body.get("session") or "default", "default")
            try:
                text = s.audit(cfg)
                self._json({"ok": True, "audit": text or "（无未回收伏笔）"})
            except Exception as e:
                self._json({"error": str(e)[:200]}, 500)
            return

        if p == "/api/compress":
            s = engine.Session(body.get("session") or "default", "default")
            try:
                t = s.compress(cfg)
                self._json({"ok": True, "summary": t or ""})
            except Exception as e:
                self._json({"error": str(e)[:200]}, 500)
            return

        if p == "/api/session_meta":
            s = engine.Session(body.get("session") or "default", "default")
            for k in ("card_id", "module_id", "act_no", "system", "map_id", "room_id"):
                if k in body:
                    s.meta[k] = body[k]
            s.save_meta()
            self._json({"ok": True, "meta": s.meta})
            return

        if p == "/api/state":
            s = engine.Session(body.get("session") or "default", "default")
            s.state = engine.merge_state(s.state, body.get("state") or {})
            s.save_state()
            self._json({"ok": True, "state": s.state,
                         "state_text": engine.render_state(s.state)})
            return

        self._json({"error": "unknown"}, 404)

    def _save_upload(self, b64, filename):
        """把前端传的 base64 落成临时文件，返回路径。"""
        import base64, tempfile
        d = ROOT / "_uploads"
        d.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in (filename or "upload.bin"))
        p = d / (str(int(time.time() * 1000)) + "_" + safe)
        p.write_bytes(base64.b64decode(b64))
        return p

    def _tavern_import(self, body):
        """导入酒馆角色卡，只取性格与外形。"""
        b64 = body.get("base64") or ""
        filename = body.get("filename") or ""
        text = body.get("text") or ""
        p = None
        if b64:
            p = self._save_upload(b64, filename or "card.png")
        elif text.strip():
            # 直接粘 JSON
            try:
                obj = json.loads(text)
            except Exception as e:
                self._json({"error": "JSON 解析失败：" + str(e)[:100]}, 400)
                return
            persona = tavern_card.extract_persona(obj)
            self._json({"ok": True, "persona": persona, "raw_keys": sorted(tavern_card.normalize(obj).keys())})
            return
        else:
            self._json({"error": "没有文件也没有内容"}, 400)
            return

        obj, err = tavern_card.load_any(p)
        if err:
            self._json({"error": err}, 400)
            return
        persona = tavern_card.extract_persona(obj)
        self._json({"ok": True, "persona": persona,
                     "raw_keys": sorted(tavern_card.normalize(obj).keys())})

    def _occ_defs(self):
        """内置职业 + 自定义职业，统一成 {name: {points, skills, credit, custom}}。"""
        out = {}
        for k, v in coc7.OCCUPATIONS.items():
            out[k] = {"points": [list(p) for p in (v.get("points") or [("EDU", 4)])],
                      "skills": list(v.get("skills") or []),
                      "credit": list(v.get("credit") or [0, 0]),
                      "custom": False}
        for k, v in self._load_custom_occ().items():
            out[k] = v
        return out

    def _load_custom_occ(self):
        p = ROOT / "custom_occ.json"
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_custom_occ(self, d):
        (ROOT / "custom_occ.json").write_text(
            json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    def _vision_models(self, cfg):
        """列出本机带 vision 能力的模型。"""
        import urllib.request as ur
        try:
            req = ur.Request((cfg.get("ollama") or "http://127.0.0.1:11434").rstrip("/") + "/api/tags")
            with ur.urlopen(req, timeout=5) as r:
                tags = json.loads(r.read().decode("utf-8"))
        except Exception:
            return []
        out = []
        for m in tags.get("models", []):
            name = m.get("name") or ""
            low = name.lower()
            for kw in ("vl", "vision", "llava", "moondream", "minicpm-v", "granite3.2-vision"):
                if kw in low:
                    out.append(name)
                    break
        return out

    def _map_import(self, cfg, body):
        """地图导入：图片走视觉模型，文本走解析器。"""
        title = body.get("title") or "未命名地图"
        b64 = body.get("base64") or ""
        filename = body.get("filename") or ""
        desc = body.get("text") or ""
        model = body.get("model") or ""
        mid = body.get("map_id") or ""

        m = mapdata.load_map(mid) if mid else None
        if not m:
            m = mapdata.new_map(title)

        data = None
        err = None
        if b64:
            p = self._save_upload(b64, filename or "map.png")
            m["image_path"] = str(p)
            if not model:
                vm = self._vision_models(cfg)
                model = vm[0] if vm else ""
            if not model:
                err = "本机没有视觉模型。可以先 ollama pull qwen2.5vl:3b（3.2GB），或改用文字描述导入。"
            else:
                data, err = map_vision.ocr_via_vision(p, model, cfg)
        elif desc.strip():
            data = map_vision.from_text_desc(desc)
            if not data.get("rooms"):
                err = "文字里没解析出房间。格式：1: 前厅，中央有枯井。通往 2、3"
        else:
            err = "没有图片也没有文字"

        if err and not data:
            self._json({"error": err, "map_id": m["id"] if m.get("id") else ""}, 400)
            return

        added = map_vision.apply_to_map(m, data)
        mapdata.save_map(m)
        self._json({"ok": True, "id": m["id"], "added": added,
                     "total": len(m["rooms"]), "map": m, "warn": err or ""})

    def _roll(self, body):
        """掷骰。三种模式：expr(自由表达式) / coc(技能检定) / dnd(d20 检定)。"""
        mode = body.get("mode") or "expr"
        try:
            if mode == "coc":
                res = dice.coc_check(body.get("skill") or 50,
                                     body.get("label") or "",
                                     int(body.get("bonus") or 0),
                                     int(body.get("penalty") or 0))
            elif mode == "dnd":
                res = dice.dnd_check(body.get("modifier") or 0,
                                     body.get("dc") or 10,
                                     body.get("label") or "",
                                     bool(body.get("advantage")),
                                     bool(body.get("disadvantage")))
            else:
                res = dice.roll_expr(body.get("expr") or "1d100")
                res["system"] = "generic"
        except Exception as e:
            self._json({"error": str(e)[:160]}, 400)
            return
        # 落盘到当前会话的骰子日志
        sess = body.get("session") or ""
        if sess:
            try:
                s = engine.Session(sess, "default")
                log = s.dir / "dice.jsonl"
                with log.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(res, ensure_ascii=False) + engine.NL)
            except Exception:
                pass
        self._json({"ok": True, "result": res})

    def _grow(self, cfg, body):
        """跑完后自动更新技能。"""
        cid = body.get("card_id") or ""
        system = body.get("system") or "coc7"
        used = body.get("used_skills") or []
        card = coc7.load_card(cid)
        if not card:
            self._json({"error": "角色卡不存在"}, 404)
            return
        rep = rules.auto_grow(card, system, used)
        if system == "dnd5e":
            coc7.save_card(rules.dnd_recalc(card))
        else:
            coc7.save_card(coc7.recalc(card))
        self._json({"ok": True, "report": rep, "card": card})

    def _card_import(self, body):
        """从文本、base64 文件或路径导入角色卡。"""
        filename = body.get("filename") or ""
        raw = body.get("text") or ""
        b64 = body.get("base64") or ""
        if b64:
            p = self._save_upload(b64, filename)
            raw, err = doc_import.extract(p)
            if err:
                self._json({"error": err}, 400)
                return
        if not raw:
            self._json({"error": "没有内容"}, 400)
            return
        try:
            card, warn = card_import.detect_and_import(filename, raw)
        except Exception as e:
            self._json({"error": str(e)[:200]}, 500)
            return
        if not card:
            self._json({"error": warn or "解析失败"}, 400)
            return
        cid = coc7.save_card(coc7.recalc(card))
        card["id"] = cid
        self._json({"ok": True, "card": card, "warn": warn})

    def _module_import(self, body):
        """导入模组：原文直接给，或给文件路径由后端解析。"""
        title = body.get("title") or "未命名模组"
        text = body.get("text") or ""
        source = body.get("filename") or ""
        path = body.get("path") or ""
        b64 = body.get("base64") or ""
        if b64 and not text:
            p = self._save_upload(b64, source)
            text, err = doc_import.extract(p)
            if err:
                self._json({"error": err}, 400)
                return
        if path and not text:
            text, err = doc_import.extract(path)
            if err:
                self._json({"error": err}, 400)
                return
        if not text.strip():
            self._json({"error": "模组内容为空"}, 400)
            return
        m = module_store.import_text(title, text, source)
        self._json({"ok": True, "id": m["id"], "acts": len(m["acts"]),
                     "chars": m["chars"], "tokens": m["tokens"]})

    def _scene_brief(self, s, card):
        """给队友看的简版场景：不含模组原文，只给状态里的事实。"""
        st = s.state or {}
        parts = []
        if st.get("location"):
            parts.append("地点：" + str(st["location"]))
        if st.get("time"):
            parts.append("时间：" + str(st["time"]))
        if st.get("scene"):
            parts.append("正在发生：" + str(st["scene"]))
        if st.get("npcs"):
            parts.append("在场：" + "、".join(st["npcs"]))
        if card:
            parts.append("你在和 " + str(card.get("name", "调查员")) + " 同行")
        return "；".join(parts)

    def _team_speak(self, cfg, s, card, recent):
        """所有启用的队友依次发言。失败不阻塞主线。"""
        out = []
        brief = self._scene_brief(s, card)
        for item in teammates.active_teammates():
            tcard = None
            if item.get("card_id"):
                tcard = coc7.load_card(item["card_id"])
            try:
                line = teammates.speak(item, tcard, brief, recent, cfg)
            except Exception as e:
                out.append({"name": item.get("name", "?"), "text": "",
                            "error": str(e)[:160]})
                continue
            if line:
                out.append({"name": item.get("name", "?"), "text": line, "error": ""})
        return out

    def _chat_stream(self, cfg, body):
        """SSE 流式：先逐字推正文，最后推一份状态块。"""
        import urllib.request
        sess_name = body.get("session") or "default"
        world = body.get("world") or "default"
        text = (body.get("text") or "").strip()
        if not text:
            self._json({"error": "空输入"}, 400)
            return
        s = engine.Session(sess_name, world)
        if not s.world or s.world == "default":
            ws = engine.list_worlds()
            if ws:
                s.world = ws[0]
                s.meta["world"] = s.world
                s.save_meta()
        fixed = engine.build_fixed_layer(s.world)
        if not fixed.strip():
            self._json({"error": "世界书为空：请在「准备 → 世界设定」里写提示词"}, 400)
            return

        # 规则系统
        system = s.meta.get("system") or "coc7"

        # 角色卡
        card = None
        card_id = s.meta.get("card_id") or ""
        if card_id:
            card = coc7.load_card(card_id)
        if card and (card.get("system") or "coc7") == "dnd5e":
            card_ctx = rules.dnd_card_context(card)
            system = "dnd5e"
        else:
            card_ctx = coc7.card_to_context(card) if card else ""

        # 模组：只装载当前幕
        mod_ctx = ""
        mod_info = {"loaded": 0}
        mid = s.meta.get("module_id") or ""
        if mid:
            mod = module_store.load_module(mid)
            if mod:
                budget = int(body.get("module_budget") or 7000)
                mod_ctx, mod_info = module_store.build_context(
                    mod, s.meta.get("act_no") or 1, budget)

        # 地图：只装载当前房间
        map_ctx = ""
        map_info = {"loaded": 0}
        map_id = s.meta.get("map_id") or ""
        if map_id:
            mm = mapdata.load_map(map_id)
            if mm:
                map_ctx, map_info = mapdata.build_context(mm, 1800)

        # 角色关系
        rel_ctx = relations.to_context(relations.load(),
                                       card.get("name", "") if card else "")

        sys_ctx = ""
        if system == "dnd5e":
            sys_ctx = NL.join([
                "## 本局规则：DND 5e",
                "",
                "判定用 d20 + 调整值 vs DC。不要用 d100，不要用理智值。",
                "DC 参考：很容易 5 / 容易 10 / 中等 15 / 困难 20 / 极难 25 / 几乎不可能 30。",
                "战斗按先攻顺序，攻击 d20 vs AC。",
            ])
        else:
            sys_ctx = NL.join([
                "## 本局规则：COC 7th",
                "",
                "判定用 d100。01-05 大成功，96-100 大失败。",
                "≤技能/5 极难成功，≤技能/2 困难成功，≤技能 普通成功。",
            ])

        extra = NL.join(x for x in (sys_ctx, player_input.force_instruction_block(),
                                    mod_ctx, map_ctx, card_ctx, rel_ctx) if x.strip())
        if extra.strip():
            fixed = fixed + NL + NL + extra

        parsed = player_input.parse(text)
        rendered = player_input.render_for_prompt(text, parsed) or text
        s.append_turn("user", rendered)
        msgs = engine.assemble(fixed, s.state, s.summary, s.turns, int(cfg["window"]))

        payload = json.dumps({
            "model": cfg["model"], "stream": True, "think": False,
            "options": {"num_ctx": int(cfg["num_ctx"]),
                        "num_predict": int(cfg["num_predict"]),
                        "temperature": float(cfg["temperature"])},
            "messages": msgs,
        }, ensure_ascii=False).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def emit(obj):
            chunk = "data: " + json.dumps(obj, ensure_ascii=False) + engine.NL + engine.NL
            self.wfile.write(chunk.encode("utf-8"))
            self.wfile.flush()

        t0 = time.time()
        buf = []
        last_meta = {}
        try:
            req = urllib.request.Request(cfg["ollama"] + "/api/chat", data=payload,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1800) as resp:
                for line in resp:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    piece = (obj.get("message") or {}).get("content") or ""
                    if piece:
                        buf.append(piece)
                        emit({"t": "d", "v": piece})
                    if obj.get("done"):
                        last_meta = obj
        except Exception as e:
            emit({"t": "err", "v": str(e)[:200]})
            self.wfile.flush()
            return

        dt = time.time() - t0
        reply = "".join(buf)
        prose, new_state = engine.split_state(reply)
        # 模型没在正文里吐状态块时，单独发一次轻量请求提取状态
        # （实测有些模型 0/3 概率吐 JSON 块，拆成独立调用后成功率明显提高）
        if not new_state:
            new_state = engine.extract_state(prose, s.state, cfg)
        if new_state:
            s.state = engine.merge_state(s.state, new_state)
            s.save_state()
        s.append_turn("assistant", prose)
        s.archive_turn(prose)

        did_compress = False
        n = len([t for t in s.turns if t["role"] == "assistant"])
        ce = int(cfg["compress_every"])
        if ce > 0 and n and n % ce == 0:
            try:
                s.compress(cfg)
                did_compress = True
            except Exception:
                pass

        # 队友发言（失败不影响主线）
        team_lines = []
        if teammates.active_teammates():
            recent = s.turns[-4:]
            emit({"t": "team_start"})
            try:
                team_lines = self._team_speak(cfg, s, card, recent)
            except Exception:
                team_lines = []
            for tl in team_lines:
                emit({"t": "team", "name": tl.get("name"), "text": tl.get("text"),
                      "error": tl.get("error", "")})

        emit({"t": "done", "prose": prose, "state_text": engine.render_state(s.state),
              "compressed": did_compress, "elapsed": round(dt, 1),
              "prompt_tokens": last_meta.get("prompt_eval_count", 0),
              "eval_tokens": last_meta.get("eval_count", 0),
              "module_info": mod_info, "card_name": (card or {}).get("name", ""),
              "system": system, "map_info": map_info,
              "force_count": len(parsed.get("force_texts") or []),
              "ooc": bool(parsed.get("has_ooc"))})

    def _chat(self, cfg, body):
        sess_name = body.get("session") or "default"
        world = body.get("world") or "default"
        text = (body.get("text") or "").strip()
        if not text:
            self._json({"error": "空输入"}, 400)
            return
        s = engine.Session(sess_name, world)
        fixed = engine.build_fixed_layer(s.world)
        if not fixed.strip():
            self._json({"error": "世界书为空，请先在「世界设定」里写提示词"}, 400)
            return

        s.append_turn("user", text)
        msgs = engine.assemble(fixed, s.state, s.summary, s.turns, int(cfg["window"]))
        t0 = time.time()
        try:
            r = engine.chat(msgs, cfg)
        except Exception as e:
            s.turns.pop()
            with s.turns_file.open("w", encoding="utf-8") as f:
                for t in s.turns:
                    f.write(json.dumps(t, ensure_ascii=False) + engine.NL)
            self._json({"error": "模型调用失败：" + str(e)[:200]}, 500)
            return
        dt = time.time() - t0

        reply = r["message"]["content"]
        prose, new_state = engine.split_state(reply)
        # 模型没在正文里吐状态块时，单独发一次轻量请求提取状态
        # （实测有些模型 0/3 概率吐 JSON 块，拆成独立调用后成功率明显提高）
        if not new_state:
            new_state = engine.extract_state(prose, s.state, cfg)
        if new_state:
            s.state = engine.merge_state(s.state, new_state)
            s.save_state()
        s.append_turn("assistant", prose)
        s.archive_turn(prose)

        did_compress = False
        n = len([t for t in s.turns if t["role"] == "assistant"])
        ce = int(cfg["compress_every"])
        if ce > 0 and n and n % ce == 0:
            try:
                s.compress(cfg)
                did_compress = True
            except Exception:
                pass

        self._json({"ok": True, "prose": prose, "state": s.state,
                     "state_text": engine.render_state(s.state),
                     "compressed": did_compress, "elapsed": round(dt, 1),
                     "prompt_tokens": r.get("prompt_eval_count", 0),
                     "eval_tokens": r.get("eval_count", 0)})


def main():
    port = PORT
    for i in range(20):
        try:
            srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            port += 1
    else:
        print("找不到可用端口"); return
    url = "http://127.0.0.1:" + str(port)
    print("跑团 KP 已启动：" + url)
    print("关闭这个窗口即退出。")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()