import { useEffect, useMemo, useState } from 'react'
import type {
  SandboxAgentId,
  SandboxEnvironmentSignal,
  SandboxEnvironmentState,
  SandboxEnvironmentType,
  SandboxPipelineStage,
} from '../../lib/types/sandbox'

type Props = {
  state: SandboxEnvironmentState | null
  pipelineStage?: SandboxPipelineStage | 'idle'
  isRunning?: boolean
  onInspectChange?: (payload: {
    environmentType: SandboxEnvironmentType | null
    signalId: string | null
    agentIds: SandboxAgentId[]
  }) => void
}

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

const RISK_TONE_LABEL: Record<string, string> = {
  risk_on: '↑ 风险偏好',
  risk_off: '↓ 风险规避',
  mixed: '↕ 信号分化',
  neutral: '— 中性基准',
}

const AFFECTED_AGENT_MAP: Record<SandboxEnvironmentType, SandboxAgentId[]> = {
  geopolitics: ['offshore_capital', 'traditional_institution', 'short_term_capital'],
  macro_policy: ['traditional_institution', 'quant_institution', 'offshore_capital'],
  market_sentiment: ['retail', 'short_term_capital', 'quant_institution'],
  fundamentals: ['traditional_institution', 'quant_institution', 'retail'],
  alternative_data: ['quant_institution', 'short_term_capital', 'traditional_institution'],
}

export function EnvironmentBar({
  state,
  pipelineStage = 'idle',
  isRunning = false,
  onInspectChange,
}: Props) {
  const [expandedType, setExpandedType] = useState<SandboxEnvironmentType | null>(null)
  const [hoveredSignalId, setHoveredSignalId] = useState<string | null>(null)

  const buckets = useMemo(() => {
    if (!state) return []
    return ENVIRONMENT_ORDER.map((type) => state.buckets.find((bucket) => bucket.type === type)).filter(Boolean)
  }, [state]) as NonNullable<SandboxEnvironmentState>['buckets']

  const expandedBucket = expandedType
    ? buckets.find((bucket) => bucket.type === expandedType) ?? null
    : null

  const inspectedSignal = expandedBucket?.activeSignals.find((signal) => signal.id === hoveredSignalId) ?? null

  useEffect(() => {
    const environmentType = inspectedSignal?.environmentType ?? expandedType ?? null
    onInspectChange?.({
      environmentType,
      signalId: inspectedSignal?.id ?? null,
      agentIds: environmentType ? AFFECTED_AGENT_MAP[environmentType] : [],
    })
  }, [expandedType, inspectedSignal, onInspectChange])

  if (!state) {
    return null
  }

  return (
    <section
      className={`env-rail env-rail--${pipelineStage}${isRunning ? ' env-rail--running' : ''}`}
      aria-label="Environment Rail"
    >
      <div className="env-rail-head">
        <div className="env-rail-meta">
          <span className="env-rail-kicker">Environment Rail</span>
          <span className={`env-risk-badge env-risk-badge--${state.globalRiskTone}`}>
            {RISK_TONE_LABEL[state.globalRiskTone] ?? '— 中性基准'}
          </span>
        </div>
        <div className="env-rail-copy">
          <strong>环境信号先成型，再触发 5 个市场力量同步响应。</strong>
          <span>点击类别展开具体信号，悬停单条信号可查看它影响哪些 Agent。</span>
        </div>
      </div>

      <div className="env-rail-buckets">
        {buckets.map((bucket) => {
          const isExpanded = expandedType === bucket.type
          const isActive = bucket.status !== 'idle'
          return (
            <button
              key={bucket.type}
              type="button"
              className={`env-bucket${isExpanded ? ' env-bucket--expanded' : ''}${isActive ? ' env-bucket--active' : ''}`}
              onClick={() => {
                setHoveredSignalId(null)
                setExpandedType((current) => (current === bucket.type ? null : bucket.type))
              }}
            >
              <span className="env-bucket-topline">
                <span className={`env-bucket-dot env-bucket-dot--${bucket.status}`} />
                <span className="env-bucket-title">{ENVIRONMENT_LABELS[bucket.type]}</span>
              </span>
              <span className="env-bucket-bottomline">
                <span className={`env-bucket-direction env-bucket-direction--${bucket.dominantDirection}`}>
                  {renderDirection(bucket.dominantDirection)}
                </span>
                <span className="env-bucket-count">{bucket.activeSignals.length} signals</span>
                <span className="env-bucket-strength">S{bucket.aggregateStrength}</span>
              </span>
            </button>
          )
        })}
      </div>

      {expandedBucket ? (
        <div className="env-detail-tray">
          <div className="env-detail-head">
            <div>
              <strong>{expandedBucket.displayName}</strong>
              <p>
                当前共有 {expandedBucket.activeSignals.length} 条活跃信号，默认流向{' '}
                {AFFECTED_AGENT_MAP[expandedBucket.type].length} 个 Agent。
              </p>
            </div>
            <span className={`env-detail-status env-detail-status--${expandedBucket.status}`}>
              {expandedBucket.status}
            </span>
          </div>

          <div className="env-signal-list">
            {expandedBucket.activeSignals.length > 0 ? (
              expandedBucket.activeSignals.map((signal) => (
                <article
                  key={signal.id}
                  className={`env-signal-card${hoveredSignalId === signal.id ? ' env-signal-card--inspected' : ''}`}
                  onMouseEnter={() => setHoveredSignalId(signal.id)}
                  onMouseLeave={() => setHoveredSignalId(null)}
                >
                  <div className="env-signal-head">
                    <strong>{signal.title}</strong>
                    <span className={`env-signal-bias env-signal-bias--${signal.direction}`}>
                      {renderDirection(signal.direction)} · {signal.strength}
                    </span>
                  </div>
                  <p className="env-signal-summary">{signal.summary}</p>
                  <div className="env-signal-meta">
                    <span>{signal.horizon}</span>
                    <span>{signal.relatedMarkets.join(' / ') || 'market-wide'}</span>
                    <span>{signal.relatedSymbols.join(', ') || 'multi-asset'}</span>
                  </div>
                  <div className="env-signal-routing">
                    {AFFECTED_AGENT_MAP[signal.environmentType].map((agentId) => (
                      <span key={agentId} className="env-route-chip">
                        {renderAgentLabel(agentId)}
                      </span>
                    ))}
                  </div>
                </article>
              ))
            ) : (
              <div className="env-empty-state">当前没有活跃信号，环境变量仍处于基准态。</div>
            )}
          </div>
        </div>
      ) : null}
    </section>
  )
}

function renderDirection(direction: SandboxEnvironmentSignal['direction']): string {
  switch (direction) {
    case 'positive':
      return '↑'
    case 'negative':
      return '↓'
    case 'mixed':
      return '↕'
    default:
      return '—'
  }
}

function renderAgentLabel(agentId: SandboxAgentId): string {
  switch (agentId) {
    case 'traditional_institution':
      return '传统机构'
    case 'quant_institution':
      return '量化机构'
    case 'retail':
      return '普通散户'
    case 'offshore_capital':
      return '海外资金'
    case 'short_term_capital':
      return '短线资金'
  }
}
