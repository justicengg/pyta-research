import { useCallback, useEffect, useRef, useState } from 'react'
import type { CanvasState, RoundRecord, SceneParams } from '../../lib/types/canvas'
import type { SandboxInputEvent } from '../../lib/types/sandbox'
import { useCanvasViewport } from '../../hooks/useCanvasViewport'
import { useTopologyLayout, TOPOLOGY_CENTER } from '../../hooks/useTopologyLayout'
import '../../styles/canvas-motion.css'
import { AgentNode } from '../canvas/AgentNode'
import { CanvasBackground } from '../canvas/CanvasBackground'
import { CenterCoreCard } from '../canvas/CenterCoreCard'
import { EdgeLayer } from '../canvas/EdgeLayer'
import { MeridianGridView } from '../canvas/MeridianGridView'
import '../../styles/meridian-grid.css'
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

  const [viewMode, setViewMode] = useState<'topology' | 'meridian'>('topology')
  const [showPromptMascot, setShowPromptMascot] = useState(false)
  const [promptMessage, setPromptMessage] = useState('说吧，今天研究什么')
  const [promptTrigger, setPromptTrigger] = useState<OrbTrigger>('first_load')
  const [orbVariant] = useState(resolveOrbVariant)
  const [orbMode] = useState(resolveOrbMode)
  const hasShownFirstCompleteRef = useRef(false)
  const wasRunningRef = useRef(isRunning)
  const promptHideTimerRef = useRef<number | null>(null)

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

  const dismissPromptMascot = useCallback(() => {
    if (promptHideTimerRef.current) {
      window.clearTimeout(promptHideTimerRef.current)
      promptHideTimerRef.current = null
    }
    setShowPromptMascot(false)
  }, [])

  const revealPromptMascot = useCallback((trigger: OrbTrigger) => {
    if (orbMode === 'off') return
    const profile = ORB_PROFILES[orbVariant]
    setPromptTrigger(trigger)
    setPromptMessage(pickOrbMessage(orbVariant, trigger))
    setShowPromptMascot(true)
    if (promptHideTimerRef.current) {
      window.clearTimeout(promptHideTimerRef.current)
    }
    promptHideTimerRef.current = window.setTimeout(() => {
      setShowPromptMascot(false)
      promptHideTimerRef.current = null
    }, orbMode === 'soft' ? Math.round(profile.dwellMs * 0.8) : profile.dwellMs)
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
    if (draft.trim()) {
      dismissPromptMascot()
    }
  }, [draft, dismissPromptMascot])

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
        <div className="view-toggle-group">
          <button
            className={`view-toggle-btn${viewMode === 'topology' ? ' view-toggle-btn--active' : ''}`}
            onClick={() => setViewMode('topology')}
            title="拓扑视图"
          >⬡</button>
          <button
            className={`view-toggle-btn${viewMode === 'meridian' ? ' view-toggle-btn--active' : ''}`}
            onClick={() => setViewMode('meridian')}
            title="经线对比视图"
          >⊞</button>
        </div>
      </div>

      {/* Zone B — Canvas viewport */}
      <div
        ref={stageRef}
        className={`stage${isPanning ? ' panning' : ''}`}
        {...stagePointerHandlers}
      >
        {/* canvas-layer transforms with pan + zoom */}
        {viewMode === 'topology' ? (
          <div
            className="canvas-layer"
            style={{ transform: `translate(${panX}px, ${panY}px) scale(${zoom})`, transformOrigin: '0 0' }}
          >
            <CanvasBackground />
            <EdgeLayer edges={state.edges} agentPositions={agentPositions} centerPos={CENTER_POS} />
            <CenterCoreCard sceneParams={sceneParams} onSceneParamsChange={onSceneParamsChange} />
            {state.agents.map((agent, i) => (
              <AgentNode key={agent.id} agent={agent} position={agentPositions[agent.id]} zoom={zoom} onDragMove={handleAgentDragMove} isRunning={isRunning} nodeIndex={i} />
            ))}
            {error ? <div className="canvas-error">{error}</div> : null}
          </div>
        ) : (
          <MeridianGridView
            agents={state.agents.filter(a => (a.ring ?? 1) === 1)}
            isRunning={isRunning}
            sceneParams={sceneParams}
          />
        )}

        {/* Corner controls — zoom readout + reset */}
        <div className="canvas-corner-controls" data-no-pan>
          <div className="view-toggle-group" data-no-pan>
            <button
              className={`view-toggle-btn${viewMode === 'topology' ? ' view-toggle-btn--active' : ''}`}
              onClick={() => setViewMode('topology')}
              title="拓扑视图"
            >⬡</button>
            <button
              className={`view-toggle-btn${viewMode === 'meridian' ? ' view-toggle-btn--active' : ''}`}
              onClick={() => setViewMode('meridian')}
              title="经线对比视图"
            >⊞</button>
          </div>
          {viewMode === 'topology' && (
            <>
              <span className="corner-zoom">{zoomPercent}%</span>
              <button
                className="corner-reset"
                onClick={resetViewport}
                title="重置视图 (Reset view)"
              >
                ⌖
              </button>
            </>
          )}
        </div>
      </div>

      {/* Zone C — Command console */}
      <PromptMascot
        visible={showPromptMascot}
        message={promptMessage}
        variant={orbVariant}
        mode={orbMode}
        trigger={promptTrigger}
      />
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
