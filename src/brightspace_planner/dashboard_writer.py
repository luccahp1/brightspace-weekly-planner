"""Dashboard HTML writer — generates a single-file local dashboard."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .config import AppConfig
from .utils import ensure_dir, read_json

logger = logging.getLogger("brightspace_planner")


_DASHBOARD_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Brightspace Weekly Planner</title>
<style>
:root {{
  --bg: #0f1117; --surface: #1a1d27; --border: #2a2d3a;
  --text: #e2e8f0; --muted: #8892a4; --accent: #6366f1;
  --high: #ef4444; --high-bg: #1f1315;
  --med: #f59e0b; --med-bg: #1f1a10;
  --low: #22c55e; --low-bg: #101f14;
  --link: #818cf8; --radius: 8px;
}}
@media (prefers-color-scheme: light) {{
  :root {{
    --bg: #f8fafc; --surface: #ffffff; --border: #e2e8f0;
    --text: #1e293b; --muted: #64748b; --accent: #4f46e5;
    --high: #dc2626; --high-bg: #fef2f2;
    --med: #d97706; --med-bg: #fffbeb;
    --low: #16a34a; --low-bg: #f0fdf4;
    --link: #4f46e5;
  }}
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6; padding: 24px; }}
.container {{ max-width: 960px; margin: 0 auto; }}
h1 {{ font-size: 1.6rem; margin-bottom: 4px; }}
.muted {{ color: var(--muted); font-size: 0.85rem; }}
.filters {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 16px 0; align-items: center; }}
.filters label {{ font-size: 0.85rem; color: var(--muted); }}
.filters select, .filters input {{ padding: 6px 10px; border-radius: 6px;
  border: 1px solid var(--border); background: var(--surface); color: var(--text); }}
.stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0; }}
.stat {{ background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 12px 16px; flex: 1; min-width: 120px; }}
.stat .num {{ font-size: 1.8rem; font-weight: 700; }}
.stat .label {{ font-size: 0.75rem; color: var(--mutumuted); text-transform: uppercase; }}
.card {{ background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); margin: 8px 0; overflow: hidden; }}
.card-header {{ display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; cursor: pointer; }}
.card-header:hover {{ filter: brightness(1.1); }}
.card-header .title {{ font-weight: 600; font-size: 0.95rem; }}
.card-header .meta {{ font-size: 0.8rem; color: var(--muted); }}
.badge {{ padding: 2px 8px; border-radius: 999px; font-size: 0.7rem;
  font-weight: 600; text-transform: uppercase; }}
.badge-high {{ background: var(--high-bg); color: var(--high); }}
.badge-med {{ background: var(--med-bg); color: var(--med); }}
.badge-low {{ background: var(--low-bg); color: var(--low); }}
.card-body {{ padding: 0 16px 14px; font-size: 0.85rem; display: none; }}
.card-body.open {{ display: block; }}
.card-body p {{ margin: 4px 0; }}
.card-body a {{ color: var(--link); }}
.tag {{ display: inline-block; background: var(--border); border-radius: 4px;
  padding: 1px 6px; font-size: 0.7rem; margin: 2px 3px 2px 0; }}
.warnings {{ color: var(--high); font-size: 0.8rem; }}
#timeline {{ margin: 16px 0; }}
.tl-item {{ display: flex; gap: 10px; align-items: flex-start; margin: 4px 0; padding: 4px 0; }}
.tl-date {{ min-width: 80px; font-size: 0.8rem; color: var(--muted); }}
.section-title {{ font-size: 1.1rem; margin: 20px 0 8px; padding-bottom: 4px;
  border-bottom: 1px solid var(--border); }}
.empty {{ color: var(--muted); font-style: italic; padding: 16px 0; }}
</style>
</head>
<body>
<div class="container">
<h1>Brightspace Weekly Planner</h1>
<p class="muted" id="subtitle"></p>
<div class="stats" id="stats"></div>
<div class="filters">
  <label>Course:</label>
  <select id="courseFilter"><option value="">All</option></select>
  <label>Priority:</label>
  <select id="priorityFilter"><option value="">All</option>
    <option value="HIGH">HIGH</option><option value="MEDIUM">MEDIUM</option>
    <option value="LOW">LOW</option>
  </select>
  <label>Search:</label>
  <input type="text" id="searchInput" placeholder="Filter items..."/>
</div>
<h2 class="section-title">Timeline</h2>
<div id="timeline"></div>
<h2 class="section-title">Items Due (<span id="countTop">0</span>)</h2>
<div id="cardList"></div>
<h2 class="section-title">Needs Human Review</h2>
<div id="unclearSection" class="empty">None</div>
<h2 class="section-title">Errors</h2>
<div id="errorSection" class="empty">None</div>
</div>
<script>
const REPORT = __EMBEDDED_JSON__;

function el(tag, cls, text) {{
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}}

function render() {{
  const data = REPORT;
  const items = data.items_due || [];
  const unclear = data.unclear_items || [];
  const errors = data.errors || [];
  const courseSel = document.getElementById('courseFilter');
  const priSel = document.getElementById('priorityFilter');
  const searchInput = document.getElementById('searchInput');

  document.getElementById('subtitle').textContent =
    `Week: ${{data.week_start}} to ${{data.week_end}} · Last checked: ${{data.last_checked}}`;

  // Stats
  const high = items.filter(i => i.priority === 'HIGH').length;
  const med = items.filter(i => i.priority === 'MEDIUM').length;
  const low = items.filter(i => i.priority === 'LOW').length;
  const statsEl = document.getElementById('stats');
  statsEl.innerHTML = '';
  [['Total', items.length], ['HIGH', high], ['MEDIUM', med], ['LOW', low]]
    .forEach(([l, n]) => {{
      const d = el('div', 'stat');
      d.appendChild(el('div', 'num', n));
      d.appendChild(el('div', 'label', l));
      statsEl.appendChild(d);
    }});

  // Course filter options
  const courses = [...new Set(items.map(i => i.course).filter(Boolean))];
  courseSel.innerHTML = '<option value="">All</option>';
  courses.forEach(c => {{
    const o = document.createElement('option');
    o.value = c; o.textContent = c;
    courseSel.appendChild(o);
  }});

  function filtered() {{
    const cVal = courseSel.value;
    const pVal = priSel.value;
    const q = searchInput.value.toLowerCase();
    return items.filter(i => {{
      if (cVal && i.course !== cVal) return false;
      if (pVal && i.priority !== pVal) return false;
      if (q && !(`${{i.title}} ${{i.course}} ${{i.type}}`.toLowerCase().includes(q))) return false;
      return true;
    }});
  }}

  function renderCards(list) {{
    const container = document.getElementById('cardList');
    container.innerHTML = '';
    document.getElementById('countTop').textContent = list.length;
    if (!list.length) {{
      container.appendChild(el('p', 'empty', 'No items match the current filters.'));
      return;
    }}
    list.forEach((item, idx) => {{
      const card = el('div', 'card');
      const hdr = el('div', 'card-header');
      hdr.onclick = () => {{
        const b = card.querySelector('.card-body');
        b.classList.toggle('open');
      }};
      const left = el('div');
      left.appendChild(el('div', 'title', item.title || 'Untitled'));
      left.appendChild(el('div', 'meta', `${{item.course || ''}} · ${{item.type || 'unknown'}} · Due: ${{item.due_date || 'unknown'}}`));
      const badge = el('span', `badge badge-${{item.priority.toLowerCase()}}`, item.priority);
      hdr.appendChild(left); hdr.appendChild(badge);
      const body = el('div', `card-body idx-${{idx}}`);
      if (item.summary) body.appendChild(el('p', null, `Summary: ${{item.summary}}`));
      if (item.link) {{
        const a = document.createElement('a');
        a.href = item.link; a.textContent = 'Open in Brightspace'; a.target = '_blank';
        const p = el('p'); p.appendChild(a); body.appendChild(p);
      }}
      if (item.requirements && item.requirements.length) {{
        const p = el('p', null, 'Requirements:');
        item.requirements.forEach(r => p.appendChild(el('span', 'tag', r)));
        body.appendChild(p);
      }}
      if (item.warnings && item.warnings.length) {{
        item.warnings.forEach(w => body.appendChild(el('p', 'warnings', `⚠ ${{w}}`)));
      }}
      if (item.estimated_time) body.appendChild(el('p', null, `Est. time: ${{item.estimated_time}}`));
      if (item.status) body.appendChild(el('p', null, `Status: ${{item.status}}`));
      card.appendChild(hdr); card.appendChild(body);
      container.appendChild(card);
    }});
  }}

  function renderTimeline(list) {{
    const tl = document.getElementById('timeline');
    tl.innerHTML = '';
    const sorted = [...list].sort((a, b) => (a.due_date || '').localeCompare(b.due_date || ''));
    sorted.forEach(i => {{
      const row = el('div', 'tl-item');
      row.appendChild(el('div', 'tl-date', i.due_date || '?'));
      const badge = el('div', `badge badge-${{i.priority.toLowerCase()}}`, `${{i.course_code || i.course}}: ${{i.title}}`);
      row.appendChild(badge);
      tl.appendChild(row);
    }});
  }}

  function renderUnclear() {{
    const sec = document.getElementById('unclearSection');
    sec.innerHTML = ''; sec.className = '';
    if (!unclear.length) {{ sec.className = 'empty'; sec.textContent = 'None'; return; }}
    unclear.forEach(u => sec.appendChild(el('p', null, typeof u === 'string' ? u : JSON.stringify(u))));
  }}
  function renderErrors() {{
    const sec = document.getElementById('errorSection');
    sec.innerHTML = ''; sec.className = '';
    if (!errors.length) {{ sec.className = 'empty'; sec.textContent = 'None'; return; }}
    errors.forEach(e => sec.appendChild(el('p', 'warnings', e)));
  }}

  function update() {{
    const list = filtered();
    renderCards(list);
    renderTimeline(list);
  }}

  courseSel.onchange = priSel.onchange = searchInput.oninput = update;

  update();
  renderUnclear();
  renderErrors();
}}
document.addEventListener('DOMContentLoaded', render);
</script>
</body>
</html>
"""


def write_dashboard(cfg: AppConfig, report_data: dict[str, Any] | None = None) -> str:
    """Write dashboard.html. Reads report JSON if report_data not supplied."""
    out_dir = ensure_dir(cfg.output.folder)
    html_path = str(out_dir / "dashboard.html")

    if report_data is None:
        json_path = str(out_dir / "weekly_due_report.json")
        report_data = read_json(json_path) or {}

    html = _DASHBOARD_TEMPLATE.replace("__EMBEDDED_JSON__", json.dumps(report_data, default=str))

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("Dashboard written to %s", html_path)
    return html_path
