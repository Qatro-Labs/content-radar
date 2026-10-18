// La respuesta de Rad aparece palabra a palabra (DESIGN.md §7). Quien la reproduce cuenta las
// palabras y quien la pinta corta el texto: los dos usan esta misma definición.
// Una palabra es un tramo entre blancos (espacios o saltos de línea).
const WORD_PATTERN = /\S+/g

export function countWords(text: string): number {
  return text.match(WORD_PATTERN)?.length ?? 0
}

// Corta el texto original tras la palabra `count` en lugar de unir palabras sueltas: así se
// conservan los saltos de línea de los párrafos.
export function leadingWords(text: string, count: number): string {
  const words = [...text.matchAll(WORD_PATTERN)]
  if (count >= words.length) return text
  const last = words[count - 1]
  if (last === undefined) return ''
  return text.slice(0, last.index + last[0].length)
}
