import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  fetchCatalog,
  validateConnector,
  createConnector,
  type ProviderInfo,
  type ConnectorResponse,
} from '../../lib/api/sources'

type Step = 'select' | 'configure' | 'done'

type Props = {
  onClose: () => void
  onCreated: (connector: ConnectorResponse) => void
}

const COST_LABELS: Record<string, string> = {
  free: 'free',
  freemium: 'freemium',
  paid: 'paid',
  enterprise: 'enterprise',
}

export function AddSourceModal({ onClose, onCreated }: Props) {
  const [step, setStep] = useState<Step>('select')
  const [catalog, setCatalog] = useState<ProviderInfo[]>([])
  const [selected, setSelected] = useState<ProviderInfo | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [validating, setValidating] = useState(false)
  const [validateResult, setValidateResult] = useState<{ ok: boolean; error: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchCatalog().then(setCatalog).catch(console.error)
  }, [])

  useEffect(() => {
    if (step === 'configure') {
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [step])

  // close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  async function handleValidate() {
    if (!selected || !apiKey.trim()) return
    setValidating(true)
    setValidateResult(null)
    try {
      const result = await validateConnector(selected.id, apiKey.trim())
      setValidateResult(result)
    } catch {
      setValidateResult({ ok: false, error: '请求失败，请检查网络' })
    } finally {
      setValidating(false)
    }
  }

  async function handleSave() {
    if (!selected || !apiKey.trim()) return
    setSaving(true)
    setSaveError(null)
    try {
      const connector = await createConnector(selected.id, apiKey.trim())
      onCreated(connector)
      setStep('done')
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

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

        {/* Step: select provider */}
        {step === 'select' && (
          <div className="modal-body">
            <p className="modal-hint">选择数据源类型</p>
            <div className="provider-grid">
              {catalog.map((p) => (
                <button
                  key={p.id}
                  className={`provider-card${selected?.id === p.id ? ' selected' : ''}`}
                  onClick={() => setSelected(p)}
                >
                  <span className="provider-title">{p.title}</span>
                  <span className="provider-channel">{p.source_channel}</span>
                  <span className="provider-cost-badge">{COST_LABELS[p.cost] ?? p.cost}</span>
                  <span className="provider-desc">{p.description}</span>
                </button>
              ))}
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={onClose}>取消</button>
              <button
                className="btn-primary"
                disabled={!selected}
                onClick={() => setStep('configure')}
              >
                下一步
              </button>
            </div>
          </div>
        )}

        {/* Step: configure API key */}
        {step === 'configure' && selected && (
          <div className="modal-body">
            <div className="configure-provider-name">
              <span className="eyebrow">配置</span>
              <strong>{selected.title}</strong>
            </div>

            <label className="field-label">API Key</label>
            <input
              ref={inputRef}
              type="password"
              className="field-input"
              placeholder={`输入 ${selected.title} API Key`}
              value={apiKey}
              onChange={(e) => { setApiKey(e.target.value); setValidateResult(null) }}
              onKeyDown={(e) => { if (e.key === 'Enter') handleValidate() }}
            />

            {validateResult && (
              <div className={`validate-result ${validateResult.ok ? 'ok' : 'err'}`}>
                {validateResult.ok ? '✓ 连接成功' : `✗ ${validateResult.error}`}
              </div>
            )}

            {saveError && (
              <div className="validate-result err">{saveError}</div>
            )}

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => { setStep('select'); setValidateResult(null); setApiKey('') }}>
                返回
              </button>
              <button
                className="btn-outline"
                disabled={!apiKey.trim() || validating}
                onClick={handleValidate}
              >
                {validating ? '验证中…' : '测试连接'}
              </button>
              <button
                className="btn-primary"
                disabled={!apiKey.trim() || saving}
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
            <p className="done-title">{selected.title} 已接入</p>
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
