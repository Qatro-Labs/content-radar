# Fuentes, coste y límites

> Cómo se accede a cada fuente, qué guardamos, cuánto cuesta y qué límites tiene. Las decisiones
> viven en [`CLAUDE.md`](../CLAUDE.md) §5 y los precios en [`data/pricing.yaml`](../data/pricing.yaml).
> Precios y términos verificados el 2026-10-17.

## Resumen

| Fuente | Acceso | Qué guardamos | Coste | Límites |
|---|---|---|---|---|
| YouTube | Data API v3 oficial | Metadatos, métricas públicas y snapshots | 0 $ (cupo propio de 100 llamadas/día a `search.list`, a 1 unidad cada una, y 10.000 unidades/día para el resto) | El cupo de `search.list` es pequeño: mejor `playlistItems` de canales conocidos |
| Hacker News | Algolia HN Search API | Metadatos, puntos, comentarios y snapshots | 0 $ | Comunidad técnica: no representa a la audiencia de negocio |
| RSS | `feedparser` + `httpx` | Título, enlace, fecha y descripción del feed | 0 $ | Sin métricas de engagement |
| Brave Search | API oficial (cabecera `X-Subscription-Token`) | Solo agregados: sus resultados son transitorios | 5 $ por 1.000 consultas, con 5 $ de crédito gratis al mes (≈ 1.000 consultas) | Solo descubrimiento web, nunca LinkedIn |
| LinkedIn · Instagram · TikTok | **Fuera del MVP** (decidido el 17/10). Roadmap: vías oficiales (abajo) | Nada | — | Sin login ni scraping no hay acceso; la curación manual se descartó |

## Brave: uso transitorio

Los [términos de la API de Brave](https://api-dashboard.search.brave.com/terms-of-service), §3(b)(i),
prohíben "store, cache, or create a database of Search Results, in whole or in part, other than
transient storage" si el plan no incluye derechos de almacenamiento. Brave no publica el precio de
ese plan.

Con el plan estándar:

- Los resultados se usan en memoria y se descartan al terminar el job o la petición.
- Se guardan solo agregados que no son resultados: conteos por tema y día. Es interpretación nuestra
  de §3(b)(i). Si hiciera falta guardar resultados como evidencia persistente, se contrata el plan
  con derechos de almacenamiento.
- Cuando Brave descubre un artículo de un medio, se puede leer después su RSS o sus metadatos
  públicos directamente en el medio, respetando su robots.txt. Lo que se guarda es esa observación,
  no el resultado de Brave.

## LinkedIn sin scraping

### ¿Sirve una cuenta normal con un token de API?

Sí: con una cuenta normal se puede crear una app y un token. La app tiene que ir asociada a una
página de empresa. Pero ningún producto self-serve permite leer posts de otros miembros:

| Producto self-serve | Qué permite | ¿Sirve para descubrir posts? |
|---|---|---|
| Sign In with LinkedIn (OpenID Connect) | Nombre, foto y email de quien inicia sesión | No |
| Share on LinkedIn (`w_member_social`) | Publicar en nombre del usuario | No: solo escribe |
| [Member Data Portability (Member)](https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/member-data-portability-member/), solo EEE y Suiza | Descargar los datos propios: posts, comentarios y reacciones del miembro | De forma indirecta (vía 1) |

El permiso para leer posts de miembros (`r_member_social`) está cerrado y LinkedIn no acepta
solicitudes. La Community Management API exige revisión y solo da acceso a las páginas que uno
administra.

### Lo que no hacemos: leer LinkedIn a través de un buscador

El [User Agreement de LinkedIn](https://www.linkedin.com/legal/user-agreement), §8.2, prohíbe "Copy,
use, display or distribute any information (including content) obtained from the Services, whether
directly or through third parties (such as search tools or data aggregators or brokers), without the
consent of the content owner". El equipo y 30X tienen cuenta en LinkedIn, así que leer sus posts a
través de Brave u otro buscador violaría esos términos, y el reto lo excluye. Esto corrige una
versión anterior de este documento.

La misma cláusula marca la salida: **con el consentimiento del dueño del contenido, o por una API
oficial de LinkedIn, sí se puede.**

### Vías legítimas (roadmap)

> **Decidido el 17/10:** LinkedIn, Instagram y TikTok no entran en el MVP, y la curación manual se
> descartó. Sus referentes entran por sus canales abiertos (punto 4). El resto queda como roadmap.

1. **"Un clic = señal" con la API de portabilidad (DMA). Requiere una prueba previa de 30 minutos.**
   Es self-serve para miembros del EEE y Suiza; David y Melkin están en España.
   - **Alta:** crear la app con la página "Member Data Portability (Member) Default Company", pedir
     el producto y generar el token con el scope `r_dma_portability_self_serve` en el OAuth Token
     Generator.
   - **Funcionamiento:** desde ese momento LinkedIn archiva las interacciones del curador (posts,
     comentarios y reacciones). `GET https://api.linkedin.com/rest/memberChangeLogs?q=memberAndApplication`,
     con la cabecera `Linkedin-Version: 202312`, las devuelve: 28 días como máximo, `count` ≤ 50, y
     una consulta por hora. Cuando el curador reacciona a un post que funciona, un colector lee el
     evento y guarda el URN del post como señal curada.
   - **Filtrado obligatorio (regla 1):** el changelog devuelve **toda** la actividad del curador,
     mensajes privados incluidos. El colector filtra por `resourceName` y solo procesa reacciones a
     posts; nunca guarda mensajes ni `processedActivity`, que trae contenido de terceros.
   - **Términos:** los [términos de portabilidad](https://www.linkedin.com/legal/l/portability-api-terms)
     permiten guardar los datos con el consentimiento del miembro, obligan a borrarlos si el miembro
     lo pide y no restringen el uso comercial.
   - **A validar en la prueba:** que el evento de una reacción incluya el URN del post (la doc dice
     que los comentarios traen el post original en `processedActivity`), y si "guardar post" también
     genera evento. Si lo genera, sería una curación privada.
   - **Límites:** las reacciones son públicas, y solo pueden usarlo curadores del EEE.
2. **Datos propios con consentimiento: los exports oficiales de analítica.** Pedir hoy a 30X el
   export de la analítica de su página de LinkedIn y, con su permiso, el del perfil de Andrés Bilbao
   (Creator analytics). Es la única fuente de métricas reales de LinkedIn, viene de su propia
   audiencia y los dueños consienten. Un job (`jobs/import_linkedin_export`) los carga como señales
   `observed`. Si llegan, son la mejor validación del audience fit.
3. **Embed oficial** para mostrar cualquiera de las anteriores: el
   ["Embed this post"](https://www.linkedin.com/help/linkedin/answer/a529065) de los posts públicos.
   El User Agreement (§3.1) contempla que otro miembro embeba un post. No funciona con posts de
   varias fotos ni con reposts con comentario.
4. **Los canales abiertos de los referentes (en el MVP):** muchos referentes de negocio e IA en LATAM publican lo
   mismo en newsletters con RSS, blogs o YouTube. Se dan de alta en `data/sources.yaml` con su
   `segment`.

### Después de la hackathon

- **Community Management API** (con revisión de LinkedIn): las métricas de las páginas de 30X, de
  forma automática.
- **DMA para terceros:** creadores del EEE que den su consentimiento pueden compartir sus datos con
  30X.
- **Premium Company Page:** la vista nativa de "trending competitor posts", para hasta 3
  competidores.

### Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Leer LinkedIn a través de Brave u otro buscador | User Agreement §8.2: usar contenido obtenido "through third parties (such as search tools)" sin consentimiento del dueño |
| Actores de Apify y "LinkedIn post scrapers" sin cookies | Scrapean LinkedIn (§8.2: "crawlers, browser plugins…") |
| Herramientas que buscan dentro de la sesión del usuario | Automatizan el acceso con la cuenta del usuario (§8.2) |
| Newsletters de LinkedIn recibidas por email y procesadas | Es contenido obtenido de LinkedIn, usado sin consentimiento del dueño |
| APIs que scrapean los resultados de Google | Dependen de violar los términos de Google |
| Google Custom Search JSON API | [Cerrada a clientes nuevos; se apaga el 1 de enero de 2027](https://brave.com/learn/google-api-shutdown/) |
| Bing Web Search API | Microsoft la retiró en 2025 |

## Instagram: Business Discovery (roadmap)

La
[Business Discovery API](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery)
oficial de Instagram devuelve, por nombre de usuario, los datos públicos de otras cuentas business o
creator: seguidores, publicaciones y, según conectores de terceros, likes y comentarios. Requiere
una cuenta business de Instagram vinculada a una página de Facebook y una app de Meta. Serviría para
@crece30x, @andresbilbao y otros referentes. Falta validar los campos disponibles y el acceso sin
revisión de la app.
