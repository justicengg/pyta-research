import { useState } from 'react'
import type { PrimaryCanvasState } from '../../../lib/types/primaryCanvas'
import { FinancialLensCard } from './FinancialLensCard'
import { FounderAnalysisCard } from './FounderAnalysisCard'
import { KeyAssumptionsCard } from './KeyAssumptionsCard'
import { PathForkCard } from './PathForkCard'
import { UncertaintyMapCard } from './UncertaintyMapCard'

type Pos = { x: number; y: number }

// Horizontal layout — 4 cards in a single row, centered in canvas
// Canvas visible width at zoom 0.72: ~1583px → cards (1400px) + ~183px margin
// Start X = (1583 - 1400) / 2 ≈ 92px, card width 320px, gap 40px
const CARD_WIDTH = 320
const CARD_GAP   = 40
const ROW_START_X = 92
const ROW_Y       = 280

const DEFAULT_POSITIONS: Record<string, Pos> = {
  uncertainty: { x: ROW_START_X,                                        y: ROW_Y },
  founder:     { x: ROW_START_X + (CARD_WIDTH + CARD_GAP),             y: ROW_Y },
  assumptions: { x: ROW_START_X + (CARD_WIDTH + CARD_GAP) * 2,        y: ROW_Y },
  financial:   { x: ROW_START_X + (CARD_WIDTH + CARD_GAP) * 3,        y: ROW_Y },
}

const FORK_START_X = ROW_START_X
const FORK_START_Y = ROW_Y + 460
const FORK_GAP_X   = CARD_WIDTH + CARD_GAP

type Props = {
  state: PrimaryCanvasState
}

export function PrimaryCanvasLayout({ state }: Props) {
  const [positions, setPositions] = useState<Record<string, Pos>>(DEFAULT_POSITIONS)

  function move(id: string, dx: number, dy: number) {
    setPositions(prev => {
      const cur = prev[id] ?? { x: 0, y: 0 }
      return { ...prev, [id]: { x: cur.x + dx, y: cur.y + dy } }
    })
  }

  // Initialise PathFork positions lazily
  const forkPositions: Record<string, Pos> = {}
  state.pathForks.forEach((fork, i) => {
    const key = `fork-${fork.forkId}`
    forkPositions[key] = positions[key] ?? {
      x: FORK_START_X + i * FORK_GAP_X,
      y: FORK_START_Y,
    }
  })

  return (
    <div className="pm-canvas-layout">
      <UncertaintyMapCard
        data={state.uncertaintyMap}
        position={positions.uncertainty}
        onDragMove={(dx, dy) => move('uncertainty', dx, dy)}
      />
      <FounderAnalysisCard
        data={state.founderAnalysis}
        position={positions.founder}
        onDragMove={(dx, dy) => move('founder', dx, dy)}
      />
      <KeyAssumptionsCard
        data={state.keyAssumptions}
        position={positions.assumptions}
        onDragMove={(dx, dy) => move('assumptions', dx, dy)}
      />
      <FinancialLensCard
        data={state.financialLens}
        position={positions.financial}
        onDragMove={(dx, dy) => move('financial', dx, dy)}
      />

      {state.pathForks.map((fork, i) => {
        const key = `fork-${fork.forkId}`
        return (
          <PathForkCard
            key={fork.forkId}
            data={fork}
            position={forkPositions[key] ?? { x: FORK_START_X + i * FORK_GAP_X, y: FORK_START_Y }}
            onDragMove={(dx, dy) => move(key, dx, dy)}
          />
        )
      })}

      {/* Overall verdict banner — centered above the four cards */}
      {state.overallVerdict && (
        <div
          className="pm-verdict"
          style={{
            left: ROW_START_X,
            top: ROW_Y - 56,
          }}
        >
          <span className="pm-verdict__company">{state.companyName}</span>
          {state.sector && <span className="pm-verdict__sector">{state.sector}</span>}
          <span className="pm-verdict__text">{state.overallVerdict}</span>
        </div>
      )}
    </div>
  )
}
