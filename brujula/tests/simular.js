// Pruebas de puntaje con perfiles simulados. Uso: servir brujula/ en :8799 y correr `node brujula/tests/simular.js`.
// Cada perfil fija posiciones objetivo (0-100) en algunos ejes; la respuesta a cada frase sale de esas posiciones
// con la misma regla de intensidad que usa la certeza (nivel 1-4).
const { chromium } = require('playwright');
const URL = process.env.URL || 'http://localhost:8799/quiz/?test';
const PERFILES = {
  izquierda: { pla: 10, col: 8, dis: 8, bie: 10, lab: 12, mon: 30, ind: 20, glo: 30, pro: 20, rel: 15, mig: 75, lib: 70, dem: 25, int: 35, uni: 20, pen: 25, inf: 30, ecl: 30, tec: 55 },
  libertario: { pla: 95, col: 95, dis: 95, bie: 95, lab: 90, mon: 95, ind: 90, glo: 95, lib: 92, dem: 25, inf: 5, int: 50, mil: 60, ipe: 70, pen: 45, ecl: 80, rel: 35, pro: 50 },
  conservador: { rel: 88, pro: 90, mig: 20, lib: 30, pen: 85, int: 70, idc: 85, eti: 85, epi: 75, uni: 75, pla: 65, col: 72, mil: 30, dem: 55 },
  nacionalista_autoritario: { dem: 92, int: 92, mil: 12, lib: 10, inf: 90, ipe: 10, uni: 92, pen: 95, mig: 8, glo: 20, ind: 15, pro: 85, fed: 80 },
  ecologista: { tec: 88, ecl: 8, fut: 10, tem: 88, glo: 35, pla: 30, col: 35, int: 25, mil: 85, lib: 75, ges: 75, dem: 20, pro: 20 },
  centro: { pla: 55, col: 55, lib: 55, pro: 50, dem: 30, ipe: 80, tra: 10, int: 45 },
};
const ESP = {
  izquierda: /socialis|comunis|marx|anarq|anarco|izquierda|ecosocial|consej|eurocom|mao|trotsk|laboris|libertario de izq|teolog/i,
  libertario: /libertari|anarcocap|objetiv|minarq|agoris|liberalismo cl|paleolib|neoliberal/i,
  conservador: /conserv|cristian|integris|distribut|monarq|teocr|tradicion|reaccion|comunitar/i,
  nacionalista_autoritario: /nacional|fascis|populismo de derecha|tercera pos|reaccion|etnona|bonapart|juche|corporat|soberan|capitalismo autorit/i,
  ecologista: /ecolog|ecosoc|decrec|verde|primitiv|ecología profunda|confederal/i,
  centro: /centr|tercera vía|liberalismo social|socialdem|republican|radical|ordolib|cristian|igualitario|liberalismo progres/i,
};
function respuesta(q, t) {
  let num = 0, den = 0;
  for (const [k, w] of Object.entries(q.e)) {
    if (t[k] == null || !w) continue;
    const L = q.nivel || (Math.abs(w) >= 2 ? 3 : 1);
    num += Math.abs(w) * (Math.sign(w) * (t[k] - 50) - (L - 1) * 12.5); den += Math.abs(w);
  }
  if (!den) return 0;
  const z = num / den;
  return z > 25 ? 2 : z > 5 ? 1 : z < -25 ? -2 : z < -5 ? -1 : 0;
}
(async () => {
  const b = await chromium.launch(), errs = [], out = [];
  const p = await (await b.newContext({ viewport: { width: 1280, height: 900 }, locale: 'es-AR' })).newPage();
  p.on('pageerror', e => errs.push(e.message));
  await p.goto(URL); await p.waitForFunction(() => window.__brujula && window.__brujula.S.preg);
  const corre = async (ver, modo, fn, fnArg) => p.evaluate(async ([ver, modo, fnSrc, arg]) => {
    const B = window.__brujula, S = B.S, f = new Function('q', 'arg', fnSrc);
    S.ver = ver; S.modo = modo; S.qs = B.seleccion(ver, modo); S.ans = S.qs.map(q => f(q, arg)); S.t0 = Date.now();
    B.demograficas(); await new Promise(r => setTimeout(r, 50));
    const rk = S.rk;
    return { n: S.qs.length, sc: S.scores, cert: S.cert, sc2: S.scores2, cert2: S.cert2, nresp: S.nresp,
      ideo: rk.ideo.slice(0, 5).map(x => [x.i.es.nombre, x.af]), lejos: rk.ideo.slice(-2).map(x => x.i.es.nombre),
      figs: rk.figs.slice(0, 3).map(x => [x.f.nombre, x.af]),
      lema: document.querySelector('#bandera .lema-b')?.textContent, valoras: [...document.querySelectorAll('#valoras .vchip b')].map(x => x.textContent),
      temas: [...document.querySelectorAll('#temas .vt b')].map(x => x.textContent), sobre: document.querySelector('#sob')?.innerText.slice(0, 80) };
  }, [ver, modo, fn, fnArg]);
  const SRC_RESP = `const t = arg; ${respuesta.toString()}; return respuesta(q, t);`;
  for (const modo of ['rapida', 'completa', 'exhaustiva']) {
    for (const [nom, t] of Object.entries(PERFILES)) {
      const r = await corre('ar', modo, SRC_RESP, t);
      const errores = Object.entries(t).map(([k, v]) => {
        const s = r.sc[k] != null ? r.sc[k] : r.sc2 && r.sc2[k];
        return s == null || (r.nresp && !r.nresp[k]) ? null : { k, obj: v, s, ok: Math.sign(v - 50) === 0 || Math.sign(s - 50) === Math.sign(v - 50) || Math.abs(s - 50) < 5 };
      }).filter(Boolean);
      const mal = errores.filter(x => !x.ok), ideoOk = r.ideo.slice(0, 3).some(([n]) => ESP[nom].test(n));
      out.push({ modo, perfil: nom, n: r.n, ejes_mal_lado: mal.map(x => `${x.k} obj ${x.obj} dio ${x.s}`), ideo_ok: ideoOk, ideo: r.ideo.slice(0, 3), figs: r.figs, cer: r.sc2.cer, lema: r.lema });
    }
    // sesgo de aquiescencia: todo "muy de acuerdo" y todo "muy en desacuerdo"
    for (const [nom, v] of [['todo_de_acuerdo', 2], ['todo_en_desacuerdo', -2], ['todo_neutral', 0]]) {
      const r = await corre('ar', modo, `return ${v}`);
      const des = [...Object.entries(r.sc), ...Object.entries(r.sc2).filter(([k]) => k !== 'cer' && r.nresp[k])].filter(([, s]) => Math.abs(s - 50) >= 20).map(([k, s]) => `${k}=${s}`);
      out.push({ modo, perfil: nom, n: r.n, ejes_corridos: des, ideo: r.ideo.slice(0, 2), figs: r.figs.slice(0, 1), cer: r.sc2.cer, lema: r.lema });
    }
    // al azar (semilla fija)
    const r = await corre('ar', modo, `let s = (q.id.split('').reduce((a, c) => a * 31 + c.charCodeAt(0), 7)) % 997; return [2, 1, 0, -1, -2][s % 5]`);
    out.push({ modo, perfil: 'al_azar', n: r.n, cer: r.sc2.cer, cert_media: Math.round(Object.values(r.cert).reduce((a, b) => a + b, 0) / 12), ideo: r.ideo.slice(0, 2), figs: r.figs.slice(0, 1) });
  }
  console.log(JSON.stringify(out, null, 1));
  console.log('ERRORES', errs);
  await b.close();
})();
