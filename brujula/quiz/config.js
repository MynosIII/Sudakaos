/* Configuración del quiz. publicar_sitio.py reescribe este archivo al publicar:
   - datos: carpeta con ejes.json, preguntas.json y figuras.json
   - endpoint: URL del Apps Script que guarda respuestas en la planilla privada (secret QUIZ_ENDPOINT).
     Vacío = el quiz funciona igual, pero no envía nada. */
window.BRUJULA = { datos: '../datos/', endpoint: '' };
