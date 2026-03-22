import { useMemo } from 'react'
import type { AgentCardData } from '../lib/types/canvas'

type Pos = { x: number; y: number }

// Canvas logical center — matches canvas-layer 1200×900, CSS top:50% = 450
export const TOPOLOGY_CENTER: Pos = { x: 600, y: 450 }

// Ring radii: ring 1 = base agents, ring 2 = derived conclusions, ring 3 = synthesis
// Ring 1 = 310px: top card (y=140) clears center card (top=370), gap=130px ✓
// Ring 2 = 540px: minimum to clear parent card (ring1=310, CARD_H=200) → 310+200+30=540
//   Some ring-2 nodes extend slightly off-canvas; user pans to see them (canvas is pannable)
// Ring 3 = 750px: synthesis nodes; expected to extend beyond canvas, always panned to
const RING_RADIUS: Record<number, number> = {
  1: 310,
  2: 540,
  3: 750,
}

// Card bounding box for collision detection (actual collapsed card height ~200px)
const CARD_W = 200
const CARD_H = 200

// Center core card obstacle (width ~220px, min-height ~140px, centered at TOPOLOGY_CENTER)
const CENTER_CARD_W = 240
const CENTER_CARD_H = 160
const CENTER_OBSTACLE = {
  left:   TOPOLOGY_CENTER.x - CENTER_CARD_W / 2,
  top:    TOPOLOGY_CENTER.y - CENTER_CARD_H / 2,
  right:  TOPOLOGY_CENTER.x + CENTER_CARD_W / 2,
  bottom: TOPOLOGY_CENTER.y + CENTER_CARD_H / 2,
}

/**
 * Computes stable canvas positions for all agent nodes using concentric ring layout.
 *
 * Ring 1: 5 base agents evenly spaced (72° apart), starting from top (−90°).
 * Ring 2+: child nodes anchored near their parent's angle.
 * Push-apart pass resolves any bounding-box collisions radially.
 *
 * Returns { agentId → { x, y } } where (x, y) is the card top-left corner.
 */
export function useTopologyLayout(agents: AgentCardData[]): Record<string, Pos> {
  // Recompute only when the set of nodes changes (id + ring + parentId)
  const cacheKey = agents.map((a) => `${a.id}:${a.ring ?? 1}:${a.parentId ?? ''}`).join('|')

  return useMemo(() => {
    if (agents.length === 0) return {}

    // Group by ring
    const byRing = new Map<number, AgentCardData[]>()
    for (const agent of agents) {
      const ring = agent.ring ?? 1
      if (!byRing.has(ring)) byRing.set(ring, [])
      byRing.get(ring)!.push(agent)
    }

    // Sort rings ascending so ring 1 positions are known before ring 2 computes angles
    const sortedRings = [...byRing.keys()].sort((a, b) => a - b)

    // orbital_point = center of the card (not top-left) on the ring circumference
    const orbitalPoints: Record<string, Pos> = {}

    for (const ring of sortedRings) {
      const ringAgents = byRing.get(ring)!
      const radius = RING_RADIUS[ring] ?? RING_RADIUS[3]

      if (ring === 1) {
        // Evenly distribute 5 agents starting from top (−π/2), clockwise
        const n = ringAgents.length
        ringAgents.forEach((agent, i) => {
          const angle = -Math.PI / 2 + (2 * Math.PI * i) / n
          orbitalPoints[agent.id] = {
            x: TOPOLOGY_CENTER.x + radius * Math.cos(angle),
            y: TOPOLOGY_CENTER.y + radius * Math.sin(angle),
          }
        })
      } else {
        // Group children by parent, distribute near parent's angle
        const byParent = new Map<string, AgentCardData[]>()
        for (const agent of ringAgents) {
          const pid = agent.parentId ?? '__unknown__'
          if (!byParent.has(pid)) byParent.set(pid, [])
          byParent.get(pid)!.push(agent)
        }

        for (const [parentId, children] of byParent) {
          const parentAngle = getOrbitalAngle(parentId, orbitalPoints)
          const spread = Math.PI / 5 // ±36° spread per parent group

          children.forEach((child, i) => {
            const offset =
              children.length === 1
                ? 0
                : ((i / (children.length - 1)) - 0.5) * spread
            const angle = parentAngle + offset
            orbitalPoints[child.id] = {
              x: TOPOLOGY_CENTER.x + radius * Math.cos(angle),
              y: TOPOLOGY_CENTER.y + radius * Math.sin(angle),
            }
          })
        }
      }
    }

    // Convert orbital center-points to card top-left positions
    const positions: Record<string, Pos> = {}
    for (const [id, pt] of Object.entries(orbitalPoints)) {
      positions[id] = {
        x: Math.round(pt.x - CARD_W / 2),
        y: Math.round(pt.y - CARD_H / 2),
      }
    }

    // Radial push-apart pass — resolves bounding-box collisions without physics
    pushApart(positions)

    return positions
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cacheKey])
}

/** Returns the angle (radians) of a node's orbital point relative to TOPOLOGY_CENTER */
function getOrbitalAngle(nodeId: string, orbitalPoints: Record<string, Pos>): number {
  const pt = orbitalPoints[nodeId]
  if (!pt) return 0
  return Math.atan2(pt.y - TOPOLOGY_CENTER.y, pt.x - TOPOLOGY_CENTER.x)
}

/** Iterative radial push-apart to prevent bounding-box overlap between cards and center obstacle */
function pushApart(positions: Record<string, Pos>, iterations = 5) {
  const ids = Object.keys(positions)

  for (let iter = 0; iter < iterations; iter++) {
    // 1. Push agent cards away from each other
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = positions[ids[i]]
        const b = positions[ids[j]]

        const overlapX = Math.max(0, Math.min(a.x + CARD_W, b.x + CARD_W) - Math.max(a.x, b.x))
        const overlapY = Math.max(0, Math.min(a.y + CARD_H, b.y + CARD_H) - Math.max(a.y, b.y))

        if (overlapX > 0 && overlapY > 0) {
          const push = Math.max(overlapX, overlapY) / 2 + 10
          const nA = radialNormal(a)
          const nB = radialNormal(b)
          positions[ids[i]] = { x: a.x + nA.x * push, y: a.y + nA.y * push }
          positions[ids[j]] = { x: b.x + nB.x * push, y: b.y + nB.y * push }
        }
      }
    }

    // 2. Push each agent card away from the fixed center card obstacle
    for (const id of ids) {
      const p = positions[id]
      const overlapX = Math.max(0, Math.min(p.x + CARD_W, CENTER_OBSTACLE.right) - Math.max(p.x, CENTER_OBSTACLE.left))
      const overlapY = Math.max(0, Math.min(p.y + CARD_H, CENTER_OBSTACLE.bottom) - Math.max(p.y, CENTER_OBSTACLE.top))

      if (overlapX > 0 && overlapY > 0) {
        const push = Math.max(overlapX, overlapY) + 12
        const n = radialNormal(p)
        positions[id] = { x: p.x + n.x * push, y: p.y + n.y * push }
      }
    }
  }
}

function radialNormal(cardTopLeft: Pos): Pos {
  const cx = cardTopLeft.x + CARD_W / 2
  const cy = cardTopLeft.y + CARD_H / 2
  const dx = cx - TOPOLOGY_CENTER.x
  const dy = cy - TOPOLOGY_CENTER.y
  const len = Math.sqrt(dx * dx + dy * dy) || 1
  return { x: dx / len, y: dy / len }
}
