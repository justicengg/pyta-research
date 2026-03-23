import { useEffect, useRef, useState } from 'react'
import type { SceneParams } from '../../lib/types/canvas'
import { useMarketSnapshot } from '../../hooks/useMarketSnapshot'

const MARKET_LABEL: Record<string, string> = {
  HK: '港股',
  US: '美股',
  A:  'A股',
}

type Props = {
  sceneParams: SceneParams
  onSceneParamsChange: (params: SceneParams) => void
}

function fmt(n: number | null, decimals = 2): string {
  if (n === null || n === undefined) return '—'
  return n.toFixed(decimals)
}

function fmtPrice(n: number | null, currency: string | null): string {
  if (n === null || n === undefined) return '—'
  const sym = currency === 'HKD' ? 'HK$' : currency === 'CNY' ? '¥' : '$'
  return `${sym}${n.toFixed(2)}`
}

export function CenterCoreCard({ sceneParams, onSceneParamsChange }: Props) {
  const [editing, setEditing] = useState(false)
  const [temp, setTemp] = useState<SceneParams>(sceneParams)
  const cardRef = useRef<HTMLDivElement>(null)

  // Only fetch when ticker is non-empty and not editing
  const shouldFetch = sceneParams.ticker.trim().length > 0
  const { snapshot, loading, error } = useMarketSnapshot(
    shouldFetch ? sceneParams.ticker : '',
    sceneParams.market,
  )

  // Sync temp when external sceneParams changes
  useEffect(() => { setTemp(sceneParams) }, [sceneParams])

  // Click-outside → save
  useEffect(() => {
    if (!editing) return
    function onMouseDown(e: MouseEvent) {
      if (cardRef.current && !cardRef.current.contains(e.target as Node)) {
        handleSave()
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [editing])

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); handleSave() }
    if (e.key === 'Escape') { handleCancel() }
  }

  function handleSave() {
    if (!temp.ticker.trim()) return
    onSceneParamsChange(temp)
    setEditing(false)
  }

  function handleCancel() {
    setTemp(sceneParams)
    setEditing(false)
  }

  if (editing) {
    return (
      <div ref={cardRef} className="center-core center-core--editing" data-no-pan>
        <p className="center-core-edit-hint">编辑场景参数</p>
        <input
          className="core-field-input"
          value={temp.ticker}
          onChange={(e) => setTemp({ ...temp, ticker: e.target.value })}
          onKeyDown={handleKeyDown}
          placeholder="标的代码，如 0700.HK"
          autoFocus
        />
        <select
          className="core-field-input"
          value={temp.market}
          onChange={(e) => setTemp({ ...temp, market: e.target.value })}
          onKeyDown={handleKeyDown}
        >
          <option value="HK">港股</option>
          <option value="US">美股</option>
          <option value="A">A股</option>
        </select>
        <select
          className="core-field-input"
          value={temp.timeHorizon}
          onChange={(e) => setTemp({ ...temp, timeHorizon: e.target.value })}
          onKeyDown={handleKeyDown}
        >
          <option value="1个月">1个月</option>
          <option value="3个月">3个月</option>
          <option value="6个月">6个月</option>
          <option value="1年">1年</option>
        </select>
        <p className="center-core-edit-hint center-core-edit-hint--kbd">
          Enter 保存 · Esc 取消
        </p>
      </div>
    )
  }

  const change1d = snapshot?.price.change_1d_pct ?? null
  const isUp = change1d !== null && change1d >= 0

  // Build stats tokens
  const statTokens: string[] = []
  if (snapshot?.fundamentals.pe_ttm !== null && snapshot?.fundamentals.pe_ttm !== undefined) {
    statTokens.push(`PE ${fmt(snapshot.fundamentals.pe_ttm)}x`)
  }
  if (snapshot?.fundamentals.market_cap_bn !== null && snapshot?.fundamentals.market_cap_bn !== undefined) {
    const cap = snapshot.fundamentals.market_cap_bn
    const capStr = cap >= 1000 ? `$${(cap / 1000).toFixed(1)}T` : `$${cap.toFixed(1)}B`
    statTokens.push(`市值 ${capStr}`)
  }
  if (snapshot?.fundamentals.revenue_ttm_bn !== null && snapshot?.fundamentals.revenue_ttm_bn !== undefined) {
    statTokens.push(`营收 $${fmt(snapshot.fundamentals.revenue_ttm_bn, 1)}B`)
  }

  return (
    <div
      ref={cardRef}
      className="center-core center-core--view"
      onClick={() => setEditing(true)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && setEditing(true)}
      data-no-pan
      title="点击编辑场景参数"
    >
      <h3>
        {sceneParams.ticker}
        <span className="core-market-tag">{MARKET_LABEL[sceneParams.market] ?? sceneParams.market}</span>
        <span className="core-edit-icon">✎</span>
      </h3>

      {/* Price row */}
      {loading ? (
        <div className="core-data-shimmer" />
      ) : error ? (
        <p className="core-data-error">数据暂不可用</p>
      ) : snapshot ? (
        <div className="core-price-row">
          <span className="core-price">{fmtPrice(snapshot.price.current, snapshot.currency)}</span>
          {change1d !== null && (
            <span className={`core-change ${isUp ? 'core-change--up' : 'core-change--down'}`}>
              {isUp ? '▲' : '▼'} {isUp ? '+' : ''}{fmt(change1d, 2)}%
            </span>
          )}
        </div>
      ) : null}

      {/* Stats row */}
      {loading ? (
        <div className="core-data-shimmer" style={{ width: '85%', marginBottom: 'var(--sp-1)' }} />
      ) : !error && statTokens.length > 0 ? (
        <div className="core-stats-row">
          {statTokens.map((tok, i) => (
            <span key={i} className="core-stat">{tok}</span>
          ))}
        </div>
      ) : null}

      <p>核心推演对象。所有 Agent 围绕这个核心对象提供反应、解释、修正和收敛。</p>
      <div className="center-tags">
        <span className="core-tag">核心场景</span>
        <span className="core-tag">{sceneParams.timeHorizon}</span>
        <span className="core-tag">持续推演</span>
      </div>
    </div>
  )
}
