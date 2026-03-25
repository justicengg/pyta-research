import { useState } from 'react'
import { CanvasStage } from '../components/layout/CanvasStage'
import { InformationPanel } from '../components/layout/InformationPanel'
import { useSandboxRun } from '../hooks/useSandboxRun'
import { mockCanvasState } from '../lib/mock/canvasState'

export function ResearchCanvasPage() {
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const {
    canvasState,
    backendState,
    draft,
    setDraft,
    isRunning,
    error,
    qualityLabel,
    currentInputEvents,
    currentRound,
    roundHistory,
    sceneParams,
    setSceneParams,
    submit,
  } = useSandboxRun({
    initialDraft: mockCanvasState.commandDraft,
  })

  return (
    <div className={`shell research-canvas-shell ${leftCollapsed ? 'left-collapsed' : ''}`}>
      <InformationPanel
        collapsed={leftCollapsed}
        onToggle={() => setLeftCollapsed((value) => !value)}
        state={canvasState}
        currentInputEvents={currentInputEvents}
        sessionStatus={backendState?.sessionStatus ?? (isRunning ? 'running' : 'initializing')}
        error={error}
        defaultSymbol={sceneParams.ticker}
        defaultMarket={sceneParams.market}
      />
      <CanvasStage
        state={canvasState}
        draft={draft}
        onDraftChange={setDraft}
        isRunning={isRunning}
        error={error}
        qualityLabel={qualityLabel}
        currentRound={currentRound}
        roundHistory={roundHistory}
        currentInputEvents={currentInputEvents}
        sceneParams={sceneParams}
        onSceneParamsChange={setSceneParams}
        onSubmit={() => void submit()}
      />
    </div>
  )
}
