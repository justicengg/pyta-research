import type { KeyAssumptionsData } from '../../../lib/types/primaryCanvas'

type Props = {
  data: KeyAssumptionsData
  position: { x: number; y: number }
  onDragMove: (dx: number, dy: number) => void
}

const STATUS_LABEL: Record<string, string> = {
  confirmed:  '已确认',
  unverified: '待验证',
  violated:   '已违反',
}

export function KeyAssumptionsCard({ data, position, onDragMove }: Props) {
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

  function handlePointerUp() { dragRef.active = false }

  const hard = data.items.filter(a => a.level === 'hard')
  const soft = data.items.filter(a => a.level === 'soft')

  return (
    <div
      className="pm-card pm-card--assumptions"
      style={{ left: position.x, top: position.y }}
      data-no-pan
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <div className="pm-card__header">
        <span className="pm-card__label">模块 3</span>
        <h3 className="pm-card__title">关键假设</h3>
      </div>

      <div className="pm-card__body">
        {hard.length > 0 && (
          <div className="pm-assumption-group">
            <span className="pm-assumption-group-label">硬假设</span>
            {hard.map((item, i) => (
              <div key={i} className={`pm-assumption-item pm-assumption-item--${item.status}`}>
                <span className={`pm-assumption-status pm-assumption-status--${item.status}`}>
                  {STATUS_LABEL[item.status]}
                </span>
                <span className="pm-assumption-desc">{item.description}</span>
                {item.timeHorizonMonths != null && (
                  <span className="pm-assumption-horizon">{item.timeHorizonMonths}M</span>
                )}
              </div>
            ))}
          </div>
        )}

        {soft.length > 0 && (
          <div className="pm-assumption-group">
            <span className="pm-assumption-group-label">软假设</span>
            {soft.map((item, i) => (
              <div key={i} className={`pm-assumption-item pm-assumption-item--${item.status}`}>
                <span className={`pm-assumption-status pm-assumption-status--${item.status}`}>
                  {STATUS_LABEL[item.status]}
                </span>
                <span className="pm-assumption-desc">{item.description}</span>
                {item.timeHorizonMonths != null && (
                  <span className="pm-assumption-horizon">{item.timeHorizonMonths}M</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
