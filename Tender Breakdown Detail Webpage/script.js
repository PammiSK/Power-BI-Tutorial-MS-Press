// script.js
function tenderBreakdownDetail(report) {
  const priceRe = /\.\d{2}\s*$/; // line ends with .xx
  const rows = [];
  const dfAttributes = ['day', 'date', 'tender', 'docket_no', 'sales_rep', 'time', 'value'];

  // normalise line endings
  report = report.replace(/\r\n?/g, '\n').replace(/\\r|\\n/g, '\n');

  let day = '', date = '', tender = '';

  for (const rawLine of report.split('\n')) {
    const line = rawLine.replace(/\s+$/g, ''); // rstrip

    if (line.includes('day') && !line.includes('Total') && !line.includes('Birthday')) {
      // expects: "<Day> <dd/mm/yyyy>"
      const parts = line.trim().split(/\s+/);
      if (parts.length >= 2) {
        day = parts[0];
        date = parts[1];
      }
    }

    if (line.includes('Value')) {
      // tender name lives in first 17 chars (like Python slice)
      tender = line.slice(0, 17).trim();
    }

    if (priceRe.test(line) && !line.includes('Total')) {
      const docket_no = line.slice(0, 14).trim();
      const sales_rep = line.slice(17, 32).trim();
      const time = line.slice(32, 40).trim();
      const value = line.slice(41).trim();

      rows.push({ day, date, tender, docket_no, sales_rep, time, value });
    }
  }

  // clean + types
  for (const r of rows) {
    // numeric value
    r.value = parseFloat(String(r.value).replace(/,/g, '')) || 0;

    // make sortable keys (datefirst dd/mm/yyyy + time)
    // date: dd/mm/yyyy
    const [d, m, y] = String(r.date).split('/').map(Number);
    // time can be "HH:MM" or "HH:MM AM/PM"
    const tm = String(r.time).trim();
    let h = 0, min = 0;
    if (/am|pm/i.test(tm)) {
      const [, hh, mm, ap] = tm.match(/(\d{1,2}):(\d{2})\s*([ap]m)/i) || [];
      if (hh !== undefined) {
        h = Number(hh) % 12;
        if (/[pP]M/.test(ap)) h += 12;
        min = Number(mm);
      }
    } else {
      const [hh, mm] = tm.split(':').map(Number);
      h = Number(hh) || 0;
      min = Number(mm) || 0;
    }
    r._sortKey = new Date(y || 1970, (m || 1) - 1, d || 1, h, min, 0, 0).getTime();
  }

  // sort by date then time (ascending)
  rows.sort((a, b) => a._sortKey - b._sortKey);

  // drop helper key
  for (const r of rows) delete r._sortKey;

  return { columns: dfAttributes, rows };
}

function renderTable({ columns, rows }, mountId = 'tableWrap') {
  const el = document.getElementById(mountId);
  if (!rows.length) {
    el.innerHTML = '<p>No rows parsed.</p>';
    return;
  }
  const thead = `<thead><tr>${columns.map(c => `<th>${c}</th>`).join('')}</tr></thead>`;
  const tbody = `<tbody>${rows.map(r =>
    `<tr>${columns.map(c => `<td>${c === 'value' ? r[c].toFixed(2) : (r[c] ?? '')}</td>`).join('')}</tr>`
  ).join('')}</tbody>`;
  el.innerHTML = `<table>${thead}${tbody}</table>`;
}

document.getElementById('submitBtn').addEventListener('click', () => {
  const text = document.getElementById('userInput').value;
  const df = tenderBreakdownDetail(text);
  renderTable(df);
});

// --- Helpers: parse date/time and comparisons ---
function parseDMY(dmy) {
  // expects dd/mm/yyyy
  const [d, m, y] = String(dmy || '').split('/').map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d).getTime();
}

function parseHHMM(t) {
  // supports "12:34", "12:34 pm"
  if (!t) return null;
  const s = t.toString().trim();
  const m = s.match(/^(\d{1,2}):(\d{2})(?:\s*([ap]m))?$/i);
  if (!m) return null;
  let hh = Number(m[1]), mm = Number(m[2]);
  const ap = m[3]?.toLowerCase();
  if (ap) {
    hh = hh % 12;
    if (ap === 'pm') hh += 12;
  }
  return hh * 60 + mm; // minutes from midnight
}

function compareValue(val, op, target) {
  if (op === '' || target === '' || target == null) return true;
  const a = Number(val), b = Number(target);
  if (Number.isNaN(a) || Number.isNaN(b)) return false;
  switch (op) {
    case '=': return a === b;
    case '>': return a > b;
    case '<': return a < b;
    case '>=': return a >= b;
    case '<=': return a <= b;
    default: return true;
  }
}

// --- Filtering ---
function applyFiltersToRows(rows) {
  const repsCSV = document.getElementById('f_sales_reps').value.trim();
  const tendStr = document.getElementById('f_tender').value.trim().toLowerCase();
  const dayFilter = document.getElementById('f_day').value.trim().toLowerCase();
  const docketStr = document.getElementById('f_docket').value.trim().toLowerCase();
  const valOp = document.getElementById('f_val_op').value;
  const valNum = document.getElementById('f_val_num').value;

  const df = document.getElementById('f_date_from').value; // yyyy-mm-dd
  const dt = document.getElementById('f_date_to').value;
  const incl = document.getElementById('f_date_inclusive').checked;

  const tf = document.getElementById('f_time_from').value; // HH:MM (24h)
  const tt = document.getElementById('f_time_to').value;

  const repSet = new Set(
    repsCSV
      ? repsCSV.split(',').map(s => s.trim().toLowerCase()).filter(Boolean)
      : []
  );

  const dateFrom = df ? new Date(df + 'T00:00:00').getTime() : null;
  const dateTo = dt ? new Date(dt + 'T00:00:00').getTime() : null;

  const timeFrom = tf ? parseHHMM(tf) : null;
  const timeTo = tt ? parseHHMM(tt) : null;

  return rows.filter(r => {
    // sales rep(s)
    if (repSet.size) {
      const rep = String(r.sales_rep || '').toLowerCase();
      if (!repSet.has(rep)) return false;
    }

    // tender contains
    if (tendStr) {
      if (!String(r.tender || '').toLowerCase().includes(tendStr)) return false;
    }

    // day filter
    if (dayFilter && String(r.day || '').toLowerCase() !== dayFilter) return false;

    // docket contains
    if (docketStr) {
      if (!String(r.docket_no || '').toLowerCase().includes(docketStr)) return false;
    }

    // value comparison
    if (!compareValue(r.value, valOp, valNum)) return false;

    // date bound (r.date is dd/mm/yyyy)
    const rDate = parseDMY(r.date);
    if (rDate != null) {
      if (dateFrom != null && rDate < dateFrom) return false;
      if (dateTo != null) {
        if (incl) { if (rDate > dateTo) return false; }
        else { if (rDate >= dateTo) return false; }
      }
    }

    // time range (r.time like "12:34 pm")
    const rMin = parseHHMM(r.time);
    if (rMin != null) {
      if (timeFrom != null && rMin < timeFrom) return false;
      if (timeTo != null && rMin > timeTo) return false;
    }

    return true;
  });
}

// --- Stats / aggregations on 'value' ---
function stats(values) {
  if (!values.length) return { count: 0, sum: 0, min: null, max: null, mean: null, median: null, mode: null, sd: null };
  const count = values.length;
  const sum = values.reduce((a, b) => a + b, 0);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const mean = sum / count;

  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(count / 2);
  const median = count % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;

  // mode (most frequent; if tie, show smallest)
  const freq = new Map();
  for (const v of values) freq.set(v, (freq.get(v) || 0) + 1);
  let mode = null, mf = -1;
  for (const [v, f] of freq.entries()) if (f > mf || (f === mf && v < mode)) { mode = v; mf = f; }

  // population std dev
  const variance = values.reduce((a, b) => a + (b - mean) ** 2, 0) / count;
  const sd = Math.sqrt(variance);

  return { count, sum, min, max, mean, median, mode, sd };
}

function renderStats(rows) {
  const vals = rows.map(r => r.value).filter(v => Number.isFinite(v));
  const s = stats(vals);
  const fmt = n => (n == null ? '—' : n.toFixed(2));
  document.getElementById('statsWrap').innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(8,minmax(100px,1fr));gap:8px;max-width:1200px">
      <div><b>Count</b><div>${s.count}</div></div>
      <div><b>Sum</b><div>${fmt(s.sum)}</div></div>
      <div><b>Min</b><div>${fmt(s.min)}</div></div>
      <div><b>Max</b><div>${fmt(s.max)}</div></div>
      <div><b>Mean</b><div>${fmt(s.mean)}</div></div>
      <div><b>Median</b><div>${fmt(s.median)}</div></div>
      <div><b>Mode</b><div>${fmt(s.mode)}</div></div>
      <div><b>Std Dev</b><div>${fmt(s.sd)}</div></div>
    </div>`;
}

// --- Helpers: parse date/time and comparisons ---
function parseDMY(dmy) {
  // expects dd/mm/yyyy
  const [d, m, y] = String(dmy || '').split('/').map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d).getTime();
}

function parseHHMM(t) {
  // supports "12:34", "12:34 pm"
  if (!t) return null;
  const s = t.toString().trim();
  const m = s.match(/^(\d{1,2}):(\d{2})(?:\s*([ap]m))?$/i);
  if (!m) return null;
  let hh = Number(m[1]), mm = Number(m[2]);
  const ap = m[3]?.toLowerCase();
  if (ap) {
    hh = hh % 12;
    if (ap === 'pm') hh += 12;
  }
  return hh * 60 + mm; // minutes from midnight
}

function compareValue(val, op, target) {
  if (op === '' || target === '' || target == null) return true;
  const a = Number(val), b = Number(target);
  if (Number.isNaN(a) || Number.isNaN(b)) return false;
  switch (op) {
    case '=': return a === b;
    case '>': return a > b;
    case '<': return a < b;
    case '>=': return a >= b;
    case '<=': return a <= b;
    default: return true;
  }
}

// --- Filtering ---
function applyFiltersToRows(rows) {
  const repsCSV = document.getElementById('f_sales_reps').value.trim();
  const tendStr = document.getElementById('f_tender').value.trim().toLowerCase();
  const docketStr = document.getElementById('f_docket').value.trim().toLowerCase();
  const valOp = document.getElementById('f_val_op').value;
  const valNum = document.getElementById('f_val_num').value;

  const df = document.getElementById('f_date_from').value; // yyyy-mm-dd
  const dt = document.getElementById('f_date_to').value;
  const incl = document.getElementById('f_date_inclusive').checked;

  const tf = document.getElementById('f_time_from').value; // HH:MM (24h)
  const tt = document.getElementById('f_time_to').value;

  const repSet = new Set(
    repsCSV
      ? repsCSV.split(',').map(s => s.trim().toLowerCase()).filter(Boolean)
      : []
  );

  const dateFrom = df ? new Date(df + 'T00:00:00').getTime() : null;
  const dateTo = dt ? new Date(dt + 'T00:00:00').getTime() : null;

  const timeFrom = tf ? parseHHMM(tf) : null;
  const timeTo = tt ? parseHHMM(tt) : null;

  return rows.filter(r => {
    // sales rep(s)
    if (repSet.size) {
      const rep = String(r.sales_rep || '').toLowerCase();
      if (!repSet.has(rep)) return false;
    }

    // tender contains
    if (tendStr) {
      if (!String(r.tender || '').toLowerCase().includes(tendStr)) return false;
    }

    // docket contains
    if (docketStr) {
      if (!String(r.docket_no || '').toLowerCase().includes(docketStr)) return false;
    }

    // value comparison
    if (!compareValue(r.value, valOp, valNum)) return false;

    // date bound (r.date is dd/mm/yyyy)
    const rDate = parseDMY(r.date);
    if (rDate != null) {
      if (dateFrom != null && rDate < dateFrom) return false;
      if (dateTo != null) {
        if (incl) { if (rDate > dateTo) return false; }
        else { if (rDate >= dateTo) return false; }
      }
    }

    // time range (r.time like "12:34 pm")
    const rMin = parseHHMM(r.time);
    if (rMin != null) {
      if (timeFrom != null && rMin < timeFrom) return false;
      if (timeTo != null && rMin > timeTo) return false;
    }

    return true;
  });
}

// --- Stats / aggregations on 'value' ---
function stats(values) {
  if (!values.length) return { count: 0, sum: 0, min: null, max: null, mean: null, median: null, mode: null, sd: null };
  const count = values.length;
  const sum = values.reduce((a, b) => a + b, 0);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const mean = sum / count;

  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(count / 2);
  const median = count % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;

  // mode (most frequent; if tie, show smallest)
  const freq = new Map();
  for (const v of values) freq.set(v, (freq.get(v) || 0) + 1);
  let mode = null, mf = -1;
  for (const [v, f] of freq.entries()) if (f > mf || (f === mf && v < mode)) { mode = v; mf = f; }

  // population std dev
  const variance = values.reduce((a, b) => a + (b - mean) ** 2, 0) / count;
  const sd = Math.sqrt(variance);

  return { count, sum, min, max, mean, median, mode, sd };
}

function renderStats(rows) {
  const vals = rows.map(r => r.value).filter(v => Number.isFinite(v));
  const s = stats(vals);
  const fmt = n => (n == null ? '—' : n.toFixed(2));
  document.getElementById('statsWrap').innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(8,minmax(100px,1fr));gap:8px;max-width:1200px">
      <div><b>Count</b><div>${s.count}</div></div>
      <div><b>Sum</b><div>${fmt(s.sum)}</div></div>
      <div><b>Min</b><div>${fmt(s.min)}</div></div>
      <div><b>Max</b><div>${fmt(s.max)}</div></div>
      <div><b>Mean</b><div>${fmt(s.mean)}</div></div>
      <div><b>Median</b><div>${fmt(s.median)}</div></div>
      <div><b>Mode</b><div>${fmt(s.mode)}</div></div>
      <div><b>Std Dev</b><div>${fmt(s.sd)}</div></div>
    </div>`;
}

let ALL_ROWS = []; // global in this page

document.getElementById('submitBtn').addEventListener('click', () => {
  const text = document.getElementById('userInput').value;
  const df = tenderBreakdownDetail(text);
  ALL_ROWS = df.rows; // keep raw parsed
  renderTable(df);
  renderStats(ALL_ROWS);
});

// Apply & Clear
document.getElementById('applyFilters').addEventListener('click', () => {
  const filtered = applyFiltersToRows(ALL_ROWS);
  renderTable({ columns: ['day', 'date', 'tender', 'docket_no', 'sales_rep', 'time', 'value'], rows: filtered });
  renderStats(filtered);
});

document.getElementById('clearFilters').addEventListener('click', () => {
  // reset inputs
  for (const id of ['f_sales_reps', 'f_tender', 'f_docket', 'f_val_num', 'f_date_from', 'f_date_to', 'f_time_from', 'f_time_to']) {
    const el = document.getElementById(id); if (el) el.value = '';
  }
  document.getElementById('f_val_op').value = '';
  document.getElementById('f_date_inclusive').checked = true;

  renderTable({ columns: ['day', 'date', 'tender', 'docket_no', 'sales_rep', 'time', 'value'], rows: ALL_ROWS });
  renderStats(ALL_ROWS);
});
