import { describe, it, expect } from 'vitest'
import { getWardrobeHealth } from './wardrobeHealth.js'

describe('getWardrobeHealth', () => {
  it('returns zero counts for empty wardrobe', () => {
    const { counts, total } = getWardrobeHealth([])
    expect(total).toBe(0)
    expect(counts.top).toBe(0)
    expect(counts.shoes).toBe(0)
  })

  it('counts items by category correctly', () => {
    const items = [
      { category: 'top' },
      { category: 'top' },
      { category: 'bottom' },
      { category: 'shoes' },
    ]
    const { counts, total } = getWardrobeHealth(items)
    expect(counts.top).toBe(2)
    expect(counts.bottom).toBe(1)
    expect(counts.shoes).toBe(1)
    expect(total).toBe(4)
  })

  it('ignores unknown categories', () => {
    const items = [{ category: 'unknown_type' }, { category: 'top' }]
    const { counts, total } = getWardrobeHealth(items)
    expect(total).toBe(1)
    expect(counts.top).toBe(1)
  })

  it('flags missing top/dress/jumpsuit gap', () => {
    const items = [{ category: 'bottom' }, { category: 'shoes' }]
    const { gaps } = getWardrobeHealth(items)
    expect(gaps.some(g => /top|dress|jumpsuit/i.test(g))).toBe(true)
  })

  it('flags missing bottom/dress/jumpsuit gap', () => {
    const items = [{ category: 'top' }, { category: 'shoes' }]
    const { gaps } = getWardrobeHealth(items)
    expect(gaps.some(g => /bottom|dress|jumpsuit/i.test(g))).toBe(true)
  })

  it('flags missing shoes gap', () => {
    const items = [{ category: 'top' }, { category: 'bottom' }]
    const { gaps } = getWardrobeHealth(items)
    expect(gaps.some(g => /shoe/i.test(g))).toBe(true)
  })

  it('has no gaps for a complete wardrobe', () => {
    const items = [
      { category: 'top' },
      { category: 'bottom' },
      { category: 'shoes' },
    ]
    const { gaps, canRecommend } = getWardrobeHealth(items)
    expect(gaps).toHaveLength(0)
    expect(canRecommend).toBe(true)
  })

  it('dress satisfies both top and bottom gap', () => {
    const items = [{ category: 'dress' }, { category: 'shoes' }]
    const { gaps } = getWardrobeHealth(items)
    expect(gaps).toHaveLength(0)
  })

  it('canRecommend is true when total >= 2 even with gaps', () => {
    const items = [{ category: 'top' }, { category: 'top' }]
    const { canRecommend } = getWardrobeHealth(items)
    expect(canRecommend).toBe(true)
  })

  it('canRecommend is false for single item with gaps', () => {
    const items = [{ category: 'top' }]
    const { canRecommend } = getWardrobeHealth(items)
    expect(canRecommend).toBe(false)
  })
})
