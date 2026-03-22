import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { Theme } from '../../hooks/useTheme'
import { fetchLLMStatus, saveLLMConfig } from '../../lib/api/settings'

type Props = {
  theme: Theme
  setTheme: (t: Theme) => void
  onClose: () => void
  anchorRef: React.RefObject<HTMLElement | null>
}

const THEMES: { value: Theme; label: string }[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'auto', label: 'Auto' },
]

export function SettingsPopover({ theme, setTheme, onClose, anchorRef }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState({ top: 0, left: 0 })

  useEffect(() => {
    if (anchorRef.current) {
      const rect = anchorRef.current.getBoundingClientRect()
      setPos({ top: rect.top, left: rect.right + 8 })
    }
  }, [])

  // LLM config state
  const [llmConfigured, setLlmConfigured] = useState<boolean | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('https://api.minimax.chat/v1')
  const [model, setModel] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  useEffect(() => {
    fetchLLMStatus()
      .then((s) => {
        setLlmConfigured(s.configured)
        setBaseUrl(s.base_url || 'https://api.minimax.chat/v1')
        setModel(s.model || '')
      })
      .catch(() => setLlmConfigured(false))
  }, [])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [onClose])

  async function handleSave() {
    if (!apiKey.trim()) return
    setSaving(true)
    setSaveMsg(null)
    try {
      await saveLLMConfig({ api_key: apiKey, base_url: baseUrl, model })
      setLlmConfigured(true)
      setApiKey('')
      setSaveMsg('已保存 ✓')
      setTimeout(() => setSaveMsg(null), 3000)
    } catch (e) {
      setSaveMsg(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return createPortal(
    <div className="settings-popover" ref={ref} style={{ position: 'fixed', top: pos.top, left: pos.left }}>

      {/* ── 外观 ── */}
      <div className="settings-section-label">外观</div>
      <div className="settings-theme-row">
        {THEMES.map((t) => (
          <button
            key={t.value}
            className={`settings-theme-btn ${theme === t.value ? 'active' : ''}`}
            onClick={() => setTheme(t.value)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="settings-divider" />

      {/* ── 模型 API Keys ── */}
      <div className="settings-section-label">
        模型 API Key
        {llmConfigured === true && <span className="settings-configured-badge">已配置 ✓</span>}
        {llmConfigured === false && <span className="settings-unconfigured-badge">未配置</span>}
      </div>

      <div className="settings-field">
        <label className="settings-field-label">Base URL</label>
        <input
          className="settings-input"
          type="text"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://api.minimax.chat/v1"
        />
      </div>

      <div className="settings-field">
        <label className="settings-field-label">Model</label>
        <input
          className="settings-input"
          type="text"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="MiniMax-Text-01"
        />
      </div>

      <div className="settings-field">
        <label className="settings-field-label">
          API Key {llmConfigured && <span className="settings-key-hint">（留空保持不变）</span>}
        </label>
        <input
          className="settings-input"
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={llmConfigured ? '••••••••••••••••' : '输入 API Key'}
          autoComplete="off"
        />
      </div>

      <div className="settings-save-row">
        {saveMsg && <span className="settings-save-msg">{saveMsg}</span>}
        <button
          className="settings-save-btn"
          onClick={handleSave}
          disabled={saving || !apiKey.trim()}
        >
          {saving ? '保存中…' : '保存'}
        </button>
      </div>

    </div>,
    document.body
  )
}
