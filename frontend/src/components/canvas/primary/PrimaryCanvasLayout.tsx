import { useState } from 'react'
import type { PrimaryCanvasState } from '../../../lib/types/primaryCanvas'
import { FinancialLensCard } from './FinancialLensCard'
import { FounderAnalysisCard } from './FounderAnalysisCard'
import { KeyAssumptionsCard } from './KeyAssumptionsCard'
import { PathForkCard } from './PathForkCard'
import { UncertaintyMapCard } from './UncertaintyMapCard'

type Pos = { x: number; y: number }

// Default 2×2 grid layout, centered around x=800
const DEFAULT_POSITIONS: Record<string, Pos> = {
  uncertainty: { x: 460,  y: 260 },
  founder:     { x: 830,  y: 260 },
  assumptions: { x: 460,  y: 620 },
  financial:   { x: 830,  y: 620 },
}

const FORK_START_X = 645
const FORK_START_Y = 980
const FORK_GAP_X   = 380

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

      {/* Overall verdict banner */}
      {state.overallVerdict && (
        <div
          className="pm-verdict"
          style={{
            left: positions.uncertainty.x,
            top: positions.uncertainty.y - 56,
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
