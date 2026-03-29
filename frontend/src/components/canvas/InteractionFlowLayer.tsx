import type { SandboxAgentId } from '../../lib/types/sandbox'
import { CARD_WIDTH } from './AgentNode'
import { INTERACTION_PANEL_WIDTH } from './InteractionSummaryPanel'

type Props = {
  isActive: boolean
  agentOrder: SandboxAgentId[]
  agentPositions: Record<string, { x: number; y: number }>
  panelPosition: { x: number; y: number }
}

export function InteractionFlowLayer({ isActive, agentOrder, agentPositions, panelPosition }: Props) {
  if (!isActive || agentOrder.length === 0) {
    return null
  }

  const targetX = panelPosition.x + INTERACTION_PANEL_WIDTH / 2
  const targetY = panelPosition.y + 10

  return (
    <svg className="interaction-flow-layer" viewBox="0 0 1600 1100" preserveAspectRatio="none" aria-hidden="true">
      <g className="interaction-flow-layer__group">
        {agentOrder.map((agentId) => {
          const source = agentPositions[agentId]
          if (!source) return null
          const sourceX = source.x + CARD_WIDTH / 2
          const sourceY = source.y + 276
          const curveMidY = Math.max(sourceY + 70, targetY - 96)
          const path = `M ${sourceX} ${sourceY} C ${sourceX} ${curveMidY}, ${targetX} ${curveMidY}, ${targetX} ${targetY}`
          return (
            <g key={agentId}>
              <path className="interaction-flow-line" d={path} />
            </g>
          )
        })}
      </g>
    </svg>
  )
}
