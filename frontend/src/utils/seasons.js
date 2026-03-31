/**
 * Detects which fashion season is currently active based on the calendar date.
 * Entirely client-side — no API calls needed.
 */

const SEASONS = [
  {
    key:    'eid_fitr',
    start:  [3, 15],
    end:    [4, 20],
    label:  'Eid ul-Fitr',
    vibe:   'mehndi-festive',
    emoji:  '🌙',
    daysWarning: [30, 14, 7, 3, 1],
  },
  {
    key:    'eid_adha',
    start:  [5, 20],
    end:    [6, 25],
    label:  'Eid ul-Adha',
    vibe:   'desi-formal',
    emoji:  '🐑',
    daysWarning: [30, 14, 7, 3, 1],
  },
  {
    key:    'lawn',
    start:  [3, 1],
    end:    [7, 31],
    label:  'Lawn Season',
    vibe:   'lawn-chic',
    emoji:  '🌿',
    daysWarning: [],
  },
  {
    key:    'wedding',
    start:  [10, 1],
    end:    [12, 31],
    label:  'Wedding Season',
    vibe:   'desi-formal',
    emoji:  '💍',
    daysWarning: [],
  },
]

/**
 * Returns the currently active season object, or null if none.
 * @param {Date} date
 */
export function getActiveSeason(date = new Date()) {
  const m = date.getMonth() + 1  // 1-based
  const d = date.getDate()
  for (const s of SEASONS) {
    const [sm, sd] = s.start
    const [em, ed] = s.end
    const after  = m > sm || (m === sm && d >= sd)
    const before = m < em || (m === em && d <= ed)
    if (after && before) return s
  }
  return null
}

/**
 * Returns upcoming seasons within the next `withinDays` days.
 * @param {number} withinDays
 * @param {Date} date
 */
export function getUpcomingSeasons(withinDays = 30, date = new Date()) {
  const m = date.getMonth() + 1
  const d = date.getDate()
  const upcoming = []
  for (const s of SEASONS) {
    const [sm, sd] = s.start
    // Days until season start (rough, same-year)
    const startDate = new Date(date.getFullYear(), sm - 1, sd)
    const diffMs    = startDate - date
    const diffDays  = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
    if (diffDays > 0 && diffDays <= withinDays) {
      upcoming.push({ ...s, daysUntil: diffDays })
    }
  }
  return upcoming
}
