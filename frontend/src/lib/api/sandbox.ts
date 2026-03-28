import type {
  BackendSandboxEnvironmentState,
  BackendSandboxResultResponse,
  BackendSandboxRunRequest,
  BackendSandboxRunResponse,
  SandboxEnvironmentState,
  SandboxInputEvent,
  SandboxRunRequest,
} from '../types/sandbox'

export type SandboxClientOptions = {
  apiKey?: string
  baseUrl?: string
  fetchImpl?: typeof fetch
  signal?: AbortSignal
  headers?: HeadersInit
}

export class SandboxApiError extends Error {
  readonly status: number
  readonly payload: unknown

  constructor(message: string, status: number, payload: unknown = null) {
    super(message)
    this.name = 'SandboxApiError'
    this.status = status
    this.payload = payload
  }
}

const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY ?? ''

function joinUrl(baseUrl: string, path: string): string {
  const normalizedBase = baseUrl.replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${normalizedBase}${normalizedPath}`
}

function toBackendEvent(event: SandboxInputEvent) {
  return {
    event_id: event.eventId,
    event_type: event.eventType,
    content: event.content,
    source: event.source,
    timestamp: event.timestamp,
    symbol: event.symbol ?? null,
    metadata: event.metadata ?? {},
  }
}

function toBackendEnvironmentState(state: SandboxEnvironmentState): BackendSandboxEnvironmentState {
  return {
    sandbox_id: state.sandboxId ?? null,
    symbol: state.symbol ?? null,
    market: state.market ?? null,
    buckets: state.buckets.map((bucket) => ({
      type: bucket.type,
      display_name: bucket.displayName,
      active_signals: bucket.activeSignals.map((signal) => ({
        id: signal.id,
        message_id: signal.messageId,
        environment_type: signal.environmentType,
        title: signal.title,
        summary: signal.summary,
        direction: signal.direction,
        strength: signal.strength,
        horizon: signal.horizon,
        related_symbols: signal.relatedSymbols,
        related_markets: signal.relatedMarkets,
        entities: signal.entities,
        tags: signal.tags,
        detected_at: signal.detectedAt,
        expires_at: signal.expiresAt ?? null,
        evidence: signal.evidence.map((item) => ({ kind: item.kind, value: item.value })),
      })),
      dominant_direction: bucket.dominantDirection,
      aggregate_strength: bucket.aggregateStrength,
      last_updated_at: bucket.lastUpdatedAt ?? null,
      status: bucket.status,
    })),
    global_risk_tone: state.globalRiskTone,
    updated_at: state.updatedAt,
    version: state.version,
  }
}

function buildHeaders(options: SandboxClientOptions): Headers {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  const apiKey = options.apiKey ?? DEFAULT_API_KEY
  if (apiKey) {
    headers.set('X-API-Key', apiKey)
  }
  return headers
}

async function requestJson<T>(
  path: string,
  options: SandboxClientOptions & { method?: 'GET' | 'POST'; body?: unknown } = {},
): Promise<T> {
  const fetchImpl = options.fetchImpl ?? fetch
  const response = await fetchImpl(joinUrl(options.baseUrl ?? DEFAULT_BASE_URL, path), {
    method: options.method ?? 'GET',
    headers: buildHeaders(options),
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  })

  const text = await response.text()
  const payload = text ? safeParseJson(text) : null

  if (!response.ok) {
    const message = extractErrorMessage(payload) ?? response.statusText ?? 'Sandbox request failed'
    throw new SandboxApiError(message, response.status, payload)
  }

  return payload as T
}

function safeParseJson(text: string): unknown {
  try {
    return JSON.parse(text) as unknown
  } catch {
    return text
  }
}

function extractErrorMessage(payload: unknown): string | null {
  if (typeof payload === 'string') {
    return payload
  }
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail
    if (typeof detail === 'string') {
      return detail
    }
  }
  return null
}

export async function runSandbox(
  request: SandboxRunRequest,
  options: SandboxClientOptions = {},
): Promise<BackendSandboxRunResponse> {
  const body: BackendSandboxRunRequest = {
    ticker: request.ticker,
    market: request.market,
    events: request.events.map(toBackendEvent),
    environment_state: request.environmentState ? toBackendEnvironmentState(request.environmentState) : null,
    round_timeout_ms: request.roundTimeoutMs,
    narrative_guide: request.narrativeGuide ?? null,
  }

  return requestJson<BackendSandboxRunResponse>('/api/v1/sandbox/run', {
    ...options,
    method: 'POST',
    body,
  })
}

export async function getSandboxResult(
  sandboxId: string,
  options: SandboxClientOptions = {},
): Promise<BackendSandboxResultResponse> {
  return requestJson<BackendSandboxResultResponse>(`/api/v1/sandbox/${sandboxId}/result`, {
    ...options,
    method: 'GET',
  })
}
