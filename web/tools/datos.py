"""Datos reales para la landing: tablero por país y sala de situación.

Escribe web/data/paises.json y web/data/situacion.json. Solo fuentes gratuitas y sin clave:
  - OCDE (inflación interanual mensual) y Banco Mundial (último año, donde la OCDE no llega)
  - Yahoo Finance (índice bursátil principal, cierre diario del último mes)
  - currency-api de fawazahmed0 (tipo de cambio diario, vía jsDelivr / Cloudflare)
  - Google News RSS (titulares y alertas por país)
  - GDELT DOC 2.0 (tono de la cobertura internacional, 7 días)
  - USGS (sismos M4.5+) y GDACS (alertas de desastres)
Regla: el dato más fresco disponible, siempre con su fecha. Nada de esto toca tableros de clientes. Uso: python3 web/tools/datos.py
"""
import json, re, sys, time, urllib.parse, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
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


# Palabras que convierten un titular en alerta: (categoría, severidad 1-3, términos por idioma).
# Un término terminado en "*" es prefijo; el resto se busca como palabra o frase completa.
REGLAS = [
    ('Seguridad', 3, {'es': ['atentado', 'tiroteo', 'balacera', 'masacre', 'asesinad*', 'asesinato', 'muertos', 'secuestr*', 'narcotráfico', 'cártel', 'enfrentamientos', 'explosión', 'coche bomba', 'homicidio*', 'feminicidio*', 'motín'],
                      'pt': ['atentado', 'tiroteio', 'chacina', 'assassinad*', 'assassinato', 'mortos', 'sequestr*', 'facção', 'explosão', 'homicídio*', 'feminicídio*', 'rebelião'],
                      'en': ['shooting', 'gunman', 'killed', 'massacre', 'kidnap*', 'cartel', 'car bomb', 'explosion', 'terror attack', 'terrorist*', 'stabbing', 'murder*', 'riot police']}),
    ('Desastre', 3, {'es': ['inundaci*', 'incendio forestal', 'incendios forestales', 'huracán', 'tornado', 'alerta roja', 'evacuad*', 'evacuación', 'estado de emergencia', 'emergencia climática', 'derrumbe', 'deslave', 'alud', 'sequía', 'damnificados', 'temporal'],
                     'pt': ['enchente*', 'inundaç*', 'incêndio florestal', 'queimadas', 'furacão', 'tornado', 'alerta vermelho', 'desalojad*', 'evacuaç*', 'estado de emergência', 'calamidade', 'deslizamento*', 'seca', 'desabrigad*'],
                     'en': ['flood*', 'wildfire*', 'hurricane', 'tornado', 'evacuat*', 'state of emergency', 'landslide', 'drought', 'heatwave', 'blizzard']}),
    ('Sismo', 2, {'es': ['sismo', 'terremoto', 'temblor'], 'pt': ['terremoto', 'tremor de terra', 'abalo sísmico'], 'en': ['earthquake', 'quake']}),
    ('Protesta', 2, {'es': ['protesta*', 'paro nacional', 'paro general', 'huelga*', 'marcha*', 'manifestaci*', 'piquete*', 'bloqueo*', 'cacerolazo', 'represión', 'disturbios', 'movilizaci*'],
                     'pt': ['protesto*', 'greve*', 'paralisaç*', 'manifestaç*', 'bloqueio*', 'repressão'],
                     'en': ['protest*', 'protesters', 'general strike', 'on strike', 'strike action', 'walkout', 'riot*', 'unrest', 'demonstrators']}),
    ('Institucional', 2, {'es': ['renuncia*', 'renunció', 'destitu*', 'juicio político', 'imputad*', 'detenid*', 'allanamiento*', 'escándalo', 'corrupción', 'decreto', 'veto', 'vetó', 'corte suprema', 'tribunal supremo', 'moción de censura', 'golpe de estado', 'indulto'],
                          'pt': ['renúncia', 'renunciou', 'impeachment', 'indiciad*', 'preso', 'presa', 'operação da pf', 'escândalo', 'corrupção', 'stf', 'decreto', 'veto', 'vetou', 'cassação', 'golpe'],
                          'en': ['resign*', 'impeach*', 'indict*', 'arrested', 'scandal', 'corruption', 'supreme court', 'no-confidence', 'coup', 'sanctions', 'executive order', 'pardon*']}),
    ('Economía', 1, {'es': ['inflación', 'devaluaci*', 'riesgo país', 'default', 'cesación de pagos', 'fmi', 'recesión', 'aranceles', 'desempleo', 'tasa de interés', 'banco central', 'déficit'],
                     'pt': ['inflação', 'desvaloriz*', 'selic', 'calote', 'fmi', 'recessão', 'tarifaço', 'desemprego', 'banco central', 'déficit'],
                     'en': ['inflation', 'tariff*', 'recession', 'interest rate*', 'default', 'imf', 'central bank', 'unemployment', 'budget deficit']}),
    ('Elecciones', 1, {'es': ['elecciones', 'electoral', 'encuesta*', 'candidat*', 'balotaje', 'segunda vuelta', 'comicios', 'referéndum', 'primarias'],
                       'pt': ['eleição', 'eleições', 'eleitoral', 'pesquisa eleitoral', 'candidat*', 'segundo turno'],
                       'en': ['election*', 'poll*', 'candidate*', 'ballot', 'referendum', 'primaries', 'by-election']}),
]
# Titulares de servicio (cotización del día, pronóstico, horóscopo…) no son alertas
RUIDO = re.compile(r'(precio del d[oó]lar|cotizaci[oó]n|tipo de cambio hoy|d[oó]lar hoy|cu[aá]nto est[aá] el d[oó]lar|pron[oó]stico|forecast|hor[oó]scopo|loter[ií]a|quiniela|resultados del sorteo|en vivo|minuto a minuto|live updates|recipe|receta)', re.I)
FINANZAS = re.compile(r'(riesgo pa[ií]s|bonos|activos|acciones|bolsa|mercados|merval|wall street|d[oó]lar|stocks|bonds|markets|a[cç][oõ]es|ibovespa)', re.I)
_L = 'a-záéíóúâêôãõçñü'
_RX = {}


def _rx(term):
    if term not in _RX:
        if term.endswith('*'):
            _RX[term] = re.compile(r'(?<![' + _L + r'])' + re.escape(term[:-1]))
        else:
            _RX[term] = re.compile(r'(?<![' + _L + r'])' + re.escape(term) + r'(?![' + _L + r'])')
    return _RX[term]


def get(url, retries=2, timeout=30):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json, application/xml, text/xml, */*', 'Accept-Language': 'es-419,es;q=0.9,en;q=0.8'})
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
    corte = (NOW - timedelta(days=31)).strftime('%Y-%m-%d')
    for h in hist.values():  # nada con más de un mes
        for k in [k for k in h if k < corte]:
            del h[k]
    tienen = set().union(*[set(h) for h in hist.values()]) if hist else set()
    fechas += [NOW - timedelta(days=k) for k in range(1, 31) if (NOW - timedelta(days=k)).strftime('%Y-%m-%d') not in tienen]
    fallas = 0
    for f in fechas:
        fecha, rates = fx_dia(f)
        if not fecha or not rates:
            fallas += 1
            if fallas >= 6:
                log('FX: demasiadas fallas, se corta'); break
            continue
        for c, m in monedas.items():
            if m in rates:
                hist[c][fecha] = round(float(rates[m]), 6)
        time.sleep(.3)
    out = {}
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
    root = ET.fromstring(get(url, retries=1, timeout=20))
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
    if RUIDO.search(low):
        return None, 0
    fin = FINANZAS.search(low)
    for cat, sev, terms in REGLAS:
        if fin and cat in ('Desastre', 'Sismo'):  # "derrumbe de bonos", "terremoto financiero": metáforas de mercado
            continue
        for w in terms[lang]:
            if _rx(w).search(low):
                return cat, sev
    return None, 0


def norm(s):
    return re.sub(r'[^a-z0-9áéíóúñâêôãõç ]', '', s.lower())[:70]


def noticias():
    titulares, alertas, fallas = {}, [], 0
    for c, nombre, _, _, lat, lon, loc, q, _ in PAISES:
        lang = lang_of(loc[0])
        if fallas >= 3:  # Google News limita por IP: si falla seguido, se usa lo de la corrida anterior
            continue
        log('GNews', c)
        try:
            items = gnews(q, loc, '1d')
            if len(items) < 8:
                items = gnews(q, loc, '3d')
            fallas = 0
        except Exception as e:
            log('GNews', c, e); fallas += 1
            continue
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
        d = get_json('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_month.geojson')
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


# Índices bursátiles (Yahoo Finance, cierre diario, 1 mes). Si no responde, el país queda sin índice.
INDICES = {'AR': ('^MERV', 'S&P Merval'), 'BR': ('^BVSP', 'Ibovespa'), 'CL': ('^IPSA', 'S&P IPSA'), 'MX': ('^MXX', 'S&P/BMV IPC'),
           'PE': ('^SPBLPGPT', 'S&P/BVL Perú General'), 'CO': ('^767679-USD-STRD', 'MSCI Colombia'), 'US': ('^GSPC', 'S&P 500'),
           'ES': ('^IBEX', 'IBEX 35'), 'GB': ('^FTSE', 'FTSE 100'), 'EU': ('^STOXX50E', 'Euro Stoxx 50')}


def indices():
    out = {}
    for c, (sym, nombre) in INDICES.items():
        for host in ('query1', 'query2'):
            try:
                d = get_json(f'https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=1mo&interval=1d', retries=0, timeout=20)
                r = d['chart']['result'][0]
                ts, cl = r.get('timestamp') or [], r['indicators']['quote'][0].get('close') or []
                serie = [[datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%d'), round(v, 2)] for t, v in zip(ts, cl) if v is not None]
                if serie and serie[-1][0] >= (NOW - timedelta(days=7)).strftime('%Y-%m-%d'):
                    out[c] = {'nombre': nombre, 'serie': serie}
                break
            except Exception as e:
                log('Índice', c, host, e)
        time.sleep(.5)
    return out


OCDE = {'AR': 'ARG', 'BR': 'BRA', 'CL': 'CHL', 'CO': 'COL', 'MX': 'MEX', 'US': 'USA', 'ES': 'ESP', 'GB': 'GBR', 'EU': 'EU27_2020'}


def inflacion(prev):
    """Inflación interanual: mensual de la OCDE donde la hay; si no, el último año del Banco Mundial (con su fecha)."""
    out = {}
    try:
        desde = (NOW - timedelta(days=420)).strftime('%Y-%m')
        url = ('https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/'
               + '+'.join(OCDE.values()) + f'.M..CPI.PA._T.N.GY?startPeriod={desde}&format=csvfile')
        import csv, io
        filas = list(csv.DictReader(io.StringIO(get(url, retries=1, timeout=60).decode('utf8', 'replace'))))
        inv = {v: k for k, v in OCDE.items()}
        series = {}
        for f in filas:
            c = inv.get(f.get('REF_AREA'))
            try:
                v = round(float(f.get('OBS_VALUE')), 1)
            except (TypeError, ValueError):
                continue
            if c:
                series.setdefault(c, {}).setdefault(f.get('METHODOLOGY') or 'N', []).append([f.get('TIME_PERIOD'), v])
        for c, por_met in series.items():  # IPC nacional o armonizado: el que tenga el dato más reciente
            sr = max(por_met.values(), key=lambda x: (max(r[0] for r in x), len(x)))
            sr.sort()
            if sr[-1][0] >= (NOW - timedelta(days=150)).strftime('%Y-%m'):
                out[c] = {'valor': sr[-1][1], 'periodo': sr[-1][0], 'frecuencia': 'mensual', 'fuente': 'OCDE', 'serie': sr[-13:]}
        log('Inflación OCDE', len(out), 'países')
    except Exception as e:
        log('Inflación OCDE', e)
    for c, nombre, iso3, *_ in PAISES:
        if c in out:
            continue
        old = prev.get('paises', {}).get(c, {}).get('inflacion')
        if old and old.get('frecuencia') == 'mensual' and old.get('periodo', '') >= (NOW - timedelta(days=120)).strftime('%Y-%m'):
            out[c] = old; continue
        try:
            d = get_json(f'https://api.worldbank.org/v2/country/{iso3}/indicator/FP.CPI.TOTL.ZG?format=json&mrnev=1', retries=1, timeout=30)
            r = d[1][0]
            if r.get('value') is not None and int(r['date']) >= NOW.year - 2:
                out[c] = {'valor': round(r['value'], 1), 'periodo': r['date'], 'frecuencia': 'anual', 'fuente': 'Banco Mundial'}
        except Exception as e:
            log('Inflación BM', c, e)
            if old:
                out[c] = old
        time.sleep(.3)
    return out


def archivo_alertas(nuevas):
    """Guarda las alertas de los últimos 30 días (sin repetir) para contar alertas por día."""
    f = OUT / 'archivo.json'
    try:
        arch = json.loads(f.read_text(encoding='utf8'))
    except Exception:
        arch = []
    corte = iso(NOW - timedelta(days=30))
    vistos = {a['k'] for a in arch}
    for a in nuevas:
        k = a.get('url') or a['titulo']
        if k not in vistos:
            vistos.add(k); arch.append({'k': k, 't': a['t'], 'p': a['pais'], 'c': a['cat'], 's': a['sev']})
    arch = [a for a in arch if a['t'] >= corte]
    f.write_text(json.dumps(arch, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    dias = [(NOW - timedelta(days=k)).strftime('%Y-%m-%d') for k in range(29, -1, -1)]
    serie = {c: {d: 0 for d in dias} for c in BY}
    for a in arch:
        d = a['t'][:10]
        if a['p'] in serie and d in serie[a['p']]:
            serie[a['p']][d] += 1
    return {c: [[d, n] for d, n in v.items()] for c, v in serie.items()}


def main():
    OUT.mkdir(exist_ok=True)
    prev = {}
    try:
        prev = json.loads((OUT / 'paises.json').read_text(encoding='utf8'))
    except Exception:
        pass
    log('Tipo de cambio…'); fx = tipo_cambio(prev)
    log('Índices…'); idx = indices()
    for c, v in prev.get('paises', {}).items():  # si Yahoo no respondió, se conserva lo último si tiene menos de una semana
        if c not in idx and v.get('indice') and v['indice']['serie'][-1][0] >= (NOW - timedelta(days=7)).strftime('%Y-%m-%d'):
            idx[c] = v['indice']
    log('Inflación…'); infl = inflacion(prev)
    log('Noticias…'); tit, al_medios = noticias()
    prev_sit = {}
    try:
        prev_sit = json.loads((OUT / 'situacion.json').read_text(encoding='utf8'))
    except Exception:
        pass
    corte30 = iso(NOW - timedelta(days=30))
    for c in BY:  # países sin respuesta de Google News: titulares y alertas de medios de la corrida anterior
        if c in tit:
            continue
        v = prev.get('paises', {}).get(c, {})
        tit[c] = {'items': [x for x in v.get('titulares', []) if x['t'] >= corte30], 'n24': v.get('notas24', 0)}
        al_medios += [a for a in prev_sit.get('alertas', []) if a.get('pais') == c and a.get('tipo') == 'medios' and a['t'] >= iso(NOW - timedelta(hours=48))]
    log('GDELT…'); tono = gdelt_tono()
    for c, v in prev.get('paises', {}).items():  # GDELT limita fuerte: lo que no respondió se toma de la corrida anterior
        if not tono.get(c) and v.get('tono'):
            tono[c] = v['tono']
    corte7 = (NOW - timedelta(days=7)).strftime('%Y%m%d')
    tono = {c: [r for r in v if r[0] >= corte7] for c, v in tono.items()}
    log('Sismos y desastres…'); sis = sismos(); al_geo = [a for a in sis if a['t'] >= iso(NOW - timedelta(days=7))] + gdacs()

    alertas = sorted(al_medios + al_geo, key=lambda a: a['t'], reverse=True)
    serie_al = archivo_alertas(alertas)
    corte24 = iso(NOW - timedelta(hours=24))
    nivel = {}
    for c in BY:
        a24 = [a for a in alertas if a['pais'] == c and a['t'] >= corte24]
        nivel[c] = {'n24': len(a24), 'peso': sum(a['sev'] for a in a24), 'n7': sum(n for _, n in serie_al[c][-7:]), 'n30': sum(n for _, n in serie_al[c])}
    mx = max([v['peso'] for v in nivel.values()] + [1])
    for v in nivel.values():
        v['indice'] = round(v['peso'] / mx, 3)

    paises = {}
    for c, nombre, iso3, *_ in PAISES:
        p = BY[c]
        paises[c] = {'nombre': nombre, 'iso3': iso3, 'lat': p[4], 'lon': p[5], 'fx': fx.get(c, {}), 'indice': idx.get(c), 'inflacion': infl.get(c),
                     'tono': tono.get(c) or [], 'titulares': tit.get(c, {}).get('items', []), 'notas24': tit.get(c, {}).get('n24', 0),
                     'alertas': nivel[c], 'serie_alertas': serie_al[c], 'sismos30': sum(1 for a in sis if a['pais'] == c)}
    meta = {'actualizado': iso(NOW), 'fuentes': ['currency-api (fawazahmed0)', 'OCDE', 'Banco Mundial', 'Yahoo Finance', 'Google News', 'GDELT', 'USGS', 'GDACS']}
    (OUT / 'paises.json').write_text(json.dumps({'meta': meta, 'paises': paises}, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    sit = {'meta': meta, 'nivel': nivel, 'alertas': alertas[:160]}
    (OUT / 'situacion.json').write_text(json.dumps(sit, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    log('ok', len(alertas), 'alertas;', sum(len(v['titulares']) for v in paises.values()), 'titulares;', len(idx), 'índices')


if __name__ == '__main__':
    main()
