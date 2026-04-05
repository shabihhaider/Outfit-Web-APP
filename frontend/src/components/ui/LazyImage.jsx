import { useState } from 'react'

export default function LazyImage({ src, alt, className = '', fallback, ...props }) {
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)

  if (error && fallback) return fallback

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      onLoad={() => setLoaded(true)}
      onError={() => setError(true)}
      className={`transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'} ${className}`}
      {...props}
    />
  )
}
