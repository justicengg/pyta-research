import { useState } from 'react'
import type { AgentCardData, AgentSentiment } from '../../lib/types/canvas'

type Props = {
  agent: AgentCardData
}

const SENTIMENT_LABEL: Record<AgentSentiment, string> = {
  bullish: '看多',
  neutral: '中性',
  bearish: '看空',
}

export function AgentResultCard({ agent }: Props) {
  const [expanded, setExpanded] = useState(false)
  const confidence = Math.max(0, Math.min(100, agent.confidence ?? 0))
  const hasDetails =
    agent.observations.length > 0 ||
    agent.concerns.length > 0 ||
    agent.focus.length > 0

  return (
    <div className="agent-result-card">
      {/* Row 1: sentiment badge + confidence value */}
      <div className="arc-header">
        <span className={`sentiment-badge sentiment-badge--${agent.sentiment}`}>
          {SENTIMENT_LABEL[agent.sentiment]}
        </span>
        <span className="confidence-value">{confidence}%</span>
      </div>

      {/* Row 2: confidence bar */}
      <div className="confidence-bar">
        <div
          className="confidence-bar-fill"
          style={{ width: `${confidence}%` }}
        />
      </div>

      {/* Row 3: one-line stance */}
      <p className="stance-summary">{agent.summary}</p>

      {/* Row 4: expandable detail */}
      {hasDetails && (
        <>
          <button
            className={`detail-toggle${expanded ? ' detail-toggle--open' : ''}`}
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
          >
            <span>{expanded ? '收起详情' : '展开详情'}</span>
            <svg className="detail-chevron" width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>

          {expanded && (
            <div className="detail-content">
              {agent.observations.length > 0 && (
                <div className="agent-result-group">
                  <strong>观察</strong>
                  <ul>{agent.observations.map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
              )}
              {agent.concerns.length > 0 && (
                <div className="agent-result-group">
                  <strong>顾虑</strong>
                  <ul>{agent.concerns.map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
              )}
              {agent.focus.length > 0 && (
                <div className="agent-result-group">
                  <strong>关注点</strong>
                  <ul>{agent.focus.map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
