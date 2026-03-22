const BASE = '/api/v1'

export type ProviderInfo = {
  id: string
  title: string
  description: string
  source_channel: string
  coverage_dimension: string
  cost: string
  usage_level: string
  capabilities: string[]
}

export type ConnectorResponse = {
  id: string
  provider_id: string
  title: string
  source_channel: string
  coverage_dimension: string
  cost: string
  usage_level: string
  capabilities: string[]
  status: 'healthy' | 'syncing' | 'error' | 'inactive'
  error_message: string | null
  last_synced_at: string | null
  created_at: string
}

export type ValidateResponse = {
  ok: boolean
  error: string
}

export async function fetchCatalog(): Promise<ProviderInfo[]> {
  const res = await fetch(`${BASE}/sources/catalog`)
  if (!res.ok) throw new Error('Failed to load catalog')
  return res.json()
}

export async function fetchConnectors(): Promise<ConnectorResponse[]> {
  const res = await fetch(`${BASE}/sources/connectors`)
  if (!res.ok) throw new Error('Failed to load connectors')
  return res.json()
}

export async function validateConnector(
  provider_id: string,
  api_key: string,
  custom_config?: CustomProviderConfig,
): Promise<ValidateResponse> {
  const res = await fetch(`${BASE}/sources/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider_id, api_key, custom_config }),
  })
  if (!res.ok) throw new Error('Validate request failed')
  return res.json()
}

export type CustomProviderConfig = {
  title: string
  base_url: string
  auth_style: 'query_param' | 'bearer' | 'x_api_key'
  auth_param: string
  validate_path?: string
  source_channel?: string
  coverage_dimension?: string
  cost?: string
  usage_level?: string
  capabilities?: string[]
}

export async function createConnector(
  provider_id: string,
  api_key: string,
  custom_config?: CustomProviderConfig,
): Promise<ConnectorResponse> {
  const res = await fetch(`${BASE}/sources/connectors`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider_id, api_key, custom_config }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Failed to create connector')
  }
  return res.json()
}

export async function deleteConnector(connector_id: string): Promise<void> {
  const res = await fetch(`${BASE}/sources/connectors/${connector_id}`, {
    method: 'DELETE',
  })
  if (!res.ok && res.status !== 404) throw new Error('Failed to delete connector')
}
