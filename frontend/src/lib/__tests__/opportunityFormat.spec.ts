import { describe, expect, it } from 'vitest'

import {
  audienceReading,
  bubbleSize,
  formatAcceleration,
  formatFit,
  isDeclining,
  formatScore,
  latamGapLabel,
  pulsePeriodSeconds,
} from '../opportunityFormat'

describe('formatAcceleration', () => {
  it.each([
    {
      name: 'growth with an up arrow and a plus sign',
      acceleration: 0.86,
      expected: '↑ +86\u00a0%',
    },
    { name: 'decline with a down arrow and U+2212', acceleration: -0.3, expected: '↓ −30\u00a0%' },
    { name: 'flat when it rounds to 0 %', acceleration: 0.004, expected: '→ 0\u00a0%' },
  ])('writes $name', ({ acceleration, expected }) => {
    expect(formatAcceleration(acceleration)).toBe(expected)
  })
})

describe('formatScore', () => {
  it('says "no disponible" when the score is missing, never 0', () => {
    expect(formatScore(null)).toBe('no disponible')
  })

  it('rounds to a whole number', () => {
    expect(formatScore(74.2)).toBe('74')
  })
})

describe('formatFit', () => {
  it.each([
    { name: 'Alto from 67', fit: 67, expected: 'Alto · 67' },
    { name: 'Medio just below 67', fit: 66, expected: 'Medio · 66' },
    { name: 'Medio from 34', fit: 34, expected: 'Medio · 34' },
    { name: 'Bajo below 34', fit: 33, expected: 'Bajo · 33' },
    { name: 'the band of the number it shows', fit: 66.6, expected: 'Alto · 67' },
    { name: '"no disponible" without a fit', fit: null, expected: 'no disponible' },
  ])('writes $name', ({ fit, expected }) => {
    expect(formatFit(fit)).toBe(expected)
  })
})

describe('pulsePeriodSeconds', () => {
  it.each([
    { name: '1.4 s from +100 %', lifecycle: 'accelerating', acceleration: 1.0, expected: 1.4 },
    { name: '2.0 s from +50 %', lifecycle: 'accelerating', acceleration: 0.5, expected: 2.0 },
    { name: '2.8 s just above +20 %', lifecycle: 'emerging', acceleration: 0.21, expected: 2.8 },
    { name: '3.6 s at exactly +20 %', lifecycle: 'emerging', acceleration: 0.2, expected: 3.6 },
    { name: '3.6 s for any growth', lifecycle: 'peaking', acceleration: 0.01, expected: 3.6 },
    { name: 'no pulse without growth', lifecycle: 'peaking', acceleration: 0, expected: null },
    { name: 'no pulse when shrinking', lifecycle: 'saturated', acceleration: -0.3, expected: null },
    { name: 'no pulse without a stage', lifecycle: 'unknown', acceleration: 1.0, expected: null },
  ] as const)('gives $name', ({ lifecycle, acceleration, expected }) => {
    expect(pulsePeriodSeconds(lifecycle, acceleration)).toBe(expected)
  })
})

describe('bubbleSize', () => {
  it.each([
    { name: '43 px for strength 74 (18 + 0.34 · 74 = 43.16)', strength: 74, expected: 43 },
    { name: 'the 18 px floor for strength 0', strength: 0, expected: 18 },
  ])('gives $name', ({ strength, expected }) => {
    expect(bubbleSize(strength)).toBe(expected)
  })
})

describe('audienceReading', () => {
  const TRANSLATE_TO_BUSINESS =
    'Mucho tech y poco negocio: todavía no llegó a ejecutivos. Hay que traducirlo a negocio.'
  const LATAM_GAP =
    'Ya lo empujan fuentes de negocio y casi no hay evidencia de fuentes latinoamericanas.'
  const LATAM_COVERED = 'Ya hay cobertura en fuentes latinoamericanas: conviene buscar otro ángulo.'
  const NO_READING = 'Con estos datos no hay una lectura clara de audiencia.'

  it.each([
    {
      name: 'tech-heavy with a high fit, before the LATAM gap',
      mix: { tech: 0.7, business: 0.2, latam_es: 0.1 },
      fit: 82,
      gap: true,
      expected: TRANSLATE_TO_BUSINESS,
    },
    {
      name: 'a LATAM gap',
      mix: { tech: 0.55, business: 0.4, latam_es: 0.05 },
      fit: 82,
      gap: true,
      expected: LATAM_GAP,
    },
    {
      name: 'LATAM already covered',
      mix: { tech: 0.3, business: 0.25, latam_es: 0.45 },
      fit: 75,
      gap: false,
      expected: LATAM_COVERED,
    },
    {
      name: 'no clear reading when the fit is below 60 and the gap is unknown',
      mix: { tech: 0.85, business: 0.15, latam_es: 0 },
      fit: 58,
      gap: null,
      expected: NO_READING,
    },
    {
      name: 'no clear reading at tech 0.6 · business 0.3 (business is not below 0.3)',
      mix: { tech: 0.6, business: 0.3, latam_es: 0.1 },
      fit: 80,
      gap: null,
      expected: NO_READING,
    },
    {
      name: 'no clear reading when the fit is missing',
      mix: { tech: 0.8, business: 0.1, latam_es: 0.1 },
      fit: null,
      gap: null,
      expected: NO_READING,
    },
  ])('reads $name', ({ mix, fit, gap, expected }) => {
    expect(audienceReading({ audience_mix: mix, audience_fit_score: fit, latam_gap: gap })).toBe(
      expected,
    )
  })
})

describe('latamGapLabel', () => {
  it.each([
    { name: 'a gap', gap: true, expected: 'hueco en LATAM' },
    { name: 'coverage', gap: false, expected: 'ya cubierto en LATAM' },
    { name: 'a missing decision', gap: null, expected: 'hueco en LATAM no disponible' },
  ])('labels $name', ({ gap, expected }) => {
    expect(latamGapLabel(gap)).toBe(expected)
  })
})

describe('isDeclining', () => {
  it.each([
    { name: 'a fall shown as a negative percent', acceleration: -0.3, expected: true },
    { name: 'a fall that rounds to 0 %', acceleration: -0.004, expected: false },
    { name: 'growth', acceleration: 0.86, expected: false },
  ])('is $expected for $name', ({ acceleration, expected }) => {
    expect(isDeclining(acceleration)).toBe(expected)
  })
})
