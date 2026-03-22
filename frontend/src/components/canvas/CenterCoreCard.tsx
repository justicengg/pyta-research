import { useEffect, useRef, useState } from 'react'
import type { SceneParams } from '../../lib/types/canvas'

const MARKET_LABEL: Record<string, string> = {
  HK: '港股',
  US: '美股',
  A:  'A股',
}

type Props = {
  sceneParams: SceneParams
  onSceneParamsChange: (params: SceneParams) => void
}

export function CenterCoreCard({ sceneParams, onSceneParamsChange }: Props) {
  const [editing, setEditing] = useState(false)
  const [temp, setTemp] = useState<SceneParams>(sceneParams)
  const cardRef = useRef<HTMLDivElement>(null)

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
  })

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
      <p>核心推演对象。所有 Agent 围绕这个核心对象提供反应、解释、修正和收敛。</p>
      <div className="center-tags">
        <span className="core-tag">核心场景</span>
        <span className="core-tag">{sceneParams.timeHorizon}</span>
        <span className="core-tag">持续推演</span>
      </div>
    </div>
  )
}
