import type { AgentStatus } from '../../lib/types/canvas'

const statusLabel: Record<AgentStatus, string> = {
  live: 'Live',
  reused_last_round: 'Reused',
  degraded: 'Degraded',
}

export function StatusDot({ status }: { status: AgentStatus }) {
  return (
    <span className={`status-chip status-${status}`}>
      <span className="status-chip-dot" />
      {statusLabel[status]}
    </span>
  )
}
