/* ── État ───────────────────────────────────────────────────────────── */
const state = {
  fileId    : null,
  historyId : null,
  opts      : { dup: true, miss: true, out: true, norm: true },
};

/* ── Upload ─────────────────────────────────────────────────────────── */
const fileInput  = document.getElementById('fileInput');
const uploadZone = document.getElementById('uploadZone');

if (fileInput) {
  fileInput.addEventListener('change', async e => {
    const file = e.target.files[0];
    if (!file) return;
    uploadFile(file);
    await analyzeFile(file);
  });
}

if (uploadZone) {
  uploadZone.addEventListener('dragover', e => {
    e.preventDefault(); uploadZone.classList.add('drag-over');
  });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault(); uploadZone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]);
  });
}

async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  setUploadUI(file.name, `${(file.size / 1024).toFixed(1)} Ko`, '⏳');

  try {
    const res  = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.error) {
      setUploadUI('Erreur', data.error, '❌');
      return;
    }
    state.fileId = data.file_id;
    setUploadUI(file.name, data.warning ? '⚠ Fichier déjà traité' : `${(file.size / 1024).toFixed(1)} Ko`, '✅');
    showAlert('fileAlert', `Fichier prêt : ${file.name}`);
    uploadZone.classList.add('has-file');
  } catch (err) {
    setUploadUI('Erreur réseau', err.message, '❌');
  }
}

function setUploadUI(label, sub, icon) {
  document.getElementById('uploadIcon').textContent  = icon;
  document.getElementById('uploadLabel').textContent = label;
  document.getElementById('uploadSub').textContent   = sub;
}

/* ── Options Toggle ─────────────────────────────────────────────────── */
document.querySelectorAll('.opt-row').forEach(row => {
  row.addEventListener('click', () => {
    const key = row.dataset.key;
    state.opts[key] = !state.opts[key];
    row.classList.toggle('active', state.opts[key]);
    document.getElementById('tog-' + key).classList.toggle('on', state.opts[key]);
    const sub = document.getElementById('sub-' + key);
    if (sub) sub.classList.toggle('show', state.opts[key]);
  });
});

/* ── Tabs ───────────────────────────────────────────────────────────── */
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const name = tab.dataset.tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.tab-body').forEach(b => b.style.display = 'none');
    document.getElementById('tab-' + name).style.display = 'block';
  });
});

/* ── Run ────────────────────────────────────────────────────────────── */
const runBtn = document.getElementById('runBtn');
if (runBtn) runBtn.addEventListener('click', runCleaning);

async function runCleaning() {
  if (!state.fileId) {
    alert('Veuillez d\'abord charger un fichier.');
    return;
  }

  runBtn.disabled = true;
  show('progressPanel');
  hide('statsGrid');
  hide('resultTabs');

  const steps = [
    { id: 'upload', label: 'Validation du fichier',             pct: 15 },
    { id: 'dup',    label: 'Suppression des doublons',          pct: 35 },
    { id: 'miss',   label: 'Traitement valeurs manquantes',     pct: 55 },
    { id: 'out',    label: 'Détection et traitement outliers',  pct: 75 },
    { id: 'norm',   label: 'Normalisation des données',         pct: 88 },
    { id: 'score',  label: 'Calcul du score de qualité',        pct: 100 },
  ];

  // Animation progress
  for (const s of steps) {
    setChip(s.id, 'active');
    setProgress(s.label, s.pct);
    await sleep(300);
    setChip(s.id, 'done');
  }

  // Appel API
  try {
    const body = {
      file_id: state.fileId,
      options: {
        duplicates    : state.opts.dup,
        missing       : state.opts.miss,
        missing_method: document.getElementById('missingMethod').value,
        outliers      : state.opts.out,
        outlier_method: document.getElementById('outlierMethod').value,
        normalize     : state.opts.norm,
        norm_method   : document.getElementById('normMethod').value,
      },
    };

    const res  = await fetch('/api/clean', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify(body),
    });
    const data = await res.json();

    if (data.error) {
      alert('Erreur : ' + data.error);
      runBtn.disabled = false;
      return;
    }

    state.historyId = data.history_id;
    showResults(data);

  } catch (err) {
    alert('Erreur réseau : ' + err.message);
  }

  runBtn.disabled = false;
}

/* ── Affichage résultats ─────────────────────────────────────────────── */
function showResults(data) {
  const s = data.stats;

  show('statsGrid');
  show('resultTabs');

  // Valeurs
  set('svRows', s.final_rows);
  set('sdRows', `<span class="${s.duplicates_removed > 0 ? 'bad' : 'good'}">${s.duplicates_removed > 0 ? '−' + s.duplicates_removed + ' doublons' : '✓ Aucun doublon'}</span>`);

  set('svMiss', s.missing_treated);
  set('sdMiss', `<span class="good">✓ Imputées</span>`);

  set('svOut', s.outliers_treated);
  set('sdOut', `<span class="${s.outliers_treated > 0 ? 'bad' : 'good'}">${s.outliers_treated > 0 ? 'Remplacés → médiane' : '✓ Aucun outlier'}</span>`);

  const q     = s.quality_score;
  const qcol  = q >= 80 ? '#10b981' : q >= 60 ? '#f59e0b' : '#ef4444';
  const qCard = document.getElementById('svScore');
  if (qCard) { qCard.textContent = q + '%'; qCard.style.color = qcol; }
  set('sdScore', `<span style="color:${qcol}">${q >= 80 ? '✓ Excellent' : q >= 60 ? '⚠ Acceptable' : '✗ À améliorer'}</span>`);

  // Score header
  const sd = document.getElementById('scoreDisplay');
  if (sd) { sd.textContent = q + '%'; sd.style.color = qcol; }

  // Animate cards
  document.querySelectorAll('.scard').forEach((c, i) => {
    setTimeout(() => c.classList.add('show'), i * 100);
  });

  // Aperçu
  renderPreview(data.preview, s);

  // Export buttons
  renderExportButtons();
  renderCharts(data);
}

function renderAnalyzeOutliers(outliers) {
  const container = document.getElementById('analyzeOutliers');
  if (!container) return;

  if (!outliers || outliers.length === 0) {
    container.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;color:#10b981;padding:12px 0;">
        <span style="font-size:20px;">✅</span>
        <span>Aucun outlier détecté (méthode IQR ± 1.5)</span>
      </div>`;
    return;
  }
  const totalOutliers = outliers.reduce((s, o) => s + o.count, 0);

  const rows = outliers.map(o => {
    const color = o.pct > 10 ? '#ef4444' : o.pct > 5 ? '#f59e0b' : '#10b981';
    return `
      <tr>
        <td><strong>${o.column}</strong></td>
        <td style="color:${color};font-weight:600;">${o.count.toLocaleString()}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="flex:1;height:6px;background:var(--surface2);border-radius:3px;">
              <div style="width:${Math.min(o.pct, 100)}%;height:6px;background:${color};border-radius:3px;"></div>
            </div>
            <span style="color:${color};font-size:12px;min-width:38px;text-align:right;">${o.pct}%</span>
          </div>
        </td>
        <td style="font-size:11px;color:var(--muted);">
          [${o.lower} ; ${o.upper}]
        </td>
        <td style="font-size:11px;color:#ef4444;">
          ${o.min_val} → ${o.max_val}
        </td>
      </tr>`;
  }).join('');

  container.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
      <span style="font-size:13px;color:var(--muted);">
        Méthode : <strong style="color:var(--fg);">IQR × 1.5</strong>
        &nbsp;·&nbsp;
        <strong style="color:#f59e0b;">${outliers.length}</strong> colonne(s) concernée(s)
        &nbsp;·&nbsp;
        <strong style="color:#ef4444;">${totalOutliers.toLocaleString()}</strong> valeur(s) aberrante(s)
      </span>
    </div>
    <div class="table-scroll">
      <table class="htable">
        <thead>
          <tr>
            <th>Colonne</th>
            <th>Nb outliers</th>
            <th>Proportion</th>
            <th>Intervalle IQR</th>
            <th>Valeurs extrêmes</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <p style="font-size:11px;color:var(--muted);margin-top:8px;">
      Intervalle IQR = [Q1 − 1.5×IQR ; Q3 + 1.5×IQR] — valeurs hors de cet intervalle sont considérées comme outliers.
    </p>`;
}

function renderPreview(rows, stats) {
  if (!rows || rows.length === 0) return;
  const al = document.getElementById('previewAlert');
  if (al) al.textContent = `${stats.final_rows} lignes × ${stats.initial_cols} colonnes — 10 premières lignes`;

  const cols = Object.keys(rows[0]);
  let html = '<table><thead><tr>' + cols.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
  rows.forEach(r => {
    html += '<tr>' + cols.map(c => {
      const v = r[c];
      return `<td>${v === null || v === undefined ? '<em style="color:var(--danger)">NULL</em>' : v}</td>`;
    }).join('') + '</tr>';
  });
  html += '</tbody></table>';
  const pt = document.getElementById('previewTable');
  if (pt) pt.innerHTML = html;
}

function renderExportButtons() {
  const row = document.getElementById('exportRow');
  if (!row || !state.historyId) return;
  const fmts = ['csv', 'json', 'xml', 'xlsx', 'pdf'];
  row.innerHTML = fmts.map(f =>
    `<button class="exp-btn" onclick="downloadExport(${state.historyId},'${f}')">${f.toUpperCase()}</button>`
  ).join('');
}

function downloadExport(histId, fmt) {
  window.location.href = `/api/export/${histId}/${fmt}`;
}

/* ── Helpers ────────────────────────────────────────────────────────── */
function show(id) { const el = document.getElementById(id); if (el) el.style.display = 'block'; }
function hide(id) { const el = document.getElementById(id); if (el) el.style.display = 'none'; }
function set(id, html) { const el = document.getElementById(id); if (el) el.innerHTML = html; }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function showAlert(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = msg; el.style.display = 'block'; }
}

function setProgress(label, pct) {
  set('progStep', label);
  set('progPct', pct + '%');
  const fill = document.getElementById('progFill');
  if (fill) fill.style.width = pct + '%';
}

function setChip(id, cls) {
  const chip = document.getElementById('chip-' + id);
  if (!chip) return;
  chip.className = 'chip ' + cls;
}
/* ── Graphiques ─────────────────────────────────────────────────────── */
let chartCleaning = null;
let chartQuality  = null;
let chartRows     = null;
let chartHistory  = null;

function renderCharts(data) {
  const s = data.stats;
  show('chartsSection');

  // Détruire anciens graphiques
  if (chartCleaning) chartCleaning.destroy();
  if (chartQuality)  chartQuality.destroy();
  if (chartRows)     chartRows.destroy();

  // ── 1. Résumé nettoyage (Bar) ────────────────────────────────────
  chartCleaning = new Chart(document.getElementById('chartCleaning'), {
    type: 'bar',
    data: {
      labels: ['Doublons', 'Val. manquantes', 'Outliers'],
      datasets: [{
        label: 'Éléments traités',
        data: [s.duplicates_removed, s.missing_treated, s.outliers_treated],
        backgroundColor: ['#6366f1', '#10b981', '#f59e0b'],
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
        x: { ticks: { color: '#94a3b8' }, grid: { display: false } }
      }
    }
  });

  // ── 2. Score qualité (Doughnut) ──────────────────────────────────
  const q    = s.quality_score;
  const qcol = q >= 80 ? '#10b981' : q >= 60 ? '#f59e0b' : '#ef4444';
  chartQuality = new Chart(document.getElementById('chartQuality'), {
    type: 'doughnut',
    data: {
      labels: ['Score', 'Restant'],
      datasets: [{
        data: [q, 100 - q],
        backgroundColor: [qcol, '#1e293b'],
        borderWidth: 0,
      }]
    },
    options: {
      responsive: true,
      cutout: '75%',
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
      }
    },
    plugins: [{
      id: 'centerText',
      beforeDraw(chart) {
        const { ctx, width, height } = chart;
        ctx.save();
        ctx.font = 'bold 28px DM Sans';
        ctx.fillStyle = qcol;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(q + '%', width / 2, height / 2);
        ctx.restore();
      }
    }]
  });

  // ── 3. Évolution lignes (Bar comparatif) ─────────────────────────
  chartRows = new Chart(document.getElementById('chartRows'), {
    type: 'bar',
    data: {
      labels: ['Avant', 'Après'],
      datasets: [{
        label: 'Lignes',
        data: [s.initial_rows, s.final_rows],
        backgroundColor: ['#6366f1', '#10b981'],
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
        x: { ticks: { color: '#94a3b8' }, grid: { display: false } }
      }
    }
  });

  // ── 4. Historique scores (Line) ──────────────────────────────────
  loadHistoryChart();
}

async function loadHistoryChart() {
  try {
    const res  = await fetch('/api/history');
    const data = await res.json();
    if (!data.length) return;

    const labels = data.reverse().map(h => h.file_name.substring(0, 12));
    const scores = data.map(h => h.quality_score ?? 0);

    if (chartHistory) chartHistory.destroy();
    chartHistory = new Chart(document.getElementById('chartHistory'), {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Score qualité',
          data: scores,
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99,102,241,0.15)',
          borderWidth: 2,
          pointBackgroundColor: '#6366f1',
          fill: true,
          tension: 0.4,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { min: 0, max: 100, ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
          x: { ticks: { color: '#94a3b8', maxRotation: 30 }, grid: { display: false } }
        }
      }
    });
  } catch (e) {
    console.warn('Historique non disponible', e);
  }
}

/* ── Analyse automatique après sélection du fichier ──────────────────────── */
async function analyzeFile(file) {
  const panel    = document.getElementById('analyzePanel');
  const spinner  = document.getElementById('analyzeSpinner');
  const title    = document.getElementById('analyzePanelTitle');
  const runBtn   = document.getElementById('runBtn');

  // Afficher le panel et le spinner
  panel.style.display   = 'block';
  spinner.style.display = 'inline';
  title.textContent     = `Analyse : ${file.name}`;
  runBtn.disabled       = true;

  // Vider les contenus précédents
  ['analyzeCards', 'analyzeColTypes', 'analyzeMissing',
   'analyzeOutliers', 'analyzePreview'].forEach(id => {
    document.getElementById(id).innerHTML = '';
  });

  try {
    const formData = new FormData();
    formData.append('file', file);

    const res  = await fetch('/api/analyze', { method: 'POST', body: formData });
    const data = await res.json();

    if (!data.success) {
      showAnalyzeError(data.error || 'Erreur lors de l\'analyse');
      return;
    }

    renderAnalyzeOverview(data.info);
    renderAnalyzeOutliers(data.outliers);
    renderAnalyzeMissing(data.missing, data.info.rows);
    //renderAnalyzeStats(data.stats);
    renderAnalyzePreview(data.preview, data.info.columns);

    // Activer le bouton de traitement
    runBtn.disabled = false;

  } catch (err) {
    showAnalyzeError('Impossible de contacter le serveur : ' + err.message);
  } finally {
    spinner.style.display = 'none';
  }
}

function showAnalyzeError(msg) {
  document.getElementById('analyzeCards').innerHTML =
    `<div class="alert-info" style="color:#ef4444;">${msg}</div>`;
}


/* ── Tab : Vue d'ensemble ─────────────────────────────────────────────────── */
function renderAnalyzeOverview(info) {
  // Cards résumé
  const cards = [
    { label: 'Lignes',    value: info.rows.toLocaleString(),          icon: '📋' },
    { label: 'Colonnes',  value: info.cols,                           icon: '🗂️' },
    { label: 'Doublons',  value: info.duplicates,
          extra: info.duplicates > 0 ? 'warning' : 'ok', icon: '🔁' },
    { label: 'Outliers',  value: info.total_outlier_cols + ' col.',
          extra: info.total_outlier_cols > 0 ? 'warning' : 'ok', icon: '⚡' },
    { label: 'Extension', value: '.' + info.extension.toUpperCase(),  icon: '📄' },
  ];

  document.getElementById('analyzeCards').innerHTML = `
    <div class="analyze-cards-grid">
      ${cards.map(c => `
        <div class="acard ${c.extra || ''}">
          <span class="acard-icon">${c.icon}</span>
          <div>
            <div class="acard-val">${c.value}</div>
            <div class="acard-lbl">${c.label}</div>
          </div>
        </div>
      `).join('')}
    </div>`;

  // Tableau des types de colonnes
  const rows = info.columns.map(col => `
    <tr>
      <td>${col}</td>
      <td><span class="dtype-badge">${info.col_types[col]}</span></td>
    </tr>`).join('');

  document.getElementById('analyzeColTypes').innerHTML = `
    <div style="font-size:12px;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em;">
      Types des colonnes
    </div>
    <div class="table-scroll">
      <table class="htable">
        <thead><tr><th>Colonne</th><th>Type</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}


/* ── Tab : Valeurs manquantes ─────────────────────────────────────────────── */
function renderAnalyzeMissing(missing, totalRows) {
  const container = document.getElementById('analyzeMissing');

  if (!missing || missing.length === 0) {
    container.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;color:#10b981;padding:12px 0;">
        <span style="font-size:20px;">✅</span>
        <span>Aucune valeur manquante détectée</span>
      </div>`;
    return;
  }

  const rows = missing.map(m => {
    const pct  = m.pct;
    const color = pct > 30 ? '#ef4444' : pct > 10 ? '#f59e0b' : '#10b981';
    return `
      <tr>
        <td>${m.column}</td>
        <td>${m.missing.toLocaleString()}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="flex:1;height:6px;background:var(--surface2);border-radius:3px;">
              <div style="width:${Math.min(pct,100)}%;height:6px;background:${color};border-radius:3px;"></div>
            </div>
            <span style="color:${color};font-size:12px;min-width:38px;text-align:right;">${pct}%</span>
          </div>
        </td>
      </tr>`;
  }).join('');

  container.innerHTML = `
    <table class="htable">
      <thead><tr><th>Colonne</th><th>Manquantes</th><th>Proportion</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}


/* ── Tab : Statistiques descriptives ─────────────────────────────────────── */
function renderAnalyzeStats(stats) {
  const container = document.getElementById('analyzeStats');
  const cols      = Object.keys(stats);

  if (cols.length === 0) {
    container.innerHTML = `<p style="color:var(--muted);padding:12px 0;">
      Aucune colonne numérique détectée.</p>`;
    return;
  }

  const statKeys  = ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'];
  const statLabel = { count:'Count', mean:'Moyenne', std:'Écart-type',
                      min:'Min', '25%':'25%', '50%':'Médiane', '75%':'75%', max:'Max' };

  const fmt = v => (v === null || v === undefined) ? '—'
    : Number.isInteger(v) ? v.toLocaleString()
    : parseFloat(v.toFixed(4)).toLocaleString();

  const headerCols = cols.map(c => `<th>${c}</th>`).join('');
  const bodyRows   = statKeys.map(sk => `
    <tr>
      <td style="color:var(--muted);font-size:11px;">${statLabel[sk]}</td>
      ${cols.map(c => `<td>${fmt(stats[c]?.[sk])}</td>`).join('')}
    </tr>`).join('');

  container.innerHTML = `
    <table class="htable">
      <thead><tr><th></th>${headerCols}</tr></thead>
      <tbody>${bodyRows}</tbody>
    </table>`;
}


/* ── Tab : Aperçu des données ────────────────────────────────────────────── */
function renderAnalyzePreview(rows, columns) {
  const container = document.getElementById('analyzePreview');
  if (!rows || rows.length === 0) {
    container.innerHTML = '<p style="color:var(--muted);">Aucune donnée à afficher.</p>';
    return;
  }

  const headers = columns.map(c => `<th>${c}</th>`).join('');
  const bodyRows = rows.map(row => `
    <tr>${columns.map(c => {
      const val = row[c];
      const empty = val === null || val === undefined || val === '';
      return `<td style="${empty ? 'color:#ef4444;' : ''}">${empty ? '∅' : val}</td>`;
    }).join('')}</tr>`).join('');

  container.innerHTML = `
    <table class="htable">
      <thead><tr>${headers}</tr></thead>
      <tbody>${bodyRows}</tbody>
    </table>
    <p style="font-size:11px;color:var(--muted);margin-top:8px;">
      Affichage des 5 premières lignes — ∅ = valeur manquante
    </p>`;
}


/* ── Gestion des tabs de l'analyse ──────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('analyzeTabs')?.addEventListener('click', e => {
    const tab = e.target.closest('[data-atab]');
    if (!tab) return;

    const key = tab.dataset.atab;

    // Activer l'onglet cliqué
    document.querySelectorAll('#analyzeTabs .tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    // Afficher le bon contenu
    document.querySelectorAll('.atab-body').forEach(b => b.style.display = 'none');
    const body = document.getElementById('atab-' + key);
    if (body) body.style.display = 'block';
  });
});

