import { useEffect, useState } from 'react'

export type MarketSnapshot = {
  symbol: string
  name: string | null
  sector: string | null
  currency: string | null
  price: {
    current: number | null
    change_1d_pct: number | null
    change_5d_pct: number | null
    high_52w: number | null
    low_52w: number | null
    volume: number | null
  }
  fundamentals: {
    market_cap_bn: number | null
    pe_ttm: number | null
    pe_forward: number | null
    revenue_ttm_bn: number | null
    revenue_growth_pct: number | null
    gross_margin_pct: number | null
  }
  source: string
  data_as_of: string
}

type State = {
  snapshot: MarketSnapshot | null
  loading: boolean
  error: string | null
}

// Normalize raw API response → MarketSnapshot (handles field name differences)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalize(raw: any): MarketSnapshot {
  const p = raw.price ?? {}
  const f = raw.fundamentals ?? {}
  return {
    symbol:   raw.symbol ?? '',
    name:     raw.name ?? null,
    sector:   raw.sector ?? null,
    currency: raw.currency ?? null,
    price: {
      current:       p.current       ?? null,
      change_1d_pct: p.change_1d_pct ?? null,
      change_5d_pct: p.change_5d_pct ?? null,
      high_52w:      p.high_52w      ?? null,
      low_52w:       p.low_52w       ?? null,
      volume:        p.volume        ?? null,
    },
    fundamentals: {
      // API returns raw values; convert to display-friendly units
      market_cap_bn:    f.market_cap    != null ? f.market_cap / 1e9    : null,
      pe_ttm:           f.pe_ratio      ?? f.pe_ttm       ?? null,
      pe_forward:       f.forward_pe    ?? f.pe_forward   ?? null,
      revenue_ttm_bn:   f.revenue_ttm   != null ? f.revenue_ttm / 1e9  : null,
      revenue_growth_pct: f.revenue_growth != null ? f.revenue_growth * 100 : null,
      gross_margin_pct:   f.gross_margin  != null ? f.gross_margin  * 100 : null,
    },
    source:     raw.source      ?? 'unknown',
    data_as_of: raw.fetched_at  ?? raw.data_as_of ?? '',
  }
}

export function useMarketSnapshot(ticker: string, market: string): State {
  const [state, setState] = useState<State>({ snapshot: null, loading: false, error: null })

  useEffect(() => {
    const t = ticker.trim()
    if (!t) {
      setState({ snapshot: null, loading: false, error: null })
      return
    }
    setState({ snapshot: null, loading: true, error: null })
    const controller = new AbortController()

    fetch(`/api/v1/market/snapshot/${encodeURIComponent(t)}?market=${market}`, {
      signal: controller.signal,
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((raw) => setState({ snapshot: normalize(raw), loading: false, error: null }))
      .catch((err) => {
        if (err.name === 'AbortError') return
        setState({ snapshot: null, loading: false, error: String(err.message) })
      })

    return () => controller.abort()
  }, [ticker, market])

  return state
}
