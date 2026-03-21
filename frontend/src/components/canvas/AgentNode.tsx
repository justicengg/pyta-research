import type { CSSProperties } from 'react'
import type { AgentCardData } from '../../lib/types/canvas'
import { StatusDot } from '../common/StatusDot'
import { AgentResultCard } from './AgentResultCard'

type Props = {
  agent: AgentCardData
}

export function AgentNode({ agent }: Props) {
  const position = agent.position as CSSProperties

  return (
    <div className="agent-cluster" style={position}>
      <div className={`agent agent-${agent.tint}`}>
        <div className="agent-copy">
          <strong>{agent.title}</strong>
          <span>{agent.subtitle}</span>
          <p>{agent.summary}</p>
        </div>
        <StatusDot status={agent.status} />
      </div>
      <AgentResultCard agent={agent} />
    </div>
  )
}
