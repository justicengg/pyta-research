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

export type StreamItem = {
  title: string
  description: string
}

export type SourceItem = {
  title: string
  description: string
}

export type CanvasState = {
  quality: 'complete' | 'partial' | 'degraded'
  leftPanel: {
    connectedSources: SourceItem[]
    liveEvents: StreamItem[]
    recommendedFeeds: StreamItem[]
  }
  commandDraft: string
  agents: AgentCardData[]
}
