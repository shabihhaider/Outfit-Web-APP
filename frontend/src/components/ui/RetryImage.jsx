import { useEffect, useRef, useState } from 'react'

function withRetryToken(url, attempt) {
  if (!url || attempt <= 0) return url
  const divider = url.includes('?') ? '&' : '?'
  return `${url}${divider}retry=${attempt}`
}

export default function RetryImage({
  src,
  alt,
  className = '',
  maxRetries = 2,
  retryDelayMs = 350,
  fallback = null,
  ...imgProps
}) {
  const [attempt, setAttempt] = useState(0)
  const [failed, setFailed] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => {
    setAttempt(0)
    setFailed(false)
  }, [src])

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [])

  if (!src || failed) {
    return fallback
  }

  const resolvedSrc = withRetryToken(src, attempt)

  function handleError() {
    if (attempt >= maxRetries) {
      setFailed(true)
      return
    }

    const nextAttempt = attempt + 1
    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }

    timerRef.current = setTimeout(() => {
      setAttempt(nextAttempt)
    }, retryDelayMs * nextAttempt)
  }

  return (
    <img
      src={resolvedSrc}
      alt={alt}
      className={className}
      onError={handleError}
      {...imgProps}
    />
  )
}
