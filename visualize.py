"""Build a self-contained static HTML page to explore one day of WakaTime data.

Reads the latest WakaTime export under data/ (YYYYMMDD.json), keeps only the per-day project
durations (plus language/editor drill-down), and embeds that compact dataset
into a single static HTML file. Open visualize.html in any browser - no server,
no CORS, no external dependencies.

Run:  python visualize.py
"""

import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "visualize.html")


def latest_source():
    """Newest YYYYMMDD.json under data/ (WakaTime exports are cumulative)."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    if not files:
        raise SystemExit("No *.json found in " + DATA_DIR)
    return files[-1]

MIN_SECONDS = 600  # drop days with less than 10 minutes of coding time


def extract_days(raw):
    """Flatten the export into [{d, s, gt, p:[{n,s,t,l,e}]}].

    d  : date string (YYYY-MM-DD)
    s  : grand total seconds for the day
    gt : human readable grand total text from WakaTime
    p  : projects -> n name, s seconds, t text, l languages, e editors
    Only days with >= MIN_SECONDS (10 min) of coding time are kept.
    """
    out = []
    for day in raw["days"]:
        gt_seconds = day["grand_total"]["total_seconds"]
        if gt_seconds < MIN_SECONDS:
            continue
        projects = []
        for p in day.get("projects", []):
            s = p["grand_total"]["total_seconds"]
            if s <= 0:
                continue
            projects.append({
                "n": p["name"],
                "s": s,
                "t": p["grand_total"]["text"],
                "l": _sub(p.get("languages", [])),
                "e": _sub(p.get("editors", [])),
            })
        out.append({
            "d": day["date"],
            "s": gt_seconds,
            "gt": day["grand_total"]["text"],
            "p": projects,
        })
    return out


def _sub(items):
    """Compact a languages/editors list to [{n, s}] sorted desc, drop zeros."""
    kept = [{"n": x["name"], "s": x["total_seconds"]}
            for x in items if x["total_seconds"] > 0]
    kept.sort(key=lambda r: r["s"], reverse=True)
    return kept


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WakaTime · Daily Projects</title>
<style>
  :root {
    color-scheme: light;
    --page:           #f9f9f7;
    --surface:        #fcfcfb;
    --ink:            #0b0b0b;
    --ink-2:          #52514e;
    --muted:          #898781;
    --gridline:       #e1e0d9;
    --baseline:       #c3c2b7;
    --border:         rgba(11,11,11,0.10);
    --series:         #2a78d6;   /* dataviz slot-1 blue */
    --series-soft:    #cde2fb;   /* sequential step 100 */
    --track:          #ecebe4;
    /* heatmap sequential (blue ramp, light→dark = more) */
    --hm0: #ecebe4; --hm1: #b7d3f6; --hm2: #6da7ec; --hm3: #3987e5; --hm4: #1c5cab;
  }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) {
      color-scheme: dark;
      --page:        #0d0d0d;
      --surface:     #1a1a19;
      --ink:         #ffffff;
      --ink-2:       #c3c2b7;
      --muted:       #898781;
      --gridline:    #2c2c2a;
      --baseline:    #383835;
      --border:      rgba(255,255,255,0.10);
      --series:      #3987e5;
      --series-soft: #1c5cab;
      --track:       #2c2c2a;
      /* heatmap: anchor flips in dark — dark=near surface, bright=more */
      --hm0: #2c2c2a; --hm1: #184f95; --hm2: #1c5cab; --hm3: #3987e5; --hm4: #6da7ec;
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --page:        #0d0d0d;
    --surface:     #1a1a19;
    --ink:         #ffffff;
    --ink-2:       #c3c2b7;
    --muted:       #898781;
    --gridline:    #2c2c2a;
    --baseline:    #383835;
    --border:      rgba(255,255,255,0.10);
    --series:      #3987e5;
    --series-soft: #1c5cab;
    --track:       #2c2c2a;
    --hm0: #2c2c2a; --hm1: #184f95; --hm2: #1c5cab; --hm3: #3987e5; --hm4: #6da7ec;
  }

  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--page);
    color: var(--ink);
    font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 880px; margin: 0 auto; padding: 32px 24px 96px; }

  /* Header */
  header {
    display: flex; align-items: baseline; justify-content: space-between;
    margin-bottom: 28px;
  }
  header h1 { font-size: 18px; font-weight: 600; margin: 0; letter-spacing: -0.01em; }
  header .sub { color: var(--ink-2); font-size: 13px; }
  .theme-btn {
    background: var(--surface); color: var(--ink-2);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 6px 10px; font-size: 13px; cursor: pointer;
  }
  .theme-btn:hover { color: var(--ink); }

  /* Controls */
  .controls {
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 10px 12px; margin-bottom: 24px;
  }
  .nav-btn {
    background: transparent; color: var(--ink); border: 1px solid var(--border);
    border-radius: 8px; padding: 7px 12px; cursor: pointer; font: inherit;
  }
  .nav-btn:hover:not(:disabled) { background: var(--gridline); }
  .nav-btn:disabled { opacity: 0.35; cursor: not-allowed; }
  select#day {
    flex: 1; min-width: 200px;
    background: var(--surface); color: var(--ink);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 7px 10px; font: inherit; cursor: pointer;
  }

  /* Hero figure */
  .hero {
    display: flex; gap: 28px; align-items: center; flex-wrap: wrap;
    margin-bottom: 28px;
  }
  .hero-date {
    font-size: 52px; font-weight: 600; letter-spacing: -0.02em;
    line-height: 1.1; font-variant-numeric: tabular-nums;
  }
  .hero-main { flex: 1; min-width: 0; }
  .hero .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; }
  .hero .value {
    font-size: 52px; font-weight: 600; letter-spacing: -0.02em;
    line-height: 1.1; margin-top: 4px;
    font-variant-numeric: tabular-nums;
  }
  .hero .meta { color: var(--ink-2); font-size: 13px; margin-top: 6px; }

  /* Section heads */
  .section-title { color: var(--muted); font-size: 12px; text-transform: uppercase;
    letter-spacing: 0.06em; margin: 0 0 12px; }
  .section { margin-bottom: 36px; }

  /* Chart */
  .chart { display: flex; flex-direction: column; gap: 10px; }
  .row { border-radius: 8px; }
  .row-head {
    display: grid;
    grid-template-columns: minmax(110px, 200px) 1fr auto;
    gap: 12px; align-items: center; padding: 4px 2px; cursor: pointer;
  }
  .row-head:hover .name { color: var(--series); }
  .name {
    color: var(--ink); font-weight: 500; font-size: 13.5px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    transition: color .12s;
  }
  .track {
    position: relative; height: 22px; background: var(--track);
    border-radius: 4px; overflow: hidden;
  }
  .fill {
    position: absolute; left: 0; top: 0; bottom: 0;
    background: var(--series); border-radius: 4px;
    transition: width .35s cubic-bezier(.2,.7,.2,1);
  }
  .row-head:hover .fill { filter: brightness(1.08); }
  .dur {
    position: relative; color: var(--ink); font-size: 13px;
    font-variant-numeric: tabular-nums; white-space: nowrap; cursor: help;
  }
  /* tooltip on hover: shows exact hours */
  .dur[data-tip]:hover::after {
    content: attr(data-tip);
    position: absolute; right: 0; bottom: calc(100% + 6px);
    background: var(--ink); color: var(--surface);
    padding: 4px 8px; border-radius: 5px; font-size: 11px;
    white-space: nowrap; pointer-events: none; z-index: 30;
    font-variant-numeric: tabular-nums;
    box-shadow: 0 2px 8px rgba(0,0,0,.18);
  }
  .dur .pct { color: var(--muted); }
  .caret { display: inline-block; color: var(--muted); font-size: 10px; margin-left: 6px;
    transition: transform .15s; }
  .row.open .caret { transform: rotate(180deg); }

  /* Drill-down */
  .detail {
    display: none; padding: 8px 0 14px 12px;
    border-left: 2px solid var(--gridline); margin-top: 6px;
  }
  .row.open .detail { display: block; }
  .detail-group { margin-bottom: 12px; }
  .detail-group:last-child { margin-bottom: 0; }
  .detail-label { color: var(--muted); font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.05em; margin-bottom: 6px; }
  .sub-row {
    display: grid; grid-template-columns: minmax(90px, 160px) 1fr auto;
    gap: 10px; align-items: center; padding: 2px 0;
  }
  .sub-row .name { font-size: 12.5px; font-weight: 400; color: var(--ink-2); }
  .sub-track { position: relative; height: 8px; background: var(--track); border-radius: 3px; overflow: hidden; }
  .sub-fill { position: absolute; left:0; top:0; bottom:0; background: var(--series-soft);
    border-radius: 3px; opacity: .9; }
  .sub-row .dur { font-size: 12px; color: var(--ink-2); }
  .empty { color: var(--muted); font-size: 12px; }

  /* Activity heatmap (per year) */
  .hm { display: flex; flex-direction: column; gap: 14px; }
  .hm-year { display: flex; align-items: flex-start; gap: 8px; }
  .hm-label {
    font-size: 12px; color: var(--muted); padding-top: 1px;
    min-width: 34px; font-variant-numeric: tabular-nums;
  }
  .hm-grid {
    display: grid;
    grid-template-rows: repeat(7, 13px);
    grid-auto-flow: column;
    gap: 3px;
  }
  .hm-cell, .hm-spacer { width: 13px; height: 13px; border-radius: 3px; }
  .hm-spacer { background: transparent; }
  .hm-cell { background: var(--hm0); cursor: default; }
  .hm-cell[data-l="1"] { background: var(--hm1); }
  .hm-cell[data-l="2"] { background: var(--hm2); }
  .hm-cell[data-l="3"] { background: var(--hm3); }
  .hm-cell[data-l="4"] { background: var(--hm4); cursor: pointer; }
  .hm-cell[data-l]:not([data-l="0"]):hover { outline: 1.5px solid var(--ink); outline-offset: 1px; }
  .hm-cell.sel { outline: 2px solid var(--ink); outline-offset: 1px; }
  .hm-legend {
    display: flex; align-items: center; gap: 6px; margin-top: 4px;
    color: var(--muted); font-size: 11px;
  }
  .hm-legend .hm-cell, .hm-legend .hm-spacer { width: 11px; height: 11px; cursor: default; }

  footer { margin-top: 8px; color: var(--muted); font-size: 12px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>WakaTime · Daily Projects</h1>
      <div class="sub" id="user-sub"></div>
    </div>
    <button class="theme-btn" id="theme">☾</button>
  </header>

  <div class="controls">
    <button class="nav-btn" id="prev" title="Previous day (←)">‹ Prev</button>
    <select id="day"></select>
    <button class="nav-btn" id="next" title="Next day (→)">Next ›</button>
  </div>

  <div class="hero">
    <div class="hero-date" id="hero-date">—</div>
    <div class="hero-main">
      <div class="label">Total coding time</div>
      <div class="value" id="hero-val">—</div>
      <div class="meta" id="hero-meta"></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Projects</div>
    <div class="chart" id="chart"></div>
  </div>

  <div class="section">
    <div class="section-title">Activity · click a day to view</div>
    <div class="hm" id="hm"></div>
    <div class="hm-legend">
      <span>Less</span>
      <span class="hm-cell"></span>
      <span class="hm-cell" data-l="1"></span>
      <span class="hm-cell" data-l="2"></span>
      <span class="hm-cell" data-l="3"></span>
      <span class="hm-cell" data-l="4"></span>
      <span>More</span>
    </div>
  </div>

  <footer>Built from your WakaTime export. Use ← / → to move between days.</footer>
</div>

<script>
const DATA = __DATA__;
const USER = __USER__;

/* ---- formatters ---- */
const fmtHMS = (s) => {                                  // H:MM:SS (hero + tooltip)
  s = Math.round(s);
  const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = s%60;
  if (h) return h + ":" + String(m).padStart(2,'0') + ":" + String(sec).padStart(2,'0');
  return m + ":" + String(sec).padStart(2,'0');
};
const fmtMin = (s) => {                                  // "N min" for list rows
  const m = Math.round(s/60);
  return (m < 1 ? '<1' : m) + ' min';
};
const fmtTip = (s) => fmtHMS(s) + ' · ' + (Math.round(s/3600*100)/100) + ' hours';
const escapeHtml = (s) => String(s).replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

document.getElementById('user-sub').textContent =
  USER.name + ' · ' + DATA.length + ' active days';

/* populate dropdown, newest on top; option value = forward time index (0 = oldest) */
const sel = document.getElementById('day');
for (let k = DATA.length - 1; k >= 0; k--) {
  const o = document.createElement('option');
  o.value = k;
  o.textContent = DATA[k].d + '  ·  ' + DATA[k].gt;
  sel.appendChild(o);
}

/* ---- main detail view for one day ---- */
function render(i) {
  const d = DATA[i];
  if (!d) return;
  document.getElementById('hero-date').textContent = d.d;
  document.getElementById('hero-val').textContent = fmtHMS(d.s);
  const top = d.p[0];
  document.getElementById('hero-meta').textContent =
    d.p.length + (d.p.length === 1 ? ' project' : ' projects') +
    (top ? '  ·  most: ' + escapeHtml(top.n) + ' (' + fmtMin(top.s) + ')' : '');

  const chart = document.getElementById('chart');
  chart.innerHTML = '';
  if (!d.p.length) { chart.innerHTML = '<div class="empty">No project time recorded.</div>'; return; }

  const max = d.p[0].s || 1;
  d.p.forEach((p) => {
    const pct = Math.max(2, (p.s / max) * 100);
    const row = document.createElement('div');
    row.className = 'row';
    const hasDetail = p.l.length || p.e.length;
    row.innerHTML =
      '<div class="row-head">' +
        '<div class="name">' + escapeHtml(p.n) +
          (hasDetail ? '<span class="caret">▼</span>' : '') + '</div>' +
        '<div class="track"><div class="fill" style="width:' + pct + '%"></div></div>' +
        '<div class="dur" data-tip="' + escapeHtml(fmtTip(p.s)) + '">' +
          fmtMin(p.s) + '<span class="pct">  ·  ' + (p.s/d.s*100).toFixed(0) + '%</span>' +
        '</div>' +
      '</div>' +
      (hasDetail ? '<div class="detail"></div>' : '');

    if (hasDetail) {
      const head = row.querySelector('.row-head');
      const detail = row.querySelector('.detail');
      head.addEventListener('click', () => {
        const open = row.classList.toggle('open');
        if (open && !detail.dataset.built) {
          detail.dataset.built = '1';
          detail.innerHTML = renderDetail(p);
        }
      });
    }
    chart.appendChild(row);
  });
}

function renderDetail(p) {
  const block = (label, items) => {
    if (!items.length) return '';
    const max = items[0].s || 1;
    const rows = items.slice(0, 10).map(x =>
      '<div class="sub-row">' +
        '<div class="name">' + escapeHtml(x.n) + '</div>' +
        '<div class="sub-track"><div class="sub-fill" style="width:' + Math.max(2, x.s/max*100) + '%"></div></div>' +
        '<div class="dur" data-tip="' + escapeHtml(fmtTip(x.s)) + '">' + fmtMin(x.s) + '</div>' +
      '</div>'
    ).join('');
    const more = items.length > 10 ? '<div class="empty">+ ' + (items.length-10) + ' more</div>' : '';
    return '<div class="detail-group"><div class="detail-label">' + label + '</div>' + rows + more + '</div>';
  };
  return block('Languages', p.l) + block('Editors', p.e);
}

/* ---- activity heatmap (one block per year) ---- */
const byDate = new Map();                                // 'YYYY-MM-DD' -> {s, idx}
let maxS = 1;
DATA.forEach((d, i) => { byDate.set(d.d, {s: d.s, idx: i}); if (d.s > maxS) maxS = d.s; });

function hmLevel(s) {                                    // sqrt-scaled 0..4
  if (s <= 0) return 0;
  const r = Math.sqrt(s / maxS);
  if (r < 0.25) return 1;
  if (r < 0.5)  return 2;
  if (r < 0.75) return 3;
  return 4;
}
const isoDate = (y, m, d) =>
  y + '-' + String(m+1).padStart(2,'0') + '-' + String(d).padStart(2,'0');
const dimOf = (y, m) => new Date(y, m+1, 0).getDate();

function buildHeatmap() {
  const wrap = document.getElementById('hm');
  const years = [...new Set(DATA.map(d => Number(d.d.slice(0,4))))].sort();
  years.forEach((year) => {
    const block = document.createElement('div');
    block.className = 'hm-year';
    const label = document.createElement('div');
    label.className = 'hm-label';
    label.textContent = year;
    const grid = document.createElement('div');
    grid.className = 'hm-grid';

    // leading empty cells so Jan 1 lands on its real weekday column (Sun-start)
    const startDow = new Date(year, 0, 1).getDay();
    for (let i = 0; i < startDow; i++) {
      const sp = document.createElement('div');
      sp.className = 'hm-spacer';
      grid.appendChild(sp);
    }
    for (let m = 0; m < 12; m++) {
      const dim = dimOf(year, m);
      for (let dd = 1; dd <= dim; dd++) {
        const key = isoDate(year, m, dd);
        const cell = document.createElement('div');
        cell.className = 'hm-cell';
        cell.dataset.date = key;
        cell.title = key + ' · No activity';
        const info = byDate.get(key);
        if (info) {
          const lv = hmLevel(info.s);
          cell.dataset.l = lv;
          cell.title = key + ' · ' + fmtMin(info.s) + ' (' + fmtHMS(info.s) + ')';
          cell.addEventListener('click', () => { selectDay(info.idx); window.scrollTo({top:0, behavior:'smooth'}); });
        }
        grid.appendChild(cell);
      }
    }
    block.appendChild(label);
    block.appendChild(grid);
    wrap.appendChild(block);
  });
}

/* ---- selection (single path for all triggers) ---- */
function selectDay(i) {
  sel.value = String(i);
  render(i);
  document.getElementById('prev').disabled = (i <= 0);
  document.getElementById('next').disabled = (i >= DATA.length - 1);
  document.querySelectorAll('.hm-cell.sel').forEach(c => c.classList.remove('sel'));
  const cell = document.querySelector('.hm-cell[data-date="' + DATA[i].d + '"]');
  if (cell) cell.classList.add('sel');
}
function move(delta) {
  const ni = Number(sel.value) + delta;
  if (ni < 0 || ni >= DATA.length) return;
  selectDay(ni);
}

sel.addEventListener('change', () => selectDay(Number(sel.value)));
document.getElementById('prev').addEventListener('click', () => move(-1));
document.getElementById('next').addEventListener('click', () => move(1));
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'SELECT') return;
  if (e.key === 'ArrowLeft')  move(-1);
  if (e.key === 'ArrowRight') move(1);
});

/* theme toggle (overrides OS) */
const themeBtn = document.getElementById('theme');
function applyTheme(t) {
  if (t) document.documentElement.setAttribute('data-theme', t);
  else   document.documentElement.removeAttribute('data-theme');
  themeBtn.textContent = (t === 'dark' ||
    (!t && matchMedia('(prefers-color-scheme: dark)').matches)) ? '☀' : '☾';
}
themeBtn.addEventListener('click', () => {
  const cur = document.documentElement.getAttribute('data-theme');
  const osDark = matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = cur === 'dark' || (!cur && osDark);
  applyTheme(isDark ? 'light' : 'dark');
});
applyTheme(null);

/* init */
buildHeatmap();
selectDay(DATA.length - 1);   // newest day
</script>
</body>
</html>
"""


def build():
    src = latest_source()
    with open(src, "r", encoding="utf-8") as f:
        raw = json.load(f)

    days = extract_days(raw)
    user = {
        "name": raw.get("user", {}).get("display_name")
        or raw.get("user", {}).get("username", ""),
    }

    # Embed JSON safely: escape so a literal </script> in data can never break out.
    data_js = json.dumps(days, separators=(",", ":")).replace("<", "\\u003c")
    user_js = json.dumps(user, separators=(",", ":")).replace("<", "\\u003c")

    page = HTML.replace("__DATA__", data_js).replace("__USER__", user_js)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"source         : {src}")
    print(f"days with data : {len(days)}")
    print(f"data embedded  : {len(data_js.encode('utf-8')) / 1e6:.2f} MB")
    print(f"wrote          : {OUT}  ({len(page.encode('utf-8')) / 1e6:.2f} MB)")


if __name__ == "__main__":
    build()
