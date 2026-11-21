export function safeOfficialUrl(value?: string | null): string | null {
  if (!value) return null
  try {
    const url = new URL(value)
    if (url.protocol !== 'https:' || !url.hostname.endsWith('.go.kr') || url.username || url.password || url.port && url.port !== '443') return null
    return url.href
  } catch { return null }
}
