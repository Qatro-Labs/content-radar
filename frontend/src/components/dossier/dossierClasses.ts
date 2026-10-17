// Clases que comparten las tarjetas del expediente (DESIGN.md §3 y §4): tarjeta blanca de radio
// 20px sin borde ni sombra, título Bricolage 22px y botones con objetivo táctil ≥ 44px.
export const CARD_CLASS = 'flex min-w-0 flex-col rounded-card bg-card p-6'
export const CARD_TITLE_CLASS =
  'font-display text-[22px] leading-tight font-semibold tracking-[-0.02em]'

const BUTTON_CLASS =
  'inline-flex min-h-11 items-center justify-center gap-1.5 rounded-xl px-4 text-[15px] font-semibold transition-[background-color,scale] duration-150 ease-out active:scale-[0.98]'
export const PRIMARY_BUTTON_CLASS = `${BUTTON_CLASS} bg-primary text-primary-foreground hover:bg-primary-hover`
export const SECONDARY_BUTTON_CLASS = `${BUTTON_CLASS} bg-secondary text-secondary-foreground hover:bg-secondary-hover`
// Sobre el lienzo el secundario va en blanco, como «Restablecer vista»: el gris de siempre casi
// no se distingue del fondo (DESIGN.md §4).
export const SECONDARY_ON_CANVAS_CLASS = `${BUTTON_CLASS} bg-card text-foreground hover:bg-secondary-hover`
