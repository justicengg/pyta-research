import { useState } from 'react'
import { CanvasStage } from '../components/layout/CanvasStage'
import { InformationPanel } from '../components/layout/InformationPanel'
import { MarketModeSelector } from '../components/layout/MarketModeSelector'
import { usePrimaryRun } from '../hooks/usePrimaryRun'
import { useSandboxRun } from '../hooks/useSandboxRun'
import { mockCanvasState } from '../lib/mock/canvasState'
import type { MarketMode } from '../lib/types/canvas'

export function ResearchCanvasPage() {
  const [marketMode, setMarketMode] = useState<MarketMode | null>(null)
  const [leftCollapsed, setLeftCollapsed] = useState(false)

  // Secondary market hook
  const secondary = useSandboxRun({ initialDraft: mockCanvasState.commandDraft })

  // Primary market hook
  const primary = usePrimaryRun()

  if (marketMode === null) {
    return (
      <div className="shell research-canvas-shell">
        <MarketModeSelector onSelect={setMarketMode} />
      </div>
    )
  }

  if (marketMode === 'primary') {
    return (
      <div className="shell research-canvas-shell research-canvas-shell--no-left-panel">
        <CanvasStage
          state={secondary.canvasState}
          draft={primary.draft}
          onDraftChange={primary.setDraft}
          isRunning={primary.isRunning}
          error={primary.error}
          qualityLabel={primary.stopReason ?? (primary.isRunning ? 'running…' : 'ready')}
          currentRound={primary.roundsCompleted}
          roundHistory={[]}
          currentInputEvents={[]}
          sceneParams={{ ticker: primary.canvasState.companyName, market: 'primary', timeHorizon: '' }}
          onSceneParamsChange={() => {}}
          onSubmit={() => void primary.submit()}
          marketMode="primary"
          onSwitchMode={() => setMarketMode(null)}
          primaryCanvasState={primary.canvasState}
        />
      </div>
    )
  }

  return (
    <div className={`shell research-canvas-shell ${leftCollapsed ? 'left-collapsed' : ''}`}>
      <InformationPanel
        collapsed={leftCollapsed}
        onToggle={() => setLeftCollapsed(v => !v)}
        state={secondary.canvasState}
        currentInputEvents={secondary.currentInputEvents}
        sessionStatus={secondary.backendState?.sessionStatus ?? (secondary.isRunning ? 'running' : 'initializing')}
        error={secondary.error}
        defaultSymbol={secondary.sceneParams.ticker}
        defaultMarket={secondary.sceneParams.market}
      />
      <CanvasStage
        state={secondary.canvasState}
        draft={secondary.draft}
        onDraftChange={secondary.setDraft}
        isRunning={secondary.isRunning}
        error={secondary.error}
        qualityLabel={secondary.qualityLabel}
        currentRound={secondary.currentRound}
        roundHistory={secondary.roundHistory}
        currentInputEvents={secondary.currentInputEvents}
        sceneParams={secondary.sceneParams}
        onSceneParamsChange={secondary.setSceneParams}
        onSubmit={() => void secondary.submit()}
        marketMode="secondary"
        onSwitchMode={() => setMarketMode(null)}
      />
    </div>
  )
}
