// Clases de «Tu marca» (boceto C y DESIGN.md §3–§4): tarjetas blancas de radio 20px sin borde ni
// sombra, etiquetas de 14px en peso 600 y controles con objetivo táctil ≥ 44px.
export const CARD_CLASS = 'flex flex-col gap-4 rounded-card bg-card p-5 sm:p-6'
export const LABEL_CLASS = 'text-sm font-semibold text-foreground'
export const FIELD_CLASS =
  'min-h-11 rounded-[10px] border-data-line bg-card px-3 py-2.5 text-[15px] shadow-none md:text-[15px]'
export const READ_VALUE_CLASS = 'text-[15px] leading-normal text-ink-read'

const CHIP_BASE =
  'inline-flex min-h-10 items-center rounded-full px-3.5 text-sm transition-colors duration-150 ease-out'
export const CHIP_CLASS = `${CHIP_BASE} border border-data-line bg-card font-medium text-foreground hover:border-foreground disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-data-line`
export const CHIP_ON_CLASS = `${CHIP_BASE} border border-foreground bg-primary font-semibold text-primary-foreground`
export const CHIP_READ_CLASS =
  'inline-flex min-h-8 items-center rounded-full bg-secondary px-3 text-sm font-medium text-foreground'

export const SELECT_CLASS =
  'min-h-11 min-w-0 flex-1 rounded-[10px] border border-data-line bg-card px-3 text-[15px] text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
