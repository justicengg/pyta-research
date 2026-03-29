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

  const isPrimary = marketMode === 'primary'

  return (
    <div className={`shell research-canvas-shell ${leftCollapsed ? 'left-collapsed' : ''}`}>
      {/* Mode selector dialog — shown on top when no mode selected */}
      {marketMode === null && (
        <MarketModeSelector onSelect={setMarketMode} />
      )}

      {/* Left panel */}
      <InformationPanel
        collapsed={leftCollapsed}
        onToggle={() => setLeftCollapsed(v => !v)}
        state={secondary.canvasState}
        currentInputEvents={isPrimary ? [] : secondary.currentInputEvents}
        sessionStatus={
          isPrimary
            ? (primary.isRunning ? 'running' : 'initializing')
            : (secondary.backendState?.sessionStatus ?? (secondary.isRunning ? 'running' : 'initializing'))
        }
        error={isPrimary ? primary.error : secondary.error}
        defaultSymbol={isPrimary ? primary.canvasState.companyName : secondary.sceneParams.ticker}
        defaultMarket={isPrimary ? 'primary' : secondary.sceneParams.market}
      />

      {/* Canvas stage */}
      {isPrimary ? (
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
          primaryRoundsCompleted={primary.roundsCompleted}
          primaryStopReason={primary.stopReason}
        />
      ) : (
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
      )}
    </div>
  )
}
