import type { AgentStatus } from '../../lib/types/canvas'

const statusLabel: Record<AgentStatus, string> = {
  live: 'Live',
  reused_last_round: 'Reused',
  degraded: 'Degraded',
}

export function StatusDot({ status, isLoading }: { status: AgentStatus; isLoading?: boolean }) {
  return (
    <span className={`status-chip status-${status}${isLoading ? ' status-thinking' : ''}`}>
      <span className="status-chip-dot" />
      {isLoading ? '思考中…' : statusLabel[status]}
    </span>
  )
}
