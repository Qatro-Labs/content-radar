import type { components } from '@/types/api'

type Schemas = components['schemas']

// Textos de los tooltips: qué es cada cosa y cómo se usa, en palabras de quien decide qué
// publicar. Un solo módulo para que el vocabulario no se contradiga entre vistas.

export const RECOMMENDATION_HELP: Record<Schemas['Recommendation'], string> = {
  publish_now:
    'Encaja con la audiencia de 30X y conviene publicarlo esta semana. En algunos temas el crecimiento aún no está demostrado: lo dice su motivo.',
  find_angle:
    'Interesa, pero hace falta un enfoque propio antes de publicar: ya hay cobertura o el encaje es medio.',
  wait_for_case: 'Aún no hay un caso real o datos suficientes: mejor esperar.',
  discard: 'El tema está saturado: publicarlo ya no aporta.',
}

export const GROWTH_HELP: Record<Schemas['GrowthStatus'], string> = {
  observed: 'Observado: medido en dos ventanas de 3 días, la actual y la anterior.',
  estimated:
    'Estimado: la ventana anterior no tiene piezas, así que el crecimiento es una estimación.',
  preliminary: 'Preliminar: hay muy pocas piezas; tómalo como un indicio, no como una tendencia.',
}

export const HELP = {
  // Navegación y cabecera
  navRadar: 'Qué temas de IA conviene publicar esta semana, ordenados por oportunidad.',
  navExplore:
    'Todas las piezas de todos los temas, ordenadas por cuánto rinden frente a lo normal en su canal.',
  navCreate:
    'Prepara un brief para LinkedIn, Instagram, YouTube o una newsletter a partir de un tema.',
  search: 'Busca un tema, una pieza o una fuente por su nombre (atajo ⌘K).',
  period: 'Ventana de tiempo que se analiza. Los temas y sus cifras cambian según el periodo.',
  lastCollection: 'Última vez que se recogieron piezas de las fuentes monitoreadas.',

  // Radar
  counterPublishNow:
    'Temas que encajan con la audiencia de 30X y conviene publicar esta semana. En algunos el crecimiento aún no está demostrado. Pulsa para ver solo esos.',
  weekPublishNow:
    'Temas que encajan con la audiencia de 30X y conviene publicar esta semana. En algunos el crecimiento aún no está demostrado.',
  counterAccelerating:
    'Temas con más del 50 % de piezas nuevas que los 3 días anteriores, en 3 fuentes o más. Pulsa para ver solo esos.',
  counterEmerging:
    'Temas que empiezan a crecer, en pocas fuentes y con poco contenido parecido: la ocasión de llegar antes. Pulsa para ver solo esos.',
  radar:
    'Cada burbuja es un tema. Más arriba, más crece; más a la derecha, más encaja con 30X. El tamaño es la fuerza de la evidencia y el color, su etapa. Pulsa una burbuja para ver el tema al lado.',
  axisGrowth:
    'Crecimiento (0–100): cuántas piezas nuevas aparecen, si se aceleran y si alguna rinde muy por encima de lo normal.',
  axisFit:
    'Encaje con 30X (0–100): evaluación editorial de si el tema sirve a ejecutivos y equipos de Latinoamérica. No es una medición.',
  quadrantPriority: 'Crece y encaja con 30X: lo primero que hay que mirar.',
  quadrantGrowthOnly:
    'Crece, pero a la audiencia de 30X le interesa poco. Puede servir con otro ángulo.',
  quadrantFitOnly: 'Encaja con 30X, pero no está creciendo ahora.',
  quadrantWeak: 'Ni crece ni encaja: poca señal por ahora.',
  pulse: 'Las burbujas que laten están creciendo: cuanto más rápido laten, más aceleran.',
  ranking:
    'Todos los temas ordenados por oportunidad. Pulsa una fila para ver el tema en el panel de al lado.',
  colRank: 'Posición del tema en el ranking de oportunidad.',
  colTopic: 'Nombre del tema. El punto de color es su etapa: pasa el cursor para ver cuál.',
  colRecommendation:
    'Qué conviene hacer con el tema: publicar ya, buscar un ángulo propio, esperar un caso o descartarlo. Pasa el cursor por el chip para ver el motivo.',
  colBars:
    'Piezas nuevas cada 24 h durante 6 días: en gris los 3 días anteriores, en negro los últimos 3.',
  colAcceleration:
    'Cuánto más rápido aparecen piezas en los últimos 3 días que en los 3 anteriores, ajustado por el volumen de las fuentes. Debajo, las piezas nuevas de cada ventana. Si dice «Estimado» o «Preliminar», hay pocos datos.',
  colScore:
    'Oportunidad (0–100): combina crecimiento, encaje con 30X, número de fuentes, lo poco cubierto que está y lo fácil que es llevarlo a contenido.',
  outliers:
    'Un outlier es una pieza que rinde 3× o más que lo normal en su canal. Señala qué está funcionando, no por qué.',
  limits: 'Lo que los datos no permiten afirmar. Conviene leerlo antes de publicar.',
  backToWeek: 'Vuelve a «Esta semana» sin quitar los filtros.',
  openDossier: 'Abre el expediente completo: evolución, encaje con 30X y toda la evidencia.',
  generateBrief: 'Prepara un brief de contenido a partir de este tema y su evidencia.',
  rad: 'Rad, el agente del Radar: pregúntale en lenguaje natural y responde moviendo la página, con los mismos filtros que usas tú y citando la evidencia.',
  minimizeRad: 'Minimizar',
  resetView: 'Quita los filtros y los resaltados y vuelve a la vista de todos los temas.',

  // Explorar
  exploreFilter:
    'Filtra las piezas. «Outliers» muestra las que rinden 3× o más que lo normal; cada plataforma muestra solo sus piezas.',
  piecesSearch: 'Filtra la tabla por palabras del título o por el nombre de la fuente.',
  colPiece: 'Título de la pieza, su plataforma, la fuente y la fecha de publicación.',
  colPieceTopic: 'Tema del radar al que pertenece la pieza. El punto de color es su etapa.',
  colRatio:
    'Cuántas veces rinde la pieza frente a lo normal en su canal: 1× es lo normal y 3× o más es un outlier. En lima, los outliers.',
  whereItWorks: 'Los temas y las fuentes que acumulan más outliers.',

  // Expediente
  opportunityRing:
    'Oportunidad (0–100) y puesto en el ranking. «Cómo se calcula» abre el desglose al final de la página.',
  tileNewPieces: 'Piezas nuevas del tema en los últimos 3 días, frente a los 3 días anteriores.',
  tileAcceleration:
    'Cuánto más rápido aparecen piezas en los últimos 3 días que en los 3 anteriores, ajustado por el volumen de las fuentes.',
  tileFit: 'Encaje con 30X: evaluación editorial de seis criterios, no una medición.',
  tileSources:
    'Fuentes independientes en las que aparece el tema. Un medio o un canal cuenta una vez, y las republicaciones no suman.',
  whyItMatters:
    'Explicación redactada por IA a partir de la evidencia del tema. Es una lectura editorial, no una certeza.',
  evolution:
    'Piezas nuevas por día en la ventana actual (3 días) frente a la anterior. Sirve para ver si el tema acelera.',
  acceleration:
    'Cambio de ritmo frente a la ventana anterior, ajustado por el volumen de las fuentes: no es la resta directa de las barras.',
  fit: 'Seis criterios de 0 a 5 que evalúa la IA con la evidencia. Abre uno para ver la justificación y las piezas en que se apoya.',
  evidence:
    'Las piezas que forman el tema, outliers primero. Pulsa el título para abrir la pieza original.',
  audienceMix:
    'Qué tipo de fuentes impulsan el tema: tecnología, negocio o en español. Sirve para saber a quién le está llegando.',
  performance:
    'Frente a lo normal en su canal: 1× es lo normal y 3× o más es un outlier. La barra llega hasta 6×.',
  scoreBreakdown: 'Cada componente con su valor y el peso con que entra en la oportunidad.',

  // Crear
  briefPanel:
    'Elige plataforma, objetivo y formato, y genera un brief. Solo se usan opciones cerradas: ningún texto libre llega a la IA.',
  briefPlatform:
    'Dónde se publicará la pieza. Cambia el tono, la extensión y la estructura del brief.',
  briefGoal:
    'Qué se busca: educar explica el tema, conversación invita a opinar y captar leads lleva a un contacto.',
  briefFormat: 'Forma de la pieza: post, carrusel, vídeo corto, vídeo largo o artículo.',
  briefSources:
    'Las piezas de la evidencia que mejor rinden. El brief se escribe a partir de ellas y de los criterios de encaje.',
  copyBrief: 'Copia el brief completo, con sus fuentes, para pegarlo donde quieras.',
  copyLink: 'Copia un enlace que abre esta misma vista con las mismas opciones.',
} as const

export const SCORE_COMPONENT_HELP: Record<Schemas['ScoreComponentName'], string> = {
  momentum:
    'Crecimiento: piezas nuevas, aceleración y piezas que rinden muy por encima de lo normal.',
  audience_fit: 'Encaje con 30X: evaluación editorial de seis criterios, de 0 a 100.',
  cross_source: 'Fuentes: en cuántas fuentes independientes aparece el tema.',
  freshness: 'Poco cubierto todavía: cuanto menos contenido parecido hay, más alto.',
  actionability: 'Fácil de llevar a contenido: si el tema da para una pieza concreta y útil.',
}
