import type { SandboxAgentId, SandboxEnvironmentType } from '../../lib/types/sandbox'
import { CARD_WIDTH } from './AgentNode'

type Props = {
  isActive: boolean
  agentOrder: SandboxAgentId[]
  agentPositions: Record<string, { x: number; y: number }>
  anchors?: Partial<Record<SandboxEnvironmentType, { x: number; y: number }>>
}

const ENVIRONMENT_ANCHORS: Record<SandboxEnvironmentType, { x: number; y: number; label: string }> = {
  geopolitics: { x: 150, y: 92, label: '地缘政治' },
  macro_policy: { x: 370, y: 80, label: '宏观政策' },
  market_sentiment: { x: 600, y: 72, label: '市场情绪' },
  fundamentals: { x: 830, y: 80, label: '公司基本面' },
  alternative_data: { x: 1050, y: 92, label: '另类数据' },
}

const ENVIRONMENT_ORDER: SandboxEnvironmentType[] = [
  'geopolitics',
  'macro_policy',
  'market_sentiment',
  'fundamentals',
  'alternative_data',
]

export function EnvironmentFlowLayer({ isActive, agentOrder, agentPositions, anchors = {} }: Props) {
  if (!isActive || agentOrder.length === 0) {
    return null
  }

  return (
    <svg className="environment-flow-layer" viewBox="0 0 1200 900" preserveAspectRatio="none" aria-hidden="true">
      <g className="environment-flow-layer__group">
        {agentOrder.map((agentId, index) => {
          const environmentType = ENVIRONMENT_ORDER[index]
          const baseAnchor = ENVIRONMENT_ANCHORS[environmentType]
          const measuredAnchor = anchors[environmentType]
          const anchor = measuredAnchor ?? baseAnchor
          const target = agentPositions[agentId]
          if (!target) return null
          const targetX = target.x + CARD_WIDTH / 2
          const targetY = target.y + 12
          const curveMidY = Math.min(targetY - 110, 232)
          const path = `M ${anchor.x} ${anchor.y} C ${anchor.x} ${curveMidY}, ${targetX} ${curveMidY}, ${targetX} ${targetY}`
          return (
            <g key={agentId}>
              <circle className="environment-flow-anchor" cx={anchor.x} cy={anchor.y} r={9} />
              <text className="environment-flow-anchor-label" x={anchor.x} y={anchor.y - 18} textAnchor="middle">
                {baseAnchor.label}
              </text>
              <path className="environment-flow-line" d={path} />
            </g>
          )
        })}
      </g>
    </svg>
  )
}
