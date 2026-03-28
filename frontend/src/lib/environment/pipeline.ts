import type {
  SandboxEnvironmentBucket,
  SandboxEnvironmentSignal,
  SandboxEnvironmentState,
  SandboxEnvironmentType,
  SandboxInputEvent,
  SandboxRiskTone,
  SandboxSignalDirection,
  SandboxTimeHorizon,
} from '../types/sandbox'

const ENVIRONMENT_LABELS: Record<SandboxEnvironmentType, string> = {
  geopolitics: '地缘政治',
  macro_policy: '宏观政策',
  market_sentiment: '市场情绪',
  fundamentals: '公司基本面',
  alternative_data: '另类数据',
}

const ENVIRONMENT_ORDER: SandboxEnvironmentType[] = [
  'geopolitics',
  'macro_policy',
  'market_sentiment',
  'fundamentals',
  'alternative_data',
]

const KEYWORD_RULES: Array<{ type: SandboxEnvironmentType; keywords: string[] }> = [
  { type: 'geopolitics', keywords: ['tariff', 'sanction', 'war', 'geopolit', '出口', '制裁', '关税', '冲突', '地缘'] },
  { type: 'macro_policy', keywords: ['fed', 'fomc', 'rate', 'cpi', 'ppi', 'policy', '宏观', '利率', '降息', '加息', '监管', '政策'] },
  { type: 'market_sentiment', keywords: ['sentiment', 'fear', 'greed', 'panic', 'social', '情绪', '舆情', '热度', '恐慌'] },
  { type: 'fundamentals', keywords: ['earnings', 'revenue', 'margin', 'guidance', '财报', '利润', '收入', '基本面', '订单'] },
  { type: 'alternative_data', keywords: ['download', 'traffic', 'hiring', 'satellite', '另类', '下载量', '流量', '招聘', '渠道'] },
]

export function buildEnvironmentStateFromInputEvents(
  events: SandboxInputEvent[],
  symbol: string | null,
  market: string | null,
): SandboxEnvironmentState {
  const signals = events.flatMap((event) => normalizeEventToSignals(event, symbol, market))
  const buckets = ENVIRONMENT_ORDER.map((type) => buildBucket(type, signals))
  return {
    sandboxId: null,
    symbol,
    market,
    buckets,
    globalRiskTone: deriveGlobalRiskTone(buckets),
    updatedAt: new Date().toISOString(),
    version: 1,
  }
}

function normalizeEventToSignals(
  event: SandboxInputEvent,
  symbol: string | null,
  market: string | null,
): SandboxEnvironmentSignal[] {
  const categories = classifyEvent(event)
  const title = event.content.split('\n')[0]?.trim() || event.eventType
  const summary = event.content.trim()

  return categories.map((environmentType, index) => ({
    id: `${event.eventId}:${environmentType}:${index}`,
    messageId: event.eventId,
    environmentType,
    title,
    summary,
    direction: deriveDirection(event),
    strength: deriveStrength(event),
    horizon: deriveHorizon(event),
    relatedSymbols: compactStrings([event.symbol ?? symbol]),
    relatedMarkets: compactStrings([market]),
    entities: compactStrings([event.symbol ?? symbol, event.source]),
    tags: categories,
    detectedAt: event.timestamp,
    expiresAt: null,
    evidence: [{ kind: 'event', value: title }],
  }))
}

function classifyEvent(event: SandboxInputEvent): SandboxEnvironmentType[] {
  const explicitDimension = String(event.metadata?.dimension ?? event.eventType ?? '').toLowerCase()
  const content = `${event.eventType} ${event.content}`.toLowerCase()
  const matches = new Set<SandboxEnvironmentType>()

  if (explicitDimension.includes('geo')) matches.add('geopolitics')
  if (explicitDimension.includes('macro') || explicitDimension.includes('policy')) matches.add('macro_policy')
  if (explicitDimension.includes('sentiment') || explicitDimension.includes('social')) matches.add('market_sentiment')
  if (explicitDimension.includes('fundamental') || explicitDimension.includes('earning')) matches.add('fundamentals')
  if (explicitDimension.includes('alternative') || explicitDimension.startsWith('alt')) matches.add('alternative_data')

  for (const rule of KEYWORD_RULES) {
    if (rule.keywords.some((keyword) => content.includes(keyword))) {
      matches.add(rule.type)
    }
  }

  if (matches.size === 0) {
    matches.add('market_sentiment')
  }

  return ENVIRONMENT_ORDER.filter((type) => matches.has(type))
}

function deriveDirection(event: SandboxInputEvent): SandboxSignalDirection {
  const explicit = String(event.metadata?.impact_direction ?? '').toLowerCase()
  if (explicit === 'positive' || explicit === 'negative' || explicit === 'neutral') {
    return explicit
  }
  const content = event.content.toLowerCase()
  if (/(beat|surge|expand|upgrade|positive|improve|利好|回暖|增长|超预期)/.test(content)) return 'positive'
  if (/(cut|downgrade|panic|risk-off|negative|miss|利空|下滑|承压|鹰派)/.test(content)) return 'negative'
  return 'neutral'
}

function deriveStrength(event: SandboxInputEvent): 1 | 2 | 3 | 4 | 5 {
  const explicit = Number(event.metadata?.impact_strength ?? 0)
  if (explicit >= 0.85) return 5
  if (explicit >= 0.65) return 4
  if (explicit >= 0.45) return 3
  if (explicit >= 0.2) return 2

  const length = event.content.length
  if (length > 320) return 4
  if (length > 160) return 3
  return 2
}

function deriveHorizon(event: SandboxInputEvent): SandboxTimeHorizon {
  const content = `${event.eventType} ${event.content}`.toLowerCase()
  if (/(intraday|today|盘中|今日|短线|次日)/.test(content)) return 'intraday'
  if (/(week|short|短期|几天|几周)/.test(content)) return 'short_term'
  if (/(quarter|earnings|财报|季度|中期)/.test(content)) return 'mid_term'
  return 'long_term'
}

function buildBucket(
  type: SandboxEnvironmentType,
  signals: SandboxEnvironmentSignal[],
): SandboxEnvironmentBucket {
  const activeSignals = signals.filter((signal) => signal.environmentType === type)
  if (activeSignals.length === 0) {
    return {
      type,
      displayName: ENVIRONMENT_LABELS[type],
      activeSignals: [],
      dominantDirection: 'neutral',
      aggregateStrength: 0,
      lastUpdatedAt: null,
      status: 'idle',
    }
  }

  return {
    type,
    displayName: ENVIRONMENT_LABELS[type],
    activeSignals,
    dominantDirection: dominantDirection(activeSignals),
    aggregateStrength: activeSignals.reduce((sum, signal) => sum + signal.strength, 0),
    lastUpdatedAt: activeSignals[0]?.detectedAt ?? null,
    status: 'active',
  }
}

function dominantDirection(signals: SandboxEnvironmentSignal[]): SandboxSignalDirection {
  const positive = signals.reduce((sum, signal) => sum + (signal.direction === 'positive' ? signal.strength : 0), 0)
  const negative = signals.reduce((sum, signal) => sum + (signal.direction === 'negative' ? signal.strength : 0), 0)
  if (positive > 0 && negative > 0) return 'mixed'
  if (positive > 0) return 'positive'
  if (negative > 0) return 'negative'
  return 'neutral'
}

function deriveGlobalRiskTone(buckets: SandboxEnvironmentBucket[]): SandboxRiskTone {
  const positive = buckets.reduce((sum, bucket) => sum + (bucket.dominantDirection === 'positive' ? bucket.aggregateStrength : 0), 0)
  const negative = buckets.reduce((sum, bucket) => sum + (bucket.dominantDirection === 'negative' ? bucket.aggregateStrength : 0), 0)
  if (positive > 0 && negative > 0) return 'mixed'
  if (negative > positive && negative > 0) return 'risk_off'
  if (positive > negative && positive > 0) return 'risk_on'
  return 'neutral'
}

function compactStrings(values: Array<string | null | undefined>): string[] {
  return [...new Set(values.map((value) => value?.trim()).filter((value): value is string => Boolean(value)))]
}
