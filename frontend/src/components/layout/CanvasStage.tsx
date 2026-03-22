import { useCallback, useRef, useState } from 'react'
import type { CanvasState, RoundRecord, SceneParams } from '../../lib/types/canvas'
import type { SandboxInputEvent } from '../../lib/types/sandbox'
import { useCanvasViewport } from '../../hooks/useCanvasViewport'
import { AgentNode } from '../canvas/AgentNode'
import { CanvasBackground } from '../canvas/CanvasBackground'
import { CanvasToolbar } from '../canvas/CanvasToolbar'
import { CenterCoreCard } from '../canvas/CenterCoreCard'
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
  currentRound: number
  roundHistory: RoundRecord[]
  currentInputEvents: SandboxInputEvent[]
  sceneParams: SceneParams
  onSceneParamsChange: (p: SceneParams) => void
}

// Center core anchor — center-core uses left:50% top:49% translate(-50%,-50%).
// Canvas layer is ~960px wide × 760px tall → visual center ≈ (480, 370)
// Adjust to match actual orbital center used in mock positions
const CENTER_POS: AgentPos = { x: 480, y: 270 }

export function CanvasStage({
  state,
  draft,
  onDraftChange,
  onSubmit,
  isRunning,
  error,
  qualityLabel,
  currentRound,
  roundHistory,
  currentInputEvents,
  sceneParams,
  onSceneParamsChange,
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

          {/* Center core — editable scene params */}
          <CenterCoreCard
            sceneParams={sceneParams}
            onSceneParamsChange={onSceneParamsChange}
          />

          {/* Agent nodes */}
          {state.agents.map((agent) => (
            <AgentNode
              key={agent.id}
              agent={agent}
              position={agentPositions[agent.id]}
              zoom={zoom}
              onDragMove={handleAgentDragMove}
              isRunning={isRunning}
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
        currentRound={currentRound}
        roundHistory={roundHistory}
        currentInputEvents={currentInputEvents}
      />
    </section>
  )
}
