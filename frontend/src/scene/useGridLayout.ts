import { useEffect, useState } from 'react'
import { layoutResponse, type GridLayout } from './gridLayout'

type Result = { session: string; layout?: GridLayout; mismatch?: boolean }

export function useGridLayout(backendId?: string, sourceId?: string) {
  const [result, setResult] = useState<Result>()
  const session = backendId && sourceId ? backendId + '/' + sourceId : undefined

  useEffect(() => {
    if (!session) return
    const request = new AbortController()
    void fetch('/api/warehouse-layout', { signal: request.signal })
      .then(async response => {
        if (!response.ok || request.signal.aborted) return
        const parsed = layoutResponse.safeParse(await response.json())
        if (!parsed.success || request.signal.aborted) return
        const body = parsed.data
        if (body.backend_session_id !== backendId || body.source_session_id !== sourceId) return
        setResult({ session, layout: body.layout ?? undefined, mismatch: body.profile_mismatch })
      })
      .catch(() => {
        // Older dashboard backends and a lost API connection leave the legacy scene available.
      })
    return () => request.abort()
  }, [session, backendId, sourceId])

  return result?.session === session ? result : undefined
}
