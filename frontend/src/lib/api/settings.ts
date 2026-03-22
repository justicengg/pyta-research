const BASE = '/api/v1'

export type LLMConfigStatus = {
  configured: boolean
  base_url: string
  model: string
  timeout_seconds: number
}

export async function fetchLLMStatus(): Promise<LLMConfigStatus> {
  const res = await fetch(`${BASE}/settings/llm/status`)
  if (!res.ok) throw new Error('Failed to fetch LLM status')
  return res.json()
}

export async function saveLLMConfig(payload: {
  api_key: string
  base_url: string
  model: string
  timeout_seconds: number
}): Promise<void> {
  const res = await fetch(`${BASE}/settings/llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Failed to save LLM config')
  }
}
