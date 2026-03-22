import type { CSSProperties } from 'react'

export type AgentStatus = 'live' | 'reused_last_round' | 'degraded'

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
  position: {
    top?: string
    left?: string
    right?: string
    bottom?: string
  }
}

export type PositionedCanvasAgentCard = Omit<AgentCardData, 'position'> & {
  position: CSSProperties
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
  leftPanel: {
    connectedSources: ConnectorSource[]
    recentEvents: RecentEvent[]
    recommendedBundles: RecommendedBundle[]
  }
  commandDraft: string
  agents: AgentCardData[]
}
