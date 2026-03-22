import { useRef, useState } from 'react'
import type { AgentCardData } from '../../lib/types/canvas'
import { StatusDot } from '../common/StatusDot'
import { AgentResultCard } from './AgentResultCard'

// Card dimensions used for edge anchor calculation (must match CSS)
export const CARD_WIDTH = 280
export const CARD_HEADER_HEIGHT = 88

type Props = {
  agent: AgentCardData
  position: { x: number; y: number }
  zoom: number
  onDragMove: (id: string, dx: number, dy: number) => void
  isRunning?: boolean
}

export function AgentNode({ agent, position, zoom, onDragMove, isRunning = false }: Props) {
  const dragRef = useRef<{ active: boolean; lastX: number; lastY: number }>({
    active: false,
    lastX: 0,
    lastY: 0,
  })
  const [isDragging, setIsDragging] = useState(false)

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    // Only left button; don't drag on interactive children
    if (e.button !== 0) return
    const target = e.target as HTMLElement
    if (target.closest('button, input, textarea, select, a')) return

    e.stopPropagation() // prevent canvas pan from triggering
    e.currentTarget.setPointerCapture(e.pointerId)
    dragRef.current = { active: true, lastX: e.clientX, lastY: e.clientY }
    setIsDragging(true)
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragRef.current.active) return
    const rawDx = e.clientX - dragRef.current.lastX
    const rawDy = e.clientY - dragRef.current.lastY
    dragRef.current.lastX = e.clientX
    dragRef.current.lastY = e.clientY
    // Divide by zoom so 1 screen-pixel = 1/zoom canvas-pixel
    onDragMove(agent.id, rawDx / zoom, rawDy / zoom)
  }

  function handlePointerUp() {
    dragRef.current.active = false
    setIsDragging(false)
  }

  return (
    <div
      className={`agent-cluster${isDragging ? ' agent-cluster--dragging' : ''}`}
      style={{ left: position.x, top: position.y }}
      data-no-pan
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <div className={`agent agent-${agent.tint}`}>
        <div className="agent-copy">
          <div className="agent-title-row">
            <strong>{agent.title}</strong>
            {agent.round != null && (
              <span className="agent-round-badge" title={`第 ${agent.round} 轮推演结果`}>
                R{agent.round}
              </span>
            )}
          </div>
          <span>{agent.subtitle}</span>
          <p>{agent.summary}</p>
        </div>
        <StatusDot status={agent.status} isLoading={isRunning} />
      </div>
      <AgentResultCard agent={agent} isRunning={isRunning} />
    </div>
  )
}
