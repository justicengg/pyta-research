import '../../styles/meridian-grid.css'
import type { AgentCardData, SceneParams } from '../../lib/types/canvas'

interface MeridianGridViewProps {
  agents: AgentCardData[]
  isRunning: boolean
  sceneParams: SceneParams
}

function statusLabel(status: AgentCardData['status']): string {
  if (status === 'live') return '● Live'
  if (status === 'reused_last_round') return '↺ 复用'
  return '⚠ 降级'
}

function sentimentLabel(sentiment: AgentCardData['sentiment']): string {
  if (sentiment === 'bullish') return '看多'
  if (sentiment === 'bearish') return '看空'
  return '中性'
}

function FieldSection({ label, items }: { label: string; items: string[] }) {
  if (!items || items.length === 0) return null
  return (
    <div className="meridian-field-section">
      <div className="meridian-field-label">{label}</div>
      <ul className="meridian-field-list">
        {items.slice(0, 3).map((item, i) => (
          <li key={i} className="meridian-field-item">{item}</li>
        ))}
      </ul>
    </div>
  )
}

export function MeridianGridView({ agents, isRunning, sceneParams }: MeridianGridViewProps) {
  const ring1Agents = agents.filter(a => (a.ring ?? 1) === 1)

  return (
    <div className={`meridian-grid${isRunning ? ' meridian-grid--running' : ''}`}>
      {/* Core card column */}
      <div className="meridian-core-col">
        <div className="meridian-col-header meridian-core-header">
          <div className="meridian-core-ticker">{sceneParams.ticker}</div>
          <div className="meridian-col-meta">
            <span className="meridian-core-badge">{sceneParams.market}</span>
            <span className="meridian-core-badge">{sceneParams.timeHorizon}</span>
          </div>
          <div className="meridian-conf-bar">
            <div className="meridian-conf-fill meridian-conf-fill--neutral" style={{ width: '100%' }} />
          </div>
          <div className="meridian-conf-value">{ring1Agents.length} 个 Agent</div>
        </div>
      </div>

      {/* Agent columns */}
      {ring1Agents.map(agent => (
        <div
          key={agent.id}
          className={`meridian-agent-col meridian-agent-col--${agent.tint}${isRunning && agent.status === 'live' ? ' meridian-agent-col--loading' : ''}`}
        >
          {/* Header: name, status, sentiment, confidence bar */}
          <div className="meridian-col-header">
            <div className="meridian-col-title">{agent.title}</div>
            <div className="meridian-col-meta">
              <span className={`meridian-status meridian-status--${agent.status}`}>
                {statusLabel(agent.status)}
              </span>
              <span className={`meridian-sentiment meridian-sentiment--${agent.sentiment}`}>
                {sentimentLabel(agent.sentiment)}
              </span>
            </div>
            <div className="meridian-conf-bar">
              <div
                className={`meridian-conf-fill meridian-conf-fill--${agent.sentiment}`}
                style={{ width: `${agent.confidence}%` }}
              />
            </div>
            <div className="meridian-conf-value">{agent.confidence}%</div>
          </div>

          {/* 3 field sections */}
          <div className="meridian-fields">
            <FieldSection label="核心判断" items={agent.observations} />
            <FieldSection label="风险因素" items={agent.concerns} />
            <FieldSection label="信号来源" items={agent.focus} />
          </div>
        </div>
      ))}
    </div>
  )
}
