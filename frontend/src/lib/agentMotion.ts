// Tiempos y medidas de Rad, el agente del Radar (DESIGN.md §7 «Agente» y el artboard E).
export const AGENT_TIMING = {
  // La presencia viaja hasta el objetivo y la acción se aplica al llegar.
  travelMs: 680,
  // El anillo de foco se desplaza con la presencia y se funde al pasar a una burbuja.
  ringMs: 600,
  ringFadeMs: 240,
  // Duración mínima de un paso; con movimiento reducido, más corta.
  stepMs: 1600,
  reducedStepMs: 700,
  wordMs: 45,
  // «Citadas», «Qué no sabemos» y los enlaces entran escalonados.
  endingStaggerMs: 80,
  // Lo que se espera a que aparezca un objetivo tras navegar (el expediente carga sus datos).
  anchorWaitMs: 3000,
  tapMs: 420,
} as const

// DESIGN.md §4: el anillo va separado 5 px de un control y 6 px de una sección, con el radio del
// objetivo más 6 px.
export const RING_GAP_PX = { control: 5, block: 6 } as const
export const RING_EXTRA_RADIUS_PX = 6

// Sobre una sección, la presencia se posa arriba a la derecha (como en el artboard E) para no
// tapar su contenido.
export const BLOCK_POINT_INSET = { right: 30, top: 28 } as const

// Más cerca que esto del borde derecho, el rótulo de la presencia va a la izquierda.
export const LABEL_FLIP_MARGIN_PX = 360
