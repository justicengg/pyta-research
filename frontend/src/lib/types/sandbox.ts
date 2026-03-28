export type SandboxSessionStatus = 'initializing' | 'running' | 'complete' | 'partial' | 'degraded' | 'error'

/**
 * 细粒度管线阶段状态 — 对应双层推演的内部处理步骤
 * 用于驱动前端 Environment Bar 的时序动效
 *
 * ingesting         → 消息已进入，等待分类
 * classifying       → Layer 1: 正在分类 + 清洗（chip 扫描动效触发阶段）
 * environment_ready → Environment Bar 已更新，等待派发 Agent
 * simulating        → Layer 2: 5 个 Agent 正在动作模拟
 * completed         → 本轮推演结束
 * failed            → 管线异常中断
 */
export type SandboxPipelineStage =
  | 'ingesting'
  | 'classifying'
  | 'environment_ready'
  | 'simulating'
  | 'completed'
  | 'failed'
export type SandboxPerspectiveStatus = 'live' | 'reused_last_round' | 'degraded'
export type SandboxMarketBias = 'bullish' | 'bearish' | 'neutral' | 'mixed'
export type SandboxEnvironmentType =
  | 'geopolitics'
  | 'macro_policy'
  | 'market_sentiment'
  | 'fundamentals'
  | 'alternative_data'
export type SandboxSignalDirection = 'positive' | 'negative' | 'mixed' | 'neutral'
export type SandboxTimeHorizon = 'intraday' | 'short_term' | 'mid_term' | 'long_term'
export type SandboxRiskTone = 'risk_on' | 'risk_off' | 'mixed' | 'neutral'
export type SandboxActionBias = 'accumulate' | 'reduce' | 'hold' | 'watch' | 'hedge' | 'chase' | 'exit'
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

export type SandboxEnvironmentEvidence = {
  kind: 'quote' | 'metric' | 'event'
  value: string
}

export type SandboxEnvironmentSignal = {
  id: string
  messageId: string
  environmentType: SandboxEnvironmentType
  title: string
  summary: string
  direction: SandboxSignalDirection
  strength: 1 | 2 | 3 | 4 | 5
  horizon: SandboxTimeHorizon
  relatedSymbols: string[]
  relatedMarkets: string[]
  entities: string[]
  tags: string[]
  detectedAt: string
  expiresAt?: string | null
  evidence: SandboxEnvironmentEvidence[]
}

export type SandboxEnvironmentBucket = {
  type: SandboxEnvironmentType
  displayName: string
  activeSignals: SandboxEnvironmentSignal[]
  dominantDirection: SandboxSignalDirection
  aggregateStrength: number
  lastUpdatedAt?: string | null
  status: 'idle' | 'active' | 'cooling'
}

export type SandboxEnvironmentState = {
  sandboxId?: string | null
  symbol?: string | null
  market?: string | null
  buckets: SandboxEnvironmentBucket[]
  globalRiskTone: SandboxRiskTone
  updatedAt: string
  version: number
}

export type SandboxRunRequest = {
  ticker: string
  market: string
  events: SandboxInputEvent[]
  environmentState?: SandboxEnvironmentState | null
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

export type BackendSandboxEnvironmentEvidence = {
  kind: 'quote' | 'metric' | 'event'
  value: string
}

export type BackendSandboxEnvironmentSignal = {
  id: string
  message_id: string
  environment_type: SandboxEnvironmentType
  title: string
  summary: string
  direction: SandboxSignalDirection
  strength: 1 | 2 | 3 | 4 | 5
  horizon: SandboxTimeHorizon
  related_symbols: string[]
  related_markets: string[]
  entities: string[]
  tags: string[]
  detected_at: string
  expires_at?: string | null
  evidence: BackendSandboxEnvironmentEvidence[]
}

export type BackendSandboxEnvironmentBucket = {
  type: SandboxEnvironmentType
  display_name: string
  active_signals: BackendSandboxEnvironmentSignal[]
  dominant_direction: SandboxSignalDirection
  aggregate_strength: number
  last_updated_at?: string | null
  status: 'idle' | 'active' | 'cooling'
}

export type BackendSandboxEnvironmentState = {
  sandbox_id?: string | null
  symbol?: string | null
  market?: string | null
  buckets: BackendSandboxEnvironmentBucket[]
  global_risk_tone: SandboxRiskTone
  updated_at: string
  version: number
}

export type BackendSandboxRunRequest = {
  ticker: string
  market: string
  events: BackendSandboxInputEvent[]
  environment_state?: BackendSandboxEnvironmentState | null
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

export type BackendAgentActionSnapshot = {
  agent_type: SandboxAgentId
  action_bias: SandboxActionBias
  confidence: number
  rationale_summary: string
  key_drivers: string[]
  affected_environment_types: SandboxEnvironmentType[]
  horizon: SandboxTimeHorizon
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
  action_detail?: Record<string, BackendAgentActionSnapshot> | null
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
  action_detail?: Record<string, BackendAgentActionSnapshot>
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
  environment_state?: BackendSandboxEnvironmentState | null
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
  actionBias: SandboxActionBias
  actionSummary: string
  keyDrivers: string[]
  affectedEnvironmentTypes: SandboxEnvironmentType[]
  actionHorizon: SandboxTimeHorizon
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
  environmentState: SandboxEnvironmentState | null
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
