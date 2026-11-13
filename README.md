# Sudakaos

Tablero de escucha social y opinión pública para Argentina y Brasil, hecho solo con fuentes gratuitas.

- **Tablero:** https://mynosiii.github.io/Sudakaos/
- **Radar** (`radar/`): recolecta noticias (Google News por político y verificadores), RSS de medios y comentarios públicos de YouTube; clasifica tono, emoción y agresividad (pysentimiento, con diccionarios de respaldo) y publica solo agregados en `radar/data/`.
- **Cubo político** (`radar/data/positions.json`): ubicación editorial de cada político en economía, sociedad y política, con el criterio de cada uno.
- **San Isidro** (`sanisidro/`): reclamos vecinales por localidad.
- **Meta** (`meta/`): Instagram (Business Discovery) y Biblioteca de Anuncios de Meta para 18 dirigentes de País, Boca, Provincia (con Tigre), CABA y San Isidro. Gratis con token propio: secrets `META_TOKEN` y `META_IG_USER_ID`. Los usuarios de Instagram se corrigen en `meta/config.json`.
- **Resumen accionable** (`resumen.js`): última pestaña del tablero. Informe por dirigente (resumen, acciones, análisis y conclusión) que se descarga en PDF. Con Alt+Shift+P, o tocando el punto al pie del informe, se abre un prompt para hacer videos del candidato a partir de esos datos.

## Cómo se actualiza

- `Radar social listening` corre todos los días a las 10:40 UTC. Desde *Actions → Run workflow* se pueden sumar políticos: `Juan Pérez; Ana Gómez (BR, PT)`.
- `San Isidro reclamos` corre a las 11:10 UTC.
- `Publicar tablero` publica en GitHub Pages cada vez que terminan.
- Secret necesario: `YOUTUBE_API_KEY`.

Los textos de publicaciones y comentarios nunca se suben al repositorio: viven en la caché de Actions. La pestaña Encuesta lee los agregados publicados por ProjectMilei2.
