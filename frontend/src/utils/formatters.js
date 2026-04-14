export function buildWhyText(outfit) {
  const lines = []

  if (outfit.color_score >= 0.8)
    lines.push('🎨 Excellent color harmony')
  else if (outfit.color_score >= 0.6)
    lines.push('🎨 Good color combination')
  else
    lines.push('🎨 Neutral color pairing')

  const temp = outfit.temperature_used ?? outfit.temperature
  if (outfit.weather_score >= 0.8)
    lines.push(`🌡️ Perfect for ${temp}°C weather`)
  else if (outfit.weather_score >= 0.6)
    lines.push(`🌡️ Suitable for ${temp}°C weather`)
  else
    lines.push(`🌡️ May not be ideal for ${temp}°C`)

  if (outfit.model2_score >= 0.8)
    lines.push('✨ Highly compatible style pairing')
  else if (outfit.model2_score >= 0.6)
    lines.push('✨ Compatible style pairing')
  else
    lines.push('✨ Moderate style compatibility')

  if (outfit.cohesion_score != null) {
    if (outfit.cohesion_score >= 0.75)
      lines.push('🪡 Strong visual cohesion — items share a unified aesthetic')
    else if (outfit.cohesion_score >= 0.50)
      lines.push('🪡 Good visual cohesion')
    else
      lines.push('🪡 Diverse aesthetic mix')
  }

  if (outfit.synergy_score != null) {
    if (outfit.synergy_score >= 0.85)
      lines.push('🤝 Classic fashion pairing — these items belong together')
    else if (outfit.synergy_score >= 0.65)
      lines.push('🤝 Good outfit synergy')
    else if (outfit.synergy_score > 0.5)
      lines.push('🤝 Some style synergy detected')
  }

  return lines
}

export function scoreToPercent(score) {
  return Math.round((score ?? 0) * 100)
}

export function confidenceColor(level) {
  switch (level?.toLowerCase()) {
    case 'high':   return 'confidence-high'
    case 'medium': return 'confidence-medium'
    case 'low':    return 'confidence-low'
    default:       return 'confidence-medium'
  }
}

export function formatDate(isoString) {
  if (!isoString) return ''
  return new Date(isoString).toLocaleDateString('en-PK', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

export function getGreeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

export function pluralizeCategory(cat) {
  if (cat === 'shoes') return 'shoes'
  if (cat === 'dress') return 'dresses'
  return cat + 's'
}
