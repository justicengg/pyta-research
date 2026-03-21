import type { AgentCardData } from '../../lib/types/canvas'

type Props = {
  agent: AgentCardData
}

export function AgentResultCard({ agent }: Props) {
  return (
    <div className="agent-result-card">
      <p className="agent-result-summary">{agent.summary}</p>
      <div className="agent-result-group">
        <strong>Observations</strong>
        <ul>
          {agent.observations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <div className="agent-result-group">
        <strong>Concerns</strong>
        <ul>
          {agent.concerns.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <div className="agent-result-group">
        <strong>Focus</strong>
        <ul>
          {agent.focus.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
