"""Genera los datos geográficos compactos para la landing 3D.

Salida (JSON): índices de puntos de una esfera de Fibonacci que caen en tierra
(delta + varint, base64) separados en LATAM / resto, y bordes LATAM simplificados.
"""
import json, math, base64, sys
import numpy as np

SRC = sys.argv[1]
OUT = sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 60000

LATAM = {'484','320','084','340','222','558','188','591','192','214','332','630','388','170','862','218','604','068','076','600','152','032','858','328','740','780','044','238','052','028','659','662','670','308','212','533','531','534','535'}

j = json.load(open(SRC))
sc, tr = j['transform']['scale'], j['transform']['translate']
arcs = []
for a in j['arcs']:
    x = y = 0; pts = []
    for dx, dy in a:
        x += dx; y += dy
        pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
    arcs.append(pts)

def ring(idx):
    out = []
    for i in idx:
        p = arcs[i] if i >= 0 else arcs[~i][::-1]
        out.extend(p if not out else p[1:])
    return out

polys = []  # (is_latam, [rings])
for g in j['objects']['countries']['geometries']:
    lat = g.get('id') in LATAM
    if g['type'] == 'Polygon':
        polys.append((lat, [ring(r) for r in g['arcs']]))
    elif g['type'] == 'MultiPolygon':
        for p in g['arcs']:
            polys.append((lat, [ring(r) for r in p]))

# Esfera de Fibonacci
i = np.arange(N)
golden = math.pi * (3 - math.sqrt(5))
y = 1 - (i + 0.5) / N * 2
lat_d = np.degrees(np.arcsin(y))
lon_d = np.degrees(((i * golden) % (2 * math.pi))) - 180  # [-180,180)

def pip(px, py, poly):
    inside = np.zeros(px.shape, bool)
    xs = np.array([p[0] for p in poly]); ys = np.array([p[1] for p in poly])
    xj, yj = np.roll(xs, 1), np.roll(ys, 1)
    for k in range(len(xs)):
        xi_, yi_, xk, yk = xs[k], ys[k], xj[k], yj[k]
        c = ((yi_ > py) != (yk > py)) & (px < (xk - xi_) * (py - yi_) / (yk - yi_ + 1e-12) + xi_)
        inside ^= c
    return inside

land = np.zeros(N, bool); latam = np.zeros(N, bool)
for is_lat, rings in polys:
    outer = rings[0]
    xs = [p[0] for p in outer]; ys = [p[1] for p in outer]
    m = (lon_d >= min(xs)) & (lon_d <= max(xs)) & (lat_d >= min(ys)) & (lat_d <= max(ys))
    if not m.any():
        continue
    idx = np.nonzero(m)[0]
    ins = pip(lon_d[idx], lat_d[idx], outer)
    for h in rings[1:]:
        ins &= ~pip(lon_d[idx], lat_d[idx], h)
    land[idx[ins]] = True
    if is_lat:
        latam[idx[ins]] = True
# Antártida fuera (ruido visual abajo del todo)
land &= lat_d > -60

def enc(ids):
    out = bytearray(); prev = 0
    for v in ids:
        d = int(v) - prev; prev = int(v)
        while True:
            b = d & 0x7F; d >>= 7
            if d: out.append(b | 0x80)
            else: out.append(b); break
    return base64.b64encode(bytes(out)).decode()

lat_ids = np.nonzero(latam)[0]
rest_ids = np.nonzero(land & ~latam)[0]

# Bordes LATAM simplificados (Douglas-Peucker)
def dp(pts, eps):
    if len(pts) < 3: return pts
    a, b = np.array(pts[0]), np.array(pts[-1])
    ab = b - a; L = np.hypot(*ab)
    P = np.array(pts)
    d = np.abs(ab[0]*(P[:,1]-a[1]) - ab[1]*(P[:,0]-a[0])) / L if L > 0 else np.hypot(*(P - a).T)
    k = int(np.argmax(d))
    if d[k] > eps:
        return dp(pts[:k + 1], eps)[:-1] + dp(pts[k:], eps)
    return [pts[0], pts[-1]]

lines = []
for is_lat, rings in polys:
    if not is_lat: continue
    r = rings[0]
    xs = [p[0] for p in r]; ys = [p[1] for p in r]
    if (max(xs) - min(xs)) * (max(ys) - min(ys)) < 0.6: continue  # islitas
    s = dp(r, 0.12)
    if len(s) < 4: continue
    flat = []
    for x_, y_ in s: flat += [round(x_ * 10), round(y_ * 10)]
    lines.append(flat)

json.dump({'n': N, 'latam': enc(lat_ids), 'rest': enc(rest_ids), 'borders': lines}, open(OUT, 'w'), separators=(',', ':'))
print('N', N, 'latam', len(lat_ids), 'rest', len(rest_ids), 'border pts', sum(len(l) for l in lines) // 2)
