import { useEffect, useMemo, useState } from 'react'
import { fetchSourceEvents } from '../lib/api/sources'
import type { SourceEvent, SourceEventsResponse } from '../lib/types/sourceEvents'

const STALE_TIME_MS = 60_000

type UseSourceEventsParams = {
  symbol?: string | null
  since?: string
  limit?: number
}

type CacheEntry = {
  timestamp: number
  data: SourceEventsResponse
}

type UseSourceEventsResult = {
  data: SourceEventsResponse | null
  items: SourceEvent[]
  total: number
  isLoading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

const cache = new Map<string, CacheEntry>()

function buildCacheKey(params: UseSourceEventsParams): string {
  return JSON.stringify({
    symbol: params.symbol ?? null,
    since: params.since ?? null,
    limit: params.limit ?? 20,
  })
}

export function useSourceEvents(params: UseSourceEventsParams): UseSourceEventsResult {
  const symbol = params.symbol ?? null
  const since = params.since
  const limit = params.limit ?? 20
  const key = useMemo(() => buildCacheKey(params), [params.limit, params.since, params.symbol])
  const [data, setData] = useState<SourceEventsResponse | null>(() => {
    const cached = cache.get(key)
    if (!cached || Date.now() - cached.timestamp > STALE_TIME_MS) {
      return null
    }
    return cached.data
  })
  const [isLoading, setIsLoading] = useState(data === null)
  const [error, setError] = useState<Error | null>(null)
  const [refreshToken, setRefreshToken] = useState(0)

  useEffect(() => {
    const cached = cache.get(key)
    if (cached && Date.now() - cached.timestamp <= STALE_TIME_MS) {
      setData(cached.data)
      setError(null)
      setIsLoading(false)
      return
    }

    const controller = new AbortController()
    setIsLoading(true)
    setError(null)

    fetchSourceEvents({ symbol, since, limit }, controller.signal)
      .then((response) => {
        cache.set(key, { timestamp: Date.now(), data: response })
        setData(response)
      })
      .catch((err) => {
        if (controller.signal.aborted) {
          return
        }
        setError(err instanceof Error ? err : new Error('Failed to load source events'))
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      })

    return () => controller.abort()
  }, [key, limit, refreshToken, since, symbol])

  async function refetch() {
    cache.delete(key)
    setRefreshToken((value) => value + 1)
  }

  return {
    data,
    items: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    refetch,
  }
}
