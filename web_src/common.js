/* Shared helpers for the three interfaces. Every page loads data.js (window.DATA) and this file.
   Rules enforced here (so the pages cannot drift apart):
   - all catalogue metrics are always listed, populated or not;
   - a value is plotted only if it is a real number (null/''/text never become 0);
   - uncertainty bounds in data.js are absolute; ranges, qualifiers and digitized values are shown as such;
   - a page never crashes on an empty database: it shows an explanatory banner instead. */
(function () {
  'use strict';
  if (!window.DATA) { document.body.insertAdjacentHTML('afterbegin', '<p class="banner">data.js not found. Run: python scripts/build.py</p>'); throw new Error('no DATA'); }
  const D = window.DATA;
  const STAT_ORDER = ['individual', 'minimum', 'mean', 'median', 'maximum', 'category'];
  const STAT_LABEL = { individual: 'Individual / event value', minimum: 'Minimum', mean: 'Mean / average', median: 'Median', maximum: 'Maximum', category: 'Category' };
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const isNum = x => typeof x === 'number' && Number.isFinite(x);
  const byId = (arr, key) => new Map(arr.map(x => [x[key], x]));
  const metricMap = byId(D.metrics, 'metric_id'), eventMap = byId(D.events, 'event_id'), srcMap = byId(D.sources, 'pub_id');

  // ---- indexes (built once) ----
  const recByMetric = new Map(), recByEventMetric = new Map();
  D.records.forEach(r => {
    (recByMetric.get(r.metric_id) || recByMetric.set(r.metric_id, []).get(r.metric_id)).push(r);
    const k = r.target_id + '|' + r.metric_id;
    (recByEventMetric.get(k) || recByEventMetric.set(k, []).get(k)).push(r);
  });
  const metricRecords = mid => recByMetric.get(mid) || [];
  const eventMetricRecords = (eid, mid) => recByEventMetric.get(eid + '|' + mid) || [];
  const eventRecords = (eid, mid, stat) => eventMetricRecords(eid, mid).filter(r => r.statistic_type === stat);
  const metricEvents = mid => new Set(metricRecords(mid).map(r => r.target_id));
  const median = v => { if (!v.length) return null; v = [...v].sort((a, b) => a - b); const n = v.length; return n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2; };

  // value shown for an event on a map / scatter: median across studies of the plottable numbers (categorical: first label)
  function eventValue(eid, mid, stat) {
    const a = eventRecords(eid, mid, stat);
    const n = a.filter(r => r.plottable && isNum(r.value)).map(r => r.value);
    if (n.length) return median(n);
    const t = a.find(r => r.plottable && typeof r.value === 'string' && r.metric_value_type === 'categorical');
    return t ? t.value : null;
  }
  const availableStats = mid => [...new Set(metricRecords(mid).map(r => r.statistic_type))].sort((a, b) => STAT_ORDER.indexOf(a) - STAT_ORDER.indexOf(b));

  function fillMetrics(sel, opts = {}) {
    sel.innerHTML = '';
    const groups = {};
    D.metrics.forEach(m => {
      const g = groups[m.category] || (groups[m.category] = Object.assign(document.createElement('optgroup'), { label: m.category || 'other' }));
      const n = metricEvents(m.metric_id).size;
      if (opts.onlyPopulated && !n) return;
      const o = new Option(m.display_name + (n ? ` (${n} event${n === 1 ? '' : 's'})` : ' (no data yet)'), m.metric_id);
      if (!n) o.className = 'nodata';
      g.appendChild(o);
    });
    Object.values(groups).forEach(g => g.children.length && sel.appendChild(g));
  }
  function fillStats(sel, mid, preferred) {
    const a = availableStats(mid);
    sel.innerHTML = '';
    if (!a.length) { sel.add(new Option('— no data —', '')); sel.disabled = true; return; }
    sel.disabled = false;
    a.forEach(s => sel.add(new Option(STAT_LABEL[s] || s, s)));
    sel.value = a.includes(preferred) ? preferred : a[0];
  }
  const firstPopulated = (pref) => (pref && metricRecords(pref).length) ? pref : (D.metrics.find(m => metricRecords(m.metric_id).length) || D.metrics[0] || {}).metric_id;

  const fmtNum = (v, u = '') => isNum(v) ? Number(v.toPrecision(6)) + (u ? ' ' + u : '') : esc(v);
  const mwText = e => e.mw_range || (isNum(e.mw) ? String(e.mw) : 'not reported');

  // ---- URL state (shareable views) ----
  const params = new URLSearchParams(location.hash.slice(1));
  const getParam = k => params.get(k);
  function setParams(obj) {
    Object.entries(obj).forEach(([k, v]) => v ? params.set(k, v) : params.delete(k));
    try { history.replaceState(null, '', '#' + params.toString()); } catch (e) { /* file:// sandbox */ }
  }

  // ---- provenance panel (identical on all pages) ----
  function valueText(r) {
    if (isNum(r.value)) return fmtNum(r.value, r.unit);
    if (r.value_lo != null && r.value_hi != null) return esc(r.value) + (r.unit ? ' ' + r.unit : '') + ' (published range)';
    return esc(r.value) + (r.unit && r.metric_value_type !== 'categorical' ? ' ' + r.unit : '');
  }
  function uncText(r) {
    if (r.uncertainty_type === 'not_reported' || r.uncertainty_type === 'not_propagated') return r.uncertainty_type === 'not_propagated' ? 'not propagated for computed statistics' : 'not reported';
    const lo = isNum(r.uncertainty_lower) ? fmtNum(r.uncertainty_lower) : '—', hi = isNum(r.uncertainty_upper) ? fmtNum(r.uncertainty_upper) : '—';
    return esc(r.uncertainty_type) + (isNum(r.uncertainty_lower) || isNum(r.uncertainty_upper) ? ` [${lo} … ${hi}]` : '');
  }
  function pubLinks(r) {
    return String(r.source_id || '').split('|').filter(Boolean).map(p => {
      const s = srcMap.get(p);
      if (!s) return esc(p);
      return esc(s.citation_full || s.citation_short) + (s.doi ? ` <a href="https://doi.org/${encodeURI(s.doi)}" target="_blank" rel="noopener">doi:${esc(s.doi)}</a>` : '');
    }).join('<br>');
  }
  function ctxText(r) {
    const bits = [];
    if (r.quality && r.quality !== 'not_assessed') bits.push('<b>Quality:</b> ' + esc(r.quality) + (r.quality_reason ? ' (' + esc(r.quality_reason) + ')' : ''));
    if (r.measurement_start || r.measurement_end) bits.push('<b>Measured:</b> ' + esc(r.measurement_start || '?') + (r.measurement_end && r.measurement_end !== r.measurement_start ? ' – ' + esc(r.measurement_end) : ''));
    if (r.spatial_resolution) bits.push('<b>Spatial resolution:</b> ' + esc(r.spatial_resolution));
    if (isNum(r.sensitivity_threshold)) bits.push('<b>Sensitivity threshold:</b> ' + fmtNum(r.sensitivity_threshold, r.sensitivity_threshold_unit || ''));
    if (isNum(r.confidence_level)) bits.push('<b>Confidence level:</b> ' + fmtNum(r.confidence_level) + ' %');
    if (r.dataset_id) bits.push('<b>Dataset:</b> ' + esc(r.dataset_id));
    if (isNum(r.longitude) && isNum(r.latitude)) bits.push('<b>Location:</b> ' + r.latitude.toFixed(4) + ', ' + r.longitude.toFixed(4) + (r.coordinate_origin === 'converted' ? ' (converted: ' + esc(r.coordinate_conversion_method || '') + ')' : ''));
    return bits.length ? '<br>' + bits.join('<br>') : '';
  }
  function recordCard(r, open) {
    const dig = r.origin === 'figure_digitized';
    return '<details class="value"' + (open ? ' open' : '') + '><summary>' + esc(STAT_LABEL[r.statistic_type] || r.statistic_type) + ': ' + valueText(r) + '</summary><div class="meta">' +
      (r.component ? '<span class="tag">' + esc(r.component) + '</span>' : '') +
      (r.segment ? '<span class="tag">segment: ' + esc(r.segment) + '</span>' : '') +
      (r.model_id ? '<span class="tag">model: ' + esc(r.model_id) + '</span>' : '') +
      '<span class="tag">' + (r.value_origin === 'reported' ? 'Published value' : 'Computed from a published array') + '</span>' +
      (dig ? '<span class="tag dig">digitized from figure ±' + fmtNum(r.digitization_unc) + ' (' + esc(r.digitization_method) + ')</span>' : '') +
      (r.review_status && r.review_status !== 'draft' ? '<span class="tag">' + esc(r.review_status.replace(/_/g, ' ')) + '</span>' : '<span class="tag">not yet reviewed</span>') +
      '<br><b>Study reference:</b><br>' + pubLinks(r) +
      (r.compiled_in_reference ? '<br><b>Compiled in:</b> ' + esc(r.compiled_in_reference) + '<br><b>Measurement attributed to:</b> ' + esc(r.original_measurement_reference || 'not specified') : '<br><b>Compiled from another source:</b> no') +
      '<br><b>Uncertainty:</b> ' + uncText(r) +
      (r.method || r.method_details ? '<br><b>Method:</b> ' + esc([r.method, r.method_details].filter(Boolean).join(' - ')) : '') +
      (r.sample_count ? '<br><b>Number of measurements:</b> ' + r.sample_count : '') +
      (r.calculation ? '<br><b>Permitted calculation:</b> ' + esc(r.calculation) : '') +
      ctxText(r) +
      '<br><b>Source location:</b> ' + esc(r.source_location || '—') +
      '<br><b>Stored at:</b> ' + esc(r.database_location || '') + '</div></details>';
  }
  const recordsPanel = a => a.length ? a.map((r, i) => recordCard(r, i === 0)).join('') : '<p class="empty">No published records for this exact statistic.</p>';

  // ---- CSV download of exactly what a page shows ----
  function downloadCSV(name, rows) {
    if (!rows.length) return;
    const cols = Object.keys(rows[0]);
    const q = v => { v = v == null ? '' : String(v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
    const blob = new Blob([[cols.join(','), ...rows.map(r => cols.map(c => q(r[c])).join(','))].join('\n')], { type: 'text/csv' });
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: name });
    document.body.appendChild(a); a.click(); a.remove();
  }

  // ---- navigation + build badge ----
  function nav(active) {
    const pages = [['index.html', 'Overview'], ['map.html', 'Map'], ['correlation.html', 'Correlations'], ['comparison.html', 'Study comparison']];
    const b = D.build || {};
    const el = document.createElement('nav');
    el.className = 'nav';
    el.innerHTML = pages.map(([h, t]) => `<a href="${h}"${h === active ? ' class="on"' : ''}>${t}</a>`).join('') +
      `<span class="badge">${b.records ?? 0} records · ${b.events ?? D.events.length} events · ${b.publications ?? 0} publications · build ${esc(b.hash || '?')}</span>`;
    document.body.prepend(el);
  }
  function banner(el, mid) {
    const populated = D.metrics.filter(m => metricRecords(m.metric_id).length).length;
    if (!D.records.length) { el.hidden = false; el.textContent = 'The database contains no observations yet. The event list and metric catalogue are in place; add data with the ingestion workbook (see CONTRIBUTING.md).'; }
    else if (mid && !metricRecords(mid).length) { el.hidden = false; el.textContent = `No records yet for this metric (${populated} of ${D.metrics.length} metrics have data).`; }
    else el.hidden = true;
  }

  window.RDB = { D, STAT_ORDER, STAT_LABEL, esc, isNum, metricMap, eventMap, srcMap, metricRecords, eventMetricRecords, eventRecords, metricEvents, median,
    eventValue, availableStats, fillMetrics, fillStats, firstPopulated, fmtNum, mwText, getParam, setParams, recordCard, recordsPanel, valueText,
    downloadCSV, nav, banner };
})();
