/**
 * Build a descriptive alt text string for a wardrobe item image.
 *
 * Uses available metadata fields in priority order:
 *   sub_category (e.g. "polo_shirt") → formality (when not "both") → category
 *
 * Gracefully degrades when fields are absent (recommendation API items only
 * expose `category`; full wardrobe API items expose all three).
 *
 * Examples:
 *   { sub_category: 'polo_shirt', formality: 'casual', category: 'top' }
 *     → "polo shirt casual top"
 *   { sub_category: null, formality: 'formal', category: 'bottom' }
 *     → "formal bottom"
 *   { category: 'shoes' }
 *     → "shoes"
 */
export function wardrobeItemAlt(item) {
  const parts = [
    item.sub_category?.replace(/_/g, ' '),
    item.formality && item.formality !== 'both' ? item.formality : null,
    item.category,
  ].filter(Boolean)
  return parts.join(' ') || 'Wardrobe item'
}
