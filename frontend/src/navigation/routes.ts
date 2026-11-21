export type Route = 'home' | 'guide' | 'workspace'

export function resolveRoute(hash: string): Route {
  if (hash === '#/guide') return 'guide'
  if (hash === '#/workspace') return 'workspace'
  return 'home'
}
