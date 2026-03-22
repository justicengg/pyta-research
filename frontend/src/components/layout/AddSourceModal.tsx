import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  fetchCatalog,
  validateConnector,
  createConnector,
  type ProviderInfo,
  type ConnectorResponse,
  type CustomProviderConfig,
} from '../../lib/api/sources'

type Step = 'select' | 'configure' | 'done'

// Sentinel for custom provider
const CUSTOM_PROVIDER: ProviderInfo = {
  id: 'custom',
  title: '自定义来源',
  description: '手动填入任意 REST API 的连接信息',
  source_channel: 'custom',
  coverage_dimension: 'custom',
  cost: 'custom',
  usage_level: 'exploratory',
  capabilities: [],
}

type Props = {
  onClose: () => void
  onCreated: (connector: ConnectorResponse) => void
}

export function AddSourceModal({ onClose, onCreated }: Props) {
  const [step, setStep] = useState<Step>('select')
  const [catalog, setCatalog] = useState<ProviderInfo[]>([])
  const [selected, setSelected] = useState<ProviderInfo | null>(null)
  const [apiKey, setApiKey] = useState('')

  // Custom provider fields
  const [customTitle, setCustomTitle] = useState('')
  const [customBaseUrl, setCustomBaseUrl] = useState('')
  const [customAuthStyle, setCustomAuthStyle] = useState<'query_param' | 'bearer' | 'x_api_key'>('query_param')
  const [customAuthParam, setCustomAuthParam] = useState('')
  const [customValidatePath, setCustomValidatePath] = useState('')

  const [validating, setValidating] = useState(false)
  const [validateResult, setValidateResult] = useState<{ ok: boolean; error: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const isCustom = selected?.id === 'custom'

  useEffect(() => {
    fetchCatalog().then(setCatalog).catch(console.error)
  }, [])

  useEffect(() => {
    if (step === 'configure') setTimeout(() => inputRef.current?.focus(), 50)
  }, [step])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  function buildCustomConfig(): CustomProviderConfig | undefined {
    if (!isCustom) return undefined
    return {
      title: customTitle.trim(),
      base_url: customBaseUrl.trim(),
      auth_style: customAuthStyle,
      auth_param: customAuthParam.trim(),
      validate_path: customValidatePath.trim(),
    }
  }

  function isConfigureValid(): boolean {
    if (!apiKey.trim()) return false
    if (isCustom) return !!(customTitle.trim() && customBaseUrl.trim() && customAuthParam.trim())
    return true
  }

  async function handleValidate() {
    if (!selected || !isConfigureValid()) return
    setValidating(true)
    setValidateResult(null)
    try {
      const result = await validateConnector(selected.id, apiKey.trim(), buildCustomConfig())
      setValidateResult(result)
    } catch {
      setValidateResult({ ok: false, error: '请求失败，请检查网络' })
    } finally {
      setValidating(false)
    }
  }

  async function handleSave() {
    if (!selected || !isConfigureValid()) return
    setSaving(true)
    setSaveError(null)
    try {
      const connector = await createConnector(selected.id, apiKey.trim(), buildCustomConfig())
      onCreated(connector)
      setStep('done')
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  function resetConfigure() {
    setStep('select')
    setValidateResult(null)
    setApiKey('')
    setCustomTitle('')
    setCustomBaseUrl('')
    setCustomAuthParam('')
    setCustomValidatePath('')
  }

  const allProviders = [...catalog, CUSTOM_PROVIDER]

  const modal = (
    <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal-panel" role="dialog" aria-modal="true">

        {/* Header */}
        <div className="modal-header">
          <div>
            <div className="eyebrow">Sources</div>
            <h3 className="modal-title">接入新来源</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="关闭">✕</button>
        </div>

        {/* Step: select */}
        {step === 'select' && (
          <div className="modal-body">
            <p className="modal-hint">选择数据源类型</p>
            <div className="provider-grid">
              {allProviders.map((p) => (
                <button
                  key={p.id}
                  className={`provider-card${selected?.id === p.id ? ' selected' : ''}${p.id === 'custom' ? ' provider-card-custom' : ''}`}
                  onClick={() => setSelected(p)}
                >
                  <span className="provider-title">{p.title}</span>
                  {p.id !== 'custom' && (
                    <span className="provider-channel">{p.source_channel}</span>
                  )}
                  <span className="provider-cost-badge">
                    {p.id === 'custom' ? '自定义' : (p.cost ?? 'free')}
                  </span>
                  <span className="provider-desc">{p.description}</span>
                </button>
              ))}
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={onClose}>取消</button>
              <button className="btn-primary" disabled={!selected} onClick={() => setStep('configure')}>
                下一步
              </button>
            </div>
          </div>
        )}

        {/* Step: configure */}
        {step === 'configure' && selected && (
          <div className="modal-body">
            <div className="configure-provider-name">
              <span className="eyebrow">配置</span>
              <strong>{isCustom ? (customTitle || '自定义来源') : selected.title}</strong>
            </div>

            {/* Custom-only fields */}
            {isCustom && (
              <>
                <label className="field-label">来源名称</label>
                <input
                  className="field-input"
                  placeholder="例：My Bloomberg Feed"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                />

                <label className="field-label">Base URL</label>
                <input
                  className="field-input"
                  placeholder="https://api.example.com/v1"
                  value={customBaseUrl}
                  onChange={(e) => setCustomBaseUrl(e.target.value)}
                />

                <label className="field-label">认证方式</label>
                <select
                  className="field-input"
                  value={customAuthStyle}
                  onChange={(e) => setCustomAuthStyle(e.target.value as typeof customAuthStyle)}
                >
                  <option value="query_param">Query Param（?key=xxx）</option>
                  <option value="bearer">Bearer Token（Authorization: Bearer xxx）</option>
                  <option value="x_api_key">X-API-Key Header</option>
                </select>

                <label className="field-label">
                  {customAuthStyle === 'query_param' ? 'Param 名称' : 'Header 名称'}
                </label>
                <input
                  className="field-input"
                  placeholder={customAuthStyle === 'query_param' ? 'apikey' : 'X-Api-Key'}
                  value={customAuthParam}
                  onChange={(e) => setCustomAuthParam(e.target.value)}
                />

                <label className="field-label">验证路径（可选）</label>
                <input
                  className="field-input"
                  placeholder="/status 或留空跳过验证"
                  value={customValidatePath}
                  onChange={(e) => setCustomValidatePath(e.target.value)}
                />
              </>
            )}

            <label className="field-label">API Key</label>
            <input
              ref={inputRef}
              type="password"
              className="field-input"
              placeholder={`输入 ${isCustom ? '你的' : selected.title} API Key`}
              value={apiKey}
              onChange={(e) => { setApiKey(e.target.value); setValidateResult(null) }}
              onKeyDown={(e) => { if (e.key === 'Enter') handleValidate() }}
            />

            {validateResult && (
              <div className={`validate-result ${validateResult.ok ? 'ok' : 'err'}`}>
                {validateResult.ok ? '✓ 连接成功' : `✗ ${validateResult.error}`}
              </div>
            )}
            {saveError && <div className="validate-result err">{saveError}</div>}

            <div className="modal-footer">
              <button className="btn-secondary" onClick={resetConfigure}>返回</button>
              <button
                className="btn-outline"
                disabled={!isConfigureValid() || validating}
                onClick={handleValidate}
              >
                {validating ? '验证中…' : '测试连接'}
              </button>
              <button
                className="btn-primary"
                disabled={!isConfigureValid() || saving}
                onClick={handleSave}
              >
                {saving ? '保存中…' : '确认接入'}
              </button>
            </div>
          </div>
        )}

        {/* Step: done */}
        {step === 'done' && selected && (
          <div className="modal-body modal-done">
            <div className="done-icon">✓</div>
            <p className="done-title">{isCustom ? customTitle || '自定义来源' : selected.title} 已接入</p>
            <p className="done-sub">数据源已激活，Agent 沙盘将在下一轮推演中读取此来源。</p>
            <div className="modal-footer">
              <button className="btn-primary" onClick={onClose}>完成</button>
            </div>
          </div>
        )}

      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
