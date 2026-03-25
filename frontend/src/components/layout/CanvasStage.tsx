import { useCallback, useRef, useState } from 'react'
import type { CanvasState, RoundRecord, SceneParams } from '../../lib/types/canvas'
import type { SandboxInputEvent } from '../../lib/types/sandbox'
import { useCanvasViewport } from '../../hooks/useCanvasViewport'
import { useTopologyLayout, TOPOLOGY_CENTER } from '../../hooks/useTopologyLayout'
import '../../styles/canvas-motion.css'
import { AgentNode } from '../canvas/AgentNode'
import { CanvasBackground } from '../canvas/CanvasBackground'
import { CenterCoreCard } from '../canvas/CenterCoreCard'
import { EdgeLayer } from '../canvas/EdgeLayer'
import { CommandConsole } from './CommandConsole'

type AgentPos = { x: number; y: number }

type Props = {
  state: CanvasState
  draft: string
  onDraftChange: (value: string) => void
  isRunning: boolean
  error: string | null
  qualityLabel: string
  currentRound: number
  roundHistory: RoundRecord[]
  currentInputEvents: SandboxInputEvent[]
  sceneParams: SceneParams
  onSceneParamsChange: (p: SceneParams) => void
  onSubmit: () => void
}

// Center core anchor — matches TOPOLOGY_CENTER from useTopologyLayout
const CENTER_POS: AgentPos = TOPOLOGY_CENTER

export function CanvasStage({
  state,
  draft,
  onDraftChange,
  isRunning,
  error,
  qualityLabel,
  currentRound,
  roundHistory,
  currentInputEvents,
  sceneParams,
  onSceneParamsChange,
  onSubmit,
}: Props) {
  const stageRef = useRef<HTMLDivElement>(null)
  const { panX, panY, zoom, zoomPercent, isPanning, stagePointerHandlers, resetViewport } =
    useCanvasViewport(stageRef)

  // Computed positions from topology layout algorithm
  const computedPositions = useTopologyLayout(state.agents)

  // Drag overrides — user drag moves nodes away from computed positions
  const [dragOverrides, setDragOverrides] = useState<Record<string, AgentPos>>({})
  // Final positions: computed topology base + any drag overrides
  const agentPositions: Record<string, AgentPos> = {}
  for (const agent of state.agents) {
    agentPositions[agent.id] = dragOverrides[agent.id] ?? computedPositions[agent.id] ?? { x: 0, y: 0 }
  }

  const handleAgentDragMove = useCallback((id: string, dx: number, dy: number) => {
    setDragOverrides((prev) => {
      const base = prev[id] ?? computedPositions[id] ?? { x: 0, y: 0 }
      return { ...prev, [id]: { x: base.x + dx, y: base.y + dy } }
    })
  }, [computedPositions])

  return (
    <section
      className={`stage-wrap canvas-stage${isRunning ? ' canvas-stage--running' : ''}`}
      data-quality={qualityLabel}
      data-round={currentRound}
    >

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
          {state.agents.map((agent, i) => (
            <AgentNode
              key={agent.id}
              agent={agent}
              position={agentPositions[agent.id]}
              zoom={zoom}
              onDragMove={handleAgentDragMove}
              isRunning={isRunning}
              nodeIndex={i}
            />
          ))}

          {error ? <div className="canvas-error">{error}</div> : null}
        </div>

        {/* Corner controls — zoom readout + reset */}
        <div className="canvas-corner-controls" data-no-pan>
          <span className="corner-zoom">{zoomPercent}%</span>
          <button
            className="corner-reset"
            onClick={resetViewport}
            title="重置视图 (Reset view)"
          >
            ⌖
          </button>
        </div>
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
