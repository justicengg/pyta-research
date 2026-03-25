import { useRef, useState } from 'react'

type Props = {
  onSceneSettings?: () => void
  onReset?: () => void
  zoomPercent?: number
}

export function CanvasToolbar({ onSceneSettings, onReset, zoomPercent = 100 }: Props) {
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [hidden, setHidden] = useState(true)
  const dragging = useRef(false)
  const lastPos = useRef({ x: 0, y: 0 })

  const handlePointerDown = (e: React.PointerEvent<HTMLSpanElement>) => {
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragging.current = true
    lastPos.current = { x: e.clientX, y: e.clientY }
  }

  const handlePointerMove = (e: React.PointerEvent<HTMLSpanElement>) => {
    if (!dragging.current) return
    const dx = e.clientX - lastPos.current.x
    const dy = e.clientY - lastPos.current.y
    lastPos.current = { x: e.clientX, y: e.clientY }
    setOffset(prev => ({ x: prev.x + dx, y: prev.y + dy }))
  }

  const handlePointerUp = () => {
    dragging.current = false
  }

  if (hidden) {
    return (
      <button
        className="toolbar-restore"
        data-no-pan
        onClick={() => setHidden(false)}
        title="显示工具栏"
      >
        ⊞
      </button>
    )
  }

  return (
    <div
      className="canvas-toolbar canvas-toolbar--alive"
      data-no-pan
      data-toolbar-state="open"
      style={{
        transform: `translate(calc(-50% + ${offset.x}px), ${offset.y}px)`,
      }}
    >
      {/* 拖拽把手 */}
      <span
        className="toolbar-drag-handle"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        title="拖拽移动"
      >
        ⠿
      </span>

      <div className="toolbar-sep" />

      <button
        className="toolbar-btn"
        onClick={onSceneSettings}
        data-no-pan
      >
        场景设置
      </button>

      <div className="toolbar-sep" />

      <button
        className="toolbar-btn"
        onClick={onReset}
        data-no-pan
        title="重置视图到初始位置 (Reset view)"
      >
        ⌖ 重置
      </button>

      <span className="toolbar-zoom-pct">{zoomPercent}%</span>

      <div className="toolbar-sep" />

      {/* 隐藏按钮 */}
      <button
        className="toolbar-hide"
        onClick={() => setHidden(true)}
        title="隐藏工具栏"
      >
        ✕
      </button>
    </div>
  )
}
