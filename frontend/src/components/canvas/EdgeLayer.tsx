import { useState } from 'react'
import type { AgentEdge } from '../../lib/types/canvas'
import { CARD_WIDTH, CARD_HEADER_HEIGHT } from './AgentNode'

type AgentPos = { x: number; y: number }

type Props = {
  edges: AgentEdge[]
  agentPositions: Record<string, AgentPos>
  centerPos: AgentPos
}

// Center core card approximate half-width (matches CSS .center-core ~256px wide)
const CENTER_HALF_W = 128

// Tint colors for spoke edges — muted versions of each agent's tint token
const TINT_COLORS: Record<string, string> = {
  traditional: '#6b7faa',
  offshore:    '#5a9e8a',
  retail:      '#b07a4f',
  quant:       '#7a6baa',
  shortTerm:   '#a06b6b',
}

// tint lookup by agentId
const AGENT_TINT: Record<string, string> = {
  traditional_institution: 'traditional',
  offshore_capital:        'offshore',
  retail:                  'retail',
  quant_institution:       'quant',
  short_term_capital:      'shortTerm',
}

function getCardCenter(pos: AgentPos) {
  return { cx: pos.x + CARD_WIDTH / 2, cy: pos.y + CARD_HEADER_HEIGHT / 2 }
}

function getCenterAnchor(pos: AgentPos) {
  // Center core is placed with translate(-50%,-50%) so its visual center is exactly pos
  return { cx: pos.x, cy: pos.y }
}

// Cubic Bézier from (x1,y1) to (x2,y2) with gentle arc
function bezierPath(x1: number, y1: number, x2: number, y2: number, lateralOffset: number) {
  const mx = (x1 + x2) / 2
  const my = (y1 + y2) / 2
  const dx = x2 - x1
  const dy = y2 - y1
  const len = Math.sqrt(dx * dx + dy * dy) || 1
  // Perpendicular direction
  const perpX = -dy / len
  const perpY = dx / len

  const cp1x = x1 + (mx - x1) * 0.5 + perpX * lateralOffset
  const cp1y = y1 + (my - y1) * 0.5 + perpY * lateralOffset
  const cp2x = x2 + (mx - x2) * 0.5 + perpX * lateralOffset
  const cp2y = y2 + (my - y2) * 0.5 + perpY * lateralOffset

  return `M ${x1} ${y1} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${x2} ${y2}`
}

// Shorten a segment so the line visually stops at the card border, not the center
function shortenLine(
  x1: number, y1: number,
  x2: number, y2: number,
  shortenStart: number,
  shortenEnd: number
) {
  const dx = x2 - x1
  const dy = y2 - y1
  const len = Math.sqrt(dx * dx + dy * dy) || 1
  const nx = dx / len
  const ny = dy / len
  return {
    sx: x1 + nx * shortenStart,
    sy: y1 + ny * shortenStart,
    ex: x2 - nx * shortenEnd,
    ey: y2 - ny * shortenEnd,
  }
}

type EdgeLineProps = {
  edge: AgentEdge
  fromPos: AgentPos
  toPos: AgentPos
  fromIsCenter: boolean
  toIsCenter: boolean
}

function EdgeLine({ edge, fromPos, toPos, fromIsCenter, toIsCenter }: EdgeLineProps) {
  const [hovered, setHovered] = useState(false)

  const fc = fromIsCenter ? getCenterAnchor(fromPos) : getCardCenter(fromPos)
  const tc = toIsCenter   ? getCenterAnchor(toPos)   : getCardCenter(toPos)

  const isSpoke = edge.type === 'spoke'
  // Shorten so line doesn't poke through the card/core visuals
  const startGap = fromIsCenter ? CENTER_HALF_W * 0.7 : CARD_WIDTH * 0.35
  const endGap   = toIsCenter   ? CENTER_HALF_W * 0.7 : CARD_WIDTH * 0.35

  const { sx, sy, ex, ey } = shortenLine(fc.cx, fc.cy, tc.cx, tc.cy, startGap, endGap)

  const lateralOffset = isSpoke ? 45 : 25
  const d = bezierPath(sx, sy, ex, ey, lateralOffset)

  // Spoke color = agent tint, peer color = neutral gray
  const agentId = fromIsCenter ? edge.to : edge.from
  const tint = AGENT_TINT[agentId] ?? 'traditional'
  const strokeColor = isSpoke ? (TINT_COLORS[tint] ?? '#888') : 'var(--border, #888)'
  const strokeWidth  = isSpoke ? (hovered ? 2.5 : 1.5) : (hovered ? 1.5 : 1)
  const opacity      = isSpoke ? (hovered ? 0.9 : 0.55) : (hovered ? 0.7 : 0.35)
  const dashArray    = isSpoke ? undefined : '5 4'

  const arrowId = `arrow-${edge.id}`

  return (
    <g>
      <defs>
        <marker
          id={arrowId}
          markerWidth="8"
          markerHeight="8"
          refX="6"
          refY="3"
          orient="auto"
          markerUnits="userSpaceOnUse"
        >
          <path d="M0,0 L0,6 L8,3 z" fill={strokeColor} opacity={opacity} />
        </marker>
      </defs>

      {/* Invisible hit-target for easy hover */}
      <path
        d={d}
        fill="none"
        stroke="transparent"
        strokeWidth={12}
        style={{ pointerEvents: 'stroke', cursor: 'default' }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />

      {/* Visible edge */}
      <path
        d={d}
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeDasharray={dashArray}
        opacity={opacity}
        markerEnd={`url(#${arrowId})`}
        style={{ pointerEvents: 'none', transition: 'stroke-width 0.15s, opacity 0.15s' }}
      />

      {/* Hover label */}
      {hovered && edge.label && (
        <text
          x={(sx + ex) / 2}
          y={(sy + ey) / 2 - 8}
          textAnchor="middle"
          fontSize="11"
          fill={strokeColor}
          opacity={0.9}
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          {edge.label}
        </text>
      )}
    </g>
  )
}

export function EdgeLayer({ edges, agentPositions, centerPos }: Props) {
  return (
    <svg
      className="canvas-edges"
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        overflow: 'visible',
        pointerEvents: 'none',
      }}
    >
      {edges.map((edge) => {
        const fromIsCenter = edge.from === 'center'
        const toIsCenter   = edge.to   === 'center'
        const fromPos = fromIsCenter ? centerPos : agentPositions[edge.from]
        const toPos   = toIsCenter   ? centerPos : agentPositions[edge.to]
        if (!fromPos || !toPos) return null
        return (
          <EdgeLine
            key={edge.id}
            edge={edge}
            fromPos={fromPos}
            toPos={toPos}
            fromIsCenter={fromIsCenter}
            toIsCenter={toIsCenter}
          />
        )
      })}
    </svg>
  )
}
