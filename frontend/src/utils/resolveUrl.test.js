import { describe, it, expect, beforeEach, vi } from 'vitest'

// resolveUrl reads import.meta.env and localStorage — stub them before import
beforeEach(() => {
  vi.stubGlobal('localStorage', {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
  })
})

// Dynamic import so stubs are in place before module evaluates
async function getResolveUrl() {
  vi.resetModules()
  const mod = await import('./resolveUrl.js')
  return mod.resolveUrl
}

describe('resolveUrl', () => {
  it('returns null for null input', async () => {
    const resolveUrl = await getResolveUrl()
    expect(resolveUrl(null)).toBeNull()
  })

  it('returns null for undefined input', async () => {
    const resolveUrl = await getResolveUrl()
    expect(resolveUrl(undefined)).toBeNull()
  })

  it('returns null for empty string', async () => {
    const resolveUrl = await getResolveUrl()
    expect(resolveUrl('')).toBeNull()
  })

  it('returns absolute http URL unchanged', async () => {
    const resolveUrl = await getResolveUrl()
    const url = 'http://cdn.example.com/img.jpg'
    expect(resolveUrl(url)).toBe(url)
  })

  it('returns absolute https URL unchanged', async () => {
    const resolveUrl = await getResolveUrl()
    const url = 'https://cdn.example.com/img.jpg'
    expect(resolveUrl(url)).toBe(url)
  })

  it('prepends API_URL to relative path when no token', async () => {
    const resolveUrl = await getResolveUrl()
    const result = resolveUrl('/uploads/abc.jpg')
    // No token → no ?token= appended; result ends with the relative path
    expect(result).toMatch(/\/uploads\/abc\.jpg$/)
    expect(result).not.toContain('token=')
  })

  it('appends token query param for relative path when token exists', async () => {
    localStorage.getItem = vi.fn(() => 'mytoken123')
    const resolveUrl = await getResolveUrl()
    const result = resolveUrl('/uploads/abc.jpg')
    expect(result).toContain('token=mytoken123')
    expect(result).toContain('/uploads/abc.jpg')
  })

  it('uses & separator when URL already has query params', async () => {
    localStorage.getItem = vi.fn(() => 'tok')
    const resolveUrl = await getResolveUrl()
    const result = resolveUrl('/uploads/abc.jpg?size=lg')
    expect(result).toContain('&token=tok')
  })
})
