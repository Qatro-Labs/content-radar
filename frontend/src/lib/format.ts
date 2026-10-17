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
