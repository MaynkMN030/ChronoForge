// CityPulse dashboard - plain JavaScript, no libraries (works offline at the venue).
const $ = (id) => document.getElementById(id);
let report = null;

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") el.className = v; else if (k.startsWith("on")) el.addEventListener(k.slice(2), v); else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) el.append(kid && kid.nodeType ? kid : document.createTextNode(kid ?? ""));
  return el;
}
const DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
function dayName(startDate, d) { const dt = new Date(startDate + "T00:00:00"); dt.setDate(dt.getDate() + d); return DAY_SHORT[(dt.getDay() + 6) % 7] + " " + dt.getDate(); }
function hhmm(x) { const hh = Math.floor(x), mm = Math.round((x - hh) * 60); return String(hh).padStart(2, "0") + ":" + String(mm).padStart(2, "0"); }
async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : undefined);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
  return data;
}

async function init() {
  const o = await api("/api/options");
  for (const [k, v] of Object.entries(o.personas)) $("persona").append(h("option", { value: k }, v.name + " - " + v.title));
  for (const [k, v] of Object.entries(o.cities)) $("city").append(h("option", { value: k }, v));
  for (const [k, v] of Object.entries(o.languages)) $("lang").append(h("option", { value: k }, v));
  if (!o.llm_available) { $("llm").disabled = true; $("llm").parentElement.append(" (not configured)"); }
  $("go").addEventListener("click", generate);
  $("send").addEventListener("click", sendChat);
  $("msg").addEventListener("keydown", (e) => { if (e.key === "Enter") sendChat(); });
}

async function generate() {
  $("go").disabled = true; $("status").textContent = "Agent is observing, planning and acting...";
  try {
    report = await api("/api/plan", { persona: $("persona").value, city: $("city").value, lang: $("lang").value,
      use_live: $("live").checked, use_llm: $("llm").checked });
    render(report);
    $("status").textContent = "Data source: " + report.data_source + " - " + report.data_note;
  } catch (e) { $("status").textContent = "Error: " + e.message; }
  $("go").disabled = false;
}

function tile(k, v, cls) { return h("div", { class: "tile" }, h("div", { class: "v " + (cls || "") }, v), h("div", { class: "k" }, k)); }

function render(r) {
  const m = r.metrics;
  $("results").classList.remove("hidden");
  const wk = m.weekly_pm_reduction_pct_incl_workouts;
  $("tiles").replaceChildren(
    tile("Weekly Exposure Score (0-100)", r.baseline.score + " / " + r.baseline.label),
    tile("Score after commute swaps", m.score_after_swaps, "good"),
    tile("Commute PM2.5 change", (-m.commute_pm_reduction_pct).toFixed(1) + "%", "good"),
    tile("Whole-week PM2.5 (swaps only)", (-m.weekly_pm_reduction_pct_swaps_only).toFixed(1) + "%", "good"),
    tile("Whole-week PM2.5 incl. workouts", (wk > 0 ? "-" : "+") + Math.abs(wk).toFixed(1) + "%", wk > 0 ? "good" : "bad"),
    tile("Long sitting blocks with a workout", m.gaps_filled + " / " + m.gaps_total),
    tile("Plan acceptance rate", m.acceptance_rate == null ? "no data yet" : Math.round(m.acceptance_rate * 100) + "%"));
  $("summary").textContent = r.summary.text;

  // heatmap
  const max = Math.max(...r.baseline.grid.flat(), 1e-9);
  const wset = new Set(r.workouts.map((w) => w.day + "-" + Math.floor(w.start)));
  const heat = $("heat"); heat.replaceChildren(h("div", {}));
  for (let hr = 0; hr < 24; hr++) heat.append(h("div", { class: "lbl" }, hr % 3 === 0 ? String(hr) : ""));
  for (let d = 0; d < 7; d++) {
    heat.append(h("div", { class: "lbl" }, dayName(r.start_date, d)));
    for (let hr = 0; hr < 24; hr++) {
      const v = r.after.grid[d][hr], a = Math.min(1, v / max);
      const cell = h("div", { class: "cell" + (wset.has(d + "-" + hr) ? " w" : ""), title: dayName(r.start_date, d) + " " + hr + ":00 - exposure " + v.toFixed(3) });
      if (v > 0) cell.style.background = "rgba(217,72,15," + (0.08 + 0.92 * a).toFixed(2) + ")";
      heat.append(cell);
    }
  }

  // workouts with feedback
  $("workouts").replaceChildren(...r.workouts.map((w) => feedbackRow(w.id,
    h("div", {}, h("b", {}, dayName(r.start_date, w.day) + "  " + hhmm(w.start) + "-" + hhmm(w.end)),
      h("span", { class: "tag" + (w.type === "indoor" ? " warn" : "") }, w.type),
      h("div", { class: "mute" }, w.title + " - forecast PM2.5 " + w.pm25 + ", " + w.temp + " C, UV " + w.uv)))));
  $("ics").href = "/api/calendar/" + encodeURIComponent(r.user_id) + ".ics";

  $("swaps").replaceChildren(...(r.swaps.length ? r.swaps.map((s) => feedbackRow(s.id,
    h("div", {}, h("b", {}, dayName(r.start_date, s.day) + ": " + s.place),
      h("span", { class: "tag" }, s.type),
      h("div", { class: "mute" }, s.old_window + " -> " + s.new_window + (s.via ? " via " + s.via : "") + " - saves about " + s.saving_pct + "% exposure"))))
    : [h("div", { class: "mute" }, "No big swaps needed.")]));

  $("gaps").replaceChildren(...(r.gaps.length ? r.gaps.slice(0, 8).map((g) => h("div", { class: "row" },
    h("div", {}, dayName(r.start_date, g.day) + "  " + hhmm(g.start) + "-" + hhmm(g.end) + "  (" + g.hours + " h sitting)"),
    h("span", { class: "tag" + (g.has_free_slot ? "" : " warn") }, g.has_free_slot ? "free slot available" : "take 5-min breaks")))
    : [h("div", { class: "mute" }, "None found.")]));

  const mt = r.meetups;
  $("meetups").replaceChildren(...(mt.triggered && mt.items.length ? mt.items.map((i) => h("div", { class: "row" },
    h("div", {}, h("b", {}, i.name), h("div", { class: "mute" }, i.type + " - " + i.date + " " + i.time + " - " + (i.indoor ? "indoor" : "outdoor") + " - " + i.cost)),
    h("span", { class: "tag" + (i.air_ok ? "" : " warn") }, i.air_ok ? "air OK" : "poor air")))
    : [h("div", { class: "mute" }, "Social time this week was enough (" + mt.social_hours + " h) - no suggestion needed.")]));
}

function feedbackRow(id, content) {
  const ok = h("button", { class: "small ok" }, "Accept"), no = h("button", { class: "small no" }, "Skip");
  const row = h("div", { class: "row" }, content, h("div", {}, ok, no));
  const send = async (accepted) => {
    ok.disabled = no.disabled = true;
    try { const res = await api("/api/feedback", { user_id: report.user_id, item_id: id, accepted }); (accepted ? ok : no).textContent = res.ok ? (accepted ? "Accepted" : "Skipped") : "?"; }
    catch (e) { ok.disabled = no.disabled = false; }
  };
  ok.addEventListener("click", () => send(true)); no.addEventListener("click", () => send(false));
  return row;
}

async function sendChat() {
  const text = $("msg").value.trim(); if (!text) return;
  $("msg").value = ""; $("chatlog").append(h("div", { class: "me" }, text));
  try {
    const res = await api("/api/chat", { message: text, lang: $("lang").value, user_id: report ? report.user_id : null });
    $("chatlog").append(h("div", { class: res.kind === "distress" ? "safe" : "" }, res.reply));
  } catch (e) { $("chatlog").append(h("div", {}, "Error: " + e.message)); }
}
init().catch((e) => { $("status").textContent = "Could not load options: " + e.message; });
