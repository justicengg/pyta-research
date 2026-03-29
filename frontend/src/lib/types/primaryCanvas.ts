/** Frontend types for primary market canvas — mirrors backend primary_market.py schemas */

export type UncertaintyScore = 'high' | 'medium' | 'low'
export type MarketType = 'new_market' | 'red_ocean' | 'blue_ocean'

export type UncertaintyDimension =
  | 'market_validity'
  | 'tech_barrier'
  | 'team_execution'
  | 'commercialization'
  | 'competition'
  | 'burn_cycle'

export const DIMENSION_LABELS: Record<UncertaintyDimension, string> = {
  market_validity:   '市场是否成立',
  tech_barrier:      '技术壁垒',
  team_execution:    '团队执行力',
  commercialization: '商业化路径',
  competition:       '竞争格局',
  burn_cycle:        '烧钱周期',
}

export type DimensionAssessment = {
  score: UncertaintyScore
  narrative: string
  keySignals: string[]
}

export type UncertaintyMapData = {
  marketType: MarketType
  assessments: Partial<Record<UncertaintyDimension, DimensionAssessment>>
}

// ── Founder Analysis ────────────────────────────────────────────────────

export type CompanyStage = '0_to_1' | '1_to_10' | '10_to_100'
export type FounderArchetype = 'visionary' | 'operator' | 'technical' | 'domain_expert'
export type StageFit = 'matched' | 'mismatched' | 'needs_complement'

export const ARCHETYPE_LABELS: Record<FounderArchetype, string> = {
  visionary:     '破坏者 / 愿景型',
  operator:      '执行者 / 运营型',
  technical:     '技术型',
  domain_expert: '行业专家型',
}

export const STAGE_LABELS: Record<CompanyStage, string> = {
  '0_to_1':    '0 → 1',
  '1_to_10':   '1 → 10',
  '10_to_100': '10 → 100',
}

export const STAGE_FIT_LABELS: Record<StageFit, string> = {
  matched:           '匹配',
  mismatched:        '错位',
  needs_complement:  '需要补位',
}

export type FounderAnalysisData = {
  companyStage: CompanyStage
  archetype: FounderArchetype
  founderMarketFit: UncertaintyScore
  executionSignal: string
  domainDepth: string
  teamBuilding: UncertaintyScore
  selfAwareness: UncertaintyScore
  stageFit: StageFit
  stageFitNarrative: string
  keyRisks: string[]
}

// ── Key Assumptions ─────────────────────────────────────────────────────

export type AssumptionLevel = 'hard' | 'soft'
export type AssumptionStatus = 'confirmed' | 'unverified' | 'violated'

export type KeyAssumptionItem = {
  level: AssumptionLevel
  description: string
  status: AssumptionStatus
  timeHorizonMonths?: number
  triggersPathFork: boolean
}

export type KeyAssumptionsData = {
  items: KeyAssumptionItem[]
}

// ── Financial Lens ──────────────────────────────────────────────────────

export type FinancialLensData = {
  arr?: number
  arrGrowthNarrative?: string
  nrr?: number
  grossMargin?: number
  monthlyBurn?: number
  ltvCacRatio?: number
  currentValuation?: number
  runwayMonths?: number
  valuationNarrative?: string
}

// ── PathFork ────────────────────────────────────────────────────────────

export type PathForkData = {
  forkId: string
  triggerAssumption: string
  scenarioIfHolds: string
  scenarioIfFails: string
  recommendedAction: string
}

// ── Top-level primary canvas state ─────────────────────────────────────

export type PrimaryCanvasState = {
  companyName: string
  sector?: string
  uncertaintyMap: UncertaintyMapData
  founderAnalysis: FounderAnalysisData
  keyAssumptions: KeyAssumptionsData
  financialLens: FinancialLensData
  pathForks: PathForkData[]
  overallVerdict?: string
  confidence?: number
}
