import { useSyncExternalStore } from 'react'
import { resolveRoute } from './routes'

function subscribe(onChange: () => void) {
  window.addEventListener('hashchange', onChange)
  return () => window.removeEventListener('hashchange', onChange)
}

export function useRoute() {
  return useSyncExternalStore(subscribe, () => resolveRoute(window.location.hash), () => resolveRoute(''))
}
