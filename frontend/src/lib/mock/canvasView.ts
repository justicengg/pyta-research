import type { CSSProperties } from 'react'
import type { CanvasAgentCard, SandboxAgentId } from '../types/sandbox'
import type { PositionedCanvasAgentCard } from '../types/canvas'

const AGENT_POSITIONS: Record<SandboxAgentId, CSSProperties> = {
  traditional_institution: { left: '118px', top: '156px' },
  offshore_capital: { right: '126px', top: '156px' },
  retail: { left: '160px', bottom: '128px' },
  quant_institution: { left: '448px', bottom: '62px' },
  short_term_capital: { right: '146px', bottom: '116px' },
}

export function attachAgentPositions(agents: CanvasAgentCard[]): PositionedCanvasAgentCard[] {
  return agents.map((agent) => ({
    ...agent,
    position: AGENT_POSITIONS[agent.id],
  }))
}
