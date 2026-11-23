# Brújula (nombre de trabajo)

Lo que la gente piensa cuando le preguntás y lo que se dice en redes, en el mismo tablero.

Tres piezas:

1. **Quiz público** (`quiz/`): 8 ejes (economía, comercio y moneda, territorio, valores, seguridad, sistema político, mundo, ambiente).
   Versión Latinoamérica (45 preguntas, 18 figuras de la región) y Argentina (56 preguntas con condimento local, 43 dirigentes:
   de Milei y Cristina Kirchner a figuras menos conocidas). Devuelve posición por eje, los 5 dirigentes más cercanos, un mapa
   económico × valores y un link para compartir. Al final, cinco datos opcionales (edad en rango, género, país y provincia,
   país de nacimiento, red principal) con consentimiento explícito. Se publica en `/quiz/`.
2. **Social listener** (`listener/`): escucha pasiva por eje y por dirigente. Google News, YouTube (videos y comentarios),
   Biblioteca de Anuncios de Meta (avisos por tema con edad y género del público alcanzado), Instagram desde `meta/`, X solo a mano.
3. **Tablero** (`index.html` + `panel.js`): Panorama, Encuesta, Conversación, Cruce, Resumen accionable (PDF) y Fuentes y método.
   Se publica en ruta secreta (`/brujula/t<hash>/`). Con `?demo=1` muestra datos simulados, marcados como tales.

## Datos y privacidad

- Las opiniones políticas son **datos sensibles** (Ley 25.326, art. 7): el quiz es anónimo, no pide nada identificatorio,
  pide consentimiento y no guarda nada de menores de 16. Edad en rangos, provincia (no ciudad), hora redondeada.
- Las respuestas individuales van a una **planilla privada de Google Sheets** (Apps Script, gratis). Nunca al repo.
- Actions lee la planilla con un token, recalcula todo con `datos/preguntas.json` y commitea **solo agregados**
  (`data/quiz.json`), con grupos de 30+ respuestas (`BRUJULA_MIN_N`).
- Los textos del listener viven en la caché de Actions (`listener/.store/`), como en el resto de Sudakaos.

## Puesta en marcha (una vez)

1. Crear una planilla privada en Google Drive → Extensiones → Apps Script → pegar `apps_script/Code.gs`.
2. En Apps Script: Configuración del proyecto → Propiedades del script → `TOKEN` = una clave larga al azar.
3. Implementar → Nueva implementación → Aplicación web → Ejecutar como: yo · Acceso: cualquier usuario. Copiar la URL `/exec`.
4. En GitHub → Settings → Secrets → Actions: `QUIZ_ENDPOINT` (la URL /exec) y `QUIZ_TOKEN` (la misma clave del paso 2).
   Opcional: `YOUTUBE_API_KEY_BRUJULA` (si no, usa la de dirigentes o la de Roca).
5. Correr *Actions → Brujula opinion y conversacion → Run workflow*. Para leer X (pago), marcar la casilla `x`.

## Archivos

| Archivo | Qué hace |
|---|---|
| `datos/ejes.json` | Ejes, polos, escala de respuesta y versiones por país |
| `datos/preguntas.json` | Banco de preguntas: efecto de cada una sobre cada eje y en qué versiones va |
| `datos/figuras.json` | Posición editorial de cada dirigente en los 8 ejes (**a revisar**) |
| `quiz/` | Quiz (HTML + JS vanilla, sin build) |
| `apps_script/Code.gs` | Recepción de respuestas en la planilla y lectura con token |
| `procesar.py` | Planilla → limpieza → ponderación (si hay `datos/marginales_ar.json`) → `data/quiz.json` |
| `listener/collect.py`, `listener/analyze.py` | Recolección y agregados → `data/listener.json` |
| `cruce.py` | Brechas, alertas y acciones → `data/cruce.json` |
| `tests/test_pipeline.py` | Prueba de punta a punta con datos simulados (`--guardar-demo` regenera `data/demo/`) |

## Ponderación

Sin marginales cargadas, la muestra se publica **sin ponderar**. Para ponderar por raking al Censo 2022, crear
`datos/marginales_ar.json` con `{"fuente": "Censo 2022 (INDEC)", "marginales": {"genero": {"Mujer": 0.52, ...}, "edad_g": {...}, "region": {...}}}`
usando las mismas categorías que el quiz (`edad_g`: 16-24, 25-34, 35-49, 50+; `region`: AMBA, Pampeana, NOA, NEA, Cuyo, Patagonia).

## Para después

Focus groups y modelos (ML) que afinen la afinidad y los segmentos con las dos fuentes. Más países: sumar preguntas con `"v": ["cl"]`
y una lista de figuras por país en `figuras.json`, y activar la versión en `ejes.json`.
