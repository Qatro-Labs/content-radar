// DESIGN.md §9: las fechas se escriben "17/10, 02:50 UTC".
const utcTimestamp = new Intl.DateTimeFormat('es-ES', {
  timeZone: 'UTC',
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

export function formatUtcTimestamp(iso: string): string {
  return `${utcTimestamp.format(new Date(iso))} UTC`
}

const utcDay = new Intl.DateTimeFormat('es-ES', {
  timeZone: 'UTC',
  day: '2-digit',
  month: '2-digit',
})

const utcTime = new Intl.DateTimeFormat('es-ES', {
  timeZone: 'UTC',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

// "07/10": fecha de publicación de una pieza o de un periodo del timeline.
export function formatUtcDay(iso: string): string {
  return utcDay.format(new Date(iso))
}

// "19:09": hora de corte de los periodos de 24 h del timeline.
export function formatUtcTime(iso: string): string {
  return utcTime.format(new Date(iso))
}
