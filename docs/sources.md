# Fuentes, coste y límites

> Cómo se accede a cada fuente, qué guardamos, cuánto cuesta y qué límites tiene. Las decisiones
> viven en [`CLAUDE.md`](../CLAUDE.md) §5 y los precios en [`data/pricing.yaml`](../data/pricing.yaml).
> Precios y términos verificados el 2026-10-17.

## Resumen

| Fuente | Acceso | Qué guardamos | Coste | Límites |
|---|---|---|---|---|
| YouTube | Data API v3 oficial | Metadatos, métricas públicas y snapshots | 0 $ (cuota de 10.000 unidades/día) | `search.list` cuesta 100 unidades; mejor `playlistItems` de canales conocidos |
| Hacker News | Algolia HN Search API | Metadatos, puntos, comentarios y snapshots | 0 $ | Comunidad técnica: no representa a la audiencia de negocio |
| RSS | `feedparser` + `httpx` | Título, enlace, fecha y descripción del feed | 0 $ | Sin métricas de engagement |
| Brave Search | API oficial (cabecera `X-Subscription-Token`) | Solo agregados (ver abajo) | 5 $ por 1.000 consultas, con 5 $ de crédito gratis al mes (≈ 1.000 consultas) | Sus términos solo permiten guardar resultados de forma transitoria |
| LinkedIn | Índice de Brave (transitorio) + curación + embed oficial | Lo curado a mano y los agregados por tema | Dentro del crédito de Brave | Sin reacciones ni comentarios automáticos |
| Instagram / TikTok | Solo curación manual | Lo curado: URL, etiquetas y métricas vistas | 0 $ | Sin acceso automático |

## Brave: uso transitorio

Los [términos de la API de Brave](https://api-dashboard.search.brave.com/terms-of-service), §3(b)(i),
prohíben "store, cache, or create a database of Search Results, in whole or in part, other than
transient storage" si el plan no incluye derechos de almacenamiento. Brave no publica el precio de
ese plan; las reseñas hablan de unos 45 $ por 1.000 consultas.

Por eso, con el plan estándar:

- Los resultados de Brave se usan en memoria y se descartan al terminar el job o la petición.
- Se guardan solo agregados que no son resultados: conteos por tema y día, y distribuciones de
  gancho y formato. Esto es interpretación nuestra de §3(b)(i). Si hiciera falta guardar
  resultados como evidencia persistente, se contrata el plan con derechos de almacenamiento.
- Afecta también al colector de descubrimiento web de Brave previsto como P1 (CLAUDE.md §5).

## LinkedIn sin scraping

**El problema.** El reto pone LinkedIn como ejemplo, pero LinkedIn no tiene API pública para buscar
posts de otros miembros. Su API de Community Management solo lee las páginas que uno administra y
requiere aprobación previa. Además, el reto excluye el contenido detrás de un login y cualquier
técnica que viole términos de servicio.

**La solución: cuatro vías legítimas y baratas.**

1. **Índice público de Brave (automático, P1).** El
   [robots.txt de LinkedIn](https://www.linkedin.com/robots.txt) permite a Googlebot rastrear los
   posts públicos (`/posts/`, `/pulse/`), y el
   [crawler de Brave sigue las reglas de Googlebot](https://search.brave.com/help/brave-search-crawler).
   Consultamos la API de Brave con `site:linkedin.com/posts` (o `/pulse`), las palabras clave del
   tema, `search_lang=es` y `freshness=pw`. Nunca accedemos a LinkedIn: solo leemos el índice de un
   buscador.
   - **En el job `analyze`:** contamos los posts públicos de cada tema por día, y Jev clasifica el
     gancho y el formato de cada título. El título suele ser la primera línea del post, o sea, el
     gancho. Se guardan solo los agregados por tema.
   - **En el detalle de la oportunidad:** `GET /opportunities/{id}/linkedin` consulta Brave en vivo
     y devuelve los enlaces del momento, sin guardarlos.
   - **Qué da:** tema, gancho, autor público, fecha aproximada y URL.
   - **Qué no da:** reacciones ni comentarios fiables, así que es `growth_status = preliminary`.
   - **Coste:** 30 temas × 1 consulta al día ≈ 900 consultas al mes, dentro del crédito gratis.
   - **Validar en la primera consulta real** que `site:linkedin.com/posts` devuelve posts recientes
     en español.
2. **La comunidad como sensor (manual, P1).** El equipo de 30X ya navega LinkedIn todos los días.
   Cuando ve un post que funciona, pega la URL en el dashboard con sus etiquetas y las métricas que
   ve (`POST /signals/manual`). Esto sí se guarda, porque no viene de Brave ni de scraping. Es la vía
   que sugiere el propio reto.
3. **Embed oficial para mostrar la evidencia.** Los posts públicos se muestran con el
   ["Embed this post" de LinkedIn](https://www.linkedin.com/help/linkedin/answer/a529065), un iframe
   `linkedin.com/embed/feed/update/urn:li:share:…`. LinkedIn sirve su propio contenido y nosotros no
   guardamos el texto. No funciona con posts de varias fotos ni con reposts con comentario.
4. **Los canales abiertos de los referentes de LinkedIn.** Muchos referentes de negocio e IA en LATAM
   publican lo mismo en newsletters con RSS, blogs o YouTube. Se dan de alta en `data/sources.yaml`
   con su `segment`.

**Después de la hackathon.** Con la Community Management API oficial, 30X podría leer las métricas
de sus propias páginas de LinkedIn (requiere aprobación de LinkedIn). Serían datos reales de su
audiencia.

**Alternativas descartadas.**

| Alternativa | Por qué no |
|---|---|
| Actores de Apify y "LinkedIn post scrapers" sin cookies | Scrapean LinkedIn, así que dependen de violar sus términos (el reto lo excluye) |
| Herramientas que buscan dentro de la sesión del usuario | El User Agreement de LinkedIn prohíbe copiar datos con scripts, crawlers o plugins del navegador |
| APIs que scrapean los resultados de Google | Dependen de violar los términos de Google |
| Google Custom Search JSON API | [Cerrada a clientes nuevos; se apaga el 1 de enero de 2027](https://brave.com/learn/google-api-shutdown/) |
| Bing Web Search API | Microsoft la retiró en 2025 |
| Buscadores con crawler propio que LinkedIn no autoriza | El robots.txt de LinkedIn solo admite una lista cerrada de crawlers |
