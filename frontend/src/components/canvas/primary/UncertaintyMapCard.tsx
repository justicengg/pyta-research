import type { UncertaintyMapData } from '../../../lib/types/primaryCanvas'
import { DIMENSION_LABELS } from '../../../lib/types/primaryCanvas'

type Props = {
  data: UncertaintyMapData
  position: { x: number; y: number }
  onDragMove: (dx: number, dy: number) => void
}

const SCORE_LABEL: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
}

const MARKET_TYPE_LABEL: Record<string, string> = {
  new_market: '全新市场',
  red_ocean:  '红海',
  blue_ocean: '蓝海',
}

export function UncertaintyMapCard({ data, position, onDragMove }: Props) {
  const dragRef = { active: false, lastX: 0, lastY: 0 }

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return
    const target = e.target as HTMLElement
    if (target.closest('button, input, textarea, select, a')) return
    e.stopPropagation()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragRef.active = true
    dragRef.lastX = e.clientX
    dragRef.lastY = e.clientY
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragRef.active) return
    const dx = e.clientX - dragRef.lastX
    const dy = e.clientY - dragRef.lastY
    dragRef.lastX = e.clientX
    dragRef.lastY = e.clientY
    onDragMove(dx, dy)
  }

  function handlePointerUp() {
    dragRef.active = false
  }

  return (
    <div
      className="pm-card pm-card--uncertainty"
      style={{ left: position.x, top: position.y }}
      data-no-pan
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <div className="pm-card__header">
        <span className="pm-card__label">模块 1</span>
        <h3 className="pm-card__title">不确定性地图</h3>
        <span className="pm-card__meta">{MARKET_TYPE_LABEL[data.marketType] ?? data.marketType}</span>
      </div>

      <div className="pm-card__body">
        {(Object.entries(DIMENSION_LABELS) as [string, string][]).map(([dim, label]) => {
          const assessment = data.assessments[dim as keyof typeof data.assessments]
          const score = assessment?.score ?? null
          return (
            <div key={dim} className="pm-uncertainty-row">
              <span className="pm-uncertainty-dim">{label}</span>
              {score ? (
                <span className={`pm-uncertainty-score pm-uncertainty-score--${score}`}>
                  {SCORE_LABEL[score]}
                </span>
              ) : (
                <span className="pm-uncertainty-score pm-uncertainty-score--pending">—</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
