/**
 * Brújula política: recepción de respuestas (Google Apps Script, gratis).
 *
 * Guarda cada respuesta anónima en una planilla PRIVADA de Google Sheets y deja que GitHub Actions
 * la lea con un token secreto para calcular agregados. Las respuestas individuales nunca llegan al repo.
 *
 * Instalación (una sola vez, ver brujula/README.md):
 *   1. Crear una planilla en Google Drive (privada) y abrir Extensiones → Apps Script.
 *   2. Pegar este archivo. En Configuración del proyecto → Propiedades del script, crear:
 *        TOKEN = una clave larga al azar (la misma que el secret QUIZ_TOKEN de GitHub).
 *   3. Implementar → Nueva implementación → Aplicación web: ejecutar como "Yo", acceso "Cualquier usuario".
 *   4. Copiar la URL /exec al secret QUIZ_ENDPOINT de GitHub.
 *
 * No se guarda IP (Apps Script no la expone), ni nombre, mail o teléfono.
 */
const HOJA = 'respuestas';
const COLS = ['recibido', 'schema', 'version', 'ids', 'ans', 'scores', 'top', 'dur_s', 'cid_hash',
  'edad', 'genero', 'pais_res', 'prov', 'pais_nac', 'red', 'mobile', 'lang', 'cert', 'autodef'];
const EDADES = ['16-17', '18-24', '25-34', '35-44', '45-54', '55-64', '65+'];
const MAX_BYTES = 6000;

function hoja_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(HOJA);
  if (!sh) { sh = ss.insertSheet(HOJA); sh.appendRow(COLS); sh.setFrozenRows(1) }
  // planillas creadas con una versión anterior: completar los encabezados que falten
  if (sh.getLastColumn() < COLS.length) sh.getRange(1, 1, 1, COLS.length).setValues([COLS]);
  return sh;
}

function corto_(s, n) { return String(s == null ? '' : s).slice(0, n) }

function sha_(s) {
  const b = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, 'brujula:' + s);
  return b.slice(0, 12).map(x => ((x + 256) % 256).toString(16).padStart(2, '0')).join('');
}

function doPost(e) {
  try {
    const raw = e && e.postData && e.postData.contents || '';
    if (raw.length > MAX_BYTES) return out_({ ok: false, error: 'grande' });
    const p = JSON.parse(raw);
    const d = p.demo || {};
    // Validación mínima: consentimiento, formato de respuestas y edad permitida (16+)
    if (p.consent !== true) return out_({ ok: false, error: 'consentimiento' });
    if (!/^[a-z]{2,8}$/.test(p.version || '')) return out_({ ok: false, error: 'version' });
    if (!/^[a-z0-9,]{1,800}$/.test(p.ids || '') || !/^[-0-2,]{1,400}$/.test(p.ans || '')) return out_({ ok: false, error: 'respuestas' });
    if (EDADES.indexOf(d.edad) < 0) return out_({ ok: false, error: 'edad' });
    const lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      hoja_().appendRow([
        new Date().toISOString().slice(0, 13) + ':00Z', // hora redondeada: no hace falta más precisión
        Number(p.schema) || 1, p.version, p.ids, p.ans, corto_(JSON.stringify(p.scores || {}), 300),
        corto_((p.top || []).join('|'), 200), Math.min(Number(p.dur_s) || 0, 86400),
        p.cid ? sha_(corto_(p.cid, 80)) : '',
        d.edad, corto_(d.genero, 30), corto_(d.pais_res, 40), corto_(d.prov, 40), corto_(d.pais_nac, 40), corto_(d.red, 40),
        p.ua_mobile ? 1 : 0,
        /^(es|pt|en)$/.test(p.lang || '') ? p.lang : '', corto_(JSON.stringify(p.cert || {}), 300),
        corto_(d.autodef, 40)
      ]);
    } finally { lock.releaseLock() }
    return out_({ ok: true });
  } catch (err) {
    return out_({ ok: false, error: 'formato' });
  }
}

/** Lectura para GitHub Actions: GET ?token=...  → JSON con todas las filas. Sin token correcto, nada. */
function doGet(e) {
  const tok = PropertiesService.getScriptProperties().getProperty('TOKEN');
  if (!tok || !e || !e.parameter || e.parameter.token !== tok) return out_({ ok: false });
  const v = hoja_().getDataRange().getValues();
  const head = v.shift();
  return out_({ ok: true, cols: head, rows: v });
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
