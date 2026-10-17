// Parser de Server-Sent Events para un stream que llega por `fetch` (D12 del plan fe-radar-agent):
// `EventSource` solo hace GET y el agente es un POST. Sigue el formato que emite FastAPI
// (`event: <nombre>\ndata: <json>\n\n`, keep-alive `: ping` cada 15 s).

export interface SseMessage {
  event: string
  data: string
}

export interface SseParser {
  push(chunk: string): void
  // Emite el mensaje pendiente si el stream se cerró sin línea vacía final.
  end(): void
}

// Sin `event:`, el evento se llama `message` (especificación de SSE).
const DEFAULT_EVENT = 'message'
const COMMENT_PREFIX = ':'
const FIELD_SEPARATOR = ':'
const EVENT_FIELD = 'event'
const DATA_FIELD = 'data'
const LINE_BREAK = /\r?\n/
// Varias líneas `data:` de un mismo mensaje forman un solo valor, separadas por saltos de línea.
const DATA_LINE_JOINER = '\n'

function splitField(line: string): { field: string; value: string } {
  const separator = line.indexOf(FIELD_SEPARATOR)
  if (separator === -1) return { field: line, value: '' }
  const value = line.slice(separator + 1)
  // Solo se quita el primer espacio tras los dos puntos: el resto es parte del valor.
  return { field: line.slice(0, separator), value: value.startsWith(' ') ? value.slice(1) : value }
}

export function createSseParser(onMessage: (message: SseMessage) => void): SseParser {
  let pendingLine = ''
  let event = DEFAULT_EVENT
  let dataLines: string[] = []

  function dispatch() {
    if (dataLines.length > 0) onMessage({ event, data: dataLines.join(DATA_LINE_JOINER) })
    event = DEFAULT_EVENT
    dataLines = []
  }

  function readLine(line: string) {
    if (line === '') return dispatch()
    if (line.startsWith(COMMENT_PREFIX)) return
    const { field, value } = splitField(line)
    if (field === EVENT_FIELD) event = value
    else if (field === DATA_FIELD) dataLines.push(value)
  }

  return {
    push(chunk) {
      // La última línea puede estar a medias (incluso un `\r` sin su `\n`): espera al siguiente
      // trozo.
      const lines = (pendingLine + chunk).split(LINE_BREAK)
      pendingLine = lines.pop() ?? ''
      lines.forEach(readLine)
    },
    end() {
      if (pendingLine !== '') readLine(pendingLine)
      pendingLine = ''
      dispatch()
    },
  }
}
