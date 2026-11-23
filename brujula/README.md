# Brújula (nombre de trabajo)

Lo que la gente piensa cuando le preguntás y lo que se dice en redes, en el mismo tablero.

Tres piezas:

1. **Quiz público** (`quiz/`): 12 ejes con las preguntas base de [12axes](https://github.com/politicaltests/politicaltests.github.io)
   (licencia MIT, © 2020 8values / SapplyValues), adaptadas, más preguntas locales por país. Versiones: Latinoamérica general,
   Argentina, Brasil, Paraguay, Perú, Chile, Colombia y Uruguay (56 a 62 preguntas, 15 a 43 dirigentes por país, de los más
   conocidos a figuras menores). Idioma aparte del país: selector ES / PT / EN (Brasil arranca en portugués).
   Devuelve posición por eje, **certeza** por eje (qué tan firme y coherente es la postura, dibujada como una banda), los 5
   dirigentes más cercanos (la afinidad pesa más los ejes donde la persona está segura), un mapa economía × valores y un link
   para compartir. Al final, cinco datos opcionales (edad en rango, género, país y provincia o estado, país de nacimiento, red
   principal) con una casilla de consentimiento. Se publica en `/quiz/`. Los textos de la interfaz están en `quiz/i18n.js`.
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
| `datos/generar.py` | Fuente de las preguntas (base 12axes + locales) y de la recodificación de dirigentes; genera los tres JSON de abajo |
| `datos/figuras_base.json`, `datos/locales_base.json` | Posiciones editoriales de dirigentes y preguntas locales por país (se editan acá y se corre `generar.py`) |
| `datos/ejes.json` | Ejes, polos, escala de respuesta y versiones por país |
| `datos/preguntas.json` | Banco de preguntas: efecto de cada una sobre cada eje y en qué versiones va |
| `datos/figuras.json` | Posición editorial de cada dirigente en los 12 ejes (**a revisar**) |
| `quiz/` | Quiz (HTML + JS vanilla, sin build) |
| `apps_script/Code.gs` | Recepción de respuestas en la planilla y lectura con token |
| `procesar.py` | Planilla → limpieza → ponderación (si hay `datos/marginales_ar.json`) → `data/quiz.json` |
| `listener/collect.py`, `listener/analyze.py` | Recolección y agregados → `data/listener.json` |
| `cruce.py` | Brechas, alertas y acciones → `data/cruce.json` |
| `tests/test_pipeline.py` | Prueba de punta a punta con datos simulados (`--guardar-demo` regenera `data/demo/`) |

## Certeza

Por eje, 0 a 100 = decisión × coherencia. Decisión: neutral 0, de acuerdo 0,75, muy de acuerdo 1. Coherencia: cada frase de 12axes
tiene un nivel (1 moderada … 4 extrema); una frase de nivel L la acepta quien está del lado de su polo al menos (L − 1) × 12,5 puntos
más allá del centro. Las respuestas que coinciden con eso suman y las que no, restan. El mismo cálculo está en `quiz.js` y `procesar.py`.

## Ponderación

Argentina se pondera por raking (IPF, pesos recortados a 0,2-5) a `datos/marginales_ar.json`: Censo 2022 (INDEC), población de 16+
por género y edad (`edad_g`: 16-24, 25-34, 35-49, 50+; el tramo 16-24 es estimado) y región (AMBA, Pampeana, NOA, NEA, Cuyo,
Patagonia, según población total por jurisdicción; conurbano = 24 partidos). Se usa cada variable que contestó al menos el 80%.
Fuentes: cuadros del Censo 2022 en censo.gob.ar e INDEC (c2022_tp_est_c4). Los otros países se publican sin ponderar.

## Para después

Focus groups y modelos (ML) que afinen la afinidad y los segmentos con las dos fuentes. Más países: sumar preguntas con `"v": ["cl"]`
y una lista de figuras por país en `figuras.json`, y activar la versión en `ejes.json`.
