const API = (p, opt) => fetch(p, opt).then(r => r.json());
const POST = (p, obj) => API(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(obj || {}) });
const chr96 = String.fromCharCode(96);
const el = id => document.getElementById(id);

const S = {
  sessions: [], worlds: [], cfg: {}, cur: null, world: null,
  turns: [], busy: false, status: null, meta: {},
  cards: [], modules: [], team: [], metaInfo: {}, rel: { nodes: [], edges: [] },
  curCard: null, curModule: null, actNo: 1, occDefs: {},
};

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function toast(msg) {
  const d = document.createElement("div");
  d.textContent = msg;
  d.style.cssText = "position:fixed;left:50%;bottom:40px;transform:translateX(-50%);background:#2a2320;color:#e8e0d6;padding:10px 20px;border-radius:8px;border:1px solid #4a3f36;z-index:999;font-size:13px";
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 2400);
}

async function boot() {
  S.cfg = await API("/api/config");
  S.metaInfo = await API("/api/meta");
  S.occDefs = S.metaInfo.occ_defs || {};
  const w = await API("/api/worlds");
  S.worlds = (w.worlds && w.worlds.length) ? w.worlds : ["default"];
  fillWorlds();
  S.world = S.worlds[0];
  el("worldSelect").value = S.world;
  el("worldSelect").onchange = e => { S.world = e.target.value; updateBindBox(); };
  await Promise.all([refreshStatus(), refreshCards(), refreshModules(), refreshTeam(), refreshRel()]);
  await refreshSessions();
  if (S.sessions.length) await openSession(S.sessions[0].name);
  else renderChat();
  setInterval(refreshStatus, 8000);
}

async function refreshStatus() {
  try { S.status = await API("/api/status"); } catch (e) { S.status = { online: false }; }
  const dot = el("statusDot");
  dot.className = "dot " + (S.status.online ? (S.status.model_ready ? "on" : "off") : "off");
  const mi = el("modelInfo");
  if (!S.status.online) mi.innerHTML = "<span style=\"color:#a33\">Ollama 未连接</span>";
  else if (!S.status.model_ready) mi.textContent = "模型 " + S.cfg.model + " 未安装";
  else mi.textContent = S.cfg.model + " · " + S.cfg.num_ctx + " ctx";
}

function fillWorlds() {
  const sel = el("worldSelect");
  sel.innerHTML = "";
  S.worlds.forEach(w => {
    const o = document.createElement("option");
    o.value = w; o.textContent = w;
    sel.appendChild(o);
  });
}

async function refreshSessions() {
  const r = await API("/api/sessions");
  S.sessions = r.sessions || [];
  const box = el("sessionList");
  box.innerHTML = "";
  S.sessions.forEach(s => {
    const d = document.createElement("div");
    d.className = "item" + (S.cur === s.name ? " active" : "");
    d.innerHTML = "<span>" + esc(s.name) + "</span><span class=\"n\">" + s.turns + " 轮</span>";
    d.onclick = () => openSession(s.name);
    box.appendChild(d);
  });
}

async function openSession(name) {
  const s = await API("/api/session?name=" + encodeURIComponent(name));
  S.cur = s.name;
  S.turns = s.turns || [];
  S.meta = s.meta || {};
  if (s.world && s.world !== "default") {
    S.world = s.world;
    el("worldSelect").value = s.world;
  } else {
    S.world = el("worldSelect").value || S.worlds[0];
  }
  el("title").textContent = s.name;
  updateBindBox();
  el("stateBox").textContent = s.state_text || "（尚无状态）";
  renderChat();
  await refreshSessions();
}

function updateBindBox() {
  const card = S.cards.find(c => c.id === S.meta.card_id);
  const mod = S.modules.find(m => m.id === S.meta.module_id);
  const worldShown = (S.world && S.world !== "default") ? S.world : (S.worlds[0] || "—");
  const lines = [];
  lines.push("<span class=\"k\">世界</span> " + esc(worldShown));
  lines.push("<span class=\"k\">角色</span> " + (card ? esc(card.name) : "未绑定"));
  lines.push("<span class=\"k\">模组</span> " + (mod ? esc(mod.title) + " 第 " + (S.meta.act_no || 1) + " 幕" : "未绑定"));
  el("bindInfo").innerHTML = lines.join("<br>");
}

function renderChat() {
  const box = el("chat");
  box.innerHTML = "";
  if (!S.turns.length) {
    const d = document.createElement("div");
    d.className = "hint";
    d.textContent = "输入你的第一个行动，故事就从这里开始。";
    box.appendChild(d);
    return;
  }
  S.turns.forEach(t => {
    const wrap = document.createElement("div");
    wrap.className = "turn " + (t.role === "user" ? "player" : "kp");
    const who = document.createElement("div");
    who.className = "who";
    who.textContent = t.role === "user" ? "你" : (t.role === "team" ? (t.name || "队友") : "KP");
    const b = document.createElement("div");
    b.className = "bubble";
    const display = t.role === "user" ? t.content : stripCheckHint(t.content);
    b.textContent = display;
    wrap.appendChild(who);
    wrap.appendChild(b);
    box.appendChild(wrap);
    // 历史消息里的〔检定〕也要能点（刷新页面后依然可用）
    if (t.role !== "user") {
      const checks = parseCheck(display || "");
      if (checks.length) renderCheckCard(checks, wrap);
    }
  });
  box.scrollTop = box.scrollHeight;
}

function appendTurn(role, text, name) {
  S.turns.push({ role, content: text, name });
  renderChat();
}
async function send() {
  const ta = el("input");
  const text = ta.value.trim();
  if (!text || S.busy) return;
  if (!S.cur) { await newSession(); if (!S.cur) return; }
  S.busy = true; el("send").disabled = true;
  ta.value = ""; ta.style.height = "auto";
  appendTurn("user", text);

  const box = el("chat");
  const wrap = document.createElement("div");
  wrap.className = "turn kp"; wrap.id = "streaming";
  const who = document.createElement("div");
  who.className = "who"; who.textContent = "KP";
  const b = document.createElement("div");
  b.className = "bubble";
  const cur = document.createElement("span");
  cur.className = "stream-cursor";
  b.appendChild(cur);
  wrap.appendChild(who); wrap.appendChild(b);
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;

  const stopBtn = document.createElement("button");
  stopBtn.className = "stop-btn"; stopBtn.textContent = "停止";
  document.body.appendChild(stopBtn);
  const ctrl = new AbortController();
  stopBtn.onclick = () => ctrl.abort();

  let acc = "";
  let meta = null;
  try {
    const resp = await fetch("/api/chat_stream", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session: S.cur, world: S.world, text }),
      signal: ctrl.signal,
    });
    if (!resp.ok || !resp.body) throw new Error("HTTP " + resp.status);
    const reader = resp.body.getReader();
    const dec = new TextDecoder("utf-8");
    let pending = "";
    const SEP = String.fromCharCode(10) + String.fromCharCode(10);
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      pending += dec.decode(value, { stream: true });
      const parts = pending.split(SEP);
      pending = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        let obj;
        try { obj = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }
        if (obj.t === "d") {
          acc += obj.v;
          b.textContent = acc.split(chr96 + chr96 + chr96)[0];
          b.appendChild(cur);
          if (box.scrollHeight - box.scrollTop - box.clientHeight < 140) box.scrollTop = box.scrollHeight;
        } else if (obj.t === "done") {
          meta = obj;
        } else if (obj.t === "err") {
          throw new Error(obj.v);
        }
      }
    }
  } catch (e) {
    if (e.name !== "AbortError") b.textContent = (acc || "［出错］" + e.message);
  }

  stopBtn.remove();
  const fin = el("streaming");
  if (fin) fin.remove();

  const rawProse = (meta && meta.prose) || acc.split(chr96 + chr96 + chr96)[0].trim();
  const finalProse = stripCheckHint(rawProse);
  if (finalProse) {
    appendTurn("assistant", finalProse);
    const last = el("chat").lastElementChild;
    if (last && meta) {
      const s = document.createElement("div");
      s.className = "stats";
      s.textContent = meta.elapsed + "s · 上下文 " + meta.prompt_tokens + " tok · 输出 " + meta.eval_tokens + " tok";
      if (meta.compressed) s.textContent += " · 已压缩记忆";
      last.appendChild(s);
      // KP 要求了检定 → 渲染成可点击卡片
      const checks = parseCheck(finalProse);
      if (checks.length) renderCheckCard(checks, last);
    }
  }
  if (meta) {
    el("stateBox").textContent = meta.state_text || "";
    if (meta.module_info && meta.module_info.loaded) {
      S.actNo = meta.module_info.loaded;
      S.meta.act_no = S.actNo;
      updateBindBox();
    }
  }

  S.busy = false; el("send").disabled = false; ta.focus();
  refreshSessions();
}

async function newSession() {
  const name = prompt("新会话名字（例如：灰石堡-第一夜）");
  if (!name) return;
  await API("/api/session?name=" + encodeURIComponent(name));
  await openSession(name);
}

function openModal(title, bodyHtml, footHtml, wide) {
  el("modalTitle").textContent = title;
  el("modalBody").innerHTML = bodyHtml;
  el("modalFoot").innerHTML = footHtml || "";
  el("modalBox").className = "modal-box" + (wide ? " wide" : "");
  el("modal").classList.remove("hidden");
}

function closeModal() { el("modal").classList.add("hidden"); }
// ==================== 角色卡 ====================
async function refreshCards() {
  const r = await API("/api/cards");
  S.cards = r.cards || [];
  const box = el("cardList");
  box.innerHTML = "";
  if (!S.cards.length) {
    box.innerHTML = "<div class=\"hint\">还没有角色卡</div>";
    return;
  }
  S.cards.forEach(c => {
    const d = document.createElement("div");
    d.className = "item";
    d.innerHTML = "<span>" + esc(c.name) + "</span><span class=\"n\">" + esc(c.occupation || "") + "</span>";
    d.onclick = () => editCard(c.id);
    box.appendChild(d);
  });
}

async function editCard(id) {
  const c = id ? await API("/api/card?id=" + encodeURIComponent(id)) : await API("/api/card_new");
  S.curCard = c;
  renderCardEditor(c, id ? "编辑角色卡" : "新建角色卡", id);
}

function renderCardEditor(c, title, id) {
  const attrs = c.attrs || {};
  const d = c.derived || {};
  const eff = d.eff || {};
  const sk = c.skills || {};
  const occDef = S.occDefs[c.occupation] || null;
  const isCustom = !!c.custom_occ;

  let html = "";
  html += "<div class=\"field-row\">";
  html += "<div class=\"field\"><span>姓名</span><input id=\"c_name\" value=\"" + esc(c.name) + "\"></div>";
  html += "<div class=\"field\"><span>职业</span><select id=\"c_occ\">";
  html += "<option value=\"\">（未选）</option>";
  Object.keys(S.occDefs).forEach(o => {
    html += "<option value=\"" + esc(o) + "\"" + (o === c.occupation ? " selected" : "") + ">" + esc(o) + "</option>";
  });
  html += "</select></div>";
  html += "<div class=\"field\"><span>年龄</span><input id=\"c_age\" type=\"number\" value=\"" + (c.age || 25) + "\"></div>";
  html += "<div class=\"field\"><span>玩家</span><input id=\"c_player\" value=\"" + esc(c.player) + "\"></div>";
  html += "<div class=\"field\"><span>神话（上限 99−此值）</span><input id=\"c_mythos\" type=\"number\" min=\"0\" max=\"99\" value=\"" + (c.mythos || 0) + "\"></div>";
  html += "</div>";

  // 职业点数公式（可自定义）
  const pf = (occDef && occDef.points) ? occDef.points : [["EDU", 4]];
  const pfText = pf.map(p => p[0] + "×" + p[1]).join(" + ");
  html += "<div class=\"occ-bar\">";
  html += "<span class=\"ob-label\">职业点数</span>";
  html += "<input id=\"occ_formula\" class=\"ob-input\" value=\"" + esc(pfText) + "\" placeholder=\"EDU×4 或 EDU×2+DEX×2\" title=\"可用 + 分隔多个属性\">";
  html += "<button id=\"occAuto\" class=\"btn small\">自动填职业点</button>";
  html += "<button id=\"occSave\" class=\"btn small ghost\">存为自定义职业</button>";
  html += "</div>";

  // 技能点面板
  html += "<div id=\"pointBar\" class=\"point-bar\"></div>";

  html += "<div class=\"label\" style=\"margin-top:6px\">属性</div><div class=\"card-grid\">";
  (S.metaInfo.attrs || []).forEach(a => {
    const v = attrs[a.key] != null ? attrs[a.key] : 50;
    const e = eff[a.key] != null ? eff[a.key] : v;
    html += "<div class=\"attr-box\"><label>" + esc(a.name) + " " + a.key + "</label>";
    html += "<div class=\"row\"><input type=\"number\" data-attr=\"" + a.key + "\" value=\"" + v + "\" min=\"1\" max=\"99\"></div>";
    html += "<div class=\"half\">困难 " + Math.floor(e / 2) + " / 极难 " + Math.floor(e / 5) + (e !== v ? " · 实值 " + e : "") + "</div>";
    html += "</div>";
  });
  html += "</div>";

  html += "<div class=\"derived-row\">";
  const sanShown = (d.SAN_max != null) ? Math.min(c.san || 0, d.SAN_max) : (c.san || 0);
  [["HP", c.hp, d.HP_max], ["MP", c.mp, d.MP_max], ["SAN", sanShown, d.SAN_max], ["幸运", c.luck, 99]].forEach(x => {
    html += "<div class=\"dv\">" + x[0] + "<b>" + (x[1] != null ? x[1] : "-") + (x[2] ? " / " + x[2] : "") + "</b></div>";
  });
  html += "<div class=\"dv\">伤害加成<b>" + esc(d.DB || "0") + "</b></div>";
  html += "<div class=\"dv\">体格<b>" + esc(d.BUILD != null ? d.BUILD : "0") + "</b></div>";
  html += "<div class=\"dv\">移动<b>" + esc(d.MOV || 8) + "</b></div>";
  html += "</div>";

  // 技能表：基础 / 职业 / 兴趣 / 自由 / 合计
  html += "<div class=\"label\" style=\"margin-top:6px\">技能（职=职业点 兴=兴趣点 加=单纯加点）</div>";
  html += "<div class=\"skill-scroll\">";
  html += "<table class=\"skill-table\"><thead><tr>";
  html += "<th>技能</th><th>基础</th><th title=\"职业点\">职</th><th title=\"兴趣点\">兴</th><th title=\"单纯加点，不算成长\">加</th><th>合计</th><th>困难</th><th>极难</th></tr></thead><tbody>";
  (S.metaInfo.skills || []).forEach(s => {
    const rec = sk[s.key] || {};
    const base = s.base;
    const occA = rec.occ_add || 0;
    const intA = rec.int_add || 0;
    const frA = rec.free_add || 0;
    const v = rec.value != null ? rec.value : base;
    html += "<tr data-row=\"" + s.key + "\">";
    html += "<td>" + esc(s.name) + "</td><td class=\"base\">" + base + "</td>";
    html += "<td><input type=\"number\" data-occ=\"" + s.key + "\" value=\"" + occA + "\" min=\"0\" max=\"99\" class=\"pt\"></td>";
    html += "<td><input type=\"number\" data-int=\"" + s.key + "\" value=\"" + intA + "\" min=\"0\" max=\"99\" class=\"pt\"></td>";
    html += "<td><input type=\"number\" data-free=\"" + s.key + "\" value=\"" + frA + "\" min=\"0\" max=\"99\" class=\"pt\"></td>";
    html += "<td class=\"tot\" data-tot=\"" + s.key + "\">" + v + "</td>";
    html += "<td class=\"base\" data-half=\"" + s.key + "\">" + Math.floor(v / 2) + "</td>";
    html += "<td class=\"base\" data-fifth=\"" + s.key + "\">" + Math.floor(v / 5) + "</td>";
    html += "</tr>";
  });
  html += "</tbody></table></div>";

  // 随身物品
  html += "<div class=\"label\" style=\"margin-top:6px\">随身携带</div>";
  html += "<div id=\"itemList\" class=\"item-list\"></div>";
  html += "<div class=\"item-add\">";
  html += "<input id=\"itemName\" placeholder=\"物品名（如 手电筒）\">";
  html += "<input id=\"itemQty\" type=\"number\" value=\"1\" min=\"1\" style=\"width:62px\" title=\"数量\">";
  html += "<button id=\"itemAdd\" class=\"btn small\">添加</button>";
  html += "</div>";

  html += "<div class=\"label\" style=\"margin-top:6px\">背景</div><div class=\"field-row\">";
  const bg = c.background || {};
  [["traits", "性格特征"], ["ideology", "信条/理念"], ["significant_people", "重要之人"],
   ["meaningful_locations", "意义非凡之地"], ["treasured_possessions", "珍贵之物"],
   ["injuries", "旧伤/疤痕"], ["phobias", "恐惧症/狂躁症"]].forEach(kv => {
    html += "<div class=\"field\"><span>" + kv[1] + "</span><input data-bg=\"" + kv[0] + "\" value=\"" + esc(bg[kv[0]] || "") + "\"></div>";
  });
  html += "</div>";

  const foot = [
    "<button id=\"rollCard\" class=\"btn ghost\">随机生成</button>",
    "<button id=\"bindCard\" class=\"btn ghost\">绑定到当前会话</button>",
    id ? "<button id=\"delCard\" class=\"btn ghost\" style=\"color:#a33\">删除</button>" : "",
    "<button id=\"saveCard\" class=\"btn primary\">保存</button>"
  ].join("");
  openModal(title, html, foot, true);

  bindCardEditor(c, id);
}
function collectCard() {
  const c = S.curCard;
  if (el("c_name")) c.name = el("c_name").value;
  if (el("c_occ")) c.occupation = el("c_occ").value;
  if (el("c_age")) c.age = parseInt(el("c_age").value) || 25;
  if (el("c_player")) c.player = el("c_player").value;
  if (el("c_mythos")) c.mythos = parseInt(el("c_mythos").value) || 0;
  document.querySelectorAll("#modalBody [data-skill]").forEach(inp => {
    const k = inp.dataset.skill;
    if (!c.skills[k]) c.skills[k] = {};
    c.skills[k].value = parseInt(inp.value) || 0;
  });
  document.querySelectorAll("#modalBody [data-bg]").forEach(inp => {
    c.background[inp.dataset.bg] = inp.value;
  });
}

function recalcLive() {
  // 前端只做展示性重算，最终以服务端为准
  const c = S.curCard;
  const a = c.attrs;
  const eff = Object.assign({}, a);
  const age = c.age || 25;
  let pen = 0, movPen = 0;
  if (age >= 40 && age < 50) pen = 5;
  else if (age >= 50 && age < 60) { pen = 10; movPen = 1; }
  else if (age >= 60 && age < 70) { pen = 20; movPen = 2; }
  else if (age >= 70 && age < 80) { pen = 40; movPen = 3; }
  else if (age >= 80) { pen = 80; movPen = 4; }
  ["STR", "CON", "DEX", "APP", "EDU"].forEach(k => { eff[k] = Math.max(1, (a[k] || 1) - pen); });
  const hp = Math.floor((eff.CON + (a.SIZ || 1)) / 10);
  const mp = Math.floor(eff.POW / 5);
  const mythos = c.mythos || 0;
  const sanStart = eff.POW;
  const sanMax = Math.max(0, 99 - mythos);
  const san = Math.min(sanStart, sanMax);
  const sum = (eff.STR || 0) + (a.SIZ || 0);
  let db = "0", build = 0;
  if (sum <= 64) { db = "-2"; build = -2; }
  else if (sum <= 84) { db = "-1"; build = -1; }
  else if (sum <= 124) { db = "0"; build = 0; }
  else if (sum <= 164) { db = "+1d4"; build = 1; }
  else if (sum <= 204) { db = "+1d6"; build = 2; }
  else { db = "+2d6"; build = 3; }
  let mov = 8;
  if (eff.DEX < (a.SIZ || 0) && eff.STR < (a.SIZ || 0)) mov = 7;
  else if (eff.STR > (a.SIZ || 0) && eff.DEX > (a.SIZ || 0)) mov = 9;
  mov = Math.max(1, mov - movPen);
  c.derived = { eff, HP_max: hp, MP_max: mp, SAN: san, SAN_max: sanMax, SAN_start: sanStart, DB: db, BUILD: build, MOV: mov, LUCK: c.luck || 50 };
  c.hp = Math.min(c.hp || hp, hp);
  c.mp = Math.min(c.mp || mp, mp);
  c.san = Math.min(c.san || san, sanMax);
  const rows = document.querySelectorAll("#modalBody .derived-row .dv b");
  if (rows.length >= 7) {
    rows[0].textContent = c.hp + " / " + hp;
    rows[1].textContent = c.mp + " / " + mp;
    rows[2].textContent = c.san + " / " + sanMax;
    rows[3].textContent = (c.luck || 50) + " / 99";
    rows[4].textContent = db;
    rows[5].textContent = build;
    rows[6].textContent = mov;
  }
  document.querySelectorAll("#modalBody [data-attr]").forEach(inp => {
    const k = inp.dataset.attr;
    const box = inp.closest(".attr-box");
    const half = box.querySelector(".half");
    const e = eff[k] || 1;
    half.textContent = "困难 " + Math.floor(e / 2) + " / 极难 " + Math.floor(e / 5);
  });
}
// ==================== 导入（卡 / 模组） ====================
function importCard() {
  const html = [
    "<div class=\"hint\">支持 JSON（本程序或第三方导出）、纯文本（自动抽取属性与技能）、DOCX、PDF。</div>",
    "<div class=\"file-drop\" id=\"dropCard\">点击选择文件，或把文件拖到这里</div>",
    "<input type=\"file\" id=\"fileCard\" accept=\".json,.txt,.md,.docx,.pdf\" style=\"display:none\">",
    "<div class=\"label\">或直接粘贴文本</div>",
    "<div class=\"field\"><textarea id=\"pasteCard\" rows=\"10\" placeholder=\"姓名：玛戈·维尔" + String.fromCharCode(10) + "职业：记者" + String.fromCharCode(10) + "力量 45 体质 55 ……\"></textarea></div>"
  ].join("");
  openModal("导入角色卡", html, "<button id=\"doImportCard\" class=\"btn primary\">导入</button>", false);

  const drop = el("dropCard"), file = el("fileCard");
  drop.onclick = () => file.click();
  drop.ondragover = e => { e.preventDefault(); drop.style.borderColor = "var(--accent2)"; };
  drop.ondragleave = () => { drop.style.borderColor = ""; };
  drop.ondrop = async e => {
    e.preventDefault(); drop.style.borderColor = "";
    if (e.dataTransfer.files.length) await readCardFile(e.dataTransfer.files[0]);
  };
  file.onchange = async () => { if (file.files.length) await readCardFile(file.files[0]); };

  el("doImportCard").onclick = async () => {
    const txt = el("pasteCard").value.trim();
    if (!txt) { toast("没有内容"); return; }
    await doCardImport("", txt);
  };
}

async function readCardFile(f) {
  const name = f.name.toLowerCase();
  if (name.endsWith(".docx") || name.endsWith(".pdf")) {
    toast("正在解析 " + f.name + "…");
    const b64 = await fileToBase64(f);
    const r = await POST("/api/card_import", { filename: f.name, base64: b64 });
    if (r.error) { toast(r.error); return; }
    closeModal(); await refreshCards(); toast("已导入：" + r.card.name + (r.warn ? "（" + r.warn + "）" : ""));
    return;
  }
  const txt = await f.text();
  await doCardImport(f.name, txt);
}

async function doCardImport(filename, text) {
  const r = await POST("/api/card_import", { filename, text });
  if (r.error) { toast(r.error); return; }
  closeModal();
  await refreshCards();
  toast("已导入：" + r.card.name + (r.warn ? "（" + r.warn + "）" : ""));
}

function fileToBase64(f) {
  return new Promise((res, rej) => {
    const rd = new FileReader();
    rd.onload = () => res(String(rd.result).split(",")[1]);
    rd.onerror = rej;
    rd.readAsDataURL(f);
  });
}

// ==================== 模组 ====================
async function refreshModules() {
  const r = await API("/api/modules");
  S.modules = r.modules || [];
  const box = el("moduleList");
  box.innerHTML = "";
  if (!S.modules.length) { box.innerHTML = "<div class=\"hint\">还没有模组</div>"; return; }
  S.modules.forEach(m => {
    const d = document.createElement("div");
    d.className = "item";
    d.innerHTML = "<span>" + esc(m.title) + "</span><span class=\"n\">" + m.acts + " 幕</span>";
    d.onclick = () => openModule(m.id);
    box.appendChild(d);
  });
}

async function openModule(mid) {
  const m = await API("/api/module?id=" + encodeURIComponent(mid));
  S.curModule = m;
  const tokTotal = Math.round(m.chars * 0.72);
  const budget = 7000;
  let html = "";
  html += "<div class=\"hint\">总字数 " + m.chars + " · 约 " + tokTotal + " token · 切分 " + m.acts.length + " 幕";
  html += "　上下文窗口 " + (S.cfg.num_ctx || 24576) + " token";
  if (tokTotal > (S.cfg.num_ctx || 24576)) {
    html += "<br><b style=\"color:#c8994a\">整篇塞不进窗口，所以按幕装载：每次只喂当前幕 + 目录，其余留在磁盘。</b>";
  }
  html += "</div>";
  html += "<div style=\"display:flex;gap:14px\">";
  html += "<div style=\"flex:1;min-width:0;max-height:400px;overflow-y:auto;border:1px solid var(--line);border-radius:6px;padding:6px\">";
  m.acts.forEach(a => {
    const cls = "act-item" + (a.no === (S.meta.act_no || 1) ? " active" : "");
    html += "<div class=\"" + cls + "\" data-act=\"" + a.no + "\"><span>" + a.no + ". " + esc(a.title) + "</span>";
    html += "<span class=\"meta\">" + a.chars + " 字 · " + a.tokens + " tok" + (a.status === "done" ? " · 已演" : "") + "</span></div>";
  });
  html += "</div>";
  html += "<div style=\"flex:1;min-width:0;display:flex;flex-direction:column;gap:8px\">";
  html += "<div class=\"field\"><span>当前幕正文（预览前 2000 字）</span>";
  html += "<textarea id=\"actBody\" rows=\"14\" readonly></textarea></div>";
  html += "<div class=\"field\"><span>本幕摘要（演完后填，用于下一幕回顾）</span>";
  html += "<textarea id=\"actSum\" rows=\"3\"></textarea></div>";
  html += "<div style=\"display:flex;gap:8px\">";
  html += "<button id=\"bindMod\" class=\"btn primary\">绑定到会话并从这一幕开始</button>";
  html += "<button id=\"saveSum\" class=\"btn ghost\">保存摘要</button>";
  html += "</div></div></div>";
  const foot = "<button id=\"delMod\" class=\"btn ghost\" style=\"color:#a33\">删除模组</button>";
  openModal("模组：" + m.title, html, foot, true);

  let pick = S.meta.act_no || 1;
  const showAct = n => {
    pick = n;
    const a = m.acts.find(x => x.no === n);
    if (!a) return;
    el("actBody").value = a.body.slice(0, 2000) + (a.body.length > 2000 ? String.fromCharCode(10) + "……（后面还有 " + (a.body.length - 2000) + " 字）" : "");
    el("actSum").value = a.summary || "";
    document.querySelectorAll(".act-item").forEach(x => x.classList.toggle("active", parseInt(x.dataset.act) === n));
  };
  document.querySelectorAll(".act-item").forEach(x => { x.onclick = () => showAct(parseInt(x.dataset.act)); });
  showAct(pick);

  el("saveSum").onclick = async () => {
    await POST("/api/module_act", { id: m.id, act: pick, summary: el("actSum").value });
    const a = m.acts.find(x => x.no === pick);
    if (a) { a.summary = el("actSum").value; a.status = "done"; }
    toast("摘要已保存");
  };
  el("bindMod").onclick = async () => {
    if (!S.cur) { toast("先开一个会话"); return; }
    await POST("/api/session_meta", { session: S.cur, module_id: m.id, act_no: pick });
    S.meta.module_id = m.id; S.meta.act_no = pick;
    updateBindBox();
    toast("已绑定，从第 " + pick + " 幕开始");
  };
  if (el("delMod")) el("delMod").onclick = async () => {
    if (!confirm("删除这个模组？")) return;
    await POST("/api/module_delete", { id: m.id });
    closeModal(); await refreshModules();
  };
}

function importModule() {
  const html = [
    "<div class=\"field\"><span>模组标题</span><input id=\"m_title\" placeholder=\"例如：灰石堡之夜\"></div>",
    "<div class=\"hint\">支持 DOCX / PDF / TXT / MD。PDF 需要是可选中文字的版本；扫描版需先 OCR。</div>",
    "<div class=\"file-drop\" id=\"dropMod\">点击选择文件，或拖到这里</div>",
    "<input type=\"file\" id=\"fileMod\" accept=\".docx,.pdf,.txt,.md\" style=\"display:none\">",
    "<div class=\"label\">或粘贴模组正文</div>",
    "<div class=\"field\"><textarea id=\"pasteMod\" rows=\"10\"></textarea></div>"
  ].join("");
  openModal("导入模组", html, "<button id=\"doImportMod\" class=\"btn primary\">导入并切分</button>", false);

  const drop = el("dropMod"), file = el("fileMod");
  drop.onclick = () => file.click();
  drop.ondragover = e => { e.preventDefault(); drop.style.borderColor = "var(--accent2)"; };
  drop.ondragleave = () => { drop.style.borderColor = ""; };
  drop.ondrop = async e => {
    e.preventDefault(); drop.style.borderColor = "";
    if (e.dataTransfer.files.length) await readModFile(e.dataTransfer.files[0]);
  };
  file.onchange = async () => { if (file.files.length) await readModFile(file.files[0]); };

  el("doImportMod").onclick = async () => {
    const txt = el("pasteMod").value.trim();
    const title = el("m_title").value.trim() || "未命名模组";
    if (!txt) { toast("没有内容"); return; }
    await doModImport(title, txt, "");
  };
}

async function readModFile(f) {
  const title = el("m_title").value.trim() || f.name.replace(/\.[^.]+$/, "");
  const name = f.name.toLowerCase();
  if (name.endsWith(".docx") || name.endsWith(".pdf")) {
    toast("正在解析 " + f.name + "…");
    const b64 = await fileToBase64(f);
    const r = await POST("/api/module_import", { title, filename: f.name, base64: b64 });
    if (r.error) { toast(r.error); return; }
    closeModal(); await refreshModules();
    toast("已导入：" + r.acts + " 幕 / " + r.chars + " 字");
    return;
  }
  const txt = await f.text();
  await doModImport(title, txt, f.name);
}

async function doModImport(title, text, filename) {
  // 导入时问一次要不要顺手把世界书、会话、绑定都做好
  const LF = String.fromCharCode(10);
  let auto = confirm(
    "导入后要不要自动完成这些？" + LF + LF +
    "① 让模型读模组，起草世界书（写进当前世界）" + LF +
    "② 新建一个会话并绑定到第 1 幕" + LF +
    "③ 自动写一段开场白" + LF + LF +
    "选「取消」= 只导入，其他步骤你自己来。"
  );
  const body = { title, text, filename };
  if (auto) {
    body.auto = true;
    body.world = S.world && S.world !== "default" ? S.world : "COC通用";
    body.session = title;
  }
  if (auto) {
    const wname = body.world;
    const okOverwrite = confirm(
      "即将让模型读这份模组，起草世界书并写进「" + wname + "」世界。" + LF + LF +
      "如果这个世界已经有世界书，会先自动备份成 worldbook.bak-before-<时间>.md，然后覆盖。" + LF + LF +
      "继续？"
    );
    if (!okOverwrite) { auto = false; body.auto = false; }
  }
  toast(auto ? "正在导入并起草世界书，稍等…" : "正在导入…");
  const r = await POST("/api/module_import", body);
  if (r.error) { toast(r.error); return; }
  closeModal();
  await refreshModules();
  try {
    const w2 = await API("/api/worlds");
    S.worlds = w2.worlds || [];
    fillWorlds();
  } catch (e) { /* 世界列表刷新失败不影响主流程 */ }

  if (!auto) {
    toast("已导入：" + r.acts + " 幕 / " + r.chars + " 字 / 约 " + r.tokens + " token");
    return;
  }

  const notes = [];
  if (r.worldbook_note) notes.push("世界书：" + r.worldbook_note);
  if (r.session) {
    S.world = r.world || S.world;
    if (el("worldSelect")) el("worldSelect").value = S.world;
    await openSession(r.session);
    notes.push("会话：" + r.session + "（第 1 幕）");
  }
  if (r.session_note) notes.push(r.session_note);
  toast("已导入 " + r.acts + " 幕。" + LF + notes.join(LF));

  if (r.session && !r.session_note) {
    setTimeout(() => autoOpening(), 300);
  }
}


// ==================== 检定提示卡片（2026-11-01 强化）====================
// KP 在正文末尾用〔检定〕技能名 · 技能值 · 理由 要求检定，
// 下一行用「→ 请掷「技能」（数值）」提示玩家操作。
// 这里渲染成醒目的提示条：标题写「该掷什么」+ 理由 + 掷骰按钮。
// 把正文里模型自己写的「→ 请掷…」行剥掉：卡片会重新生成更清楚的一版，
// 否则界面上会出现两条重复的提示。模型不写这行也没关系，卡片照样有。
function stripCheckHint(text) {
  const lines = String(text || "").split(String.fromCharCode(10));
  const out = [];
  for (const ln of lines) {
    const t = ln.trim();
    if (t.startsWith("→") && t.indexOf("请掷") >= 0) continue;
    out.push(ln);
  }
  return out.join(String.fromCharCode(10)).trim();
}

function parseCheck(text) {
  const pat = "〔检定〕" + "\s*([^·" + "\n]+?)" + "\s*·" + "\s*(" + "\d+)" + "\s*·" + "\s*([^" + "\n]*)";
  const re = new RegExp(pat, "g");
  const out = [];
  let m;
  while ((m = re.exec(text)) !== null) {
    out.push({ skill: m[1].trim(), value: parseInt(m[2], 10), reason: m[3].trim() });
  }
  return out;
}

function renderCheckCard(checks, hostEl) {
  if (!checks.length) return;
  const box = document.createElement("div");
  box.className = "check-card";
  const head = document.createElement("div");
  head.className = "check-head";
  head.textContent = "该掷骰了";
  box.appendChild(head);

  // 说明条：告诉玩家两种掷骰方式，不懂 COC 也能操作
  const tip = document.createElement("div");
  tip.className = "check-tip";
  const noCard = !S.meta || !S.meta.card_id;
  if (noCard) {
    tip.className = "check-tip warn";
    tip.textContent = "⚠️ 这个会话还没绑定角色卡，数值是 COC 默认值。想用自己的卡，去「准备 → 角色卡」建好并绑定。";
  } else {
    tip.textContent = "点右边「掷骰」自动掷 d100 并回传 KP；也可以自己去右上角骰子面板掷，再把结果打给 KP。";
  }
  box.appendChild(tip);

  checks.forEach(c => {
    const row = document.createElement("div");
    row.className = "check-row";

    const main = document.createElement("div");
    main.className = "check-main";
    const label = document.createElement("div");
    label.className = "check-label";
    label.textContent = "请掷「" + c.skill + "」 · 目标值 " + c.value;
    main.appendChild(label);
    if (c.reason) {
      const reason = document.createElement("div");
      reason.className = "check-reason";
      reason.textContent = c.reason;
      main.appendChild(reason);
    }

    const btn = document.createElement("button");
    btn.className = "btn primary check-btn";
    btn.textContent = "掷骰";
    btn.title = "点一下自动掷 d100 并把结果发给 KP";
    btn.onclick = async () => {
      btn.disabled = true;
      btn.textContent = "…";
      try {
        const r = await POST("/api/roll", { mode: "coc", skill: c.value, label: c.skill });
        const res = r.result || {};
        btn.textContent = res.roll + " · " + res.grade;
        btn.className = "btn check-btn " + (res.success ? "ok" : "fail");
        // 结果也显示在卡片上，玩家能看到掷了什么
        const fb = document.createElement("div");
        fb.className = "check-fb " + (res.success ? "ok" : "fail");
        fb.textContent = "d100 = " + res.roll + " → " + res.grade +
                         "（目标 " + c.value + "）";
        main.appendChild(fb);
        const ta = el("input");
        if (ta && !S.busy) {
          ta.value = "【检定：" + c.skill + " d100=" + res.roll + "，结果 " + res.grade + "】" +
                     (c.reason ? "（" + c.reason + "）" : "") + "我继续。";
          await send();
        }
      } catch (e) {
        btn.disabled = false;
        btn.textContent = "掷骰";
        toast("掷骰失败：" + (e && e.message ? e.message : e));
      }
    };

    row.appendChild(main);
    row.appendChild(btn);
    box.appendChild(row);
  });
  hostEl.appendChild(box);
}

async function autoOpening() {
  if (!S.cur) return;
  if (S.busy) { setTimeout(autoOpening, 800); return; }
  toast("正在生成开场白…");
  const ta = el("input");
  if (!ta) return;
  ta.value = "（开场）请描写这一幕的开场：交代时间、地点、在场人物与当前氛围，把调查员放进场景里。\n\n" +
             "【硬性约束】只写「调查员在这里、周围是什么样子、有什么正在发生」，" +
             "**不要**写调查员做了任何动作、说了任何话、有任何心理活动或决定。" +
             "调查员的第一个动作由玩家自己决定。写到可以开始行动的那一刻就停。";
  await send();
}
// ==================== 队友 ====================
async function refreshTeam() {
  const r = await API("/api/teammates");
  S.team = r.teammates || [];
  const box = el("teamList");
  box.innerHTML = "";
  if (!S.team.length) { box.innerHTML = "<div class=\"hint\">还没有队友</div>"; return; }
  S.team.forEach(t => {
    const d = document.createElement("div");
    d.className = "tm-item";
    const prov = t.provider === "cloud" ? "云端 · " + esc(t.model || "?") : "本地 · " + esc(t.model || "?");
    d.innerHTML = "<div class=\"nm\"><span>" + esc(t.name) + "</span>" +
      "<span class=\"" + (t.enabled ? "badge-on" : "badge-off") + "\">" + (t.enabled ? "● 启用" : "○ 停用") + "</span></div>" +
      "<div class=\"sub\">" + esc(t.role || "未设定位") + "　" + prov + "</div>";
    d.onclick = () => editTeam(t.id);
    box.appendChild(d);
  });
}

async function editTeam(tid, forceCardId) {
  let t;
  if (tid) {
    t = S.team.find(x => x.id === tid);
  } else if (S.pendingTeam) {
    // 从酒馆卡导入回来的缓存值
    t = S.pendingTeam;
    S.pendingTeam = null;
  } else {
    t = {
      id: "", name: "新队友", enabled: true, role: "", persona: "", card_id: "",
      provider: "local", model: "kp-qwen3", api_base: "", api_key: "",
      temperature: 0.8, max_tokens: 500, has_key: false
    };
  }
  if (!t) return;
  if (forceCardId) t.card_id = forceCardId;
  const presets = S.metaInfo.cloud_presets || {};
  let html = "";
  html += "<div class=\"field-row\">";
  html += "<div class=\"field\"><span>名字</span><input id=\"t_name\" value=\"" + esc(t.name) + "\"></div>";
  html += "<div class=\"field\"><span>定位（一句话）</span><input id=\"t_role\" value=\"" + esc(t.role) + "\" placeholder=\"独臂副官 / 冷面医生\"></div>";
  html += "</div>";
  html += "<div class=\"field\">";
  html += "<span style=\"display:flex;justify-content:space-between;align-items:center\">";
  html += "<span>性格与说话方式（人设）</span>";
  html += "<button id=\"tTavern\" class=\"btn ghost small\" type=\"button\">导入酒馆角色卡</button>";
  html += "</span>";
  html += "<textarea id=\"t_persona\" rows=\"5\" placeholder=\"话少，说话像钉子。对玩家保持审视，但关键时刻第一个站出来。\">" + esc(t.persona) + "</textarea></div>";
  html += "<div class=\"field\">";
  html += "<span style=\"display:flex;justify-content:space-between;align-items:center\">";
  html += "<span>关联角色卡（可选，让队友有自己的属性与技能）</span>";
  html += "<span style=\"display:flex;gap:5px\">";
  html += "<button id=\"tNewCard\" class=\"btn ghost small\" type=\"button\">新建</button>";
  html += "<button id=\"tImpCard\" class=\"btn ghost small\" type=\"button\">导入</button>";
  html += "</span></span>";
  html += "<select id=\"t_card\">";
  html += "<option value=\"\">（不绑定）</option>";
  S.cards.forEach(c => {
    html += "<option value=\"" + esc(c.id) + "\"" + (c.id === t.card_id ? " selected" : "") + ">" + esc(c.name) + (c.occupation ? " · " + esc(c.occupation) : "") + "</option>";
  });
  html += "</select></div>";

  html += "<div class=\"label\">模型来源</div>";
  html += "<div class=\"tabs\">";
  html += "<button class=\"tab" + (t.provider !== "cloud" ? " active" : "") + "\" data-prov=\"local\">本地 Ollama</button>";
  html += "<button class=\"tab" + (t.provider === "cloud" ? " active" : "") + "\" data-prov=\"cloud\">云端 API Key</button>";
  html += "</div>";

  html += "<div id=\"prov_local\" style=\"display:" + (t.provider === "cloud" ? "none" : "flex") + ";flex-direction:column;gap:9px\">";
  html += "<div class=\"field\"><span>本地模型名</span><input id=\"t_model\" value=\"" + esc(t.model) + "\" list=\"modelList\"><datalist id=\"modelList\">";
  (S.status && S.status.models ? S.status.models : []).forEach(m => { html += "<option value=\"" + esc(m) + "\">"; });
  html += "</datalist></div>";
  html += "<div class=\"hint\">可以用同一个 kp-qwen3，也可以装个小模型（如 qwen3:4b-instruct）专跑队友，省显存。</div>";
  html += "</div>";

  html += "<div id=\"prov_cloud\" style=\"display:" + (t.provider === "cloud" ? "flex" : "none") + ";flex-direction:column;gap:9px\">";
  html += "<div class=\"field\"><span>服务商预设</span><select id=\"t_preset\">";
  Object.keys(presets).forEach(k => { html += "<option value=\"" + esc(k) + "\">" + esc(k) + "</option>"; });
  html += "</select></div>";
  html += "<div class=\"field\"><span>API 地址（OpenAI 兼容）</span><input id=\"t_base\" value=\"" + esc(t.api_base) + "\" placeholder=\"https://api.deepseek.com/v1\"></div>";
  html += "<div class=\"field\"><span>API Key" + (t.has_key ? "（已保存，留空则不改）" : "") + "</span><input id=\"t_key\" type=\"password\" placeholder=\"" + (t.has_key ? "已保存 " + esc(t.api_key_masked || "") : "sk-...") + "\"></div>";
  html += "<div class=\"field\"><span>模型名</span><input id=\"t_cmodel\" value=\"" + esc(t.provider === "cloud" ? (t.model || "") : "") + "\" placeholder=\"deepseek-chat\"></div>";
  html += "<div class=\"hint\">Key 存在本机 teammates.json，不会上传到任何地方。跑团时只会发场景与最近几轮对话给云端。</div>";
  html += "</div>";

  html += "<div class=\"field-row\">";
  html += "<div class=\"field\"><span>温度</span><input id=\"t_temp\" type=\"number\" step=\"0.05\" value=\"" + t.temperature + "\"></div>";
  html += "<div class=\"field\"><span>单次输出上限</span><input id=\"t_max\" type=\"number\" value=\"" + t.max_tokens + "\"></div>";
  html += "<div class=\"field\"><span>启用</span><select id=\"t_enabled\"><option value=\"1\"" + (t.enabled ? " selected" : "") + ">是</option><option value=\"0\"" + (!t.enabled ? " selected" : "") + ">否</option></select></div>";
  html += "</div>";

  const foot = [
    "<button id=\"testTeam\" class=\"btn ghost\">测试连接</button>",
    tid ? "<button id=\"delTeam\" class=\"btn ghost\" style=\"color:#a33\">删除</button>" : "",
    "<button id=\"saveTeam\" class=\"btn primary\">保存</button>"
  ].join("");
  openModal("队友设置", html, foot, false);

  let prov = t.provider || "local";
  document.querySelectorAll("#modalBody .tab").forEach(tab => {
    tab.onclick = () => {
      document.querySelectorAll("#modalBody .tab").forEach(x => x.classList.remove("active"));
      tab.classList.add("active");
      prov = tab.dataset.prov;
      el("prov_local").style.display = prov === "cloud" ? "none" : "flex";
      el("prov_cloud").style.display = prov === "cloud" ? "flex" : "none";
    };
  });
  if (el("tTavern")) el("tTavern").onclick = () => importTavernForTeam(t);

  if (el("tNewCard")) el("tNewCard").onclick = async () => {
    const nm = el("t_name").value.trim() || "队友";
    const c = await API("/api/card_new?name=" + encodeURIComponent(nm));
    const saved = await POST("/api/card", { card: c });
    await refreshCards();
    // 回到队友面板，自动选中新卡
    t.card_id = saved.id;
    editTeam(t.id || null, saved.id);
    toast("已新建角色卡：" + nm + "（可在「角色卡」里细调）");
  };

  if (el("tImpCard")) el("tImpCard").onclick = () => {
    importCardForTeam(t);
  };
  if (el("t_preset")) el("t_preset").onchange = () => {
    const p = presets[el("t_preset").value];
    if (p && p.base) el("t_base").value = p.base;
    if (p && p.models && p.models.length) el("t_cmodel").value = p.models[0];
  };

  const collect = () => {
    const item = Object.assign({}, t);
    item.name = el("t_name").value.trim() || "队友";
    item.role = el("t_role").value.trim();
    item.persona = el("t_persona").value.trim();
    item.card_id = el("t_card").value;
    item.provider = prov;
    item.temperature = parseFloat(el("t_temp").value) || 0.8;
    item.max_tokens = parseInt(el("t_max").value) || 500;
    item.enabled = el("t_enabled").value === "1";
    if (prov === "cloud") {
      item.api_base = el("t_base").value.trim();
      item.model = el("t_cmodel").value.trim();
      const k = el("t_key").value.trim();
      if (k) item.api_key = k;
    } else {
      item.model = el("t_model").value.trim();
    }
    return item;
  };

  el("saveTeam").onclick = async () => {
    const item = collect();
    if (item.provider === "cloud" && !item.api_key) { toast("云端队友需要 API Key"); return; }
    await POST("/api/teammate", { teammate: item });
    closeModal(); await refreshTeam(); toast("已保存");
  };
  el("testTeam").onclick = async () => {
    const item = collect();
    toast("正在测试…");
    const r = await POST("/api/teammate_test", { teammate: item });
    if (r.ok) toast("连接成功 · " + r.ms + "ms · 回复：" + r.reply);
    else toast("失败：" + r.error);
  };
  if (el("delTeam")) el("delTeam").onclick = async () => {
    if (!confirm("删除这个队友？")) return;
    await POST("/api/teammate_delete", { id: t.id });
    closeModal(); await refreshTeam();
  };
}
// ==================== 关系图 ====================
async function refreshRel() {
  S.rel = await API("/api/relations");
  if (!S.rel.nodes) S.rel = { nodes: [], edges: [] };
}

function openRelEditor() {
  const relTypes = S.metaInfo.rel_types || [];
  let html = "<div class=\"rel-wrap\">";
  html += "<div id=\"relCanvas\"><svg id=\"relSvg\"></svg></div>";
  html += "<div class=\"rel-side\">";
  html += "<div class=\"field\"><span>添加角色节点</span><div style=\"display:flex;gap:6px\">";
  html += "<input id=\"relNewName\" placeholder=\"名字\" style=\"flex:1\">";
  html += "<button id=\"relAddNode\" class=\"btn small\">加</button></div></div>";
  html += "<div class=\"field\"><span>添加关系</span>";
  html += "<select id=\"relFrom\" class=\"select\"></select>";
  html += "<select id=\"relType\" class=\"select\" style=\"margin-top:4px\">";
  relTypes.forEach(t => { html += "<option value=\"" + esc(t.key) + "\">" + esc(t.name) + "</option>"; });
  html += "</select>";
  html += "<select id=\"relTo\" class=\"select\" style=\"margin-top:4px\"></select>";
  html += "<input id=\"relNote\" placeholder=\"备注（可选）\" style=\"margin-top:4px;background:var(--bg);border:1px solid var(--line);border-radius:6px;color:var(--text);padding:7px 9px;font-family:inherit;font-size:12px\">";
  html += "<button id=\"relAddEdge\" class=\"btn small\" style=\"margin-top:6px\">建立关系</button></div>";
  html += "<div class=\"label\">全部关系</div><div id=\"relEdgeList\" style=\"display:flex;flex-direction:column;gap:5px\"></div>";
  html += "</div></div>";
  const foot = "<button id=\"relSave\" class=\"btn primary\">保存关系图</button>";
  openModal("角色关系", html, foot, true);

  const canvas = el("relCanvas");
  const svg = el("relSvg");
  let drag = null, ox = 0, oy = 0;

  const W = () => canvas.clientWidth;
  const H = () => canvas.clientHeight;

  // 初始布局：环形
  if (S.rel.nodes.length) {
    const cx = W() / 2 || 380, cy = H() / 2 || 230, R = Math.min(cx, cy) * 0.62;
    S.rel.nodes.forEach((n, i) => {
      if (n.x == null || n.y == null) {
        const ang = (i / S.rel.nodes.length) * Math.PI * 2 - Math.PI / 2;
        n.x = cx + Math.cos(ang) * R;
        n.y = cy + Math.sin(ang) * R;
      }
    });
  }

  function relayout() {
    const n = S.rel.nodes.length;
    if (!n) return;
    const cx = (W() || 760) / 2, cy = (H() || 460) / 2;
    const R = Math.max(70, Math.min(cx, cy) * 0.66);
    S.rel.nodes.forEach((nd, i) => {
      const ang = (i / n) * Math.PI * 2 - Math.PI / 2;
      nd.x = cx + Math.cos(ang) * R;
      nd.y = cy + Math.sin(ang) * R;
    });
  }

  function draw() {
    canvas.querySelectorAll(".rel-node").forEach(x => x.remove());
    const byId = {};
    S.rel.nodes.forEach(n => { byId[n.id] = n; });
    let svgHtml = "";
    const defs = "<defs><marker id=\"ar\" viewBox=\"0 0 10 10\" refX=\"9\" refY=\"5\" markerWidth=\"6\" markerHeight=\"6\" orient=\"auto-start-reverse\"><path d=\"M 0 0 L 10 5 L 0 10 z\" fill=\"#7a4a2a\"/></marker></defs>";
    svgHtml += defs;
    S.rel.edges.forEach(e => {
      const a = byId[e.from], b = byId[e.to];
      if (!a || !b) return;
      svgHtml += "<line x1=\"" + a.x + "\" y1=\"" + a.y + "\" x2=\"" + b.x + "\" y2=\"" + b.y + "\" stroke=\"#7a4a2a\" stroke-width=\"" + (1 + (e.strength || 3) * 0.4) + "\" marker-end=\"url(#ar)\" opacity=\"0.75\"/>";
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      const label = (S.metaInfo.rel_types || []).find(t => t.key === e.type);
      svgHtml += "<text x=\"" + mx + "\" y=\"" + (my - 5) + "\" fill=\"#8b8078\" font-size=\"11\" text-anchor=\"middle\">" + esc(label ? label.name : e.type) + "</text>";
    });
    svg.innerHTML = svgHtml;

    S.rel.nodes.forEach(n => {
      const d = document.createElement("div");
      d.className = "rel-node" + (n.kind === "player" ? " player" : "");
      d.style.left = n.x + "px";
      d.style.top = n.y + "px";
      d.textContent = n.label;
      d.onmousedown = ev => {
        ev.preventDefault();
        drag = n;
        const r = canvas.getBoundingClientRect();
        ox = ev.clientX - r.left - n.x;
        oy = ev.clientY - r.top - n.y;
      };
      canvas.appendChild(d);
    });
    refreshSelects();
    refreshEdgeList();
  }

  canvas.onmousemove = ev => {
    if (!drag) return;
    const r = canvas.getBoundingClientRect();
    drag.x = ev.clientX - r.left - ox;
    drag.y = ev.clientY - r.top - oy;
    draw();
  };
  canvas.onmouseup = () => { drag = null; };
  canvas.onmouseleave = () => { drag = null; };

  function refreshSelects() {
    const from = el("relFrom"), to = el("relTo");
    if (!from) return;
    const opts = S.rel.nodes.map(n => "<option value=\"" + esc(n.id) + "\">" + esc(n.label) + "</option>").join("");
    from.innerHTML = opts;
    to.innerHTML = opts;
    if (S.rel.nodes.length > 1) to.selectedIndex = 1;
  }

  function refreshEdgeList() {
    const box = el("relEdgeList");
    if (!box) return;
    const byId = {};
    S.rel.nodes.forEach(n => { byId[n.id] = n.label; });
    box.innerHTML = "";
    if (!S.rel.edges.length) { box.innerHTML = "<div class=\"hint\">还没有关系</div>"; return; }
    S.rel.edges.forEach(e => {
      const lab = (S.metaInfo.rel_types || []).find(t => t.key === e.type);
      const d = document.createElement("div");
      d.className = "rel-edge-item";
      d.innerHTML = "<span>" + esc(byId[e.from] || "?") + " → " + esc(byId[e.to] || "?") + "：" + esc(lab ? lab.name : e.type) + "</span>";
      const x = document.createElement("span");
      x.className = "x"; x.textContent = "×";
      x.onclick = () => { S.rel.edges = S.rel.edges.filter(z => z.id !== e.id); draw(); };
      d.appendChild(x);
      box.appendChild(d);
    });
  }

  el("relAddNode").onclick = () => {
    const nm = el("relNewName").value.trim();
    if (!nm) return;
    if (S.rel.nodes.some(n => n.label === nm)) { toast("已存在"); return; }
    S.rel.nodes.push({
      id: "n" + Date.now() + Math.floor(Math.random() * 1000),
      label: nm, kind: "npc", card_id: "", note: "", x: null, y: null
    });
    el("relNewName").value = "";
    relayout();
    draw();
  };

  el("relAddEdge").onclick = () => {
    const f = el("relFrom").value, t2 = el("relTo").value;
    if (f === t2) { toast("不能连自己"); return; }
    const dup = S.rel.edges.some(e => e.from === f && e.to === t2 && e.type === el("relType").value);
    if (dup) { toast("这条关系已存在"); return; }
    S.rel.edges.push({
      id: "e" + Date.now() + Math.floor(Math.random() * 1000),
      from: f, to: t2, type: el("relType").value,
      note: el("relNote").value.trim(), strength: 3
    });
    el("relNote").value = "";
    draw();
  };

  el("relSave").onclick = async () => {
    await POST("/api/relations", { data: S.rel });
    toast("关系图已保存");
  };

  setTimeout(draw, 60);
}
// ==================== 世界 / 设置 / 其他 ====================
function editWorld() {
  const name = el("worldSelect").value;
  API("/api/world?name=" + encodeURIComponent(name)).then(w => {
    const html = [
      "<div class=\"tabs\">",
      "<button class=\"tab active\" data-t=\"prompt\">系统提示词</button>",
      "<button class=\"tab\" data-t=\"worldbook\">世界书</button>",
      "<button class=\"tab\" data-t=\"characters\">角色卡文本</button>",
      "</div>",
      "<div class=\"field\"><textarea id=\"wt_prompt\" rows=\"20\">" + esc(w.prompt || "") + "</textarea></div>",
      "<div class=\"field\" style=\"display:none\"><textarea id=\"wt_worldbook\" rows=\"20\">" + esc(w.worldbook || "") + "</textarea></div>",
      "<div class=\"field\" style=\"display:none\"><textarea id=\"wt_characters\" rows=\"20\">" + esc(w.characters || "") + "</textarea></div>",
      "<div class=\"hint\">世界书建议 ≤8000 字（约 5800 token）。中文 1 字 ≈ 0.72 token，窗口 24576。</div>"
    ].join("");
    const foot = "<button id=\"saveWorld\" class=\"btn primary\">保存</button><button id=\"newWorld\" class=\"btn ghost\">另存为新世界</button>";
    openModal("编辑世界：" + name, html, foot, true);

    document.querySelectorAll("#modalBody .tab").forEach(t => {
      t.onclick = () => {
        document.querySelectorAll("#modalBody .tab").forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        ["prompt", "worldbook", "characters"].forEach(k => {
          el("wt_" + k).parentElement.style.display = (k === t.dataset.t) ? "flex" : "none";
        });
      };
    });

    const gather = () => ({
      name,
      prompt: el("wt_prompt").value,
      worldbook: el("wt_worldbook").value,
      characters: el("wt_characters").value,
    });

    el("saveWorld").onclick = async () => {
      await POST("/api/world", gather());
      toast("已保存");
    };
    el("newWorld").onclick = async () => {
      const nn = prompt("新世界名字");
      if (!nn) return;
      const g = gather(); g.name = nn;
      await POST("/api/world", g);
      const w2 = await API("/api/worlds");
      S.worlds = w2.worlds || [];
      fillWorlds();
      el("worldSelect").value = nn;
      S.world = nn;
      closeModal();
      toast("已另存为 " + nn);
    };
  });
}

function openSettings() {
  const c = S.cfg;
  const backend = c.kp_backend || "ollama";
  const isCloud = backend === "openai";
  const html = [
    // ── 后端选择 ──
    "<div class=\"field\"><span>模型后端</span>",
    "<select id=\"cf_backend\">",
    "<option value=\"ollama\"" + (isCloud ? "" : " selected") + ">本地 Ollama（免费、离线、需显卡/内存）</option>",
    "<option value=\"openai\"" + (isCloud ? " selected" : "") + ">云端 API（任意 OpenAI 兼容接口，不用显卡）</option>",
    "</select></div>",

    // ── 本地 Ollama 段 ──
    "<div id=\"grp_ollama\" style=\"display:" + (isCloud ? "none" : "block") + "\">",
    "<div class=\"field\"><span>Ollama 地址</span><input id=\"cf_ollama\" value=\"" + esc(c.ollama) + "\"></div>",
    "<div class=\"field\"><span>KP 模型名</span><input id=\"cf_model\" value=\"" + esc(c.model) + "\"></div>",
    "<div class=\"field\"><span>上下文长度（8G 显存上限 24576，超过会 OOM）</span><input id=\"cf_ctx\" type=\"number\" value=\"" + c.num_ctx + "\"></div>",
    "</div>",

    // ── 云端 API 段 ──
    "<div id=\"grp_cloud\" style=\"display:" + (isCloud ? "block" : "none") + "\">",
    "<div class=\"field\"><span>API 地址（base，不要带 /chat/completions）</span>",
    "<input id=\"cf_base\" placeholder=\"https://api.deepseek.com/v1\" value=\"" + esc(c.kp_api_base || "") + "\"></div>",
    "<div class=\"field\"><span>API Key（留空则读环境变量 KP_API_KEY）</span>",
    "<input id=\"cf_key\" type=\"password\" placeholder=\"sk-...\" value=\"" + esc(c.kp_api_key || "") + "\"></div>",
    "<div class=\"field\"><span>云端模型名</span>",
    "<input id=\"cf_apimodel\" placeholder=\"deepseek-chat\" value=\"" + esc(c.kp_api_model || "") + "\"></div>",
    "<div class=\"hint\" style=\"font-size:12px;line-height:1.6\">常见地址：",
    "<br>DeepSeek　https://api.deepseek.com/v1　模型 deepseek-chat",
    "<br>智谱　　　https://open.bigmodel.cn/api/paas/v4　模型 glm-4-flash",
    "<br>Moonshot　https://api.moonshot.cn/v1　模型 moonshot-v1-32k",
    "<br>OpenRouter https://openrouter.ai/api/v1",
    "<br>本地 vLLM/LM Studio　http://127.0.0.1:8000/v1",
    "</div>",
    "</div>",

    // ── 通用参数 ──
    "<div class=\"field\"><span>单轮输出上限</span><input id=\"cf_np\" type=\"number\" value=\"" + c.num_predict + "\"></div>",
    "<div class=\"field\"><span>温度</span><input id=\"cf_temp\" type=\"number\" step=\"0.05\" value=\"" + c.temperature + "\"></div>",
    "<div class=\"field\"><span>滑窗轮数</span><input id=\"cf_win\" type=\"number\" value=\"" + c.window + "\"></div>",
    "<div class=\"field\"><span>每几轮压缩记忆（0=不自动）</span><input id=\"cf_ce\" type=\"number\" value=\"" + c.compress_every + "\"></div>",
  ].join("");
  openModal("设置", html, "<button id=\"saveCfg\" class=\"btn primary\">保存</button>", false);

  // 切换后端时显示/隐藏对应分组
  el("cf_backend").onchange = () => {
    const cloud = el("cf_backend").value === "openai";
    el("grp_ollama").style.display = cloud ? "none" : "block";
    el("grp_cloud").style.display = cloud ? "block" : "none";
  };

  el("saveCfg").onclick = async () => {
    const next = {
      kp_backend: el("cf_backend").value,
      ollama: el("cf_ollama").value.trim(),
      model: el("cf_model").value.trim(),
      num_ctx: parseInt(el("cf_ctx").value) || 24576,
      kp_api_base: el("cf_base").value.trim(),
      kp_api_key: el("cf_key").value.trim(),
      kp_api_model: el("cf_apimodel").value.trim(),
      num_predict: parseInt(el("cf_np").value) || 1600,
      temperature: parseFloat(el("cf_temp").value) || 0.85,
      window: parseInt(el("cf_win").value) || 6,
      compress_every: parseInt(el("cf_ce").value),
    };
    if (isNaN(next.compress_every)) next.compress_every = 8;
    const r = await POST("/api/config", next);
    S.cfg = r.config;
    closeModal(); await refreshStatus(); toast("已保存");
  };
}

async function doAudit() {
  if (!S.cur) return;
  openModal("伏笔审计", "<div class=\"hint\">正在让 KP 想办法把旧伏笔塞回剧情…</div>", "", false);
  const r = await POST("/api/audit", { session: S.cur });
  el("modalBody").innerHTML = "<div class=\"hint\" style=\"white-space:pre-wrap\">" + esc(r.error || r.audit) + "</div>";
}

async function doCompress() {
  if (!S.cur) return;
  openModal("压缩记忆", "<div class=\"hint\">正在压缩…</div>", "", false);
  const r = await POST("/api/compress", { session: S.cur });
  el("modalBody").innerHTML = "<div class=\"hint\" style=\"white-space:pre-wrap\">" + esc(r.error || r.summary || "（对话还不够多）") + "</div>";
}

// ==================== 绑定 ====================
el("send").onclick = send;
el("newSession").onclick = newSession;
el("editWorld").onclick = editWorld;
el("settingsBtn").onclick = openSettings;
el("auditBtn").onclick = doAudit;
el("compressBtn").onclick = doCompress;
el("modalClose").onclick = closeModal;
el("newCard").onclick = () => editCard(null);
el("importCard").onclick = importCard;
el("importModule").onclick = importModule;
el("newTeam").onclick = () => editTeam(null);
el("openRel").onclick = openRelEditor;
el("worldSelect").onchange = e => { S.world = e.target.value; updateBindBox(); };

document.querySelectorAll(".t2").forEach(t => {
  t.onclick = () => {
    document.querySelectorAll(".t2").forEach(x => x.classList.remove("active"));
    t.classList.add("active");
    el("tab-play").classList.toggle("hidden", t.dataset.tab !== "play");
    el("tab-prep").classList.toggle("hidden", t.dataset.tab !== "prep");
  };
});

el("input").addEventListener("keydown", e => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); }
});

boot();
// ==================== 骰子 ====================
const D = { log: [], system: "coc7" };

function diceToggle(show) {
  const p = el("dicePanel");
  const on = show === undefined ? p.classList.contains("hidden") : show;
  p.classList.toggle("hidden", !on);
  if (on) buildDiceQuick();
}

function buildDiceQuick() {
  const box = el("diceQuick");
  const isDnd = D.system === "dnd5e";
  const list = isDnd
    ? [["d20", "d20"], ["d20 优", "adv"], ["d20 劣", "dis"], ["d4", "1d4"], ["d6", "1d6"], ["d8", "1d8"],
       ["d10", "1d10"], ["d12", "1d12"], ["d100", "1d100"]]
    : [["d100", "1d100"], ["d10", "1d10"], ["d6", "1d6"], ["d4", "1d4"], ["d8", "1d8"],
       ["d20", "1d20"], ["2d6", "2d6"], ["3d6", "3d6"], ["d3", "1d3"]];
  box.innerHTML = "";
  list.forEach(([label, expr]) => {
    const b = document.createElement("button");
    b.textContent = label;
    b.onclick = () => {
      if (expr === "adv" || expr === "dis") {
        rollDnd(expr === "adv", expr === "dis");
      } else {
        el("diceExpr").value = expr;
        rollExpr();
      }
    };
    box.appendChild(b);
  });
  buildDiceCheck();
}

function buildDiceCheck() {
  const box = el("diceCheck");
  if (D.system === "dnd5e") {
    box.innerHTML = [
      "<div class=\"row\"><span class=\"tag\">检定</span>",
      "<input id=\"dMod\" type=\"number\" value=\"0\" title=\"调整值\">",
      "<span class=\"tag\">DC</span>",
      "<input id=\"dDc\" type=\"number\" value=\"15\" title=\"难度\">",
      "<button id=\"dCheck\" class=\"btn small\">d20 检定</button></div>",
      "<div class=\"row\"><span class=\"tag\">伤害</span>",
      "<input id=\"dDmg\" placeholder=\"1d8+3\" style=\"flex:1;background:var(--bg);border:1px solid var(--line);border-radius:5px;color:var(--text);padding:5px 7px;font-family:inherit;font-size:12px\">",
      "<button id=\"dDmgRoll\" class=\"btn small\">掷</button></div>"
    ].join("");
    el("dCheck").onclick = () => rollDnd(false, false);
    el("dDmgRoll").onclick = () => {
      const e = el("dDmg").value.trim() || "1d8";
      el("diceExpr").value = e;
      rollExpr();
    };
  } else {
    box.innerHTML = [
      "<div class=\"row\"><span class=\"tag\">技能</span>",
      "<input id=\"dSkill\" type=\"number\" value=\"50\" title=\"技能值\">",
      "<span class=\"tag\">奖励</span>",
      "<input id=\"dBonus\" type=\"number\" value=\"0\" min=\"0\" max=\"2\" title=\"奖励骰\">",
      "<span class=\"tag\">惩罚</span>",
      "<input id=\"dPen\" type=\"number\" value=\"0\" min=\"0\" max=\"2\" title=\"惩罚骰\">",
      "</div>",
      "<div class=\"row\"><input id=\"dLabel\" placeholder=\"技能名（如 侦查）\" style=\"flex:1;background:var(--bg);border:1px solid var(--line);border-radius:5px;color:var(--text);padding:5px 7px;font-family:inherit;font-size:12px\">",
      "<button id=\"dCheck\" class=\"btn primary small\">检定</button></div>"
    ].join("");
    el("dCheck").onclick = () => rollCoc();
  }
}

async function rollExpr() {
  const expr = el("diceExpr").value.trim() || "1d100";
  const r = await POST("/api/roll", { mode: "expr", expr, session: S.cur || "" });
  if (r.error) { toast(r.error); return; }
  pushDice(r.result);
}

async function rollCoc() {
  const r = await POST("/api/roll", {
    mode: "coc",
    skill: parseInt(el("dSkill").value) || 50,
    bonus: parseInt(el("dBonus").value) || 0,
    penalty: parseInt(el("dPen").value) || 0,
    label: el("dLabel").value.trim(),
    session: S.cur || "",
  });
  if (r.error) { toast(r.error); return; }
  pushDice(r.result);
}

async function rollDnd(adv, dis) {
  const modEl = el("dMod"), dcEl = el("dDc");
  const r = await POST("/api/roll", {
    mode: "dnd",
    modifier: modEl ? (parseInt(modEl.value) || 0) : 0,
    dc: dcEl ? (parseInt(dcEl.value) || 10) : 10,
    advantage: adv, disadvantage: dis,
    session: S.cur || "",
  });
  if (r.error) { toast(r.error); return; }
  pushDice(r.result);
}

function pushDice(res) {
  D.log.unshift(res);
  if (D.log.length > 30) D.log.pop();
  renderDice();
}

function renderDice() {
  const box = el("diceLog");
  box.innerHTML = "";
  D.log.forEach(r => {
    const d = document.createElement("div");
    d.className = "dp-item";
    if (r.system === "coc") {
      const cls = r.grade === "大成功" ? "crit" : (r.grade === "大失败" ? "fumble" : (r.success ? "success" : "fail"));
      d.classList.add(cls);
      d.innerHTML = "<div class=\"big\">" + r.roll + "</div>" +
        "<div class=\"sub\">" + esc(r.label || "检定") + " · " + esc(r.grade) + " · 技能 " + r.skill + "</div>";
    } else if (r.system === "dnd") {
      const cls = r.crit === "大成功" ? "crit" : (r.crit === "大失败" ? "fumble" : (r.success ? "success" : "fail"));
      d.classList.add(cls);
      d.innerHTML = "<div class=\"big\">" + r.total + "</div>" +
        "<div class=\"sub\">" + (r.label ? esc(r.label) + " · " : "") + esc(r.detail) +
        (r.mode !== "普通" ? " · " + esc(r.mode) : "") +
        (r.crit ? " · " + esc(r.crit) : "") + "</div>";
    } else {
      d.innerHTML = "<div class=\"big\">" + r.total + "</div>" +
        "<div class=\"sub\">" + esc(r.expr) + " = " + esc(r.detail) + "</div>";
    }
    box.appendChild(d);
  });
}

el("diceToggle").onclick = () => diceToggle();
el("diceClose").onclick = () => diceToggle(false);
el("diceRoll").onclick = rollExpr;
el("diceExpr").addEventListener("keydown", e => { if (e.key === "Enter") rollExpr(); });
el("sysSelect").onchange = e => {
  D.system = e.target.value;
  buildDiceQuick();
  toast("规则切换为 " + (D.system === "coc7" ? "COC 7e" : "DND 5e") + "（只影响骰子与新建卡）");
};

function bindCardEditor(c, id) {
  const upd = () => refreshPoints();

  document.querySelectorAll("#modalBody [data-attr]").forEach(inp => {
    inp.oninput = () => {
      S.curCard.attrs[inp.dataset.attr] = parseInt(inp.value) || 1;
      recalcLive();
      upd();
    };
  });
  el("c_age").oninput = () => { S.curCard.age = parseInt(el("c_age").value) || 25; recalcLive(); upd(); };
  el("c_mythos").oninput = () => { S.curCard.mythos = parseInt(el("c_mythos").value) || 0; recalcLive(); upd(); };

  el("c_occ").onchange = () => {
    S.curCard.occupation = el("c_occ").value;
    const def = S.occDefs[S.curCard.occupation];
    if (def && def.points) {
      el("occ_formula").value = def.points.map(p => p[0] + "x" + p[1]).join(" + ");
    }
    upd();
  };

  el("occ_formula").oninput = () => upd();

  el("occSave").onclick = async () => {
    const nm = prompt("自定义职业名字", S.curCard.occupation || "自定义职业");
    if (!nm) return;
    const pts = parseFormula(el("occ_formula").value);
    const r = await POST("/api/occ_custom", { name: nm, points: pts });
    if (r.error) { toast(r.error); return; }
    S.occDefs = r.occupations || S.occDefs;
    S.metaInfo.occ_defs = S.occDefs;
    S.curCard.occupation = nm;
    S.curCard.custom_occ = true;
    renderCardEditor(S.curCard, "编辑角色卡", id);
    toast("已存为自定义职业：" + nm);
  };

  el("occAuto").onclick = async () => {
    collectCard();
    const sr = await POST("/api/card", { card: S.curCard });
    if (!sr.ok) { toast("保存失败"); return; }
    S.curCard.id = sr.id;
    const r = await POST("/api/points", { card_id: sr.id, action: "auto_fill", cap: 70 });
    if (r.error) { toast(r.error); return; }
    S.curCard = r.card || S.curCard;
    renderCardEditor(S.curCard, "编辑角色卡", id);
    toast("自动填了 " + (r.report.filled || []).length + " 个技能，剩 " + r.report.left + " 点");
  };

  document.querySelectorAll("#modalBody .pt").forEach(inp => {
    inp.oninput = () => { upd(); };
  });

  el("itemAdd").onclick = () => {
    const nm = el("itemName").value.trim();
    const qty = parseInt(el("itemQty").value) || 1;
    if (!nm) return;
    S.curCard.equipment = S.curCard.equipment || [];
    S.curCard.equipment.push({ name: nm, qty: qty });
    el("itemName").value = "";
    el("itemQty").value = "1";
    renderItems();
  };
  el("itemName").onkeydown = e => { if (e.key === "Enter") el("itemAdd").click(); };
  renderItems();

  el("saveCard").onclick = async () => {
    collectCard();
    const r = await POST("/api/card", { card: S.curCard });
    if (r.ok) { toast("已保存"); S.curCard.id = r.id; await refreshCards(); }
  };
  el("rollCard").onclick = async () => {
    const cc = await API("/api/card_random");
    S.curCard = cc;
    renderCardEditor(cc, "随机角色卡（改完记得保存）", S.curCard.id || "");
  };
  if (el("bindCard")) el("bindCard").onclick = async () => {
    if (!S.cur) { toast("先开一个会话"); return; }
    collectCard();
    const r = await POST("/api/card", { card: S.curCard });
    S.curCard.id = r.id;
    await POST("/api/session_meta", { session: S.cur, card_id: r.id });
    S.meta.card_id = r.id;
    await refreshCards();
    updateBindBox();
    toast("已绑定到 " + S.cur);
  };
  if (el("delCard")) el("delCard").onclick = async () => {
    if (!confirm("删除这张角色卡？")) return;
    await POST("/api/card_delete", { id: S.curCard.id });
    closeModal(); await refreshCards();
  };

  upd();
}
function parseFormula(text) {
  const out = [];
  const parts = String(text).split("+");
  for (const p of parts) {
    const m = p.trim().match(new RegExp("^([A-Za-z]{3})\s*[xX*]\s*(\d+)$"));
    if (m) out.push([m[1].toUpperCase(), parseInt(m[2])]);
  }
  return out.length ? out : [["EDU", 4]];
}

function renderItems() {
  const box = el("itemList");
  if (!box) return;
  const items = S.curCard.equipment || [];
  box.innerHTML = "";
  if (!items.length) {
    box.innerHTML = "<div class=\"hint\" style=\"padding:6px 0\">还没有物品</div>";
    return;
  }
  items.forEach((it, idx) => {
    const d = document.createElement("div");
    d.className = "item-row";
    const nm = typeof it === "string" ? it : (it.name || "");
    const qty = typeof it === "string" ? 1 : (it.qty || 1);
    d.innerHTML = "<span>" + esc(nm) + (qty > 1 ? " ×" + qty : "") + "</span>";
    const x = document.createElement("span");
    x.className = "x";
    x.textContent = "×";
    x.onclick = () => { S.curCard.equipment.splice(idx, 1); renderItems(); };
    d.appendChild(x);
    box.appendChild(d);
  });
}

function collectPoints() {
  const c = S.curCard;
  c.skills = c.skills || {};
  ["occ", "int", "free"].forEach(kind => {
    document.querySelectorAll("#modalBody [data-" + kind + "]").forEach(inp => {
      const k = inp.dataset[kind];
      if (!k || !S.metaInfo.skills.some(s => s.key === k)) return;
      c.skills[k] = c.skills[k] || {};
      c.skills[k][kind + "_add"] = parseInt(inp.value) || 0;
    });
  });
}

function refreshPoints() {
  collectPoints();
  const c = S.curCard;
  const attrs = c.attrs || {};
  const occ = c.occupation || "";
  const def = S.occDefs[occ];
  const pf = (def && def.points) ? def.points : parseFormula(el("occ_formula").value);
  let occTotal = 0;
  pf.forEach(p => { occTotal += (parseInt(attrs[p[0]]) || 0) * p[1]; });
  const intTotal = (parseInt(attrs.INT) || 0) * 2;

  let occUsed = 0, intUsed = 0, freeUsed = 0;
  (S.metaInfo.skills || []).forEach(s => {
    const rec = c.skills[s.key] || {};
    const o = rec.occ_add || 0, i = rec.int_add || 0, f = rec.free_add || 0;
    const v = s.base + o + i + f;
    const totEl = document.querySelector("[data-tot=\"" + s.key + "\"]");
    const halfEl = document.querySelector("[data-half=\"" + s.key + "\"]");
    const fifthEl = document.querySelector("[data-fifth=\"" + s.key + "\"]");
    if (totEl) { totEl.textContent = v; totEl.style.color = (v > 70) ? "#c66" : ""; }
    if (halfEl) halfEl.textContent = Math.floor(v / 2);
    if (fifthEl) fifthEl.textContent = Math.floor(v / 5);
    occUsed += o; intUsed += i; freeUsed += f;
  });

  const bar = el("pointBar");
  if (!bar) return;
  const occLeft = occTotal - occUsed;
  const intLeft = intTotal - intUsed;
  const cls = v => v < 0 ? "over" : (v === 0 ? "full" : "");
  bar.innerHTML = [
    "<div class=\"pb " + cls(occLeft) + "\"><span>职业点</span><b>" + occLeft + " / " + occTotal + "</b>",
    "<em>已用 " + occUsed + "</em></div>",
    "<div class=\"pb " + cls(intLeft) + "\"><span>兴趣点</span><b>" + intLeft + " / " + intTotal + "</b>",
    "<em>已用 " + intUsed + "（INT×2）</em></div>",
    "<div class=\"pb neutral\"><span>单纯加点</span><b>" + freeUsed + "</b>",
    "<em>不算成长，不占池子</em></div>"
  ].join("");
}
// ==================== 酒馆卡导入（队友人设） ====================
function importTavernForTeam(t) {
  // 导入弹窗会覆盖队友编辑框，先把现有值抓到内存里
  const snap = {
    name: el("t_name") ? el("t_name").value : (t.name || ""),
    role: el("t_role") ? el("t_role").value : (t.role || ""),
    persona: el("t_persona") ? el("t_persona").value : (t.persona || ""),
    card_id: el("t_card") ? el("t_card").value : (t.card_id || ""),
  };
  const html = [
    "<div class=\"hint\">支持酒馆（SillyTavern）导出的 <b>PNG 角色卡</b> 或 <b>JSON</b>。<br>",
    "只取「性格」与「外形」两段，开场白、对话示例、世界书都不会导入。</div>",
    "<div class=\"file-drop\" id=\"dropTv\">点击选择文件，或拖到这里</div>",
    "<input type=\"file\" id=\"fileTv\" accept=\".png,.json\" style=\"display:none\">",
    "<div class=\"label\">或粘贴角色卡 JSON</div>",
    "<div class=\"field\"><textarea id=\"pasteTv\" rows=\"6\" placeholder=\"把酒馆卡的 JSON 粘这里\"></textarea></div>",
    "<div id=\"tvResult\"></div>"
  ].join("");
  const foot = "<button id=\"tvApply\" class=\"btn primary\" disabled>应用为人设</button>";
  openModal("导入酒馆角色卡", html, foot, false);

  let parsed = null;

  const show = (p) => {
    parsed = p;
    const box = el("tvResult");
    if (!p.has_any) {
      box.innerHTML = "<div class=\"callout warn\">这张卡里没找到性格或外形字段。</div>";
      el("tvApply").disabled = true;
      return;
    }
    box.innerHTML = [
      "<div class=\"label\">预览</div>",
      "<div class=\"tv-preview\">",
      "<div class=\"tv-name\">" + esc(p.name || "（无名）") + "</div>",
      p.personality ? "<div class=\"tv-sec\"><b>性格</b><p>" + esc(p.personality) + "</p></div>" : "",
      p.appearance ? "<div class=\"tv-sec\"><b>外形</b><p>" + esc(p.appearance) + "</p></div>" : "",
      "</div>"
    ].join("");
    el("tvApply").disabled = false;
  };

  const handle = async (file) => {
    const b64 = await fileToBase64(file);
    const r = await POST("/api/tavern_import", { filename: file.name, base64: b64 });
    if (r.error) { toast(r.error); return; }
    show(r.persona);
  };

  const drop = el("dropTv"), file = el("fileTv");
  drop.onclick = () => file.click();
  drop.ondragover = e => { e.preventDefault(); drop.style.borderColor = "var(--accent2)"; };
  drop.ondragleave = () => { drop.style.borderColor = ""; };
  drop.ondrop = async e => {
    e.preventDefault(); drop.style.borderColor = "";
    if (e.dataTransfer.files.length) await handle(e.dataTransfer.files[0]);
  };
  file.onchange = async () => { if (file.files.length) await handle(file.files[0]); };

  el("tvApply").onclick = () => {
    if (!parsed) return;
    const merged = parsed.merged || "";
    const cur = (snap.persona || "").trim();
    snap.persona = cur ? (cur + String.fromCharCode(10) + merged) : merged;
    // 名字是空或占位符时，用导入卡的名字
    const isPlaceholder = !snap.name.trim() || snap.name === "新队友" || snap.name === "队友";
    if (isPlaceholder && parsed.name) snap.name = parsed.name;
    closeModal();
    // 重开队友编辑框，把缓存值填回去
    const item = Object.assign({}, t);
    item.name = snap.name;
    item.role = snap.role;
    item.persona = snap.persona;
    item.card_id = snap.card_id;
    S.pendingTeam = item;
    editTeam(item.id || null);
    toast("已应用人设" + (parsed.name ? "：" + parsed.name : ""));
  };
}
function importCardForTeam(t) {
  const html = [
    "<div class=\"hint\">支持 JSON、纯文本（自动抽属性）、DOCX、PDF。</div>",
    "<div class=\"file-drop\" id=\"dropTc\">点击选择文件，或拖到这里</div>",
    "<input type=\"file\" id=\"fileTc\" accept=\".json,.txt,.md,.docx,.pdf\" style=\"display:none\">",
    "<div class=\"label\">或粘贴文本</div>",
    "<div class=\"field\"><textarea id=\"pasteTc\" rows=\"8\"></textarea></div>"
  ].join("");
  openModal("导入角色卡给队友", html, "<button id=\"doTc\" class=\"btn primary\">导入</button>", false);

  const handle = async (file) => {
    const nm = file.name.toLowerCase();
    let r;
    if (nm.endsWith(".docx") || nm.endsWith(".pdf")) {
      const b64 = await fileToBase64(file);
      r = await POST("/api/card_import", { filename: file.name, base64: b64 });
    } else {
      const txt = await file.text();
      r = await POST("/api/card_import", { filename: file.name, text: txt });
    }
    if (r.error) { toast(r.error); return; }
    closeModal();
    await refreshCards();
    t.card_id = r.card.id;
    editTeam(t.id || null, r.card.id);
    toast("已导入并绑定：" + r.card.name + (r.warn ? "（" + r.warn + "）" : ""));
  };

  const drop = el("dropTc"), file = el("fileTc");
  drop.onclick = () => file.click();
  drop.ondragover = e => { e.preventDefault(); drop.style.borderColor = "var(--accent2)"; };
  drop.ondragleave = () => { drop.style.borderColor = ""; };
  drop.ondrop = async e => {
    e.preventDefault(); drop.style.borderColor = "";
    if (e.dataTransfer.files.length) await handle(e.dataTransfer.files[0]);
  };
  file.onchange = async () => { if (file.files.length) await handle(file.files[0]); };

  el("doTc").onclick = async () => {
    const txt = el("pasteTc").value.trim();
    if (!txt) { toast("没有内容"); return; }
    const r = await POST("/api/card_import", { filename: "", text: txt });
    if (r.error) { toast(r.error); return; }
    closeModal();
    await refreshCards();
    t.card_id = r.card.id;
    editTeam(t.id || null, r.card.id);
    toast("已导入并绑定：" + r.card.name);
  };
}