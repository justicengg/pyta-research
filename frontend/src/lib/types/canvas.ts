import type { SandboxActionBias, SandboxEnvironmentState, SandboxEnvironmentType } from './sandbox'

export type AgentStatus = 'live' | 'reused_last_round' | 'degraded'

export type AgentSentiment = 'bullish' | 'neutral' | 'bearish'

export type SceneParams = {
  ticker: string       // e.g. '0700.HK'
  market: string       // e.g. 'HK' | 'US' | 'A'
  timeHorizon: string  // e.g. '3个月'
}

export type AgentCardData = {
  id: string
  title: string
  subtitle: string
  tint: 'traditional' | 'offshore' | 'retail' | 'quant' | 'shortTerm'
  status: AgentStatus
  summary: string
  observations: string[]
  concerns: string[]
  focus: string[]
  actionBias: SandboxActionBias
  actionSummary: string
  keyDrivers: string[]
  affectedEnvironmentTypes: SandboxEnvironmentType[]
  actionHorizon: 'intraday' | 'short_term' | 'mid_term' | 'long_term'
  position: { x: number; y: number }
  round?: number      // which inference round this data came from
  sentiment: AgentSentiment
  confidence: number  // 0–100
  // Topology fields
  ring?: number         // 1 = base agent, 2 = derived conclusion, 3 = synthesis node
  parentId?: string | null  // null = base agent; string = parent agent id
  angleHint?: number    // preferred angle in radians (inherited from parent)
}

export type RoundRecord = {
  round: number
  narrative: string
  agentSummaries: Record<string, string>  // agentId → summary
  quality: 'complete' | 'partial' | 'degraded'
  timestamp: string
}

export type AgentEdge = {
  id: string
  from: string   // agentId or 'center'
  to: string     // agentId or 'center'
  type: 'spoke' | 'peer' | 'derivation' | 'synthesis'
  label?: string
}

export type ConnectorStatus = 'healthy' | 'syncing' | 'error' | 'inactive'
export type CostLabel = 'free' | 'freemium' | 'paid' | 'enterprise'
export type UsageLevel = 'exploratory' | 'operational' | 'institutional_grade'

export type ConnectorSource = {
  id: string
  title: string
  provider: string
  capabilities: string[]
  cost: CostLabel
  usageLevel: UsageLevel
  status: ConnectorStatus
  lastSyncedAt: string | null
}

export type RecentEvent = {
  title: string
  dimension: string
  impactDirection: 'positive' | 'negative' | 'neutral'
  impactStrength: number
  summary: string
  syncedAt: string
}

export type RecommendedBundle = {
  name: string
  reason: string
  capabilities: string[]
}

export type CanvasState = {
  quality: 'complete' | 'partial' | 'degraded'
  environmentState: SandboxEnvironmentState | null
  leftPanel: {
    connectedSources: ConnectorSource[]
    recentEvents: RecentEvent[]
    recommendedBundles: RecommendedBundle[]
  }
  commandDraft: string
  agents: AgentCardData[]
  edges: AgentEdge[]
}
