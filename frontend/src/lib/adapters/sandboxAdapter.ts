import type {
  BackendAgentPerspective,
  BackendCheckpoint,
  BackendMarketReadingReport,
  BackendPerAgentStatus,
  BackendReportRecord,
  BackendRoundComplete,
  BackendSandboxResultResponse,
  BackendSandboxRunResponse,
  CanvasAgentCard,
  CanvasInputEvent,
  CanvasRunState,
  CanvasTension,
  SandboxAgentId,
  SandboxInputEvent,
} from '../types/sandbox'

const AGENT_META: Record<
  SandboxAgentId,
  { title: string; subtitle: string; tint: CanvasAgentCard['tint'] }
> = {
  traditional_institution: {
    title: '传统机构 Agent',
    subtitle: '重估值、仓位与中长期配置',
    tint: 'traditional',
  },
  quant_institution: {
    title: '量化机构 Agent',
    subtitle: '按规则、信号与模型快速调整',
    tint: 'quant',
  },
  retail: {
    title: '普通散户 Agent',
    subtitle: '更受叙事、情绪与热点影响',
    tint: 'retail',
  },
  offshore_capital: {
    title: '海外资金 Agent',
    subtitle: '跟随全球流动性与风险偏好变化',
    tint: 'offshore',
  },
  short_term_capital: {
    title: '游资 / 短线资金 Agent',
    subtitle: '偏题材、博弈与事件驱动',
    tint: 'shortTerm',
  },
}

const AGENT_ORDER: SandboxAgentId[] = [
  'traditional_institution',
  'quant_institution',
  'retail',
  'offshore_capital',
  'short_term_capital',
]

export function mapRunResponseToCanvasState(
  response: BackendSandboxRunResponse,
  context: { inputEvents?: SandboxInputEvent[] } = {},
): CanvasRunState {
  return buildCanvasRunState({
    sandboxId: response.sandbox_id,
    ticker: response.round_complete.ticker,
    market: response.round_complete.market,
    sessionStatus: response.session_status,
    quality: response.round_complete.data_quality,
    stopReason: response.round_complete.stop_reason,
    round: response.round_complete.rounds_completed,
    roundComplete: response.round_complete,
    report: response.report,
    latestCheckpoint: null,
    inputEvents: context.inputEvents ?? [],
  })
}

export function mapResultResponseToCanvasState(
  response: BackendSandboxResultResponse,
  context: { inputEvents?: SandboxInputEvent[] } = {},
): CanvasRunState {
  return buildCanvasRunState({
    sandboxId: response.sandbox_id,
    ticker: response.ticker,
    market: response.market,
    sessionStatus: response.session_status,
    quality: response.report.data_quality,
    stopReason: null,
    round: response.current_round,
    roundComplete: undefined,
    report: response.report,
    latestCheckpoint: response.latest_checkpoint,
    inputEvents: context.inputEvents ?? [],
  })
}

export function mapCheckpointToSummary(checkpoint: BackendCheckpoint | null): string | null {
  if (!checkpoint) {
    return null
  }
  return `Round ${checkpoint.round} · ${checkpoint.completion_status}`
}

function buildCanvasRunState(input: {
  sandboxId: string
  ticker: string
  market: string
  sessionStatus: CanvasRunState['sessionStatus']
  quality: CanvasRunState['quality']
  stopReason: string | null
  round: number
  roundComplete?: BackendRoundComplete
  report: BackendMarketReadingReport | BackendReportRecord
  latestCheckpoint: BackendCheckpoint | null
  inputEvents: CanvasInputEvent[]
}): CanvasRunState {
  const agentDetail = extractAgentDetail(input.report)
  const perAgentStatus = input.roundComplete?.per_agent_status ?? buildFallbackStatuses(agentDetail)
  const synthesis = buildSynthesis(agentDetail, input.report.perspective_synthesis, perAgentStatus)
  const tensions = buildTensions(input.report.key_tensions ?? input.roundComplete?.divergence_map ?? [])
  const trackingSignals = uniqueStrings(input.report.tracking_signals ?? [])

  return {
    sandboxId: input.sandboxId,
    ticker: input.ticker,
    market: input.market,
    sessionStatus: input.sessionStatus,
    quality: input.quality,
    stopReason: input.stopReason,
    round: input.round,
    agents: AGENT_ORDER.map((agentId) =>
      buildAgentCard(agentId, agentDetail[agentId], perAgentStatus.find((item) => item.agent_type === agentId)),
    ),
    synthesis,
    tensions,
    trackingSignals,
    inputEvents: input.inputEvents,
    latestCheckpoint: input.latestCheckpoint,
    roundComplete: input.roundComplete,
    report: input.report,
  }
}

function extractAgentDetail(
  report: BackendMarketReadingReport | BackendReportRecord,
): Partial<Record<SandboxAgentId, BackendAgentPerspective>> {
  const rawDetail: Record<string, BackendAgentPerspective> | null | undefined = (() => {
    if ('perspective_detail' in report) {
      return report.perspective_detail ?? undefined
    }
    return (report as BackendReportRecord).per_agent_detail ?? undefined
  })()
  if (!rawDetail) {
    return {}
  }

  const result: Partial<Record<SandboxAgentId, BackendAgentPerspective>> = {}
  for (const [key, value] of Object.entries(rawDetail)) {
    if (isSandboxAgentId(key) && value) {
      result[key] = value as BackendAgentPerspective
    }
  }
  return result
}

function buildAgentCard(
  agentId: SandboxAgentId,
  detail: BackendAgentPerspective | undefined,
  statusRow: BackendPerAgentStatus | undefined,
): CanvasAgentCard {
  const meta = AGENT_META[agentId]
  const fallbackSummary = statusRow?.summary ?? `${meta.title} 当前暂无明确观察。`
  const status = detail?.perspective_status ?? statusRow?.perspective_status ?? 'degraded'

  return {
    id: agentId,
    title: meta.title,
    subtitle: meta.subtitle,
    tint: meta.tint,
    status,
    summary: summarizePerspective(detail, fallbackSummary),
    observations: detail?.key_observations ?? [],
    concerns: detail?.key_concerns ?? [],
    focus: detail?.analytical_focus ?? [],
    bias: detail?.market_bias ?? 'neutral',
    confidence: detail?.confidence ?? 0,
    perspectiveType: detail?.perspective_type ?? agentId,
    perspectiveStatus: status,
    sourceTraceId: undefined,
  }
}

function summarizePerspective(detail: BackendAgentPerspective | undefined, fallbackSummary: string): string {
  if (!detail) {
    return fallbackSummary
  }
  const observations = detail.key_observations.slice(0, 1)
  const focus = detail.analytical_focus.slice(0, 1)
  const parts = [...observations, ...focus]
  return parts.length > 0 ? parts.join('；') : fallbackSummary
}

function buildSynthesis(
  detail: Partial<Record<SandboxAgentId, BackendAgentPerspective>>,
  synthesis: Record<string, string> | undefined,
  perAgentStatus: BackendPerAgentStatus[],
): Record<SandboxAgentId, string> {
  const output = {} as Record<SandboxAgentId, string>

  for (const agentId of AGENT_ORDER) {
    const explicit = synthesis?.[agentId]
    if (explicit) {
      output[agentId] = explicit
      continue
    }

    const agentDetail = detail[agentId]
    const fallbackSummary = perAgentStatus.find((item) => item.agent_type === agentId)?.summary
    output[agentId] = summarizePerspective(agentDetail, fallbackSummary ?? `${AGENT_META[agentId].title} 暂无摘要。`)
  }

  return output
}

function buildTensions(items: Array<{ between: SandboxAgentId[]; description: string }>): CanvasTension[] {
  return items.map((item) => ({ between: item.between, description: item.description }))
}

function buildFallbackStatuses(
  detail: Partial<Record<SandboxAgentId, BackendAgentPerspective>>,
): BackendPerAgentStatus[] {
  return AGENT_ORDER.map((agentId) => {
    const agentDetail = detail[agentId]
    return {
      agent_type: agentId,
      perspective_type: agentDetail?.perspective_type ?? agentId,
      saturated: agentDetail?.perspective_status === 'live',
      perspective_status: agentDetail?.perspective_status ?? 'degraded',
      summary: summarizePerspective(agentDetail, `${AGENT_META[agentId].title} 当前暂无明确观察。`),
    }
  })
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.filter((item) => item.trim().length > 0))]
}

function isSandboxAgentId(value: string): value is SandboxAgentId {
  return AGENT_ORDER.includes(value as SandboxAgentId)
}

export function createEmptyCanvasRunState(): CanvasRunState {
  return {
    sandboxId: '',
    ticker: '',
    market: '',
    sessionStatus: 'initializing',
    quality: 'partial',
    stopReason: null,
    round: 0,
    agents: AGENT_ORDER.map((agentId) => buildAgentCard(agentId, undefined, undefined)),
    synthesis: AGENT_ORDER.reduce((acc, agentId) => {
      acc[agentId] = `${AGENT_META[agentId].title} 暂无摘要。`
      return acc
    }, {} as Record<SandboxAgentId, string>),
    tensions: [],
    trackingSignals: [],
    inputEvents: [],
    latestCheckpoint: null,
    report: {
      sandbox_id: '',
      ticker: '',
      generated_at: new Date().toISOString(),
      perspective_synthesis: {},
      key_tensions: [],
      tracking_signals: [],
      data_quality: 'partial',
      perspective_detail: {},
    },
  }
}
