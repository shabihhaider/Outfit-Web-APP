export function getWardrobeHealth(items = []) {
  const counts = { top: 0, bottom: 0, outwear: 0, shoes: 0, dress: 0, jumpsuit: 0 }
  items.forEach(item => {
    if (counts[item.category] !== undefined) counts[item.category]++
  })

  const gaps = []
  if (counts.top === 0 && counts.dress === 0 && counts.jumpsuit === 0)
    gaps.push('No tops, dresses or jumpsuits — cannot form any outfit')
  if (counts.bottom === 0 && counts.dress === 0 && counts.jumpsuit === 0)
    gaps.push('No bottoms, dresses or jumpsuits — cannot form any outfit')
  if (counts.shoes === 0)
    gaps.push('No shoes — outfit templates requiring shoes will be skipped')

  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  const canRecommend = gaps.length === 0 || total >= 2

  return { counts, gaps, canRecommend, total }
}
