import { useCallback, useEffect, useRef, useState } from 'react'

export function useObjectUrl() {
  const [url, setUrl] = useState<string | null>(null)
  const currentUrl = useRef<string | null>(null)
  const setPreviewFile = useCallback((file: Blob | null) => {
    if (currentUrl.current) URL.revokeObjectURL(currentUrl.current)
    const next = file ? URL.createObjectURL(file) : null
    currentUrl.current = next
    setUrl(next)
  }, [])
  useEffect(() => () => {
    if (currentUrl.current) URL.revokeObjectURL(currentUrl.current)
    currentUrl.current = null
  }, [])
  return { url, setPreviewFile }
}
