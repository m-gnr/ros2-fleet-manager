import { useEffect, useState } from 'react'
import { z } from 'zod'
import { layoutResponse, warehouseLayoutSchema, type GridLayout } from './gridLayout'
import { staticWarehouse } from './warehouseProfile.generated'

const defaultProfile = warehouseLayoutSchema.parse(staticWarehouse.layout)
type Result = { session?: string; layout?: GridLayout; mismatch?: boolean; profileId: string; profileDigest: string }

export function resolveWarehouseProfile(current: Result, body: z.infer<typeof layoutResponse>, session: string): Result {
  const digest = body.profile_digest
  if (!digest) return current
  if (body.layout) {
    const layout = warehouseLayoutSchema.safeParse(body.layout)
    if (!layout.success) return current
    return { session, layout: layout.data, profileId: digest === staticWarehouse.profile_digest
      ? staticWarehouse.profile_id : `profile:${digest.slice(0, 12)}`, profileDigest: digest,
      mismatch: body.profile_mismatch }
  }
  if (digest === current.profileDigest) return { ...current, session, mismatch: body.profile_mismatch }
  return { session, profileId: `profile:${digest.slice(0, 12)}`, profileDigest: digest,
    mismatch: true }
}

export function useGridLayout(backendId?: string, sourceId?: string) {
  const [result, setResult] = useState<Result>(() => ({ layout: defaultProfile,
    profileId: staticWarehouse.profile_id, profileDigest: staticWarehouse.profile_digest }))
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
        setResult(current => resolveWarehouseProfile(current, body, session))
      })
      .catch(() => {
        // Keep the last validated profile when the API is unavailable.
      })
    return () => request.abort()
  }, [session, backendId, sourceId])

  return result
}
