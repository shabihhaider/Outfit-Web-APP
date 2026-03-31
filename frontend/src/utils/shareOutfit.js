const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + r)
  ctx.lineTo(x + w, y + h - r)
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
  ctx.lineTo(x + r, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - r)
  ctx.lineTo(x, y + r)
  ctx.quadraticCurveTo(x, y, x + r, y)
  ctx.closePath()
}

export async function generateOutfitImage(outfit, items) {
  const canvas = document.createElement('canvas')
  canvas.width = 800
  canvas.height = 500
  const ctx = canvas.getContext('2d')

  // Background
  ctx.fillStyle = '#fafaf8'
  ctx.fillRect(0, 0, 800, 500)

  // Header bar
  ctx.fillStyle = '#1c1917'
  ctx.fillRect(0, 0, 800, 60)
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 22px Outfit, system-ui, sans-serif'
  ctx.fillText('OutfitAI', 24, 40)

  // Occasion + score
  const pct = Math.round((outfit.final_score ?? 0) * 100)
  const occasion = outfit.occasion || 'outfit'
  ctx.fillStyle = '#fbbf24'
  ctx.font = '16px Outfit, system-ui, sans-serif'
  ctx.textAlign = 'right'
  ctx.fillText(`${occasion.charAt(0).toUpperCase() + occasion.slice(1)}  |  ${pct}% compatible`, 776, 40)
  ctx.textAlign = 'left'

  // Confidence badge
  const badgeColors = { high: '#059669', medium: '#d97706', low: '#dc2626' }
  const conf = outfit.confidence || 'medium'
  ctx.fillStyle = badgeColors[conf] || '#6b7280'
  roundRect(ctx, 24, 76, 80, 26, 13)
  ctx.fill()
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 12px Outfit, system-ui, sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText(conf.toUpperCase(), 64, 93)
  ctx.textAlign = 'left'

  ctx.fillStyle = '#78716c'
  ctx.font = '14px Outfit, system-ui, sans-serif'
  ctx.fillText(`${pct}% compatible`, 116, 93)

  // Item images
  const imageSize = 140
  const gap = 16
  const totalWidth = items.length * (imageSize + gap) - gap
  const startX = Math.max(24, (800 - totalWidth) / 2)
  const startY = 120

  for (let i = 0; i < items.length; i++) {
    const x = startX + i * (imageSize + gap)

    // Image background
    ctx.fillStyle = '#f5f5f0'
    roundRect(ctx, x, startY, imageSize, imageSize, 12)
    ctx.fill()
    ctx.strokeStyle = '#e7e5e0'
    ctx.lineWidth = 1
    ctx.stroke()

    // Load image
    const imgUrl = items[i].image_url
    if (imgUrl) {
      try {
        const img = new Image()
        img.crossOrigin = 'anonymous'
        await new Promise((resolve, reject) => {
          img.onload = resolve
          img.onerror = reject
          img.src = `${API_URL}${imgUrl}`
        })
        ctx.save()
        roundRect(ctx, x, startY, imageSize, imageSize, 12)
        ctx.clip()
        ctx.drawImage(img, x, startY, imageSize, imageSize)
        ctx.restore()
      } catch {
        // Fallback: show category text
        ctx.fillStyle = '#a8a29e'
        ctx.font = '32px sans-serif'
        ctx.textAlign = 'center'
        ctx.fillText(items[i].category || '?', x + imageSize / 2, startY + imageSize / 2 + 10)
        ctx.textAlign = 'left'
      }
    }

    // Category label
    ctx.fillStyle = '#57534e'
    ctx.font = '12px Outfit, system-ui, sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText((items[i].category || '').charAt(0).toUpperCase() + (items[i].category || '').slice(1), x + imageSize / 2, startY + imageSize + 18)
    ctx.textAlign = 'left'
  }

  // Score breakdown bar
  const barY = 340
  const breakdown = outfit.breakdown || {}
  const scores = [
    { label: 'Model', value: breakdown.model2_score ?? outfit.model2_score, color: '#1c1917' },
    { label: 'Color', value: breakdown.color_score ?? outfit.color_score, color: '#d97706' },
    { label: 'Weather', value: breakdown.weather_score ?? outfit.weather_score, color: '#059669' },
  ]

  ctx.fillStyle = '#a8a29e'
  ctx.font = '12px Outfit, system-ui, sans-serif'
  ctx.fillText('Score Breakdown', 24, barY)

  scores.forEach((s, i) => {
    const bx = 24 + i * 255
    const by = barY + 12
    const bw = 230
    const val = Math.round((s.value ?? 0) * 100)

    ctx.fillStyle = '#e7e5e0'
    roundRect(ctx, bx, by, bw, 8, 4)
    ctx.fill()

    ctx.fillStyle = s.color
    roundRect(ctx, bx, by, bw * (s.value ?? 0), 8, 4)
    ctx.fill()

    ctx.fillStyle = '#57534e'
    ctx.font = '11px Outfit, system-ui, sans-serif'
    ctx.fillText(`${s.label}: ${val}%`, bx, by + 24)
  })

  // Footer
  ctx.fillStyle = '#d4d0c8'
  ctx.font = '11px Outfit, system-ui, sans-serif'
  ctx.fillText('Built with OutfitAI — Smart Wardrobe Recommender', 24, 475)

  return canvas.toDataURL('image/png')
}

export async function shareOrDownload(outfit, items) {
  const dataUrl = await generateOutfitImage(outfit, items)

  if (navigator.share && navigator.canShare) {
    try {
      const blob = await (await fetch(dataUrl)).blob()
      const file = new File([blob], 'outfit.png', { type: 'image/png' })
      if (navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: 'My Outfit — OutfitAI' })
        return
      }
    } catch {}
  }

  // Desktop fallback: download
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = `outfit-${Date.now()}.png`
  a.click()
}
