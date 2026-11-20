"""Datos reales para la landing: tablero por país y sala de situación.

Escribe web/data/paises.json y web/data/situacion.json. Solo fuentes gratuitas y sin clave:
  - Banco Mundial (indicadores macro, último dato disponible por país)
  - currency-api de fawazahmed0 (tipo de cambio diario, vía jsDelivr / Cloudflare)
  - Google News RSS (titulares y alertas por país)
  - GDELT DOC 2.0 (tono de la cobertura internacional, 7 días)
  - USGS (sismos M4.5+) y GDACS (alertas de desastres)
Nada de esto toca tableros de clientes. Uso: python3 web/tools/datos.py
"""
import json, re, sys, time, urllib.parse, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data'
UA = 'Mozilla/5.0 (compatible; SudakaosLanding/1.0; datos públicos agregados)'
NOW = datetime.now(timezone.utc)

# code, nombre, ISO3 Banco Mundial, moneda, lat, lon, idioma de noticias (hl, gl, ceid), término de búsqueda, GDELT
PAISES = [
    ('AR', 'Argentina', 'ARG', 'ars', -34.6, -58.4, ('es-419', 'AR', 'AR:es-419'), 'Argentina', 'Argentina'),
    ('BO', 'Bolivia', 'BOL', 'bob', -16.5, -68.1, ('es-419', 'BO', 'BO:es-419'), 'Bolivia', 'Bolivia'),
    ('BR', 'Brasil', 'BRA', 'brl', -15.8, -47.9, ('pt-BR', 'BR', 'BR:pt-419'), 'Brasil', 'Brazil'),
    ('CL', 'Chile', 'CHL', 'clp', -33.4, -70.7, ('es-419', 'CL', 'CL:es-419'), 'Chile', 'Chile'),
    ('CO', 'Colombia', 'COL', 'cop', 4.7, -74.1, ('es-419', 'CO', 'CO:es-419'), 'Colombia', 'Colombia'),
    ('EC', 'Ecuador', 'ECU', 'usd', -0.2, -78.5, ('es-419', 'EC', 'EC:es-419'), 'Ecuador', 'Ecuador'),
    ('GY', 'Guyana', 'GUY', 'gyd', 6.8, -58.2, ('en-US', 'US', 'US:en'), 'Guyana', 'Guyana'),
    ('PY', 'Paraguay', 'PRY', 'pyg', -25.3, -57.6, ('es-419', 'PY', 'PY:es-419'), 'Paraguay', 'Paraguay'),
    ('PE', 'Perú', 'PER', 'pen', -12.0, -77.0, ('es-419', 'PE', 'PE:es-419'), 'Perú', 'Peru'),
    ('SR', 'Surinam', 'SUR', 'srd', 5.9, -55.2, ('en-US', 'US', 'US:en'), 'Suriname', 'Suriname'),
    ('UY', 'Uruguay', 'URY', 'uyu', -34.9, -56.2, ('es-419', 'UY', 'UY:es-419'), 'Uruguay', 'Uruguay'),
    ('VE', 'Venezuela', 'VEN', 'ves', 10.5, -66.9, ('es-419', 'VE', 'VE:es-419'), 'Venezuela', 'Venezuela'),
    ('MX', 'México', 'MEX', 'mxn', 19.4, -99.1, ('es-419', 'MX', 'MX:es-419'), 'México', 'Mexico'),
    ('US', 'Estados Unidos', 'USA', 'usd', 38.9, -77.0, ('en-US', 'US', 'US:en'), '"United States" OR Washington', '"United States"'),
    ('ES', 'España', 'ESP', 'eur', 40.4, -3.7, ('es', 'ES', 'ES:es'), 'España', 'Spain'),
    ('GB', 'Reino Unido', 'GBR', 'gbp', 51.5, -0.1, ('en-GB', 'GB', 'GB:en'), '"United Kingdom" OR Britain OR UK', '"United Kingdom"'),
    ('EU', 'Unión Europea', 'EUU', 'eur', 50.8, 4.4, ('en-GB', 'GB', 'GB:en'), '"European Union" OR "European Commission" OR Brussels', '"European Union"'),
]
BY = {p[0]: p for p in PAISES}

INDICADORES = {
    'pib_crec': 'NY.GDP.MKTP.KD.ZG',   # crecimiento real del PIB, % anual
    'inflacion': 'FP.CPI.TOTL.ZG',     # inflación, precios al consumidor, % anual
    'desempleo': 'SL.UEM.TOTL.ZS',     # desempleo, % de la población activa (OIT)
    'pib_pc': 'NY.GDP.PCAP.CD',        # PIB per cápita, US$ corrientes
    'pib': 'NY.GDP.MKTP.CD',           # PIB, US$ corrientes
    'poblacion': 'SP.POP.TOTL',
    'internet': 'IT.NET.USER.ZS',      # usuarios de internet, % de la población
    'gini': 'SI.POV.GINI',
}

# Palabras que convierten un titular en alerta: (categoría, severidad 1-3, términos por idioma)
REGLAS = [
    ('Seguridad', 3, {'es': ['atentado', 'ataque', 'tiroteo', 'masacre', 'asesinad', 'muertos', 'secuestr', 'narco', 'enfrentamiento', 'explosión', 'bomba'],
                      'pt': ['atentado', 'ataque', 'tiroteio', 'chacina', 'assassinad', 'mortos', 'sequestr', 'facção', 'explosão'],
                      'en': ['attack', 'shooting', 'killed', 'dead', 'kidnap', 'cartel', 'bomb', 'explosion', 'terror']}),
    ('Desastre', 3, {'es': ['terremoto', 'sismo', 'inundaci', 'incendio', 'huracán', 'tormenta', 'alerta roja', 'evacua', 'emergencia', 'derrumbe', 'sequía'],
                     'pt': ['terremoto', 'enchente', 'inundaç', 'incêndio', 'queimada', 'furacão', 'tempestade', 'evacua', 'emergência', 'deslizamento', 'seca'],
                     'en': ['earthquake', 'flood', 'wildfire', 'fire', 'hurricane', 'storm', 'evacuat', 'emergency', 'landslide', 'drought']}),
    ('Protesta', 2, {'es': ['protesta', 'paro', 'huelga', 'marcha', 'manifestaci', 'piquete', 'bloqueo', 'cacerolazo', 'represión', 'disturbios'],
                     'pt': ['protesto', 'greve', 'paralisação', 'manifestaç', 'bloqueio', 'repressão'],
                     'en': ['protest', 'strike', 'walkout', 'rally', 'riot', 'unrest', 'blockade']}),
    ('Institucional', 2, {'es': ['renuncia', 'destitu', 'juicio político', 'imputad', 'detenido', 'allanamiento', 'escándalo', 'corrupción', 'fiscal', 'decreto', 'veto', 'congreso', 'senado', 'corte suprema'],
                          'pt': ['renúncia', 'impeachment', 'indiciad', 'preso', 'operação', 'escândalo', 'corrupção', 'stf', 'congresso', 'senado', 'decreto', 'veto'],
                          'en': ['resign', 'impeach', 'indict', 'arrest', 'scandal', 'corruption', 'supreme court', 'congress', 'parliament', 'veto', 'sanction']}),
    ('Economía', 1, {'es': ['inflación', 'dólar', 'devaluaci', 'riesgo país', 'default', 'deuda', 'fmi', 'recesión', 'tarifa', 'aranceles', 'reservas'],
                     'pt': ['inflação', 'dólar', 'desvaloriz', 'juros', 'selic', 'dívida', 'fmi', 'recessão', 'tarifa'],
                     'en': ['inflation', 'tariff', 'recession', 'interest rate', 'debt', 'default', 'imf', 'central bank', 'markets']}),
    ('Elecciones', 1, {'es': ['elecci', 'encuesta', 'candidat', 'votaci', 'balotaje', 'campaña', 'comicios', 'referéndum'],
                       'pt': ['eleiç', 'pesquisa', 'candidat', 'votação', 'campanha', 'segundo turno'],
                       'en': ['election', 'poll', 'candidate', 'vote', 'campaign', 'referendum', 'ballot']}),
]


def get(url, retries=2, timeout=30):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(12 * (attempt + 1)); continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries:
                time.sleep(4); continue
            raise


def get_json(url, **kw):
    return json.loads(get(url, **kw).decode('utf8', 'replace'))


def iso(dt):
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:5.0f}s]', *a, file=sys.stderr, flush=True)


# ---------- Banco Mundial ----------
def banco_mundial():
    codes = ';'.join(p[2] for p in PAISES)
    out = {p[0]: {} for p in PAISES}
    iso3 = {p[2]: p[0] for p in PAISES}
    for key, ind in INDICADORES.items():
        url = f'https://api.worldbank.org/v2/country/{codes}/indicator/{ind}?format=json&date=2000:{NOW.year}&per_page=5000'
        try:
            d = get_json(url, timeout=45, retries=1)
            rows = d[1] if len(d) > 1 and d[1] else []
        except Exception as e:
            log('WB', ind, e); continue
        for r in rows:
            c = iso3.get(r.get('countryiso3code'))
            if not c or r.get('value') is None:
                continue
            out[c].setdefault(key, []).append([int(r['date']), round(float(r['value']), 3)])
        time.sleep(1)
    for c in out:
        for k in out[c]:
            out[c][k].sort()
    return out


# ---------- Tipo de cambio (unidades de moneda local por 1 US$; para US, euros por dólar) ----------
def fx_dia(fecha):
    tag = 'latest' if fecha is None else fecha.strftime('%Y-%m-%d')
    for url in (f'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{tag}/v1/currencies/usd.min.json',
                f'https://{tag}.currency-api.pages.dev/v1/currencies/usd.min.json'):
        try:
            d = get_json(url, retries=0, timeout=15)
            return d.get('date'), d.get('usd', {})
        except Exception:
            continue
    return None, {}


def tipo_cambio(prev):
    hist = {}
    for c, p in BY.items():
        hist[c] = {r[0]: r[1] for r in (prev.get('paises', {}).get(c, {}).get('fx', {}).get('serie') or [])}
    monedas = {c: ('eur' if c == 'US' else p[3]) for c, p in BY.items()}
    fechas = [None]
    if not any(len(h) > 20 for h in hist.values()):  # primera vez: completa ~6 meses, un punto por semana
        fechas += [NOW - timedelta(days=7 * k) for k in range(1, 27)]
    else:  # completa días faltantes de la última semana
        fechas += [NOW - timedelta(days=k) for k in range(1, 8)]
    fallas = 0
    for f in fechas:
        fecha, rates = fx_dia(f)
        if not fecha or not rates:
            fallas += 1
            if fallas >= 4:
                log('FX: demasiadas fallas, se corta'); break
            continue
        for c, m in monedas.items():
            if m in rates:
                hist[c][fecha] = round(float(rates[m]), 6)
        time.sleep(.3)
    out = {}
    corte = (NOW - timedelta(days=200)).strftime('%Y-%m-%d')
    for c, h in hist.items():
        serie = sorted([k, v] for k, v in h.items() if k >= corte)
        out[c] = {'moneda': monedas[c].upper(), 'serie': serie}
    return out


# ---------- Google News ----------
def lang_of(hl):
    return 'pt' if hl.startswith('pt') else ('en' if hl.startswith('en') else 'es')


def gnews(q, loc, when='1d'):
    hl, gl, ceid = loc
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': f'{q} when:{when}', 'hl': hl, 'gl': gl, 'ceid': ceid})
    root = ET.fromstring(get(url))
    items = []
    for it in root.iter('item'):
        title = (it.findtext('title') or '').strip()
        src = it.find('source')
        outlet = (src.text or '').strip() if src is not None else ''
        if outlet and title.endswith(' - ' + outlet):
            title = title[:-len(outlet) - 3]
        try:
            dt = parsedate_to_datetime(it.findtext('pubDate', ''))
        except (TypeError, ValueError):
            continue
        items.append({'t': iso(dt), 'titulo': title, 'fuente': outlet, 'url': it.findtext('link', '')})
    items.sort(key=lambda x: x['t'], reverse=True)
    return items


def clasificar(titulo, lang):
    low = titulo.lower()
    for cat, sev, terms in REGLAS:
        for w in terms[lang]:
            if re.search(r'(?<![a-záéíóúâêôãõç])' + re.escape(w), low):
                return cat, sev
    return None, 0


def norm(s):
    return re.sub(r'[^a-z0-9áéíóúñâêôãõç ]', '', s.lower())[:70]


def noticias():
    titulares, alertas = {}, []
    for c, nombre, _, _, lat, lon, loc, q, _ in PAISES:
        lang = lang_of(loc[0])
        log('GNews', c)
        try:
            items = gnews(q, loc, '1d')
            if len(items) < 8:
                items = gnews(q, loc, '3d')
        except Exception as e:
            log('GNews', c, e); items = []
        vistos, top = set(), []
        for it in items:
            k = norm(it['titulo'])
            if k in vistos:
                continue
            vistos.add(k)
            cat, sev = clasificar(it['titulo'], lang)
            it2 = dict(it, cat=cat, sev=sev)
            top.append(it2)
            if cat and it['t'] >= iso(NOW - timedelta(hours=48)):
                alertas.append(dict(it2, pais=c, lat=lat, lon=lon, tipo='medios'))
        titulares[c] = {'items': top[:12], 'n24': sum(1 for x in items if x['t'] >= iso(NOW - timedelta(hours=24)))}
        time.sleep(1.2)
    return titulares, alertas


# ---------- GDELT: tono de la cobertura (7 días) ----------
def gdelt_tono():
    out = {}
    fallas = 0
    for c, *_, gq in PAISES:
        if fallas >= 3 or time.time() - T0 > 900:
            log('GDELT: se corta (fallas o tiempo)'); break
        q = {'query': gq, 'mode': 'timelinetone', 'format': 'json', 'timespan': '7d'}
        try:
            d = get_json('https://api.gdeltproject.org/api/v2/doc/doc?' + urllib.parse.urlencode(q), retries=0, timeout=25)
            data = (d.get('timeline') or [{}])[0].get('data') or []
            serie = [[x['date'][:8] + 'T' + x['date'][9:13], round(float(x['value']), 2)] for x in data]
            # promedio diario
            dias = {}
            for t, v in serie:
                dias.setdefault(t[:8], []).append(v)
            out[c] = [[k, round(sum(v) / len(v), 2)] for k, v in sorted(dias.items())]
            fallas = 0
        except Exception as e:
            fallas += 1
            log('GDELT', c, e)
        time.sleep(8)
    return out


# ---------- Sismos y desastres ----------
NOMBRES_GEO = {
    'argentina': 'AR', 'bolivia': 'BO', 'brazil': 'BR', 'chile': 'CL', 'colombia': 'CO', 'ecuador': 'EC', 'guyana': 'GY',
    'paraguay': 'PY', 'peru': 'PE', 'suriname': 'SR', 'uruguay': 'UY', 'venezuela': 'VE', 'mexico': 'MX', 'méxico': 'MX',
    'united states': 'US', 'alaska': 'US', 'california': 'US', 'hawaii': 'US', 'nevada': 'US', 'oregon': 'US', 'washington': 'US',
    'puerto rico': 'US', 'texas': 'US', 'oklahoma': 'US', 'utah': 'US', 'idaho': 'US', 'montana': 'US', 'wyoming': 'US',
    ', ca': 'US', ', ak': 'US', ', nv': 'US', ', hi': 'US', ', tx': 'US', ', ok': 'US',
    'spain': 'ES', 'canary islands': 'ES', 'united kingdom': 'GB', 'england': 'GB', 'scotland': 'GB', 'wales': 'GB',
    'italy': 'EU', 'greece': 'EU', 'france': 'EU', 'portugal': 'EU', 'azores': 'EU', 'germany': 'EU', 'croatia': 'EU',
    'romania': 'EU', 'bulgaria': 'EU', 'cyprus': 'EU', 'slovenia': 'EU', 'austria': 'EU', 'poland': 'EU', 'netherlands': 'EU',
    'belgium': 'EU', 'ireland': 'EU', 'sweden': 'EU', 'finland': 'EU', 'denmark': 'EU', 'czech': 'EU', 'hungary': 'EU',
    'slovakia': 'EU', 'malta': 'EU', 'estonia': 'EU', 'latvia': 'EU', 'lithuania': 'EU', 'luxembourg': 'EU',
}


def pais_de(texto):
    low = (texto or '').lower()
    for k, c in NOMBRES_GEO.items():
        if k in low:
            return c
    return None


def sismos():
    out = []
    try:
        d = get_json('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson')
    except Exception as e:
        log('USGS', e); return out
    for f in d.get('features', []):
        p = f['properties']; lon, lat = f['geometry']['coordinates'][:2]
        c = pais_de(p.get('place'))
        if not c:
            continue
        m = p.get('mag') or 0
        out.append({'t': iso(datetime.fromtimestamp(p['time'] / 1000, timezone.utc)), 'pais': c, 'lat': round(lat, 2), 'lon': round(lon, 2),
                    'cat': 'Sismo', 'sev': 3 if m >= 6 else (2 if m >= 5.2 else 1), 'tipo': 'sismo',
                    'titulo': f'Sismo M{m:.1f}: {p.get("place", "")}', 'fuente': 'USGS', 'url': p.get('url', '')})
    return out


def gdacs():
    out = []
    try:
        root = ET.fromstring(get('https://www.gdacs.org/xml/rss.xml'))
    except Exception as e:
        log('GDACS', e); return out
    ns = {'geo': 'http://www.w3.org/2003/01/geo/wgs84_pos#', 'gdacs': 'http://www.gdacs.org'}
    for it in root.iter('item'):
        title = it.findtext('title', '')
        country = it.findtext('gdacs:country', '', ns)
        c = pais_de(country) or pais_de(title)
        if not c:
            continue
        try:
            dt = parsedate_to_datetime(it.findtext('pubDate', ''))
        except (TypeError, ValueError):
            continue
        if dt < NOW - timedelta(days=7):
            continue
        lvl = (it.findtext('gdacs:alertlevel', '', ns) or '').lower()
        try:
            lat = float(it.findtext('geo:Point/geo:lat', '', ns)); lon = float(it.findtext('geo:Point/geo:long', '', ns))
        except ValueError:
            lat, lon = BY[c][4], BY[c][5]
        out.append({'t': iso(dt), 'pais': c, 'lat': round(lat, 2), 'lon': round(lon, 2), 'cat': 'Desastre',
                    'sev': {'red': 3, 'orange': 2}.get(lvl, 1), 'tipo': 'gdacs', 'titulo': title, 'fuente': 'GDACS', 'url': it.findtext('link', '')})
    return out


def main():
    OUT.mkdir(exist_ok=True)
    prev = {}
    try:
        prev = json.loads((OUT / 'paises.json').read_text(encoding='utf8'))
    except Exception:
        pass
    log('Banco Mundial…'); wb = banco_mundial()
    log('Tipo de cambio…'); fx = tipo_cambio(prev)
    log('Noticias…'); tit, al_medios = noticias()
    log('GDELT…'); tono = gdelt_tono()
    if not tono:  # si GDELT no respondió, se conserva lo último
        tono = {c: v.get('tono') for c, v in prev.get('paises', {}).items() if v.get('tono')}
    log('Sismos y desastres…'); al_geo = sismos() + gdacs()

    alertas = sorted(al_medios + al_geo, key=lambda a: a['t'], reverse=True)
    corte24 = iso(NOW - timedelta(hours=24))
    nivel = {}
    for c in BY:
        a24 = [a for a in alertas if a['pais'] == c and a['t'] >= corte24]
        nivel[c] = {'n24': len(a24), 'peso': sum(a['sev'] for a in a24)}
    mx = max([v['peso'] for v in nivel.values()] + [1])
    for v in nivel.values():
        v['indice'] = round(v['peso'] / mx, 3)

    paises = {}
    for c, nombre, iso3, *_ in PAISES:
        p = BY[c]
        paises[c] = {'nombre': nombre, 'iso3': iso3, 'lat': p[4], 'lon': p[5], 'wb': wb.get(c, {}), 'fx': fx.get(c, {}),
                     'tono': tono.get(c) or [], 'titulares': tit.get(c, {}).get('items', []), 'notas24': tit.get(c, {}).get('n24', 0),
                     'alertas': nivel[c]}
    meta = {'actualizado': iso(NOW), 'fuentes': ['Banco Mundial', 'currency-api (fawazahmed0)', 'Google News', 'GDELT', 'USGS', 'GDACS']}
    (OUT / 'paises.json').write_text(json.dumps({'meta': meta, 'paises': paises}, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    sit = {'meta': meta, 'nivel': nivel, 'alertas': alertas[:160]}
    (OUT / 'situacion.json').write_text(json.dumps(sit, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    log('ok', len(alertas), 'alertas;', sum(len(v['titulares']) for v in paises.values()), 'titulares')


if __name__ == '__main__':
    main()
