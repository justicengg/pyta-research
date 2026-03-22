import { useMemo, useState } from 'react'
import { mapRunResponseToCanvasState } from '../lib/adapters'
import { runSandbox } from '../lib/api'
import { mockCanvasState } from '../lib/mock/canvasState'
import type { CanvasState, RecentEvent, RoundRecord, SceneParams } from '../lib/types/canvas'
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
    const content = draft.trim()
    if (!content || isRunning) {
      return
    }

    const inputEvents = buildInputEvents(content)
    setCurrentInputEvents(inputEvents)
    setError(null)
    setIsRunning(true)
    setCanvasState((current) => ({
      ...current,
      leftPanel: {
        ...current.leftPanel,
        recentEvents: inputEvents.map<RecentEvent>((event) => ({
          title: event.eventType,
          dimension: 'manual',
          impactDirection: 'neutral',
          impactStrength: 0,
          summary: event.content,
          syncedAt: '方才',
        })),
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
        roundTimeoutMs: 60000,
        narrativeGuide: narrativeWithContext,
      })

      const mapped = mapRunResponseToCanvasState(response, { inputEvents })
      setBackendState(mapped)

      const round = currentRound
      const newCanvasState = mergeCanvasState(mapped, inputEvents, round)
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
  round: number
): CanvasState {
  const positionMap = new Map(mockCanvasState.agents.map((agent) => [agent.id, agent.position]))

  return {
    quality: runState.quality,
    commandDraft: mockCanvasState.commandDraft,
    leftPanel: {
      ...mockCanvasState.leftPanel,
      recentEvents: inputEvents.map<RecentEvent>((event) => ({
        title: event.eventType,
        dimension: 'manual',
        impactDirection: 'neutral',
        impactStrength: 0,
        summary: event.content,
        syncedAt: '刚刚',
      })),
    },
    agents: runState.agents.map((agent) => ({
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
    })),
    edges: mockCanvasState.edges,
  }
}
