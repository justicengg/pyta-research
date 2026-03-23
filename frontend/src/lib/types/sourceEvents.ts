export type SourceEvent = {
  id: string
  connector_id: string
  provider_id: string
  title: string
  summary: string | null
  dimension: string | null
  impact_direction: 'positive' | 'negative' | 'neutral'
  impact_strength: number
  published_at: string | null
  ingested_at: string
  symbols: string[]
}

export type SourceEventsResponse = {
  total: number
  items: SourceEvent[]
}
