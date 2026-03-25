import { useState } from 'react'

export type ConnectorSpec = {
  provider_id: string
  display_name: string
  base_url: string
  auth_type: string
  auth_param: string | null
  endpoints: Array<{ name: string; path: string; method: string }>
  field_mapping: Record<string, string>
  notes: string | null
}

type Props = {
  onClose: () => void
  onSpecGenerated: (spec: ConnectorSpec) => void
}

export function ConnectorCopilotModal({ onClose, onSpecGenerated }: Props) {
  const [docText, setDocText] = useState('')
  const [providerHint, setProviderHint] = useState('')
  const [generating, setGenerating] = useState(false)
  const [spec, setSpec] = useState<ConnectorSpec | null>(null)
  const [genError, setGenError] = useState<string | null>(null)

  async function handleGenerate() {
    if (!docText.trim()) return
    setGenerating(true)
    setGenError(null)
    setSpec(null)
    try {
      const res = await fetch('/api/v1/connectors/spec/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_text: docText.trim(),
          provider_hint: providerHint.trim() || undefined,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: ConnectorSpec = await res.json()
      setSpec(data)
    } catch (err) {
      setGenError(err instanceof Error ? err.message : String(err))
    } finally {
      setGenerating(false)
    }
  }

  function handleSave() {
    if (!spec) return
    onSpecGenerated(spec)
    onClose()
  }

  return (
    <div
      className="copilot-modal-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="copilot-modal" onClick={(e) => e.stopPropagation()}>
        <div className="copilot-modal-title">
          <span>接入新数据源</span>
          <button className="copilot-modal-close" onClick={onClose} aria-label="关闭">×</button>
        </div>

        <textarea
          className="copilot-doc-area"
          placeholder="粘贴 API 文档（支持 URL 内容、PDF 文本、JSON schema 等）"
          value={docText}
          onChange={(e) => setDocText(e.target.value)}
        />

        <input
          className="copilot-hint-input"
          placeholder="服务商提示（可选，如 alpha_vantage）"
          value={providerHint}
          onChange={(e) => setProviderHint(e.target.value)}
        />

        <button
          className="copilot-generate-btn"
          onClick={handleGenerate}
          disabled={generating || !docText.trim()}
        >
          {generating ? '生成中…' : '生成接入配置'}
        </button>

        {genError && (
          <p className="copilot-error">生成失败：{genError}</p>
        )}

        {spec && (
          <>
            <div className="copilot-spec-result">
              <div className="copilot-spec-field">
                <label>服务商</label>
                <span>{spec.display_name} ({spec.provider_id})</span>
              </div>
              <div className="copilot-spec-field">
                <label>接口地址</label>
                <span>{spec.base_url}</span>
              </div>
              <div className="copilot-spec-field">
                <label>认证方式</label>
                <span>{spec.auth_type}{spec.auth_param ? ` (${spec.auth_param})` : ''}</span>
              </div>
              {spec.endpoints.length > 0 && (
                <div className="copilot-spec-section">
                  <div className="copilot-spec-section-label">端点列表</div>
                  {spec.endpoints.map((ep, i) => (
                    <div key={i} className="copilot-spec-field">
                      <label className="copilot-spec-method">{ep.method}</label>
                      <span>{ep.name} — <code className="copilot-spec-code">{ep.path}</code></span>
                    </div>
                  ))}
                </div>
              )}
              {Object.keys(spec.field_mapping).length > 0 && (
                <div className="copilot-spec-section">
                  <div className="copilot-spec-section-label">字段映射</div>
                  {Object.entries(spec.field_mapping).map(([k, v]) => (
                    <div key={k} className="copilot-spec-field">
                      <label>{k}</label><span>{v}</span>
                    </div>
                  ))}
                </div>
              )}
              {spec.notes && (
                <div className="copilot-spec-notes">{spec.notes}</div>
              )}
            </div>

            <button className="copilot-generate-btn" onClick={handleSave}>
              保存并接入 →
            </button>
          </>
        )}
      </div>
    </div>
  )
}
