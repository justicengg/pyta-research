import type { PrimaryCanvasState } from '../types/primaryCanvas'

const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const DEFAULT_API_KEY  = import.meta.env.VITE_API_KEY ?? ''

export type PrimaryRunRequest = {
  companyName: string
  sector?: string
  companyInfo: Record<string, unknown>
  maxRounds?: number
}

export type PrimaryRunResponse = {
  sandboxId: string
  companyName: string
  roundsCompleted: number
  stopReason: string
  sessionStatus: string
  report: PrimaryReportRaw
}

/** Raw backend report shape (snake_case from Python) */
export type PrimaryReportRaw = {
  sandbox_id: string
  company_name: string
  sector?: string
  generated_at: string
  uncertainty_map: {
    market_type: string
    assessments: Record<string, { score: string; narrative: string; key_signals: string[] }>
  }
  founder_analysis: {
    company_stage: string
    archetype: string
    founder_market_fit: string
    execution_signal: string
    domain_depth: string
    team_building: string
    self_awareness: string
    stage_fit: string
    stage_fit_narrative: string
    key_risks: string[]
  }
  key_assumptions: {
    items: Array<{
      level: string
      description: string
      status: string
      time_horizon_months?: number
      triggers_path_fork: boolean
    }>
  }
  financial_lens: {
    arr?: number
    arr_growth_narrative?: string
    nrr?: number
    gross_margin?: number
    monthly_burn?: number
    ltv_cac_ratio?: number
    current_valuation?: number
    runway_months?: number
    valuation_narrative?: string
  }
  path_forks: Array<{
    fork_id: string
    trigger: string
    trigger_assumption?: string
    scenario_if_holds: string
    scenario_if_fails: string
    recommended_action: string
  }>
  overall_verdict: string
  confidence: number
  round_id: string
  trace_id: string
}

export class PrimaryApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'PrimaryApiError'
    this.status = status
  }
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const url = `${DEFAULT_BASE_URL}${path}`
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': DEFAULT_API_KEY,
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new PrimaryApiError(`Primary API error ${res.status}: ${text}`, res.status)
  }
  return res.json() as Promise<T>
}

export async function runPrimaryAnalysis(req: PrimaryRunRequest): Promise<PrimaryRunResponse> {
  const raw = await post<{
    sandbox_id: string
    company_name: string
    rounds_completed: number
    stop_reason: string
    session_status: string
    report: PrimaryReportRaw
  }>('/api/v1/primary/run', {
    company_name: req.companyName,
    sector: req.sector,
    company_info: req.companyInfo,
    max_rounds: req.maxRounds ?? 3,
  })
  return {
    sandboxId:       raw.sandbox_id,
    companyName:     raw.company_name,
    roundsCompleted: raw.rounds_completed,
    stopReason:      raw.stop_reason,
    sessionStatus:   raw.session_status,
    report:          raw.report,
  }
}

/** Map backend report to PrimaryCanvasState for the canvas */
export function mapReportToCanvasState(
  report: PrimaryReportRaw,
  base: PrimaryCanvasState,
): PrimaryCanvasState {
  return {
    ...base,
    companyName: report.company_name,
    sector: report.sector,
    uncertaintyMap: {
      marketType: report.uncertainty_map.market_type as PrimaryCanvasState['uncertaintyMap']['marketType'],
      assessments: Object.fromEntries(
        Object.entries(report.uncertainty_map.assessments).map(([dim, val]) => [
          dim,
          { score: val.score as 'high' | 'medium' | 'low', narrative: val.narrative, keySignals: val.key_signals },
        ])
      ),
    },
    founderAnalysis: {
      companyStage:      report.founder_analysis.company_stage as PrimaryCanvasState['founderAnalysis']['companyStage'],
      archetype:         report.founder_analysis.archetype as PrimaryCanvasState['founderAnalysis']['archetype'],
      founderMarketFit:  report.founder_analysis.founder_market_fit as 'high' | 'medium' | 'low',
      executionSignal:   report.founder_analysis.execution_signal,
      domainDepth:       report.founder_analysis.domain_depth,
      teamBuilding:      report.founder_analysis.team_building as 'high' | 'medium' | 'low',
      selfAwareness:     report.founder_analysis.self_awareness as 'high' | 'medium' | 'low',
      stageFit:          report.founder_analysis.stage_fit as PrimaryCanvasState['founderAnalysis']['stageFit'],
      stageFitNarrative: report.founder_analysis.stage_fit_narrative,
      keyRisks:          report.founder_analysis.key_risks,
    },
    keyAssumptions: {
      items: report.key_assumptions.items.map(a => ({
        level:              a.level as 'hard' | 'soft',
        description:        a.description,
        status:             a.status as 'confirmed' | 'unverified' | 'violated',
        timeHorizonMonths:  a.time_horizon_months,
        triggersPathFork:   a.triggers_path_fork,
      })),
    },
    financialLens: {
      arr:                 report.financial_lens.arr,
      arrGrowthNarrative:  report.financial_lens.arr_growth_narrative,
      nrr:                 report.financial_lens.nrr,
      grossMargin:         report.financial_lens.gross_margin,
      monthlyBurn:         report.financial_lens.monthly_burn,
      ltvCacRatio:         report.financial_lens.ltv_cac_ratio,
      currentValuation:    report.financial_lens.current_valuation,
      runwayMonths:        report.financial_lens.runway_months,
      valuationNarrative:  report.financial_lens.valuation_narrative,
    },
    pathForks: report.path_forks.map(f => ({
      forkId:            f.fork_id,
      triggerAssumption: f.trigger_assumption ?? '',
      scenarioIfHolds:   f.scenario_if_holds,
      scenarioIfFails:   f.scenario_if_fails,
      recommendedAction: f.recommended_action,
    })),
    overallVerdict: report.overall_verdict,
    confidence:     report.confidence,
  }
}
