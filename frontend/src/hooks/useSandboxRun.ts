import { useMemo, useState } from 'react'
import { mapRunResponseToCanvasState } from '../lib/adapters'
import { runSandbox } from '../lib/api'
import { buildEnvironmentStateFromInputEvents } from '../lib/environment/pipeline'
import { mockCanvasState } from '../lib/mock/canvasState'
import type { AgentCardData, AgentEdge, CanvasState, RecentEvent, RoundRecord, SceneParams } from '../lib/types/canvas'
import type { SourceEvent } from '../lib/types/sourceEvents'
import type { CanvasRunState, SandboxInputEvent } from '../lib/types/sandbox'

export type SandboxRunController = {
  canvasState: CanvasState
  backendState: CanvasRunState | null
  draft: string
  setDraft: (value: string) => void
  currentInputEvents: SandboxInputEvent[]
  isRunning: boolean
  error: string | null
  qualityLabel: string
  currentRound: number
  roundHistory: RoundRecord[]
  sceneParams: SceneParams
  setSceneParams: (p: SceneParams) => void
  submit: () => Promise<void>
  submitWithSourceEvents: (sourceEvents: SourceEvent[]) => Promise<void>
}

type Options = {
  initialDraft?: string
}

export function useSandboxRun(options: Options = {}): SandboxRunController {
  const [draft, setDraft] = useState(options.initialDraft ?? mockCanvasState.commandDraft)
  const [canvasState, setCanvasState] = useState<CanvasState>(mockCanvasState)
  const [backendState, setBackendState] = useState<CanvasRunState | null>(null)
  const [currentInputEvents, setCurrentInputEvents] = useState<SandboxInputEvent[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentRound, setCurrentRound] = useState(1)
  const [roundHistory, setRoundHistory] = useState<RoundRecord[]>([])
  const [sceneParams, setSceneParams] = useState<SceneParams>({
    ticker: '0700.HK',
    market: 'HK',
    timeHorizon: '3个月',
  })

  const qualityLabel = useMemo(() => {
    if (!backendState) return 'Mock'
    return `${backendState.quality} · ${backendState.stopReason ?? 'running'}`
  }, [backendState])

  async function submit() {
    return submitWithSourceEvents([])
  }

  async function submitWithSourceEvents(sourceEvents: SourceEvent[]) {
    const content = draft.trim()
    if (!content || isRunning) {
      return
    }

    const inputEvents = mergeInputEvents(content, sourceEvents, sceneParams.ticker)
    const environmentState = buildEnvironmentStateFromInputEvents(
      inputEvents,
      sceneParams.ticker,
      sceneParams.market,
    )
    setCurrentInputEvents(inputEvents)
    setError(null)
    setIsRunning(true)
    setCanvasState((current) => ({
      ...current,
      environmentState,
      leftPanel: {
        ...current.leftPanel,
        recentEvents: inputEvents.map(toRecentEvent),
      },
    }))

    // Build context string from previous rounds for the LLM
    const previousContext = buildPreviousContext(roundHistory)
    const narrativeWithContext = previousContext
      ? `[历史推演上下文]\n${previousContext}\n\n[本轮指令]\n${content}`
      : content

    try {
      const response = await runSandbox({
        ticker: sceneParams.ticker,
        market: sceneParams.market,
        events: inputEvents,
        environmentState,
        roundTimeoutMs: 60000,
        narrativeGuide: narrativeWithContext,
      })

      const mapped = mapRunResponseToCanvasState(response, { inputEvents })
      setBackendState(mapped)

      const round = currentRound
      const prevSummaries = roundHistory[roundHistory.length - 1]?.agentSummaries ?? {}
      const newCanvasState = mergeCanvasState(mapped, inputEvents, round, prevSummaries)
      setCanvasState(newCanvasState)

      // Record this round in history
      const record: RoundRecord = {
        round,
        narrative: content,
        agentSummaries: Object.fromEntries(
          mapped.agents.map((a) => [a.id, a.summary])
        ),
        quality: mapped.quality,
        timestamp: new Date().toISOString(),
      }
      setRoundHistory((prev) => [...prev, record])
      setCurrentRound((prev) => prev + 1)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Sandbox run failed'
      setError(message)
    } finally {
      setIsRunning(false)
    }
  }

  return {
    canvasState,
    backendState,
    draft,
    setDraft,
    currentInputEvents,
    isRunning,
    error,
    qualityLabel,
    currentRound,
    roundHistory,
    sceneParams,
    setSceneParams,
    submit,
    submitWithSourceEvents,
  }
}

function buildInputEvents(content: string): SandboxInputEvent[] {
  return [
    {
      eventId: `cli-${Date.now()}`,
      eventType: 'manual_input',
      content,
      source: 'frontend_console',
      timestamp: new Date().toISOString(),
      symbol: '0700.HK',
      metadata: {
        inputMode: 'minimal_loop',
      },
    },
  ]
}

export function buildInputEventsFromSources(
  events: SourceEvent[],
  symbol: string | null,
): SandboxInputEvent[] {
  return events.map((event) => ({
    eventId: event.id,
    eventType: event.dimension ?? 'news',
    content: event.summary ? `${event.title}\n\n${event.summary}` : event.title,
    source: event.provider_id,
    timestamp: event.published_at ?? event.ingested_at,
    symbol,
    metadata: {
      provider_id: event.provider_id,
      connector_id: event.connector_id,
      dimension: event.dimension,
      impact_direction: event.impact_direction,
      impact_strength: event.impact_strength,
      ingested_at: event.ingested_at,
    },
  }))
}

export function mergeInputEvents(
  manualContent: string,
  sourceEvents: SourceEvent[],
  symbol: string | null,
): SandboxInputEvent[] {
  const sourceInputEvents = buildInputEventsFromSources(sourceEvents, symbol)
  const manualInputEvents = manualContent.trim()
    ? buildInputEvents(manualContent).map((event) => ({
        ...event,
        symbol,
      }))
    : []
  return [...sourceInputEvents, ...manualInputEvents]
}

// Summarize past rounds into a compact context block for the LLM
function buildPreviousContext(history: RoundRecord[]): string {
  if (history.length === 0) return ''
  return history
    .map((r) => {
      const summaries = Object.entries(r.agentSummaries)
        .map(([id, s]) => `  - ${id}: ${s}`)
        .join('\n')
      return `第 ${r.round} 轮（${r.narrative.slice(0, 60)}…）\n${summaries}`
    })
    .join('\n\n')
}

function mergeCanvasState(
  runState: CanvasRunState,
  inputEvents: SandboxInputEvent[],
  round: number,
  prevSummaries: Record<string, string> = {}
): CanvasState {
  const positionMap = new Map(mockCanvasState.agents.map((agent) => [agent.id, agent.position]))

  // Build ring-1 base agents
  const baseAgents: AgentCardData[] = runState.agents.map((agent) => ({
    id: agent.id,
    title: agent.title,
    subtitle: agent.subtitle,
    tint: agent.tint,
    status: agent.status,
    summary: agent.summary,
    observations: agent.observations,
    concerns: agent.concerns,
    focus: agent.focus,
    position: positionMap.get(agent.id) ?? { x: 0, y: 0 },
    round,
    sentiment: (agent.bias === 'mixed' ? 'neutral' : agent.bias ?? 'neutral') as 'bullish' | 'neutral' | 'bearish',
    confidence: agent.confidence ?? 0,
    ring: 1,
    parentId: null,
  }))

  // Derive ring-2 child nodes for agents whose summary changed from previous round
  const childNodes: AgentCardData[] = []
  const derivationEdges: AgentEdge[] = []

  if (round > 1 && Object.keys(prevSummaries).length > 0) {
    for (const agent of baseAgents) {
      const prevSummary = prevSummaries[agent.id]
      if (prevSummary && prevSummary !== agent.summary) {
        const childId = `${agent.id}_r${round}`
        childNodes.push({
          ...agent,
          id: childId,
          title: `${agent.title} · R${round}`,
          subtitle: '新观点',
          ring: 2,
          parentId: agent.id,
        })
        derivationEdges.push({
          id: `deriv-${agent.id}-r${round}`,
          from: agent.id,
          to: childId,
          type: 'derivation',
          label: `R${round} 衍生`,
        })
      }
    }
  }

  return {
    quality: runState.quality,
    environmentState: runState.environmentState,
    commandDraft: mockCanvasState.commandDraft,
    leftPanel: {
      ...mockCanvasState.leftPanel,
      recentEvents: inputEvents.map(toRecentEvent),
    },
    agents: [...baseAgents, ...childNodes],
    edges: [...mockCanvasState.edges, ...derivationEdges],
  }
}

function toRecentEvent(event: SandboxInputEvent): RecentEvent {
  return {
    title: event.content.split('\n')[0] ?? event.eventType,
    dimension: String(event.metadata?.dimension ?? event.eventType ?? 'manual'),
    impactDirection: (event.metadata?.impact_direction as RecentEvent['impactDirection'] | undefined) ?? 'neutral',
    impactStrength: Number(event.metadata?.impact_strength ?? 0),
    summary: event.content,
    syncedAt: '刚刚',
  }
}
