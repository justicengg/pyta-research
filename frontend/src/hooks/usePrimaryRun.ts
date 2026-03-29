import { useState } from 'react'
import { mapReportToCanvasState, runPrimaryAnalysis } from '../lib/api/primary'
import { mockPrimaryCanvasState } from '../lib/mock/primaryCanvasState'
import type { PrimaryCanvasState } from '../lib/types/primaryCanvas'

export type PrimaryRunController = {
  canvasState: PrimaryCanvasState
  isRunning: boolean
  error: string | null
  stopReason: string | null
  roundsCompleted: number
  draft: string
  setDraft: (v: string) => void
  submit: () => Promise<void>
}

export function usePrimaryRun(): PrimaryRunController {
  const [canvasState, setCanvasState] = useState<PrimaryCanvasState>(mockPrimaryCanvasState)
  const [isRunning, setIsRunning]     = useState(false)
  const [error, setError]             = useState<string | null>(null)
  const [stopReason, setStopReason]   = useState<string | null>(null)
  const [roundsCompleted, setRounds]  = useState(0)
  const [draft, setDraft]             = useState(canvasState.companyName)

  async function submit() {
    const companyName = draft.trim()
    if (!companyName || isRunning) return

    setIsRunning(true)
    setError(null)

    try {
      const response = await runPrimaryAnalysis({
        companyName,
        sector: canvasState.sector,
        companyInfo: buildCompanyInfo(canvasState),
      })
      setCanvasState(prev => mapReportToCanvasState(response.report, prev))
      setStopReason(response.stopReason)
      setRounds(response.roundsCompleted)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Primary analysis failed')
    } finally {
      setIsRunning(false)
    }
  }

  return { canvasState, isRunning, error, stopReason, roundsCompleted, draft, setDraft, submit }
}

/**
 * Serialise current canvas card state into the company_info dict
 * the backend PrimaryOrchestrator expects.
 */
function buildCompanyInfo(state: PrimaryCanvasState): Record<string, unknown> {
  return {
    market_type: state.uncertaintyMap.marketType,
    dimensions: Object.fromEntries(
      Object.entries(state.uncertaintyMap.assessments).map(([dim, val]) => [
        dim,
        {
          score:       val?.score ?? 'high',
          narrative:   val?.narrative ?? '',
          key_signals: val?.keySignals ?? [],
          confidence:  0.5,
        },
      ])
    ),
    founder: {
      company_stage:      state.founderAnalysis.companyStage,
      archetype:          state.founderAnalysis.archetype,
      founder_market_fit: state.founderAnalysis.founderMarketFit,
      execution_signal:   state.founderAnalysis.executionSignal,
      domain_depth:       state.founderAnalysis.domainDepth,
      team_building:      state.founderAnalysis.teamBuilding,
      self_awareness:     state.founderAnalysis.selfAwareness,
      stage_fit:          state.founderAnalysis.stageFit,
      stage_fit_narrative:state.founderAnalysis.stageFitNarrative,
      key_risks:          state.founderAnalysis.keyRisks,
    },
    assumptions: state.keyAssumptions.items.map(a => ({
      level:                a.level,
      description:          a.description,
      status:               a.status,
      time_horizon_months:  a.timeHorizonMonths ?? null,
    })),
    financials: {
      arr:                 state.financialLens.arr ?? null,
      arr_growth_narrative:state.financialLens.arrGrowthNarrative ?? null,
      nrr:                 state.financialLens.nrr ?? null,
      gross_margin:        state.financialLens.grossMargin ?? null,
      monthly_burn:        state.financialLens.monthlyBurn ?? null,
      ltv_cac_ratio:       state.financialLens.ltvCacRatio ?? null,
      current_valuation:   state.financialLens.currentValuation ?? null,
      runway_months:       state.financialLens.runwayMonths ?? null,
      valuation_narrative: state.financialLens.valuationNarrative ?? null,
    },
  }
}
