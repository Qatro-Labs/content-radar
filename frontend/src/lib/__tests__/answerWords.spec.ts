import { describe, expect, it } from 'vitest'

import { countWords, leadingWords } from '../answerWords'

// Trozo real de una respuesta de Rad (18/10): párrafos separados por "\n\n".
const ANSWER = 'Evaluación de agentes.\n\nComo alternativa, coste.'

describe('answer words', () => {
  it('counts a paragraph break as a gap between words', () => {
    expect(countWords(ANSWER)).toBe(6)
  })

  it('keeps the paragraph break while revealing word by word', () => {
    expect(leadingWords(ANSWER, 4)).toBe('Evaluación de agentes.\n\nComo')
  })

  it('shows the whole text once every word is counted', () => {
    expect(leadingWords(ANSWER, countWords(ANSWER))).toBe(ANSWER)
  })
})
