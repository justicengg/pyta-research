import { useCallback, useEffect, useRef, useState } from 'react'

interface Viewport {
  panX: number
  panY: number
  zoom: number
}

interface StagePointerHandlers {
  onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => void
  onPointerMove: (e: React.PointerEvent<HTMLDivElement>) => void
  onPointerUp: (e: React.PointerEvent<HTMLDivElement>) => void
}

export interface UseCanvasViewportReturn {
  panX: number
  panY: number
  zoom: number
  zoomPercent: number
  isPanning: boolean
  stagePointerHandlers: StagePointerHandlers
  resetViewport: () => void
}

const MIN_ZOOM = 0.3
const MAX_ZOOM = 2.5

export function useCanvasViewport(
  stageRef: React.RefObject<HTMLDivElement | null>,
  initialZoom = 1,
): UseCanvasViewportReturn {
  const [viewport, setViewport] = useState<Viewport>({ panX: 0, panY: 0, zoom: initialZoom })
  const [isPanning, setIsPanning] = useState(false)

  // Refs so event handlers always read current values without re-subscribing
  const isPanningRef = useRef(false)
  const lastPosRef = useRef({ x: 0, y: 0 })
  const viewportRef = useRef(viewport)
  viewportRef.current = viewport

  // ── Wheel / pinch zoom ──────────────────────────────────────────────
  // Must be an imperative listener (not React synthetic) so we can call
  // e.preventDefault() — React registers wheel listeners as passive by default.
  useEffect(() => {
    const el = stageRef.current
    if (!el) return

    const onWheel = (e: WheelEvent) => {
      e.preventDefault()

      const rect = el.getBoundingClientRect()
      // Cursor position relative to the stage element
      const cx = e.clientX - rect.left
      const cy = e.clientY - rect.top

      const prev = viewportRef.current
      let newZoom: number

      if (e.ctrlKey) {
        // macOS trackpad pinch sends wheel + ctrlKey; deltaY is in "percent" units
        newZoom = prev.zoom * (1 - e.deltaY * 0.01)
      } else {
        // Regular mouse wheel or two-finger scroll (interpreted as pan in browsers,
        // but many users expect Ctrl+wheel for zoom — handled above — and plain
        // wheel to zoom as well when no Ctrl key because this is a canvas, not a page)
        const factor = e.deltaY < 0 ? 1.08 : 1 / 1.08
        newZoom = prev.zoom * factor
      }

      newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, newZoom))

      // Zoom-to-cursor: keep the point under the cursor stationary
      const scale = newZoom / prev.zoom
      const newPanX = cx - (cx - prev.panX) * scale
      const newPanY = cy - (cy - prev.panY) * scale

      setViewport({ panX: newPanX, panY: newPanY, zoom: newZoom })
    }

    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [stageRef])

  // ── Drag-to-pan ─────────────────────────────────────────────────────
  const handlePointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return // left button only

    // Don't pan when the user clicks interactive elements inside the canvas
    const target = e.target as HTMLElement
    if (target.closest('button, input, textarea, select, [data-no-pan]')) return

    e.currentTarget.setPointerCapture(e.pointerId)
    isPanningRef.current = true
    setIsPanning(true)
    lastPosRef.current = { x: e.clientX, y: e.clientY }
  }, [])

  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (!isPanningRef.current) return
    const dx = e.clientX - lastPosRef.current.x
    const dy = e.clientY - lastPosRef.current.y
    lastPosRef.current = { x: e.clientX, y: e.clientY }
    setViewport(prev => ({ ...prev, panX: prev.panX + dx, panY: prev.panY + dy }))
  }, [])

  const handlePointerUp = useCallback(() => {
    isPanningRef.current = false
    setIsPanning(false)
  }, [])

  // ── Reset ────────────────────────────────────────────────────────────
  const resetViewport = useCallback(() => {
    setViewport({ panX: 0, panY: 0, zoom: initialZoom })
  }, [initialZoom])

  return {
    panX: viewport.panX,
    panY: viewport.panY,
    zoom: viewport.zoom,
    zoomPercent: Math.round(viewport.zoom * 100),
    isPanning,
    stagePointerHandlers: {
      onPointerDown: handlePointerDown,
      onPointerMove: handlePointerMove,
      onPointerUp: handlePointerUp,
    },
    resetViewport,
  }
}
