/**
 * LiveRegion — invisible aria-live container for screen reader announcements.
 * priority="polite"   — waits for silence before announcing (default, use for most updates)
 * priority="assertive" — interrupts immediately (use for critical errors only)
 */
export default function LiveRegion({ message, priority = 'polite' }) {
  return (
    <div
      role="status"
      aria-live={priority}
      aria-atomic="true"
      className="sr-only"
    >
      {message}
    </div>
  )
}
