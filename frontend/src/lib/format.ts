// DESIGN.md §9: las fechas se escriben "17/10, 02:50 UTC". Se montan a mano con los getters UTC
// porque ICU 78 (Node 24, Chrome reciente) ignora `day: '2-digit'` en es-ES y escribe "7/10".
const PAD_LENGTH = 2

function pad(value: number): string {
  return String(value).padStart(PAD_LENGTH, '0')
}

// "07/10": fecha de publicación de una pieza o de un periodo del timeline.
export function formatUtcDay(iso: string): string {
  const date = new Date(iso)
  return `${pad(date.getUTCDate())}/${pad(date.getUTCMonth() + 1)}`
}

// "19:09": hora de corte de los periodos de 24 h del timeline.
export function formatUtcTime(iso: string): string {
  const date = new Date(iso)
  return `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`
}

export function formatUtcTimestamp(iso: string): string {
  return `${formatUtcDay(iso)}, ${formatUtcTime(iso)} UTC`
}
