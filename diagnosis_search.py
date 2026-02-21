import os
import re
import csv
from flask import Flask, request, jsonify, render_template_string
from rapidfuzz import fuzz

app = Flask(__name__)

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "IDEA4RC - Diagnosis codes - diagnosis-codes-list.csv")
TOPO_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "Topography site ICD-O_October_2025_OMOP.xlsx - Topography.csv")

TABLE_LIMIT = 500  # max rows shown in the results table


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Lowercase, replace hyphens/underscores/slashes with spaces, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[-_/,]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# ICD-O code expansion helpers
# ---------------------------------------------------------------------------

def expand_icdo_code(code_str: str) -> list:
    """
    Expand an ICD-O-3 code string to a list of (code, is_prefix) tuples.

    Handles:
      - Simple:        C10.0  → [("C10.0", False)]
      - Decimal range: C34.1-34.9 / C15.0-C15.9 / C38.1-38.8
      - Major range:   C53-C54-C55 / C64-C65   → prefix matches
    """
    code_str = code_str.strip()
    if not code_str:
        return []

    # Decimal range: C34.1-34.9 or C15.0-C15.9 or C38.1-38.8 or C21.0-21.8
    m = re.match(r"^C(\d+)\.(\d+)-(?:C\d+\.)?(\d+)$", code_str)
    if m:
        major = int(m.group(1))
        minor_start = int(m.group(2))
        minor_end = int(m.group(3))
        return [(f"C{major:02d}.{minor}", False)
                for minor in range(minor_start, minor_end + 1)]

    # Major range with dashes: C53-C54-C55 or C64-C65
    if "-" in code_str:
        parts = re.split(r"-", code_str)
        major_matches = [re.match(r"^C?(\d+)$", p.strip()) for p in parts]
        if all(major_matches):
            nums = [int(m_.group(1)) for m_ in major_matches]
            return [(f"C{major:02d}", True)
                    for major in range(nums[0], nums[-1] + 1)]

    # Simple: C10.0  or  C12  (with possible trailing space)
    m = re.match(r"^C(\d+)(?:\.(\d+))?", code_str)
    if m:
        major = int(m.group(1))
        if m.group(2) is not None:
            return [(f"C{major:02d}.{m.group(2)}", False)]
        return [(f"C{major:02d}", True)]

    return []


def code_matches(diag_code: str, rules: list) -> bool:
    """Return True if diag_code satisfies any of the (code, is_prefix) rules."""
    for code, is_prefix in rules:
        if is_prefix:
            if diag_code == code or diag_code.startswith(code + "."):
                return True
        else:
            if diag_code == code:
                return True
    return False


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data() -> list:
    """Load diagnosis CSV; each entry is a dict with id, topo, name."""
    data = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) >= 6:
                id_val = row[3].strip()    # column D
                topo   = row[2].strip()    # column C
                name   = row[5].strip()    # column F
                if id_val and name:
                    data.append({"id": id_val, "topo": topo, "name": name})
    return data


def load_topography(data: list) -> tuple:
    """
    Parse the topography CSV and build:
      - topo_lookup  : {topo_code -> [{macrogrouping, group, site}, ...]}
      - filter_opts  : {macrogroupings, groups, sites}  (cascading)
    """
    # 1. Parse topography CSV into rules
    topo_rules = []   # (expanded_rules, macrogrouping, group, site)
    with open(TOPO_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header: Subsite, ICD-O-3, Site, Group, Macrogrouping
        for row in reader:
            if len(row) < 2:
                continue
            icdo3 = row[1].strip() if len(row) > 1 else ""
            site  = row[2].strip() if len(row) > 2 else ""
            group = row[3].strip() if len(row) > 3 else ""
            macro = row[4].strip() if len(row) > 4 else ""
            if not icdo3:
                continue
            rules = expand_icdo_code(icdo3)
            if rules:
                topo_rules.append((rules, macro, group, site))

    # 2. Match every unique topography code in the diagnosis data
    unique_topo = set(e["topo"] for e in data if e["topo"])
    topo_lookup: dict = {}
    for diag_code in unique_topo:
        attrs_list = []
        for rules, macro, group, site in topo_rules:
            if code_matches(diag_code, rules):
                attrs = {"macrogrouping": macro, "group": group, "site": site}
                if attrs not in attrs_list:
                    attrs_list.append(attrs)
        if attrs_list:
            topo_lookup[diag_code] = attrs_list

    # 3. Build cascading filter option sets
    macrogroupings: set = set()
    groups_by_macro: dict = {}
    sites_by_group: dict = {}
    for attrs_list in topo_lookup.values():
        for a in attrs_list:
            macro = a["macrogrouping"]
            group = a["group"]
            site  = a["site"]
            if macro:
                macrogroupings.add(macro)
                groups_by_macro.setdefault(macro, set())
                if group:
                    groups_by_macro[macro].add(group)
            if group:
                sites_by_group.setdefault(group, set())
                if site:
                    sites_by_group[group].add(site)

    filter_opts = {
        "macrogroupings": sorted(macrogroupings),
        "groups":  {k: sorted(v) for k, v in groups_by_macro.items()},
        "sites":   {k: sorted(v) for k, v in sites_by_group.items()},
    }
    return topo_lookup, filter_opts


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def apply_topo_filter(data: list, topo_lookup: dict,
                      macro: str, group: str, site: str) -> list:
    """Keep only entries whose topography code matches all supplied filter values."""
    if not (macro or group or site):
        return data
    out = []
    for entry in data:
        for a in topo_lookup.get(entry["topo"], []):
            if macro and a["macrogrouping"] != macro:
                continue
            if group and a["group"] != group:
                continue
            if site and a["site"] != site:
                continue
            out.append(entry)
            break
    return out


def search(query: str, data: list, threshold: int = 80,
           macro: str = "", group: str = "", site: str = "") -> dict:
    """
    1. Optionally filter by topography (macro / group / site).
    2. Optionally fuzzy-match NAME against query.
    Returns dict with all ids and up to TABLE_LIMIT result rows.
    """
    # Topography filter
    working = apply_topo_filter(data, TOPO_LOOKUP, macro, group, site)

    # Name fuzzy search
    query = query.strip()
    if query:
        norm_q = normalize(query)
        results = []
        for e in working:
            score = fuzz.partial_ratio(norm_q, normalize(e["name"]))
            if score >= threshold:
                results.append({"id": e["id"], "name": e["name"], "score": round(score, 1)})
        results.sort(key=lambda x: -x["score"])
    else:
        results = [{"id": e["id"], "name": e["name"], "score": None} for e in working]

    total = len(results)
    ids   = [r["id"] for r in results]
    return {
        "total":     total,
        "truncated": total > TABLE_LIMIT,
        "ids":       ids,
        "ids_csv":   ",".join(ids),
        "results":   results[:TABLE_LIMIT],
    }


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

DATA = load_data()
print(f"Loaded {len(DATA)} diagnosis entries.")

TOPO_LOOKUP, FILTER_OPTIONS = load_topography(DATA)
print(f"Topography lookup: {len(TOPO_LOOKUP)} unique codes mapped.")
print(f"Filter options: {FILTER_OPTIONS['macrogroupings']}")


# ---------------------------------------------------------------------------
# HTML / UI
# ---------------------------------------------------------------------------

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>IDEA4RC Diagnosis Code Search</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f0f2f5;
      color: #1a1a2e;
      min-height: 100vh;
      padding: 2rem 1rem;
    }

    .container { max-width: 900px; margin: 0 auto; }

    header { margin-bottom: 2rem; }
    header h1 { font-size: 1.6rem; font-weight: 700; }
    header p  { margin-top: 0.3rem; font-size: 0.9rem; color: #555; }

    .card {
      background: #fff;
      border-radius: 10px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }

    /* ---- search row ---- */
    .search-row {
      display: flex;
      gap: 0.75rem;
      align-items: flex-end;
      flex-wrap: wrap;
    }

    .field { display: flex; flex-direction: column; gap: 0.35rem; }
    .field label {
      font-size: 0.75rem; font-weight: 700; color: #444;
      text-transform: uppercase; letter-spacing: 0.05em;
    }

    input[type="text"], select {
      padding: 0.55rem 0.8rem;
      border: 1.5px solid #d0d5dd;
      border-radius: 7px;
      font-size: 0.95rem;
      outline: none;
      background: #fff;
      transition: border-color 0.2s;
    }
    input[type="text"]:focus, select:focus { border-color: #4361ee; }
    input[type="text"] { width: 300px; }
    select { min-width: 160px; cursor: pointer; color: #1a1a2e; }
    select:disabled { background: #f5f5f5; color: #aaa; cursor: not-allowed; }

    .range-row { display: flex; align-items: center; gap: 0.5rem; }
    input[type="range"] { width: 110px; accent-color: #4361ee; }
    .threshold-display {
      font-size: 0.85rem; color: #4361ee; font-weight: 700; min-width: 28px; text-align: center;
    }

    button#searchBtn {
      padding: 0.58rem 1.4rem;
      background: #4361ee; color: #fff;
      border: none; border-radius: 7px;
      font-size: 0.95rem; font-weight: 600;
      cursor: pointer; transition: background 0.2s;
      align-self: flex-end;
    }
    button#searchBtn:hover    { background: #3451d1; }
    button#searchBtn:disabled { background: #a0aec0; cursor: not-allowed; }

    /* ---- filter row ---- */
    .filter-row {
      display: flex; gap: 0.75rem; align-items: flex-end;
      flex-wrap: wrap; margin-top: 1rem;
      padding-top: 1rem; border-top: 1px solid #edf0f4;
    }

    .filter-label-row {
      display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.1rem;
    }
    .filter-title {
      font-size: 0.75rem; font-weight: 700; color: #444;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .filter-hint { font-size: 0.75rem; color: #888; }

    button#clearFilters {
      padding: 0.35rem 0.9rem;
      background: #fff0f0; color: #c53030;
      border: 1.5px solid #fed7d7; border-radius: 6px;
      font-size: 0.8rem; font-weight: 600; cursor: pointer;
      align-self: flex-end;
      transition: background 0.15s;
    }
    button#clearFilters:hover { background: #ffe0e0; }

    .spinner {
      display: none; width: 20px; height: 20px;
      border: 3px solid #e0e7ff; border-top-color: #4361ee;
      border-radius: 50%; animation: spin 0.7s linear infinite;
      margin-left: 0.5rem; vertical-align: middle;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ---- IDs output ---- */
    .ids-section { display: none; }
    .section-header {
      display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.6rem;
    }
    .section-title {
      font-size: 0.75rem; font-weight: 700; color: #444;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .count-badge {
      font-size: 0.78rem; background: #edf2ff; color: #4361ee;
      border-radius: 20px; padding: 0.15rem 0.6rem; font-weight: 700;
    }
    .warn-badge {
      font-size: 0.78rem; background: #fff8e1; color: #b7791f;
      border-radius: 20px; padding: 0.15rem 0.6rem; font-weight: 600;
    }

    .ids-box { display: flex; gap: 0.6rem; align-items: stretch; }
    #idsOutput {
      flex: 1; font-family: monospace; font-size: 0.82rem;
      padding: 0.6rem 0.85rem;
      border: 1.5px solid #d0d5dd; border-radius: 7px;
      background: #f8fafc; color: #1a1a2e;
      word-break: break-all; min-height: 2.4rem; line-height: 1.6;
      max-height: 120px; overflow-y: auto;
    }
    button#copyBtn {
      padding: 0.5rem 1rem;
      background: #edf2ff; color: #4361ee;
      border: 1.5px solid #c5d0fa; border-radius: 7px;
      font-size: 0.88rem; font-weight: 600; cursor: pointer;
      white-space: nowrap; transition: background 0.2s;
    }
    button#copyBtn:hover  { background: #dde6ff; }
    button#copyBtn.copied { background: #d1fae5; color: #059669; border-color: #6ee7b7; }

    /* ---- table ---- */
    .table-wrapper { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.87rem; }
    thead th {
      text-align: left; padding: 0.6rem 0.8rem;
      font-size: 0.72rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.05em; color: #555;
      border-bottom: 2px solid #e8ecf0;
    }
    tbody tr:hover { background: #f8fafc; }
    tbody td { padding: 0.5rem 0.8rem; border-bottom: 1px solid #edf0f4; color: #333; }
    td.id-cell { font-family: monospace; font-weight: 700; color: #4361ee; white-space: nowrap; }
    td.score-cell { text-align: center; white-space: nowrap; }
    .score-bar {
      display: inline-block; height: 6px; border-radius: 3px;
      background: #4361ee; vertical-align: middle; margin-right: 4px;
    }
    .empty-state { text-align: center; padding: 2rem; color: #888; font-size: 0.9rem; }
    .truncation-note {
      padding: 0.6rem 0.8rem; background: #fff8e1; color: #92400e;
      font-size: 0.82rem; border-top: 1px solid #fde68a;
    }
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>IDEA4RC Diagnosis Code Search</h1>
    <p>Search by name and/or filter by topography to retrieve matching diagnosis IDs.</p>
  </header>

  <div class="card">
    <!-- Search row -->
    <div class="search-row">
      <div class="field" style="flex:1; min-width:200px;">
        <label for="queryInput">Search term</label>
        <input type="text" id="queryInput" placeholder='e.g. "well differentiated"' autocomplete="off" />
      </div>

      <div class="field">
        <label>Fuzzy threshold</label>
        <div class="range-row">
          <input type="range" id="threshold" min="50" max="100" value="80" step="1" />
          <span class="threshold-display" id="thresholdVal">80</span>
        </div>
      </div>

      <button id="searchBtn">Search</button>
      <span class="spinner" id="spinner"></span>
    </div>

    <!-- Filter row -->
    <div class="filter-row">
      <div style="width:100%; display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem;">
        <span class="filter-title">Topography filters</span>
        <span class="filter-hint">(optional — cascade left to right)</span>
      </div>

      <div class="field">
        <label>Macrogrouping</label>
        <select id="filterMacro">
          <option value="">All</option>
        </select>
      </div>

      <div class="field">
        <label>Group</label>
        <select id="filterGroup" disabled>
          <option value="">All</option>
        </select>
      </div>

      <div class="field">
        <label>Site</label>
        <select id="filterSite" disabled>
          <option value="">All</option>
        </select>
      </div>

      <button id="clearFilters">Clear filters</button>
    </div>
  </div>

  <!-- IDs output -->
  <div class="card ids-section" id="idsSection">
    <div class="section-header">
      <span class="section-title">Matching IDs</span>
      <span class="count-badge" id="countBadge">0</span>
      <span class="warn-badge" id="truncWarn" style="display:none;"></span>
    </div>
    <div class="ids-box">
      <div id="idsOutput">—</div>
      <button id="copyBtn">Copy</button>
    </div>
  </div>

  <!-- Results table -->
  <div class="card" id="resultsCard" style="display:none;">
    <div class="section-header" style="margin-bottom:0.8rem;">
      <span class="section-title">Results</span>
    </div>
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th id="scoreHeader" style="text-align:center;">Score</th>
          </tr>
        </thead>
        <tbody id="resultsBody"></tbody>
      </table>
    </div>
    <div class="truncation-note" id="truncNote" style="display:none;"></div>
  </div>
</div>

<script>
  // ---- DOM refs ----
  const queryInput  = document.getElementById('queryInput');
  const thresholdEl = document.getElementById('threshold');
  const thresholdValEl = document.getElementById('thresholdVal');
  const searchBtn   = document.getElementById('searchBtn');
  const spinner     = document.getElementById('spinner');
  const filterMacro = document.getElementById('filterMacro');
  const filterGroup = document.getElementById('filterGroup');
  const filterSite  = document.getElementById('filterSite');
  const clearFiltersBtn = document.getElementById('clearFilters');
  const idsSection  = document.getElementById('idsSection');
  const idsOutput   = document.getElementById('idsOutput');
  const copyBtn     = document.getElementById('copyBtn');
  const countBadge  = document.getElementById('countBadge');
  const truncWarn   = document.getElementById('truncWarn');
  const resultsCard = document.getElementById('resultsCard');
  const resultsBody = document.getElementById('resultsBody');
  const truncNote   = document.getElementById('truncNote');
  const scoreHeader = document.getElementById('scoreHeader');

  // ---- Filter options (loaded once) ----
  let FILTER_OPTS = { macrogroupings: [], groups: {}, sites: {} };

  async function loadFilters() {
    const res = await fetch('/filters');
    FILTER_OPTS = await res.json();
    // Populate macrogrouping
    for (const m of FILTER_OPTS.macrogroupings) {
      const opt = document.createElement('option');
      opt.value = opt.textContent = m;
      filterMacro.appendChild(opt);
    }
  }

  // ---- Cascading filter logic ----
  filterMacro.addEventListener('change', () => {
    const macro = filterMacro.value;
    resetSelect(filterGroup, true);
    resetSelect(filterSite, true);

    if (macro && FILTER_OPTS.groups[macro]) {
      filterGroup.disabled = false;
      for (const g of FILTER_OPTS.groups[macro]) {
        const opt = document.createElement('option');
        opt.value = opt.textContent = g;
        filterGroup.appendChild(opt);
      }
    }
  });

  filterGroup.addEventListener('change', () => {
    const group = filterGroup.value;
    resetSelect(filterSite, true);

    if (group && FILTER_OPTS.sites[group]) {
      filterSite.disabled = false;
      for (const s of FILTER_OPTS.sites[group]) {
        const opt = document.createElement('option');
        opt.value = opt.textContent = s;
        filterSite.appendChild(opt);
      }
    }
  });

  function resetSelect(sel, disable) {
    sel.innerHTML = '<option value="">All</option>';
    sel.disabled = disable;
  }

  clearFiltersBtn.addEventListener('click', () => {
    filterMacro.value = '';
    resetSelect(filterGroup, true);
    resetSelect(filterSite, true);
  });

  // ---- Threshold display ----
  thresholdEl.addEventListener('input', () => {
    thresholdValEl.textContent = thresholdEl.value;
  });

  // ---- Search ----
  async function doSearch() {
    const query = queryInput.value.trim();
    const macro = filterMacro.value;
    const group = filterGroup.value;
    const site  = filterSite.value;

    if (!query && !macro && !group && !site) return;

    searchBtn.disabled = true;
    spinner.style.display = 'inline-block';

    try {
      const res = await fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          threshold: parseInt(thresholdEl.value),
          macro, group, site
        })
      });
      const data = await res.json();

      // IDs section
      idsSection.style.display = 'block';
      countBadge.textContent = data.total.toLocaleString();
      idsOutput.textContent = data.ids_csv || '(no matches)';

      if (data.truncated) {
        truncWarn.style.display = 'inline';
        truncWarn.textContent = `Showing top ${data.results.length.toLocaleString()} of ${data.total.toLocaleString()}`;
      } else {
        truncWarn.style.display = 'none';
      }

      // Table
      resultsCard.style.display = 'block';
      resultsBody.innerHTML = '';
      const hasScore = query.length > 0;
      scoreHeader.style.display = hasScore ? '' : 'none';

      if (data.results.length === 0) {
        resultsBody.innerHTML = `<tr><td colspan="3" class="empty-state">No matches found. Try lowering the threshold or adjusting filters.</td></tr>`;
      } else {
        for (const r of data.results) {
          const tr = document.createElement('tr');
          const scoreTd = hasScore
            ? `<td class="score-cell" style="display:''">
                 <span class="score-bar" style="width:${Math.round((r.score/100)*60)}px"></span>${r.score}%
               </td>`
            : `<td style="display:none"></td>`;
          tr.innerHTML = `
            <td class="id-cell">${r.id}</td>
            <td>${escHtml(r.name)}</td>
            ${scoreTd}`;
          resultsBody.appendChild(tr);
        }
      }

      // Truncation note
      if (data.truncated) {
        truncNote.style.display = 'block';
        truncNote.textContent =
          `Table shows the first ${data.results.length.toLocaleString()} rows. ` +
          `All ${data.total.toLocaleString()} IDs are included in the copy box above.`;
      } else {
        truncNote.style.display = 'none';
      }
    } finally {
      searchBtn.disabled = false;
      spinner.style.display = 'none';
    }
  }

  searchBtn.addEventListener('click', doSearch);
  queryInput.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

  // ---- Copy ----
  copyBtn.addEventListener('click', () => {
    const text = idsOutput.textContent;
    if (!text || text === '—' || text === '(no matches)') return;
    navigator.clipboard.writeText(text).then(() => {
      copyBtn.textContent = 'Copied!';
      copyBtn.classList.add('copied');
      setTimeout(() => { copyBtn.textContent = 'Copy'; copyBtn.classList.remove('copied'); }, 1800);
    });
  });

  function escHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ---- Init ----
  loadFilters();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/filters")
def get_filters():
    return jsonify(FILTER_OPTIONS)


@app.route("/search", methods=["POST"])
def do_search():
    body      = request.get_json(force=True)
    query     = body.get("query", "").strip()
    threshold = int(body.get("threshold", 80))
    macro     = body.get("macro", "").strip()
    group     = body.get("group", "").strip()
    site      = body.get("site",  "").strip()

    if not query and not macro and not group and not site:
        return jsonify({"total": 0, "truncated": False, "ids": [], "ids_csv": "", "results": []})

    result = search(query, DATA, threshold, macro=macro, group=group, site=site)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=False, port=5001)
