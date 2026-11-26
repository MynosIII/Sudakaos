"""Prueba de punta a punta con datos simulados (nada se escribe en brujula/data/ salvo --guardar-demo).

    python brujula/tests/test_pipeline.py [--guardar-demo]
"""
import json
import os
import random
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

B = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp())
env = dict(os.environ, RADAR_NLP="lexico", BRUJULA_STORE=str(tmp / "store"), BRUJULA_LISTENER_OUT=str(tmp / "listener.json"))
(tmp / "store").mkdir()
rnd = random.Random(1)
now = datetime.now(timezone.utc)
frases = ["La motosierra y el deficit cero de Milei", "Kicillof critica el ajuste a jubilados", "Bullrich y el protocolo antipiquetes: mano dura",
          "Represion en la marcha, denuncian derechos humanos", "Gobernadores reclaman coparticipacion y federalismo", "Ley de Glaciares: el agua no se negocia",
          "Vaca Muerta record de produccion y exportaciones", "Cristina habla de soberania y Malvinas", "Acuerdo con Estados Unidos, alianza con Trump",
          "Batalla cultural contra la ideologia de genero", "Ni una menos: derechos y ESI", "Casta y ensobrados, dice Adorni", "DNU y division de poderes en el Congreso",
          "Jorge Macri y la seguridad en CABA", "Mauricio Macri y el PRO", "Pagano denuncia a Adorni", "Apertura de importaciones golpea a pymes e industria nacional",
          "Cobrar a extranjeros la universidad, migrantes denuncian xenofobia", "La Iglesia y el estado laico", "Compra de F-16 y rearme de las Fuerzas Armadas",
          "Reforma laboral: la CGT defiende el convenio colectivo", "Inteligencia artificial e innovacion"]
rows = []
for i in range(1200):
    t = rnd.choice(frases) + rnd.choice([" excelente", " un desastre", "", " vergüenza", " gran avance"])
    plat = rnd.choice(["Medios", "YouTube", "YouTube", "X"])
    rows.append({"id": f"t{i}", "platform": plat, "kind": "nota" if plat == "Medios" else "comentario", "text": t, "title": t,
                 "channel": "Medio", "url": f"https://ejemplo.com/{i}", "created_at": (now - timedelta(days=rnd.randint(0, 60))).strftime("%Y-%m-%dT%H:%M:%SZ"), "tag": ""})
for i, eje in enumerate(["pla", "lib", "pro", "tec"] * 10):
    rows.append({"id": f"ad{i}", "platform": "Anuncios Meta", "kind": "aviso", "text": "Aviso sobre " + eje + " seguridad ajuste genero mineria", "channel": f"Pagina {i % 3}",
                 "url": "https://facebook.com/ads/library", "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "tag": "tema:" + eje,
                 "impressions": {"lower_bound": "1000", "upper_bound": "4999"},
                 "demo": [{"age": "18-24", "gender": "male", "percentage": "0.4"}, {"age": "25-34", "gender": "female", "percentage": "0.3"}, {"age": "65+", "gender": "female", "percentage": "0.3"}]})
(tmp / "store" / "items.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf8")
run = lambda *a: subprocess.run([sys.executable, *a], check=True, env=env, cwd=B.parent)
run(str(B / "procesar.py"), "--demo", "1500", "--out", str(tmp / "quiz.json"))
run(str(B / "listener" / "analyze.py"))
run(str(B / "cruce.py"), "--quiz", str(tmp / "quiz.json"), "--listener", str(tmp / "listener.json"), "--out", str(tmp / "cruce.json"))
L = json.loads((tmp / "listener.json").read_text())
C = json.loads((tmp / "cruce.json").read_text())
assert L["figuras"]["Jorge Macri"]["n"] > 0 and L["figuras"]["Mauricio Macri"]["n"] > 0
assert L["ejes"]["lib"]["encuadre"]["b_pct"] is not None
Q = json.loads((tmp / "quiz.json").read_text())
ar = Q["versiones"]["ar"]
E = json.loads((B / "datos" / "ejes.json").read_text())
assert set(ar["ejes"]) == {e["id"] for e in E["ejes"] + E["ejes2"]}, "faltan ejes de los 30"
assert all(v["cert"] is None or 0 <= v["cert"] <= 100 for v in ar["ejes"].values()) and ar["certeza"] is not None
assert ar["ejes"]["cer"]["m"] == ar["certeza"]
assert len(ar["ideologias"]) >= 10 and abs(sum(i["pct"] for i in ar["ideologias"]) - 100) < 1
assert ar["por"]["autodef"] and all(g["ideologias"] for g in ar["por"]["autodef"].values())
assert ar["ponderacion"].startswith("raking"), ar["ponderacion"]
assert "br" in Q["versiones"], "falta la versión Brasil"
assert len(L["ejes"]) == 12
assert C["acciones"], "sin acciones"
assert C["simulado"] is True
print("OK", tmp)
if "--guardar-demo" in sys.argv:  # vista previa del tablero con ?demo=1 (datos simulados, marcados como tales)
    import shutil
    d = B / "data" / "demo"
    d.mkdir(parents=True, exist_ok=True)
    for f in ("quiz.json", "listener.json", "cruce.json"):
        shutil.copy(tmp / f, d / f)
    print("demo guardada en", d)
for x in C["acciones"]:
    print("-", x["accion"], "|", x["metrica"])
for x in C["alertas"]:
    print("!", x["t"])
