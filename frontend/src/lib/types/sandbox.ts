export type SandboxSessionStatus = 'initializing' | 'running' | 'complete' | 'partial' | 'degraded' | 'error'
export type SandboxPerspectiveStatus = 'live' | 'reused_last_round' | 'degraded'
export type SandboxMarketBias = 'bullish' | 'bearish' | 'neutral' | 'mixed'
export type SandboxAgentId =
  | 'traditional_institution'
  | 'quant_institution'
  | 'retail'
  | 'offshore_capital'
  | 'short_term_capital'

export const SANDBOX_AGENT_ORDER: SandboxAgentId[] = [
  'traditional_institution',
  'quant_institution',
  'retail',
  'offshore_capital',
  'short_term_capital',
]

export type SandboxInputEvent = {
  eventId: string
  eventType: string
  content: string
  source: string
  timestamp: string
  symbol?: string | null
  metadata?: Record<string, unknown>
}

export type SandboxRunRequest = {
  ticker: string
  market: string
  events: SandboxInputEvent[]
  roundTimeoutMs?: number
  narrativeGuide?: string | null
}

export type BackendSandboxInputEvent = {
  event_id: string
  event_type: string
  content: string
  source: string
  timestamp: string
  symbol?: string | null
  metadata?: Record<string, unknown>
}

export type BackendSandboxRunRequest = {
  ticker: string
  market: string
  events: BackendSandboxInputEvent[]
  round_timeout_ms?: number
  narrative_guide?: string | null
}

export type BackendPerAgentStatus = {
  agent_type: SandboxAgentId
  perspective_type: SandboxAgentId
  saturated: boolean
  perspective_status: SandboxPerspectiveStatus
  summary: string
}

export type BackendDivergenceItem = {
  agents: SandboxAgentId[]
  dimension: string
  direction: string
}

export type BackendRoundComplete = {
  sandbox_id: string
  ticker: string
  market: string
  rounds_completed: number
  stop_reason: string
  per_agent_status: BackendPerAgentStatus[]
  divergence_map: BackendDivergenceItem[]
  data_quality: 'complete' | 'partial' | 'degraded'
}

export type BackendTensionItem = {
  between: SandboxAgentId[]
  description: string
}

export type BackendAgentPerspective = {
  agent_type: SandboxAgentId
  perspective_type: SandboxAgentId
  market_bias: SandboxMarketBias
  key_observations: string[]
  key_concerns: string[]
  analytical_focus: string[]
  confidence: number
  perspective_status: SandboxPerspectiveStatus
}

export type BackendMarketReadingReport = {
  sandbox_id: string
  ticker: string
  generated_at: string
  perspective_synthesis: Record<string, string>
  key_tensions: BackendTensionItem[]
  tracking_signals: string[]
  data_quality: 'complete' | 'partial' | 'degraded'
  perspective_detail?: Record<string, BackendAgentPerspective> | null
}

export type BackendReportRecord = {
  id: string
  sandbox_id: string
  trace_id: string | null
  round: number
  report_type: string
  data_quality: 'complete' | 'partial' | 'degraded'
  perspective_synthesis: Record<string, string>
  key_tensions: BackendTensionItem[]
  tracking_signals: string[]
  per_agent_detail: Record<string, BackendAgentPerspective>
  assembly_notes: Record<string, unknown>
  generated_at: string
}

export type BackendCheckpoint = {
  id: string
  sandbox_id: string
  round: number
  completion_status: string
  active_agent_ids: string[]
  reused_agent_ids: string[]
  degraded_agent_ids: string[]
  round_summary: Record<string, unknown>
  created_at: string
}

export type BackendSandboxRunResponse = {
  sandbox_id: string
  session_status: SandboxSessionStatus
  round_complete: BackendRoundComplete
  report: BackendMarketReadingReport
}

export type BackendSandboxResultResponse = {
  sandbox_id: string
  ticker: string
  market: string
  session_status: SandboxSessionStatus
  current_round: number
  report: BackendReportRecord
  latest_checkpoint: BackendCheckpoint | null
}

export type CanvasAgentCard = {
  id: SandboxAgentId
  title: string
  subtitle: string
  tint: 'traditional' | 'offshore' | 'retail' | 'quant' | 'shortTerm'
  status: SandboxPerspectiveStatus
  summary: string
  observations: string[]
  concerns: string[]
  focus: string[]
  bias: SandboxMarketBias
  confidence: number
  perspectiveType: SandboxAgentId
  perspectiveStatus: SandboxPerspectiveStatus
  sourceTraceId?: string | null
}

export type CanvasInputEvent = SandboxInputEvent

export type CanvasTension = {
  between: SandboxAgentId[]
  description: string
}

export type CanvasRunState = {
  sandboxId: string
  ticker: string
  market: string
  sessionStatus: SandboxSessionStatus
  quality: 'complete' | 'partial' | 'degraded'
  stopReason: string | null
  round: number
  agents: CanvasAgentCard[]
  synthesis: Record<SandboxAgentId, string>
  tensions: CanvasTension[]
  trackingSignals: string[]
  inputEvents: CanvasInputEvent[]
  latestCheckpoint: BackendCheckpoint | null
  roundComplete?: BackendRoundComplete
  report: BackendMarketReadingReport | BackendReportRecord
}
