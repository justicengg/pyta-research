import { useCallback, useRef, useState } from 'react'
import type { CanvasState } from '../../lib/types/canvas'
import { useCanvasViewport } from '../../hooks/useCanvasViewport'
import { AgentNode } from '../canvas/AgentNode'
import { CanvasBackground } from '../canvas/CanvasBackground'
import { CanvasToolbar } from '../canvas/CanvasToolbar'
import { EdgeLayer } from '../canvas/EdgeLayer'
import { EventChips } from '../canvas/EventChips'
import { CommandConsole } from './CommandConsole'

type AgentPos = { x: number; y: number }

type Props = {
  state: CanvasState
  draft: string
  onDraftChange: (value: string) => void
  onSubmit: () => void
  isRunning: boolean
  error: string | null
  qualityLabel: string
}

// Center core anchor — matches center-core CSS: translate(-50%,-50%) at left:550px top:300px
// so its visual center in canvas coords is (550, 300)
const CENTER_POS: AgentPos = { x: 550, y: 300 }

export function CanvasStage({
  state,
  draft,
  onDraftChange,
  onSubmit,
  isRunning,
  error,
  qualityLabel,
}: Props) {
  const stageRef = useRef<HTMLDivElement>(null)
  const { panX, panY, zoom, zoomPercent, isPanning, stagePointerHandlers, resetViewport } =
    useCanvasViewport(stageRef)

  // Lifted agent positions — initialized from state, then updated by drag
  const [agentPositions, setAgentPositions] = useState<Record<string, AgentPos>>(() =>
    Object.fromEntries(state.agents.map((a) => [a.id, { x: a.position.x, y: a.position.y }]))
  )

  const handleAgentDragMove = useCallback((id: string, dx: number, dy: number) => {
    setAgentPositions((prev) => ({
      ...prev,
      [id]: { x: prev[id].x + dx, y: prev[id].y + dy },
    }))
  }, [])

  return (
    <section className="stage-wrap">

      {/* Zone A — Context bar */}
      <div className="stage-head">
        <div className="stage-head-left">
          <div className="eyebrow">融合方向</div>
          <h2>多 Agent 沙盘推演</h2>
        </div>
        <div className="chip-row">
          <span className={`chip ${isRunning ? 'chip-running' : ''}`}>
            {isRunning ? '运行中' : '就绪'}
          </span>
          <span className="chip quality-chip">{qualityLabel}</span>
        </div>
      </div>

      {/* Zone B — Canvas viewport */}
      <div
        ref={stageRef}
        className={`stage${isPanning ? ' panning' : ''}`}
        {...stagePointerHandlers}
      >
        {/* canvas-layer transforms with pan + zoom */}
        <div
          className="canvas-layer"
          style={{
            transform: `translate(${panX}px, ${panY}px) scale(${zoom})`,
            transformOrigin: '0 0',
          }}
        >
          <CanvasBackground />

          {/* Edge layer — rendered before agent nodes so cards appear above edges */}
          <EdgeLayer
            edges={state.edges}
            agentPositions={agentPositions}
            centerPos={CENTER_POS}
          />

          {/* Center core */}
          <div className="center-core">
            <h3>腾讯 / 港股科技</h3>
            <p>核心推演对象。所有 Agent 围绕这个核心对象提供反应、解释、修正和收敛。</p>
            <div className="center-tags">
              <span className="core-tag">核心场景</span>
              <span className="core-tag">3 个月</span>
              <span className="core-tag">持续推演</span>
            </div>
          </div>

          {/* Agent nodes */}
          {state.agents.map((agent) => (
            <AgentNode
              key={agent.id}
              agent={agent}
              position={agentPositions[agent.id]}
              zoom={zoom}
              onDragMove={handleAgentDragMove}
            />
          ))}

          {error ? <div className="canvas-error">{error}</div> : null}
        </div>

        {/* Toolbar — outside canvas-layer so it stays fixed during pan/zoom */}
        <CanvasToolbar
          onRun={onSubmit}
          isRunning={isRunning}
          onSceneSettings={() => {/* TODO: open scene settings modal */}}
          onReset={resetViewport}
          zoomPercent={zoomPercent}
        />

        {/* Event chips — outside canvas-layer, not affected by transform */}
        <EventChips onSelect={(title) => onDraftChange(title)} />
      </div>

      {/* Zone C — Command console */}
      <CommandConsole
        draft={draft}
        onDraftChange={onDraftChange}
        onSubmit={onSubmit}
        isRunning={isRunning}
        error={error}
      />
    </section>
  )
}
