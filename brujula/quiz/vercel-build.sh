#!/bin/sh
# Build del quiz para Vercel (solo el quiz: nada del tablero ni de los datos agregados).
# El endpoint del Apps Script se toma del config.js que publica GitHub Pages (sale del secret QUIZ_ENDPOINT),
# así hay una sola fuente. Si Pages no responde, el quiz funciona igual pero no envía respuestas.
set -e
cd "$(dirname "$0")/../.."
rm -rf out && mkdir -p out/datos
cp brujula/quiz/quiz.js brujula/quiz/quiz.css brujula/quiz/i18n.js out/
cp brujula/datos/ejes.json brujula/datos/preguntas.json brujula/datos/figuras.json brujula/datos/ideologias.json out/datos/
V=$(git rev-parse --short HEAD 2>/dev/null || date +%s)
sed -e "s#<script src=\"config.js\"></script>#<script src=\"https://mynosiii.github.io/Sudakaos/quiz/config.js\"></script>\n<script>window.BRUJULA = window.BRUJULA || { endpoint: '' }; window.BRUJULA.datos = 'datos/';</script>#" \
    -e "s#\(quiz\.js\|quiz\.css\|i18n\.js\)\"#\1?v=$V\"#g" brujula/quiz/index.html > out/index.html
