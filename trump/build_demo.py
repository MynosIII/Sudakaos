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
(out / "index.html").write_text(s, encoding="utf8")
shutil.copytree(ROOT / "data", out / "data", dirs_exist_ok=True)
shutil.copy(ROOT.parent / "assets" / "plotly.min.js", out / "plotly.min.js")
shutil.copytree(ROOT.parent / "assets" / "topo", out / "topo", dirs_exist_ok=True)
print(f"demo -> {out}")
