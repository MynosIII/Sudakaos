"""Builds the public demo of the Trump monitor: python trump/build_demo.py <out_dir>

Public on purpose (free-trial demo for sudakaoslatam.com/demo/trump/ and GitHub Pages web/demo/trump/):
page + daily aggregates + Plotly, all inside one folder. Client boards stay in secret routes.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
s = (ROOT / "index.html").read_text(encoding="utf8")
if '"../assets/plotly.min.js"' not in s:
    sys.exit("build_demo: plotly path not found")
s = s.replace('"../assets/plotly.min.js"', '"plotly.min.js"')
s = s.replace("const TOPO='../assets/topo/'", "const TOPO='topo/'")
for f in ("sala.css", "sala.js"):  # capa visual común de los tableros
    if f'"../assets/{f}"' not in s:
        sys.exit(f"build_demo: {f} path not found")
    s = s.replace(f'"../assets/{f}"', f'"{f}"')
(out / "index.html").write_text(s, encoding="utf8")
shutil.copytree(ROOT / "data", out / "data", dirs_exist_ok=True)
for f in ("plotly.min.js", "sala.css", "sala.js"):
    shutil.copy(ROOT.parent / "assets" / f, out / f)
shutil.copytree(ROOT.parent / "assets" / "topo", out / "topo", dirs_exist_ok=True)
sys.path.insert(0, str(ROOT.parent))
from fotos.subset import copiar  # noqa: E402  solo las fotos de quien la demo ya nombra
copiar(out)
print(f"demo -> {out}")
