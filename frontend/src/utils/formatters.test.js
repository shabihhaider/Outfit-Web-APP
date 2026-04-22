import { describe, it, expect } from 'vitest'
import {
  pluralizeCategory,
  scoreToPercent,
  scoreToLabel,
  formatDate,
} from './formatters.js'

describe('pluralizeCategory', () => {
  it('returns "shoes" for shoes (not "shoess")', () => {
    expect(pluralizeCategory('shoes')).toBe('shoes')
  })
  it('returns "dresses" for dress', () => {
    expect(pluralizeCategory('dress')).toBe('dresses')
  })
  it('returns "tops" for top', () => {
    expect(pluralizeCategory('top')).toBe('tops')
  })
  it('returns "bottoms" for bottom', () => {
    expect(pluralizeCategory('bottom')).toBe('bottoms')
  })
  it('returns "outwears" for outwear', () => {
    expect(pluralizeCategory('outwear')).toBe('outwears')
  })
  it('returns "jumpsuits" for jumpsuit', () => {
    expect(pluralizeCategory('jumpsuit')).toBe('jumpsuits')
  })
})

describe('scoreToPercent', () => {
  it('converts 0.72 to 72', () => {
    expect(scoreToPercent(0.72)).toBe(72)
  })
  it('rounds 0.725 to 73', () => {
    expect(scoreToPercent(0.725)).toBe(73)
  })
  it('treats null as 0', () => {
    expect(scoreToPercent(null)).toBe(0)
  })
  it('treats undefined as 0', () => {
    expect(scoreToPercent(undefined)).toBe(0)
  })
  it('converts 1.0 to 100', () => {
    expect(scoreToPercent(1.0)).toBe(100)
  })
  it('converts 0 to 0', () => {
    expect(scoreToPercent(0)).toBe(0)
  })
})

describe('scoreToLabel', () => {
  it('returns "Perfect Match" for score >= 0.90', () => {
    expect(scoreToLabel(0.95)).toBe('Perfect Match')
    expect(scoreToLabel(0.90)).toBe('Perfect Match')
  })
  it('returns "Strong Match" for 0.80–0.89', () => {
    expect(scoreToLabel(0.85)).toBe('Strong Match')
    expect(scoreToLabel(0.80)).toBe('Strong Match')
  })
  it('returns "Good Match" for 0.70–0.79', () => {
    expect(scoreToLabel(0.75)).toBe('Good Match')
  })
  it('returns "Fair Match" for 0.60–0.69', () => {
    expect(scoreToLabel(0.65)).toBe('Fair Match')
  })
  it('returns "Weak Match" for score < 0.60', () => {
    expect(scoreToLabel(0.50)).toBe('Weak Match')
    expect(scoreToLabel(0)).toBe('Weak Match')
  })
})

describe('formatDate', () => {
  it('returns empty string for null', () => {
    expect(formatDate(null)).toBe('')
  })
  it('returns empty string for undefined', () => {
    expect(formatDate(undefined)).toBe('')
  })
  it('returns a non-empty string for a valid ISO date', () => {
    const result = formatDate('2024-03-15T10:00:00Z')
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
  })
})
