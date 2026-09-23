const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n, d = 1) => Number(n || 0).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
const kgText = (n) => (n >= 1000 ? fmt(n, 0) : fmt(n, n >= 100 ? 0 : 1));

const COLORS = { orange: "#F5621C", purple: "#7B5CF5", green: "#1FA15D", grey: "#4A4A52" };
const LEVEL_COLORS = { Low: COLORS.green, Moderate: COLORS.purple, High: COLORS.orange };
const VALID_FUELS = {
  Car: ["Petrol", "Diesel", "CNG", "Hybrid"], Motorcycle: ["Petrol"], Bus: ["Diesel", "CNG", "Electric"],
  Train: ["Diesel", "Electric"], EV: ["Electric"], Truck: ["Diesel", "CNG"],
};
// Same factors the model was trained on, used to split a single result into fuel and electricity.
const FUEL_FACTOR = { Petrol: 2.31, Diesel: 2.68, CNG: 2.0, Electric: 0.05, Hybrid: 1.2 };
const VEHICLE_MULT = { Car: 1.0, Bus: 1.4, Motorcycle: 0.65, Truck: 1.8, Train: 0.45, EV: 0.35 };

let trendChart;
const SHORT = { Motorcycle: "Bike" }; // keeps the vehicle chart labels from overlapping

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.classList.remove("show"), 2600);
}

async function api(url, options = {}) {
  const r = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || "Request failed");
  return data;
}

const levelOf = (kg) => (kg < 5 ? "Low" : kg < 15 ? "Moderate" : "High");

// ------------------------------------------------------------ tabs
function go(tab) {
  $$(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  $$(".view").forEach((v) => v.classList.toggle("hidden", v.id !== "view-" + tab));
  history.replaceState(null, "", "#" + tab);
  if (tab === "history") loadHistory();
  if (tab === "dashboard" && trendChart) trendChart.resize();
  window.scrollTo(0, 0);
}
document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-tab]");
  if (t) { e.preventDefault(); go(t.dataset.tab); }
});

// ------------------------------------------------------------ tooltips for the hand-drawn charts
const tip = $("#tip");
document.addEventListener("mousemove", (e) => {
  const t = e.target.closest("[data-tip]");
  if (!t) { tip.classList.add("hidden"); return; }
  tip.textContent = t.dataset.tip;
  tip.style.left = e.clientX + "px";
  tip.style.top = e.clientY + "px";
  tip.classList.remove("hidden");
});

// ------------------------------------------------------------ helpers
function niceMax(v) {
  if (v <= 0) return 4;
  const step = 10 ** Math.floor(Math.log10(v / 4));
  const s = [1, 2, 2.5, 5, 10].map((m) => m * step).find((x) => x * 4 >= v);
  return s * 4;
}
const tick = (v) => (Number.isInteger(v) ? v.toLocaleString("en-IN") : fmt(v, 1));
function axis(el, max) {
  el.innerHTML = [0, 1, 2, 3, 4].map((i) => `<span style="bottom:${i * 25}%">${tick((max / 4) * i)}</span>`).join("");
}
function change(el, pct) {
  if (pct == null) { el.className = ""; el.textContent = ""; el.removeAttribute("title"); return; }
  const dir = pct > 1 ? "up" : pct < -1 ? "down" : "flat";
  el.className = dir;
  el.textContent = `${pct > 0 ? "+" : ""}${fmt(pct, 0)}%`;
  el.title = "Compared with the previous 30 days";
}

// ------------------------------------------------------------ dashboard
async function loadDashboard() {
  const vehicle = $("#vehicleFilter").value;
  const d = await api("/api/dashboard" + (vehicle ? `?vehicle=${encodeURIComponent(vehicle)}` : ""));
  const s = d.stats;
  const empty = s.count === 0;
  $("#emptyDash").classList.toggle("hidden", !empty);
  $("#dashGrid").classList.toggle("hidden", empty);
  $("#emptyDash h2").textContent = vehicle ? `No ${vehicle} trips yet` : "No trips yet";
  if (empty) return;

  $("#sTotal").textContent = kgText(s.total_co2_kg);
  $("#sAvg").textContent = fmt(s.average_co2_kg, 1);
  $("#sCount").textContent = s.count.toLocaleString("en-IN");
  change($("#cTotal"), s.change_total);
  change($("#cAvg"), s.change_average);
  change($("#cCount"), s.change_count);

  drawTrend(d.weeks);
  drawDays(d.by_day, s.total_co2_kg);
  drawVehicles(d.by_vehicle);
  drawFuel(d.by_fuel, s);
  drawLevels(d.levels, s.average_co2_kg);
}

function drawTrend(weeks) {
  const labels = weeks.map((w) => new Date(w.start + "T00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" }));
  // 4-week rolling average, so single busy weeks do not turn the line into spikes.
  const values = weeks.map((_, i) => { const w = weeks.slice(Math.max(0, i - 3), i + 1); return w.reduce((a, x) => a + x.co2, 0) / w.length; });
  const ctx = $("#trendChart").getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 230);
  grad.addColorStop(0, "rgba(123, 92, 245, .45)");
  grad.addColorStop(1, "rgba(123, 92, 245, 0)");
  const max = niceMax(Math.max(...values));
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: [{ data: values, borderColor: COLORS.purple, backgroundColor: grad, fill: true, cubicInterpolationMode: "monotone", borderWidth: 2.5, pointRadius: 0, pointHoverRadius: 5, pointHoverBackgroundColor: "#fff", pointHoverBorderColor: COLORS.purple }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: { duration: 500 },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: { backgroundColor: "#fff", titleColor: "#0D0D0F", bodyColor: "#0D0D0F", displayColors: false, padding: 10, cornerRadius: 10, titleFont: { weight: "600" },
          callbacks: { title: (i) => `Week of ${i[0].label}`, label: (i) => `${fmt(i.parsed.y, 1)} kg a week (4-week average)` } },
      },
      scales: {
        x: { display: false },
        y: { min: 0, max, ticks: { stepSize: max / 4, color: "#7D7D86", callback: (v) => tick(v), padding: 8 }, border: { display: false }, grid: { color: "#2C2C31", tickLength: 0, drawTicks: false }, afterFit: (a) => { a.width = 44; } },
      },
    },
    plugins: [{ id: "dashGrid", beforeDraw: (c) => c.ctx.setLineDash([4, 5]), afterDraw: (c) => c.ctx.setLineDash([]) }],
  });
  const now = new Date();
  const months = [];
  for (let i = 11; i >= 0; i--) {
    const m = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(`<span class="${i === 0 ? "now" : ""}">${m.toLocaleDateString("en-IN", { month: "short" })}</span>`);
  }
  $("#months").innerHTML = months.join("");
}

function drawDays(days, total) {
  const max = niceMax(Math.max(...days.map((d) => d.co2)));
  axis($("#dayAxis"), max);
  $("#dayBars").innerHTML = days.map((d) => {
    const h = Math.round((d.co2 / max) * 100);
    return `<div class="bar-col" data-tip="${d.day}: ${fmt(d.co2, 1)} kg">
      <div class="track"><div class="hatch ${h >= 100 ? "none" : ""}"></div><div class="fill" style="height:${h}%${h ? "" : ";min-height:0"}"></div></div>
      <span class="lab">${d.day}</span></div>`;
  }).join("");
  const top = [...days].sort((a, b) => b.co2 - a.co2)[0];
  $("#busiest").textContent = top.co2 ? `Busiest day: ${top.day}, ${fmt((top.co2 / total) * 100, 0)}% of CO₂` : "Weekly pattern";
}

function drawVehicles(list) {
  const max = niceMax(Math.max(...list.map((v) => v.co2)));
  axis($("#vehAxis"), max);
  $("#vehBars").innerHTML = list.map((v) => {
    const t = (v.transport / max) * 100, e = (v.electricity / max) * 100;
    return `<div class="bar-col" data-tip="${esc(v.vehicle)}: ${fmt(v.co2, 1)} kg (fuel ${fmt(v.transport, 1)}, electricity ${fmt(v.electricity, 1)}) over ${v.count} trips">
      <span class="pct">${fmt(v.share, 0)}%</span>
      <div class="track"><div class="hatch"></div>
        ${e >= 1.5 ? `<div class="fill p" style="height:${e}%"></div>` : ""}
        ${t >= 1.5 ? `<div class="fill" style="height:${t}%"></div>` : ""}
      </div><span class="lab">${esc(SHORT[v.vehicle] || v.vehicle)}</span></div>`;
  }).join("");
}

function drawFuel(fuels, s) {
  const top = fuels.slice(0, 3);
  const rest = fuels.slice(3).reduce((a, f) => a + f.share, 0);
  const parts = [...top.map((f) => ({ name: f.fuel, share: f.share })), ...(rest > 0.5 ? [{ name: "Other", share: rest }] : [])];
  $("#fuelSeg").innerHTML = parts.map((p, i) => `<span class="s${i}" style="flex:${Math.max(p.share, 4)}" data-tip="${p.name}: ${fmt(p.share, 1)}% of CO₂">${p.share >= 9 ? fmt(p.share, 0) + "%" : ""}</span>`).join("");
  const dots = [COLORS.green, COLORS.purple, COLORS.orange, COLORS.grey];
  $("#fuelLegend").innerHTML = parts.map((p, i) => `<span><i style="background:${dots[i]}"></i>${p.name}</span>`).join("");
  const total = s.total_co2_kg || 1;
  $("#sFuel").textContent = `${kgText(s.transport_kg)} kg`;
  $("#sElec").textContent = `${kgText(s.electricity_kg)} kg`;
  $("#pFuel").textContent = `${fmt((s.transport_kg / total) * 100, 0)}%`;
  $("#pElec").textContent = `${fmt((s.electricity_kg / total) * 100, 0)}%`;
  $("#sPkm").textContent = `${fmt(s.per_passenger_km_g, 0)} g`;
}

function drawLevels(levels, avg) {
  const R = 88, C = 2 * Math.PI * R, GAP = 20; // gap in px along the ring, leaves room for round caps
  const shown = levels.filter((l) => l.share > 0);
  let offset = 0, arcs = "", tags = "";
  shown.forEach((l) => {
    const len = (l.share / 100) * C;
    const visible = Math.max(len - (shown.length > 1 ? GAP : 0), 1);
    arcs += `<circle cx="110" cy="110" r="${R}" fill="none" stroke="${LEVEL_COLORS[l.level]}" stroke-width="16" stroke-linecap="round"
      stroke-dasharray="${visible} ${C}" stroke-dashoffset="${-offset}"><title>${l.level}: ${fmt(l.share, 0)}% of trips</title></circle>`;
    const mid = ((offset + len / 2) / C) * 2 * Math.PI - Math.PI / 2;
    tags += `<span class="dtag" style="left:${110 + (R + 4) * Math.cos(mid)}px;top:${110 + (R + 4) * Math.sin(mid)}px">${fmt(l.share, 0)}%</span>`;
    offset += len;
  });
  $("#donut").innerHTML = `<circle cx="110" cy="110" r="${R}" fill="none" stroke="#232327" stroke-width="16"/>` + arcs;
  $("#donutTags").innerHTML = tags;
  $("#dCenter").textContent = fmt(avg, 1);
  $("#levelCards").innerHTML = levels.map((l) => `<div class="lc" data-tip="${l.count} trips, ${l.range}">
    <span class="t"><i style="background:${LEVEL_COLORS[l.level]}"></i>${l.level}</span>
    <b>${fmt(l.share, 0)}%</b><small>${l.range}</small>
    <div class="bar"><i style="width:${l.share}%;background:${LEVEL_COLORS[l.level]}"></i></div></div>`).join("");
}

// ------------------------------------------------------------ predictor
function fillFuels() {
  const v = $("#fVehicle").value, cur = $("#fFuel").value;
  $("#fFuel").innerHTML = VALID_FUELS[v].map((f) => `<option${f === cur ? " selected" : ""}>${f}</option>`).join("");
}
$("#fVehicle").addEventListener("change", fillFuels);
fillFuels();

$("#predictForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = Object.fromEntries(new FormData(e.target).entries());
  ["distance_km", "fuel_liters", "passengers", "electricity_kwh", "grid_factor", "renewable_share"].forEach((k) => (payload[k] = Number(payload[k])));
  const msg = $("#formMessage");
  msg.textContent = "Calculating…";
  try {
    const d = await api("/api/predict", { method: "POST", body: JSON.stringify(payload) });
    const kg = d.prediction.predicted_co2_kg;
    const lvl = levelOf(kg);
    let tr = payload.fuel_liters * FUEL_FACTOR[payload.fuel_type] * VEHICLE_MULT[payload.vehicle_type] / (0.65 + 0.35 * payload.passengers);
    let el = payload.electricity_kwh * payload.grid_factor * (1 - payload.renewable_share / 100);
    const raw = tr + el || 1;
    tr = (kg * tr) / raw; el = (kg * el) / raw;
    $("#resultEmpty").classList.add("hidden");
    $("#resultBody").classList.remove("hidden");
    $("#resultValue").textContent = fmt(kg, 2);
    $("#resultLevel").textContent = `${lvl} emission`;
    $("#resultLevel").style.color = LEVEL_COLORS[lvl];
    const pf = (tr / kg) * 100 || 0, pe = 100 - pf;
    $("#resultSeg").innerHTML = `<span class="s2" style="flex:${Math.max(pf, 4)}">${pf >= 12 ? fmt(pf, 0) + "%" : ""}</span><span class="s1" style="flex:${Math.max(pe, 4)}">${pe >= 12 ? fmt(pe, 0) + "%" : ""}</span>`;
    $("#resultLegend").innerHTML = `<span><i style="background:${COLORS.orange}"></i>Fuel ${fmt(tr, 2)} kg</span><span><i style="background:${COLORS.purple}"></i>Electricity ${fmt(el, 2)} kg</span>`;
    const perPerson = kg / payload.passengers;
    $("#resultNote").textContent = `That is ${fmt(perPerson, 2)} kg for each of the ${payload.passengers} passenger${payload.passengers === 1 ? "" : "s"}. The fuel and electricity split is estimated from standard emission factors.`;
    msg.textContent = "";
    toast("Prediction saved");
    loadDashboard();
  } catch (err) { msg.textContent = err.message; toast(err.message); }
});

// ------------------------------------------------------------ history
async function loadHistory() {
  const d = await api("/api/predictions?limit=200");
  $("#historyCount").textContent = `${d.items.length}${d.items.length === 200 ? "+" : ""} trips`;
  $("#emptyState").classList.toggle("hidden", d.items.length > 0);
  $("#historyBody").innerHTML = d.items.map((p) => {
    const lvl = levelOf(p.predicted_co2_kg);
    const date = new Date(p.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" });
    return `<tr><td>${date}</td><td>${esc(p.vehicle_type)}</td><td>${esc(p.fuel_type)}</td><td class="n">${fmt(p.distance_km, 1)} km</td><td class="n">${p.passengers}</td>
      <td class="n"><span class="lvl" style="background:${LEVEL_COLORS[lvl]}" title="${lvl}"></span><b>${fmt(p.predicted_co2_kg, 2)} kg</b></td>
      <td class="n"><button class="delete" data-id="${p.id}">Delete</button></td></tr>`;
  }).join("");
}
$("#historyBody").addEventListener("click", async (e) => {
  const b = e.target.closest(".delete");
  if (!b || !confirm("Delete this prediction?")) return;
  try { await api(`/api/predictions/${b.dataset.id}`, { method: "DELETE" }); toast("Deleted"); loadHistory(); loadDashboard(); }
  catch (err) { toast(err.message); }
});
$("#refreshBtn").addEventListener("click", loadHistory);

// ------------------------------------------------------------ data menu, export, model status
const menu = $("#settingsMenu");
$("#settingsBtn").addEventListener("click", (e) => { e.stopPropagation(); menu.classList.toggle("hidden"); });
document.addEventListener("click", (e) => { if (!e.target.closest(".menu-wrap")) menu.classList.add("hidden"); });
async function addSamples() {
  menu.classList.add("hidden");
  try { const r = await api("/api/sample-data", { method: "POST", body: JSON.stringify({ count: 150 }) }); toast(`Added ${r.added} sample trips`); loadDashboard(); if (!$("#view-history").classList.contains("hidden")) loadHistory(); }
  catch (err) { toast(err.message); }
}
$("#sampleBtn").addEventListener("click", addSamples);
$("#emptySample").addEventListener("click", addSamples);
$("#clearBtn").addEventListener("click", async () => {
  menu.classList.add("hidden");
  if (!confirm("Delete every saved prediction? This can't be undone.")) return;
  try { const r = await api("/api/predictions", { method: "DELETE" }); toast(`Deleted ${r.deleted} predictions`); loadDashboard(); loadHistory(); }
  catch (err) { toast(err.message); }
});
$("#exportBtn").addEventListener("click", () => (window.location = "/api/export"));
$("#vehicleFilter").addEventListener("change", loadDashboard);

async function loadMetrics() {
  try {
    const m = await api("/api/model-metrics");
    $("#modelPill").classList.add("on");
    $("#modelPill").lastChild.textContent = `Model R² ${Number(m.r2).toFixed(2)}`;
    $("#aboutRows").textContent = `${m.dataset_rows.toLocaleString("en-IN")} training rows`;
    $("#metrics").innerHTML = `<div><b>${Number(m.r2).toFixed(3)}</b><span>R² on test data</span></div><div><b>${fmt(m.mae, 2)}</b><span>Mean error (kg)</span></div><div><b>${fmt(m.rmse, 2)}</b><span>RMSE (kg)</span></div>`;
  } catch { $("#modelPill").lastChild.textContent = "Model offline"; }
}

// ------------------------------------------------------------ start
Chart.defaults.font.family = "Manrope, system-ui, sans-serif";
Chart.defaults.color = "#7D7D86";
$("#today").textContent = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
const startTab = location.hash.slice(1);
go(["dashboard", "predictor", "history", "about"].includes(startTab) ? startTab : "dashboard");
loadDashboard().catch((e) => toast(e.message));
loadMetrics();
