import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { CanvasState, RoundRecord, SceneParams } from '../../lib/types/canvas'
import type {
  SandboxAgentId,
  SandboxEnvironmentType,
  SandboxInputEvent,
  SandboxPipelineStage,
} from '../../lib/types/sandbox'
import { useCanvasViewport } from '../../hooks/useCanvasViewport'
import { SANDBOX_AGENT_ORDER } from '../../lib/types/sandbox'
import '../../styles/canvas-motion.css'
import { AgentNode, CARD_WIDTH } from '../canvas/AgentNode'
import { CanvasBackground } from '../canvas/CanvasBackground'
import { EnvironmentFlowLayer } from '../canvas/EnvironmentFlowLayer'
import { InteractionFlowLayer } from '../canvas/InteractionFlowLayer'
import {
  InteractionSummaryPanel,
  INTERACTION_PANEL_WIDTH,
} from '../canvas/InteractionSummaryPanel'
import { EnvironmentBar } from '../environment/EnvironmentBar'
import { CommandConsole } from './CommandConsole'
import { PromptMascot } from './PromptMascot'
import {
  ORB_PROFILES,
  pickOrbMessage,
  resolveOrbMode,
  resolveOrbVariant,
  type OrbTrigger,
} from '../../lib/orb/promptProfiles'

type AgentPos = { x: number; y: number }
type EnvironmentAnchorMap = Partial<Record<SandboxEnvironmentType, { x: number; y: number }>>

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

const PARALLEL_CENTER_X = 800
const PARALLEL_CENTER_Y = 516
const PARALLEL_CENTER_GAP_X = 304
const PARALLEL_CARD_HEIGHT = 288
const RETAIL_CENTER_INDEX = 2
const INTERACTION_PANEL_DEFAULT_POSITION = {
  x: PARALLEL_CENTER_X - INTERACTION_PANEL_WIDTH / 2,
  y: PARALLEL_CENTER_Y + PARALLEL_CARD_HEIGHT / 2 + 54,
}

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
  sceneParams: _sceneParams,
  onSceneParamsChange: _onSceneParamsChange,
  onSubmit,
}: Props) {
  const stageRef = useRef<HTMLDivElement>(null)
  const { panX, panY, zoom, zoomPercent, isPanning, stagePointerHandlers, resetViewport } =
    useCanvasViewport(stageRef)
  const [showPromptMascot, setShowPromptMascot] = useState(false)
  const [isOrbExiting, setIsOrbExiting] = useState(false)
  const [promptMessage, setPromptMessage] = useState('说吧，今天研究什么')
  const [promptTrigger, setPromptTrigger] = useState<OrbTrigger>('first_load')
  const [orbVariant] = useState(resolveOrbVariant)
  const [orbMode] = useState(resolveOrbMode)
  const hasShownFirstCompleteRef = useRef(false)
  const wasRunningRef = useRef(isRunning)
  const [environmentAnchorViewportMap, setEnvironmentAnchorViewportMap] = useState<EnvironmentAnchorMap>({})
  const [highlightedAgentIds, setHighlightedAgentIds] = useState<SandboxAgentId[]>([])
  const [interactionPanelPosition, setInteractionPanelPosition] = useState(INTERACTION_PANEL_DEFAULT_POSITION)

  // Drag overrides — user drag moves nodes away from computed positions
  const [dragOverrides, setDragOverrides] = useState<Record<string, AgentPos>>({})
  const visibleAgents = useMemo(() => {
    const baseAgents = state.agents.filter((agent) => (agent.ring ?? 1) === 1)
    const sourceAgents = baseAgents.length > 0 ? baseAgents : state.agents.slice(0, 5)
    return [...sourceAgents].sort((left, right) => {
      const leftIndex = SANDBOX_AGENT_ORDER.indexOf(left.id as SandboxAgentId)
      const rightIndex = SANDBOX_AGENT_ORDER.indexOf(right.id as SandboxAgentId)
      return leftIndex - rightIndex
    })
  }, [state.agents])

  const agentPositions: Record<string, AgentPos> = {}
  for (const [index, agent] of visibleAgents.entries()) {
    const centerIndexOffset = index - RETAIL_CENTER_INDEX
    const centerX = PARALLEL_CENTER_X + centerIndexOffset * PARALLEL_CENTER_GAP_X
    const basePosition = {
      x: centerX - CARD_WIDTH / 2,
      y: PARALLEL_CENTER_Y - PARALLEL_CARD_HEIGHT / 2,
    }
    agentPositions[agent.id] = dragOverrides[agent.id] ?? basePosition
  }
  const envState = state.environmentState
  const highlightedAgentSet = useMemo(() => new Set(highlightedAgentIds), [highlightedAgentIds])
  const pipelineStage = resolvePipelineStage(envState, isRunning, currentInputEvents.length)
  const environmentAnchors = useMemo(() => {
    const stageElement = stageRef.current
    if (!stageElement) {
      return {}
    }
    const stageRect = stageElement.getBoundingClientRect()
    const mapped: EnvironmentAnchorMap = {}
    for (const [type, anchor] of Object.entries(environmentAnchorViewportMap) as Array<
      [SandboxEnvironmentType, { x: number; y: number }]
    >) {
      mapped[type] = {
        x: (anchor.x - stageRect.left - panX) / zoom,
        y: (anchor.y - stageRect.top - panY) / zoom,
      }
    }
    return mapped
  }, [environmentAnchorViewportMap, panX, panY, zoom])

  const handleAgentDragMove = useCallback((id: string, dx: number, dy: number) => {
    setDragOverrides((prev) => {
      const agentIndex = visibleAgents.findIndex((agent) => agent.id === id)
      const centerIndexOffset = Math.max(agentIndex, 0) - RETAIL_CENTER_INDEX
      const centerX = PARALLEL_CENTER_X + centerIndexOffset * PARALLEL_CENTER_GAP_X
      const fallback = {
        x: centerX - CARD_WIDTH / 2,
        y: PARALLEL_CENTER_Y - PARALLEL_CARD_HEIGHT / 2,
      }
      const base = prev[id] ?? fallback
      return { ...prev, [id]: { x: base.x + dx, y: base.y + dy } }
    })
  }, [visibleAgents])

  const dismissPromptMascot = useCallback(() => {
    setIsOrbExiting(true)
    window.setTimeout(() => {
      setShowPromptMascot(false)
      setIsOrbExiting(false)
    }, 220)
  }, [])

  const revealPromptMascot = useCallback((trigger: OrbTrigger) => {
    if (orbMode === 'off') return
    setPromptTrigger(trigger)
    setPromptMessage(pickOrbMessage(orbVariant, trigger))
    setIsOrbExiting(false)
    setShowPromptMascot(true)
  }, [orbMode, orbVariant])

  useEffect(() => {
    if (orbMode === 'off') return
    const timer = window.setTimeout(() => {
      revealPromptMascot('first_load')
    }, 900)
    return () => window.clearTimeout(timer)
  }, [orbMode, revealPromptMascot])

  useEffect(() => {
    if (wasRunningRef.current && !isRunning && roundHistory.length > 0 && !hasShownFirstCompleteRef.current) {
      hasShownFirstCompleteRef.current = true
      revealPromptMascot('first_complete')
      wasRunningRef.current = isRunning
      return
    }
    wasRunningRef.current = isRunning
  }, [isRunning, roundHistory.length, revealPromptMascot])

  useEffect(() => {
    if (orbMode === 'off' || isRunning || draft.trim()) {
      return
    }
    const timer = window.setTimeout(() => {
      revealPromptMascot('idle_nudge')
    }, ORB_PROFILES[orbVariant].idleDelayMs)
    return () => window.clearTimeout(timer)
  }, [draft, isRunning, currentRound, orbMode, orbVariant, revealPromptMascot])

  useEffect(() => {
    if (isRunning) {
      dismissPromptMascot()
    }
  }, [isRunning, dismissPromptMascot])


  return (
    <section
      className={`stage-wrap canvas-stage${isRunning ? ' canvas-stage--running' : ''}`}
      data-quality={qualityLabel}
      data-round={currentRound}
    >

      {/* Zone A — Context bar */}
      <div className="stage-head">
        <div className="stage-head-left">
          <h2>多 Agent 沙盘推演</h2>
        </div>
      </div>

      {/* Environment Band — Layer 1→2 中间层 */}
      <EnvironmentBar
        state={envState}
        pipelineStage={pipelineStage}
        isRunning={isRunning}
        onAnchorLayoutChange={setEnvironmentAnchorViewportMap}
      />

      {/* Zone B — Canvas viewport */}
      <div
        ref={stageRef}
        className={`stage stage--parallel${isPanning ? ' panning' : ''}`}
        {...stagePointerHandlers}
      >
        <div
          className="canvas-layer canvas-layer--parallel"
          style={{ transform: `translate(${panX}px, ${panY}px) scale(${zoom})`, transformOrigin: '0 0' }}
        >
          <CanvasBackground />
          <EnvironmentFlowLayer
            isActive={isRunning}
            agentOrder={visibleAgents.map((agent) => agent.id as SandboxAgentId)}
            agentPositions={agentPositions}
            anchors={environmentAnchors}
          />
          <InteractionFlowLayer
            isActive={state.interactionResolution != null}
            agentOrder={visibleAgents.map((agent) => agent.id as SandboxAgentId)}
            agentPositions={agentPositions}
            panelPosition={interactionPanelPosition}
          />
          <div className="parallel-agent-board">
            {visibleAgents.map((agent, i) => (
              <AgentNode
                key={agent.id}
                agent={agent}
                position={agentPositions[agent.id]}
                zoom={1}
                onDragMove={handleAgentDragMove}
                isRunning={isRunning}
                nodeIndex={i}
                isHighlighted={highlightedAgentSet.has(agent.id as SandboxAgentId)}
                isDimmed={highlightedAgentSet.size > 0 && !highlightedAgentSet.has(agent.id as SandboxAgentId)}
              />
            ))}
          </div>
          <InteractionSummaryPanel
            resolution={state.interactionResolution}
            position={interactionPanelPosition}
            zoom={zoom}
            onDragMove={(dx, dy) =>
              setInteractionPanelPosition((current) => ({ x: current.x + dx, y: current.y + dy }))
            }
            onHighlightAgents={setHighlightedAgentIds}
            onClearHighlight={() => setHighlightedAgentIds([])}
          />
          {error ? <div className="canvas-error">{error}</div> : null}
        </div>

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
        promptMascot={showPromptMascot ? (
          <PromptMascot
            visible={!isOrbExiting}
            message={promptMessage}
            variant={orbVariant}
            mode={orbMode}
            trigger={promptTrigger}
          />
        ) : undefined}
      />
    </section>
  )
}

function resolvePipelineStage(
  environmentState: CanvasState['environmentState'],
  isRunning: boolean,
  inputCount: number,
): SandboxPipelineStage | 'idle' {
  if (isRunning && environmentState == null) {
    return inputCount > 0 ? 'classifying' : 'ingesting'
  }
  if (isRunning && environmentState != null) {
    return 'simulating'
  }
  if (environmentState == null) {
    return 'idle'
  }
  const hasSignals = environmentState.buckets.some((bucket) => bucket.activeSignals.length > 0)
  return hasSignals ? 'completed' : 'environment_ready'
}
