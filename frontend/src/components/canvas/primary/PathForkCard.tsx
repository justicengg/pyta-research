import type { PathForkData } from '../../../lib/types/primaryCanvas'

type Props = {
  data: PathForkData
  position: { x: number; y: number }
  onDragMove: (dx: number, dy: number) => void
}

export function PathForkCard({ data, position, onDragMove }: Props) {
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

  return (
    <div
      className="pm-card pm-card--pathfork"
      style={{ left: position.x, top: position.y }}
      data-no-pan
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <div className="pm-card__header">
        <span className="pm-card__label pm-card__label--fork">PathFork</span>
        <h3 className="pm-card__title">路径分叉</h3>
        <p className="pm-pathfork-trigger">触发：{data.triggerAssumption}</p>
      </div>

      <div className="pm-card__body">
        <div className="pm-pathfork-scenarios">
          <div className="pm-pathfork-scenario pm-pathfork-scenario--holds">
            <span className="pm-pathfork-scenario-tag">假设成立</span>
            <p>{data.scenarioIfHolds}</p>
          </div>
          <div className="pm-pathfork-scenario pm-pathfork-scenario--fails">
            <span className="pm-pathfork-scenario-tag">假设失败</span>
            <p>{data.scenarioIfFails}</p>
          </div>
        </div>
        <div className="pm-pathfork-action">
          <span className="pm-pathfork-action-label">建议动作</span>
          <p>{data.recommendedAction}</p>
        </div>
      </div>
    </div>
  )
}
