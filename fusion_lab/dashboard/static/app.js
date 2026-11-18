"use strict";
const D = {};
const SZ = { A: "Rücksetzer", B: "Ausbruch", C: "Abwarten" };
const PW_LABEL = { trend: "Trend", momentum: "Momentum", qualitaet: "Qualität", wachstum: "Wachstum",
  bewertung: "Bewertung", bilanz: "Bilanz", analysten: "Analysten", rel_staerke: "Rel. Stärke",
  liquiditaet: "Liquidität", verwaesserung: "Verwässerung", funding: "Funding", abstand_hoch: "Nähe Hoch", cot: "COT (contra)",
  kennzahlen_score: "Kennzahlen" };

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (x, d = 2) => x == null || isNaN(x) ? "–" : Number(x).toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d });
const px = x => x == null ? "–" : Math.abs(x) >= 1 ? num(x, 2) : Math.abs(x) >= 0.01 ? num(x, 4) : num(x, 8);
const pct = (x, d = 1) => x == null || isNaN(x) ? "–" : `<span class="${x >= 0 ? "pos" : "neg"}">${x >= 0 ? "+" : ""}${num(x, d)} %</span>`;
const sigColor = s => s === "KAUFEN" ? "var(--green)" : s === "VERKAUFEN" ? "var(--red)" : "var(--yellow)";
const ring = (score, signal) => `<div class="ring" style="--p:${Math.round(score)};--c:${sigColor(signal)}"><span>${Math.round(score)}</span></div>`;
const llmOk = c => c.llm && !c.llm.fehler;
const KIND = { aktien: "Aktien", krypto: "Krypto", rohstoffe: "Rohstoff" };
const URTEIL = { bullisch: "KAUFEN", neutral: "HALTEN", "bärisch": "VERKAUFEN" };

async function load(name) {
  try { const r = await fetch(`data/${name}.json`, { cache: "no-store" }); return r.ok ? await r.json() : null; }
  catch { return null; }
}

function kpi(l, v, s = "") { return `<div class="kpi"><div class="l">${l}</div><div class="v">${v}</div><div class="s">${s}</div></div>`; }

function card(c, kind) {
  const ch = llmOk(c) ? c.llm.szenario : null;
  const s = ch && c.szenarien[ch];
  const line = ch === "A" && s ? `A Rücksetzer ${px(s.zone_lo)}–${px(s.zone_hi)}`
    : ch === "B" && s ? `B Ausbruch über ${px(s.trigger)}` : ch === "C" ? "C Abwarten" : "Einordnung n.v.";
  return `<div class="card" data-kind="${kind}" data-obj="${esc(c.objekt)}">
    <div class="row"><div><div class="t">${esc(c.objekt)}</div><div class="n">${esc(c.name)}</div></div>${ring(c.gesamt, c.signal)}</div>
    <div class="row sc"><span class="sig ${c.signal}">${c.signal}</span><span class="muted">${px(c.kurs)}</span></div>
    <div class="sc">${esc(line)}${llmOk(c) ? ` · Stimmung ${c.llm.sentiment > 0 ? "+" : ""}${c.llm.sentiment}` : ""}</div></div>`;
}

function marketKpis() {
  const a = D.aktien, k = D.krypto, out = [];
  if (a) out.push(kpi("S&P 500 (SPY)", px(a.kontext.spy.kurs), `${esc(a.kontext.spy.trend)} · 21 T ${pct(a.kontext.spy.ret_21d)}`));
  if (k) {
    out.push(kpi("Bitcoin", px(k.kontext.btc.kurs), `${esc(k.kontext.btc.trend)} · 21 T ${pct(k.kontext.btc.ret_21d)}`));
    const f = k.kontext.fear_greed;
    if (f) out.push(kpi("Fear & Greed", f.wert, `${esc(f.einstufung)} · vor 7 T ${f.vor_7_tagen}`));
  }
  const ro = D.rohstoffe;
  if (ro?.kontext) {
    const lw = ro.kontext.leitwerte || {}, NAMES = { GOLD: "Gold", WTI: "WTI-Öl", KUPFER: "Kupfer" };
    for (const [key, n] of Object.entries(NAMES)) if (lw[key]) out.push(kpi(n, px(lw[key].kurs), `${esc(lw[key].trend)} · 21 T ${pct(lw[key].ret_21d)}`));
  }
  const m = (a || k || ro)?.kontext?.makro;
  if (m) out.push(kpi("Makro-Zustand", esc(m.zustand), `Fact Sheet ${esc(m.stand)}`));
  for (const [n, r] of [["Aktien", a], ["Krypto", k], ["Rohstoffe", ro?.stand ? ro : null]]) if (r)
    out.push(kpi(`Signale ${n}`, `<span class="pos">${r.signale.KAUFEN || 0}</span> · <span style="color:var(--yellow)">${r.signale.HALTEN || 0}</span> · <span class="neg">${r.signale.VERKAUFEN || 0}</span>`, `von ${r.anzahl} · Stand ${r.stand}`));
  return `<div class="kpis">${out.join("")}</div>`;
}

function renderOverview() {
  const el = document.getElementById("uebersicht");
  let h = marketKpis();
  for (const [kind, title] of [["aktien", "Aktien – Tiefen-Analyse"], ["krypto", "Krypto – Tiefen-Analyse"], ["rohstoffe", "Rohstoffe – Tiefen-Analyse"]]) {
    const r = D[kind];
    if (kind === "rohstoffe" && r && !r.tief.length) { h += `<h2>${title}</h2>${wocheGrid(r)}`; continue; }
    h += `<h2>${title}</h2>` + (r ? `<div class="grid">${[...r.tief].sort((x, y) => y.gesamt - x.gesamt).map(c => card(c, kind)).join("")}</div>`
      : `<div class="empty">Noch kein Lauf</div>`);
  }
  el.innerHTML = h;
}

function renderScreener(kind) {
  const r = D[kind], el = document.getElementById(kind);
  const woche = kind === "rohstoffe" && r ? `<h2>Wochen-Tiefenanalyse</h2><div class="note">1× pro Woche je Rohstoff (News, Sentiment, Makro, Angebot/Nachfrage, Technik). Tippen öffnet die ganze Analyse.</div>${wocheGrid(r)}` : "";
  if (!r || !r.tabelle.length) { el.innerHTML = `<div class="empty">Noch kein ${KIND[kind]}-Lauf</div>${woche}`; return; }
  const cols = Object.keys(r.tabelle[0] || {}).filter(k => PW_LABEL[k] && k !== "kennzahlen_score");
  el.innerHTML = `<div class="note">Score 0–100 · <b>≥ ${r.schwellen.kaufen} KAUFEN</b> · <b>≤ ${r.schwellen.verkaufen} VERKAUFEN</b>.
      Tiefen-Kandidaten: ${Math.round((1 - r.schwellen.sentiment_gewicht) * 100)} % Kennzahlen + ${Math.round(r.schwellen.sentiment_gewicht * 100)} % News-Stimmung.
      Der Score ist eine Bewertung, keine geprüfte Trefferwahrscheinlichkeit – das misst der Forward-Test.</div>
    <h2>Tiefen-Analyse · Stand ${r.stand}</h2><div class="grid">${r.tief.map(c => card(c, kind)).join("")}</div>
    ${woche}
    <h2>Alle ${r.anzahl} ${kind === "rohstoffe" ? "Rohstoffe" : "Titel"}</h2>
    <div class="toolbar"><input type="search" placeholder="Suchen …" data-k="${kind}">
      ${["ALLE", "KAUFEN", "HALTEN", "VERKAUFEN"].map((s, i) => `<button class="chip${i ? "" : " on"}" data-f="${s}" data-k="${kind}">${s === "ALLE" ? "Alle" : s}</button>`).join("")}</div>
    <div class="tablewrap"><table data-k="${kind}"><thead><tr>
      <th class="l" data-s="index">Titel</th><th data-s="gesamt">Score</th><th class="l" data-s="signal">Signal</th><th data-s="kurs">Kurs</th><th data-s="ret_21d">21 T</th>
      ${cols.map(c => `<th data-s="${c}">${PW_LABEL[c]}</th>`).join("")}</tr></thead><tbody></tbody></table></div>`;
  const st = { q: "", f: "ALLE", s: "gesamt", dir: -1 };
  const tbody = el.querySelector("tbody");
  const draw = () => {
    const rows = r.tabelle.filter(x => (st.f === "ALLE" || x.signal === st.f) &&
      (!st.q || `${x.index} ${x.name}`.toLowerCase().includes(st.q)))
      .sort((a, b) => { const va = a[st.s], vb = b[st.s]; return (typeof va === "string" ? String(va).localeCompare(vb) : (va ?? -1e9) - (vb ?? -1e9)) * st.dir; });
    tbody.innerHTML = rows.map(x => `<tr data-kind="${kind}" data-obj="${esc(x.index)}"><td class="l"><b>${esc(x.index)}</b> <span class="muted">${esc((x.name || "").slice(0, 26))}</span></td>
      <td><b>${num(x.gesamt, 0)}</b></td><td class="l"><span class="sig ${x.signal}">${x.signal}</span></td><td>${px(x.kurs)}</td><td>${pct(x.ret_21d)}</td>
      ${cols.map(c => `<td>${num(x[c], 0)}</td>`).join("")}</tr>`).join("");
  };
  el.querySelector("input").oninput = e => { st.q = e.target.value.toLowerCase(); draw(); };
  el.querySelectorAll(".chip").forEach(b => b.onclick = () => { st.f = b.dataset.f; el.querySelectorAll(".chip").forEach(x => x.classList.toggle("on", x === b)); draw(); });
  el.querySelectorAll("th").forEach(th => th.onclick = () => { const k = th.dataset.s; st.dir = st.s === k ? -st.dir : -1; st.s = k; draw(); });
  draw();
}

function wocheGrid(r) {
  const w = Object.entries(r.tief_woche || {});
  if (!w.length) return `<div class="empty">Noch keine Wochenanalyse</div>`;
  return `<div class="grid">${w.map(([key, x]) => {
    const h = x.kopf || {}, sig = URTEIL[h.urteil_kurz] || "HALTEN";
    return `<div class="card" data-kind="woche" data-obj="${esc(key)}">
      <div class="row"><div><div class="t">${esc(key)}</div><div class="n">Wochenanalyse ${esc(x.datum)}</div></div><span class="sig ${sig}">${esc(h.urteil_kurz || "–")}</span></div>
      <div class="sc">kurzfristig <b>${esc(h.urteil_kurz || "–")}</b> · strukturell <b>${esc(h.urteil_struktur || "–")}</b> · Szenario ${esc(h.szenario || "–")}</div>
      <div class="sc muted">${esc(h.fazit || "")}</div></div>`;
  }).join("")}</div>`;
}

function wocheHtml(key) {
  const x = D.rohstoffe?.tief_woche?.[key];
  if (!x) return "";
  const h = x.kopf || {};
  const md = window.marked ? marked.parse(x.markdown) : `<pre>${esc(x.markdown)}</pre>`;
  return `<div class="note"><b>Treiber:</b> ${esc((h.treiber || []).join(" · "))}<br><b>Termine:</b> ${esc((h.termine || []).join(" · "))}</div>
    <div class="card md" style="cursor:default">${md}</div>`;
}

function openWoche(key) {
  const x = D.rohstoffe?.tief_woche?.[key];
  if (!x) return;
  document.getElementById("detail-body").innerHTML = `<h2 style="margin-top:0">${esc(key)} · Wochen-Tiefenanalyse ${esc(x.datum)}</h2>${wocheHtml(key)}`;
  document.querySelectorAll("#detail-body .md a").forEach(a => { a.target = "_blank"; a.rel = "noopener"; });
  document.getElementById("detail").classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function scenCard(k, s, chosen) {
  if (!s) return `<div class="card"><b>${k} ${SZ[k]}</b><div class="muted sc">nicht gültig (kein Chance-Risiko ≥ 2)</div></div>`;
  const rows = k === "A" ? [["Zone", `${px(s.zone_lo)} – ${px(s.zone_hi)}`], ["Einstieg (Limit)", px(s.einstieg)]] : [["Trigger (Stop-Kauf)", px(s.trigger)]];
  rows.push(["Stopp", px(s.stopp)], ["Ziel", px(s.ziel)], ["Chance-Risiko", num(s.rr, 1)]);
  return `<div class="card${chosen ? " chosen" : ""}"><b>${k} ${SZ[k]}</b>${chosen ? ' <span class="sig KAUFEN">gewählt</span>' : ""}
    <div class="kv" style="margin-top:8px">${rows.map(([a, b]) => `<div><span>${a}</span>${b}</div>`).join("")}</div>
    <div class="muted" style="font-size:11px;margin-top:6px">Marken: ${esc((s.marken || []).join(", "))}</div></div>`;
}

function openDetail(kind, obj) {
  if (kind === "woche") return openWoche(obj);
  const r = D[kind]; if (!r) return;
  const c = r.tief.find(x => x.objekt === obj);
  const row = r.tabelle.find(x => x.index === obj);
  const body = document.getElementById("detail-body");
  if (!c) {
    const pw = Object.keys(PW_LABEL).filter(k => row && row[k] != null);
    body.innerHTML = `<h2 style="margin-top:0">${esc(obj)} · ${esc(row?.name)}</h2>
      <div class="row" style="display:flex;gap:12px;align-items:center">${ring(row.gesamt, row.signal)}<span class="sig ${row.signal}">${row.signal}</span><span>${px(row.kurs)}</span></div>
      <h2>Punktwerte</h2>${pw.map(k => `<div class="pw"><span>${PW_LABEL[k]}</span><div class="bar"><i style="width:${row[k]}%"></i></div><b>${num(row[k], 0)}</b></div>`).join("")}
      <div class="note">Nur Kennzahlen-Score. Volle Analyse mit Preisbereichen und News gibt es für die Top-Kandidaten und die Watchlist.</div>`;
  } else {
    const L = c.llm || {};
    const ch = llmOk(c) ? L.szenario : null;
    body.innerHTML = `<h2 style="margin-top:0">${esc(c.objekt)} · ${esc(c.name)}</h2>
      <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">${ring(c.gesamt, c.signal)}<span class="sig ${c.signal}">${c.signal}</span>
        <span class="muted">Kurs</span><b>${px(c.kurs)}</b><span class="muted">Stand ${r.stand}</span>
        ${llmOk(c) ? `<span class="muted">Überzeugung</span><b>${esc(L.ueberzeugung)}</b>` : ""}</div>
      <div id="chart" class="chart"></div>
      <div class="legend"><span><b style="background:var(--blue)"></b>Zone A</span><span><b style="background:var(--gold)"></b>Trigger B</span><span><b style="background:var(--red)"></b>Stopp</span><span><b style="background:var(--green)"></b>Ziel</span></div>
      <h2>Szenarien</h2><div class="scen">${["A", "B"].map(k => scenCard(k, c.szenarien[k], ch === k)).join("")}
        <div class="card${ch === "C" ? " chosen" : ""}"><b>C Abwarten</b>${ch === "C" ? ' <span class="sig HALTEN">gewählt</span>' : ""}<div class="muted sc">${esc(c.szenarien.C?.text)}</div></div></div>
      ${llmOk(c) ? `<div class="note"><b>Wahl ${L.szenario} ${SZ[L.szenario]}:</b> ${esc(L.szenario_grund)}<br><b>Hauptrisiko:</b> ${esc(L.hauptrisiko)}
          ${L.warnungen?.length ? `<br>⚠️ ${esc(L.warnungen.join("; "))}` : ""}</div>
        <h2>News & Stimmung (${L.sentiment > 0 ? "+" : ""}${L.sentiment})</h2><p style="font-size:14px">${esc(L.sentiment_grund)}</p>
        <ul class="clean">${L.news.map(n => `<li>${esc(n.aussage)} <span class="muted">(${esc(n.quelle)})</span></li>`).join("")}</ul>
        <div class="scen"><div class="card"><b class="pos">Pro</b><ul class="clean">${L.pro.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>
          <div class="card"><b class="neg">Contra</b><ul class="clean">${L.contra.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div></div>`
        : `<div class="note">LLM-Einordnung nicht verfügbar${L.fehler ? ": " + esc(L.fehler) : ""}.</div>`}
      <h2>Punktwerte</h2>${Object.entries(c.punktwerte).map(([k, v]) => `<div class="pw"><span>${PW_LABEL[k] || k}</span><div class="bar"><i style="width:${v}%"></i></div><b>${num(v, 0)}</b></div>`).join("")}
      <h2>Technik</h2><div class="kv">${[["RSI 14", num(c.technik.rsi14, 1)], ["ATR %", num(c.technik.atr_pct, 1)], ["SMA 20", px(c.technik.sma20)], ["SMA 50", px(c.technik.sma50)],
        ["SMA 200", px(c.technik.sma200)], ["52W-Hoch", px(c.technik.hoch_52w)], ["52W-Tief", px(c.technik.tief_52w)], ["21 T", pct(c.technik.ret_21d)], ["63 T", pct(c.technik.ret_63d)]]
        .map(([a, b]) => `<div><span>${a}</span>${b}</div>`).join("")}</div>
      <h2>Kennzahlen</h2><div class="kv">${Object.entries(c.kennzahlen || {}).filter(([, v]) => v != null && typeof v !== "object")
        .map(([k, v]) => `<div><span>${esc(k)}</span>${typeof v === "number" ? (Math.abs(v) > 1e6 ? num(v / 1e9, 1) + " Mrd." : num(v, Math.abs(v) < 10 ? 3 : 1)) : esc(v)}</div>`).join("")}</div>
      ${kind === "rohstoffe" && c.kennzahlen?.cot_managed_money ? (() => { const k = c.kennzahlen.cot_managed_money;
        return `<h2>COT Managed Money</h2><div class="kv">${[["Bericht", esc(k.bericht)], ["Netto", num(k.netto, 0)], ["Vorwoche", num(k.veraenderung_1w, 0)],
          ["% Open Interest", num(k.netto_pct_oi, 1)], ["COT-Index 3 J.", num(k.cot_index, 0)]].map(([a, b]) => `<div><span>${a}</span>${b}</div>`).join("")}</div>`; })() : ""}
      ${kind === "rohstoffe" && D.rohstoffe?.tief_woche?.[obj] ? `<h2>Wochen-Tiefenanalyse (${esc(D.rohstoffe.tief_woche[obj].datum)})</h2><details><summary>aufklappen</summary>${wocheHtml(obj)}</details>` : ""}
      <h2>Schlagzeilen</h2><ul class="clean news">${(c.schlagzeilen || []).map(n => `<li><a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.titel)}</a> <span class="muted">· ${esc(n.quelle)} · ${esc(n.zeit)}</span></li>`).join("") || "<li class='muted'>keine</li>"}</ul>`;
    drawChart(c);
  }
  document.getElementById("detail").classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function drawChart(c) {
  const el = document.getElementById("chart");
  if (!el || !window.LightweightCharts || !c.chart?.length) return;
  const chart = LightweightCharts.createChart(el, { autoSize: true, layout: { background: { color: "transparent" }, textColor: "#8b919a" },
    grid: { vertLines: { color: "#1d2128" }, horzLines: { color: "#1d2128" } }, rightPriceScale: { borderColor: "#262b33" },
    timeScale: { borderColor: "#262b33" }, crosshair: { mode: 0 } });
  const s = chart.addCandlestickSeries({ upColor: "#2fbf71", downColor: "#e5484d", borderVisible: false, wickUpColor: "#2fbf71", wickDownColor: "#e5484d",
    priceFormat: { type: "price", precision: c.kurs < 1 ? 6 : 2, minMove: c.kurs < 1 ? 0.000001 : 0.01 } });
  s.setData(c.chart.map(([t, o, h, l, cl]) => ({ time: t, open: o, high: h, low: l, close: cl })));
  const line = (price, color, title, style = 2) => price != null && s.createPriceLine({ price, color, lineWidth: 1, lineStyle: style, axisLabelVisible: true, title });
  const A = c.szenarien.A, B = c.szenarien.B;
  if (A) { line(A.zone_hi, "#5aa2ff", "A oben", 0); line(A.zone_lo, "#5aa2ff", "A unten", 0); line(A.stopp, "#e5484d", "Stopp A"); line(A.ziel, "#2fbf71", "Ziel A"); }
  if (B) { line(B.trigger, "#d4af37", "Trigger B", 0); line(B.stopp, "#e5484d", "Stopp B"); line(B.ziel, "#2fbf71", "Ziel B"); }
  chart.timeScale().fitContent();
}

function renderMakro() {
  const el = document.getElementById("makro"), m = D.makro;
  if (!m) { el.innerHTML = `<div class="empty">Kein Makro-Fact-Sheet gefunden</div>`; return; }
  const ind = Object.entries(m.indikatoren || {}).map(([k, v]) => kpi(esc(k), num(v, 2))).join("");
  const geo = (m.geopolitik || []).map(g => `<div class="card" style="cursor:default"><div class="row"><b>${esc(g.name || g.thema)}</b>
      <span class="sig ${g.lage === "eskalation" ? "VERKAUFEN" : g.lage === "entspannung" ? "KAUFEN" : "HALTEN"}">${esc(g.lage || "–")}</span></div>
      <div class="sc">${esc(g.kernaussage || "")}</div></div>`).join("");
  el.innerHTML = `<div class="kpis">${kpi("Zustand", esc(m.zustand), `Stand ${esc(m.stand)}`)}${ind}</div>
    ${geo ? `<h2>Geopolitik</h2><div class="grid">${geo}</div>` : ""}
    <h2>Fact Sheet</h2><div class="card md" style="cursor:default">${m.fact_sheet_md && window.marked ? marked.parse(m.fact_sheet_md) : "<p class='muted'>nicht verfügbar</p>"}</div>`;
  el.querySelectorAll(".md a").forEach(a => { a.target = "_blank"; a.rel = "noopener"; });
}

function renderForward() {
  const el = document.getElementById("forward");
  const b = (D.aktien || D.krypto || D.rohstoffe)?.bilanz || {};
  const blocks = Object.entries(b).map(([k, v]) => {
    const g = Object.entries(v.gruppen || {}).map(([gk, gv]) => `<tr><td class="l">${esc(gk.replace("_", " · "))} T</td><td>${gv.n}</td>
      <td>${pct(gv.rendite, 2)}</td><td>${pct(gv.minus_univ, 2)}</td><td>${pct(gv.minus_bench, 2)}</td></tr>`).join("");
    return `<h2>${esc(k.replace("_", " · "))}</h2><div class="kpis">${kpi("Offene Szenarien", v.szenarien_offen)}${kpi("Gefüllt", v.gefuellt)}
      ${kpi("Ø R", v.avg_r == null ? "–" : num(v.avg_r, 2))}${kpi("Trefferquote", v.trefferquote == null ? "–" : num(v.trefferquote, 0) + " %")}
      ${kpi("Summe R", v.summe_r == null ? "–" : num(v.summe_r, 1))}${kpi("Gewählt Ø R", v.gewaehlt_avg_r == null ? "–" : num(v.gewaehlt_avg_r, 2), `n ${v.gewaehlt_n}`)}
      ${kpi("Nicht gefüllt", v.nicht_gefuellt)}</div>
      ${g ? `<div class="tablewrap" style="margin-top:10px"><table><thead><tr><th class="l">Gruppe · Horizont</th><th>n</th><th>Rendite</th><th>− Universum</th><th>− Benchmark</th></tr></thead><tbody>${g}</tbody></table></div>` : ""}`;
  }).join("");
  el.innerHTML = `<div class="note">Forward-Test: Jede Aussage wird mit Datum ins Ledger geschrieben und erst mit späteren Kursen ausgewertet.
    <b>Probe</b> = vor dem offiziellen Forward-Start (zählt nicht). Erfolg = Ø R &gt; 0 nach Kosten <b>und</b> KAUFEN-Gruppe schlägt Universum und Benchmark.</div>
    ${blocks || '<div class="empty">Noch keine ausgewerteten Einträge</div>'}`;
}

function bind() {
  document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
    document.querySelectorAll(".tab").forEach(x => x.classList.toggle("active", x === t));
    document.querySelectorAll(".panel").forEach(p => p.classList.toggle("active", p.id === t.dataset.tab));
    try { localStorage.setItem("tab", t.dataset.tab); } catch { }
    window.scrollTo(0, 0);
  });
  document.body.addEventListener("click", e => {
    const t = e.target.closest("[data-obj]");
    if (t && !e.target.closest("#detail")) openDetail(t.dataset.kind, t.dataset.obj);
  });
  const close = () => { document.getElementById("detail").classList.add("hidden"); document.getElementById("detail-body").innerHTML = ""; document.body.style.overflow = ""; };
  document.getElementById("close").onclick = close;
  document.getElementById("detail").onclick = e => { if (e.target.id === "detail") close(); };
  document.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
  try { const t = localStorage.getItem("tab"); if (t) document.querySelector(`.tab[data-tab="${t}"]`)?.click(); } catch { }
}

(async () => {
  [D.aktien, D.krypto, D.rohstoffe, D.makro, D.meta] = await Promise.all(["aktien", "krypto", "rohstoffe", "makro", "meta"].map(load));
  document.getElementById("stand").textContent = `Aktien ${D.aktien?.stand ?? "–"} · Krypto ${D.krypto?.stand ?? "–"} · Rohstoffe ${D.rohstoffe?.stand ?? "–"} · gebaut ${D.meta?.gebaut ?? "–"}`;
  const st = D.aktien?.status || D.krypto?.status || "–";
  document.getElementById("status").textContent = st === "probe" ? "Probebetrieb" : st;
  renderOverview(); renderScreener("aktien"); renderScreener("krypto"); renderScreener("rohstoffe"); renderMakro(); renderForward(); bind();
})();
