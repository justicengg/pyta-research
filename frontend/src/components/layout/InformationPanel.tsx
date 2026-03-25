import { useEffect, useRef, useState } from 'react'
import { IconButton } from '../common/IconButton'
import { SettingsPopover } from './SettingsPopover'
import { AddSourceModal } from './AddSourceModal'
import { UploadModal, type UploadResult } from './UploadModal'
import { ConnectorCopilotModal, type ConnectorSpec } from './ConnectorCopilotModal'
import { useTheme } from '../../hooks/useTheme'
import { fetchConnectors, deleteConnector, type ConnectorResponse } from '../../lib/api/sources'
import type { CanvasState, RecommendedBundle } from '../../lib/types/canvas'
import type { CanvasInputEvent, SandboxSessionStatus } from '../../lib/types/sandbox'

type Props = {
  collapsed: boolean
  onToggle: () => void
  state: CanvasState
  currentInputEvents: CanvasInputEvent[]
  sessionStatus: SandboxSessionStatus
  error: string | null
  defaultSymbol?: string
  defaultMarket?: string
}

function ConnectorStatusDot({ status }: { status: ConnectorResponse['status'] }) {
  const colorMap: Record<string, string> = {
    healthy: 'var(--accent)',
    syncing: 'var(--orange)',
    error: 'var(--down)',
    inactive: 'var(--text-3)',
  }
  return (
    <span
      className="connector-status-dot"
      style={{ background: colorMap[status] ?? 'var(--text-3)' }}
      title={status}
    />
  )
}

function SourceCard({ source, onDelete }: { source: ConnectorResponse; onDelete: (id: string) => void }) {
  const [confirming, setConfirming] = useState(false)

  async function handleDelete() {
    if (!confirming) { setConfirming(true); return }
    await deleteConnector(source.id)
    onDelete(source.id)
  }

  return (
    <div className="connector-card">
      <div className="connector-card-head">
        <ConnectorStatusDot status={source.status} />
        <span className="connector-title">{source.title}</span>
        <span className="connector-cost">{source.cost}</span>
        <button
          className="connector-delete-btn"
          onClick={handleDelete}
          title={confirming ? '再次点击确认删除' : '移除此来源'}
        >
          {confirming ? '确认?' : '×'}
        </button>
      </div>
      <div className="connector-meta">
        <span className="connector-caps">{source.capabilities.join(' · ')}</span>
        <span className="connector-sync">
          {source.status === 'syncing' ? '同步中…' : source.last_synced_at ? source.last_synced_at : '—'}
        </span>
      </div>
    </div>
  )
}

function BundleRow({ bundle }: { bundle: RecommendedBundle }) {
  return (
    <div className="bundle-row">
      <div className="bundle-row-main">
        <span className="bundle-name">{bundle.name}</span>
        <span className="bundle-reason">{bundle.reason}</span>
      </div>
      <button className="bundle-add-btn" aria-label="接入此 Bundle">+</button>
    </div>
  )
}

export function InformationPanel({ collapsed, onToggle, state, currentInputEvents, sessionStatus, error, defaultSymbol = '', defaultMarket = 'US' }: Props) {
  const { theme, setTheme } = useTheme()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [addSourceOpen, setAddSourceOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [copilotOpen, setCopilotOpen] = useState(false)
  const [liveConnectors, setLiveConnectors] = useState<ConnectorResponse[]>([])
  const gearRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    fetchConnectors().then(setLiveConnectors).catch(console.error)
  }, [])

  function handleConnectorCreated(c: ConnectorResponse) {
    setLiveConnectors((prev) => [c, ...prev])
    setAddSourceOpen(false)
  }

  function handleConnectorDeleted(id: string) {
    setLiveConnectors((prev) => prev.filter((c) => c.id !== id))
  }

  if (collapsed) {
    return (
      <aside className="sidebar collapsed">
        <button
          ref={gearRef}
          className="sidebar-float-btn"
          type="button"
          onClick={() => setSettingsOpen((v) => !v)}
          aria-label="打开设置"
        >
          ⚙
        </button>
        {settingsOpen && (
          <SettingsPopover
            theme={theme}
            setTheme={setTheme}
            onClose={() => setSettingsOpen(false)}
            anchorRef={gearRef}
          />
        )}
        <button className="sidebar-float-btn" type="button" onClick={onToggle} aria-label="展开左侧边栏">
          ⟩
        </button>
      </aside>
    )
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <div>
          <div className="eyebrow">信源管理</div>
          <h2>情报台</h2>
        </div>
        <div className="head-actions">
          <div style={{ position: 'relative' }}>
            <IconButton
              ref={gearRef}
              aria-label="打开设置"
              type="button"
              onClick={() => setSettingsOpen((v) => !v)}
            >⚙</IconButton>
            {settingsOpen && (
              <SettingsPopover
                theme={theme}
                setTheme={setTheme}
                onClose={() => setSettingsOpen(false)}
                anchorRef={gearRef}
              />
            )}
          </div>
          <IconButton type="button" onClick={onToggle} aria-label="收起左侧边栏">⟨</IconButton>
        </div>
      </div>

      <div className="sidebar-summary">
        <div className="sidebar-summary-copy">
          <span className="sidebar-summary-label">研究对象</span>
          <strong className="sidebar-summary-title">
            {defaultSymbol ? `${defaultSymbol} · ${defaultMarket}` : '研究工作台'}
          </strong>
          <span className="sidebar-summary-sub">
            负责接入来源、筛选推荐 Bundle，并维持会话上下文。
          </span>
        </div>
        <div className="sidebar-summary-meta">
          <span className="sidebar-summary-pill">
            <span className={`sidebar-summary-pill-dot ${sessionStatus === 'running' ? 'running' : ''}`} />
            {sessionStatus === 'running' ? '运行中' : sessionStatus}
          </span>
          <span className="sidebar-summary-pill">{liveConnectors.length} 个来源</span>
        </div>
      </div>

      <div className="side-search">
        <input
          type="text"
          placeholder="搜索来源、事件、参考资料"
          aria-label="搜索来源、事件、参考资料"
        />
      </div>

      <div className="sidebar-body">

        {/* SOURCES */}
        <section className="section">
          <div className="section-label-row">
            <span className="section-label">数据来源</span>
            <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
              <button
                className="section-action-btn"
                aria-label="上传文件"
                type="button"
                onClick={() => setUploadOpen(true)}
                title="上传 CSV / Excel / Markdown"
              >
                ↑ 上传
              </button>
              <button
                className="section-action-btn"
                aria-label="接入新来源"
                type="button"
                onClick={() => setAddSourceOpen(true)}
              >
                + 接入
              </button>
            </div>
          </div>
          {liveConnectors.length === 0 && (
            <p className="section-empty">暂无接入来源，点击「+ 接入」添加数据源。</p>
          )}
          {liveConnectors.map((source) => (
            <SourceCard key={source.id} source={source} onDelete={handleConnectorDeleted} />
          ))}

          {/* Connector Copilot entry */}
          <div className="copilot-entry">
            <div className="copilot-entry-copy">
              <div className="copilot-entry-title">
                <svg className="copilot-entry-icon" width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                  <circle cx="6.5" cy="6.5" r="2" fill="currentColor" opacity="0.9"/>
                  <path d="M6.5 1v1.5M6.5 10.5V12M1 6.5h1.5M10.5 6.5H12M2.55 2.55l1.06 1.06M9.39 9.39l1.06 1.06M2.55 10.45l1.06-1.06M9.39 3.61l1.06-1.06" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                </svg>
                智能接入助手
              </div>
              <div className="copilot-entry-sub">粘贴 API 文档，自动生成接入配置</div>
            </div>
            <button className="copilot-entry-btn" type="button" onClick={() => setCopilotOpen(true)}>
              开始接入 →
            </button>
          </div>
        </section>

        {addSourceOpen && (
          <AddSourceModal
            onClose={() => setAddSourceOpen(false)}
            onCreated={handleConnectorCreated}
          />
        )}

        {uploadOpen && (
          <UploadModal
            defaultSymbol={defaultSymbol}
            defaultMarket={defaultMarket}
            onClose={() => setUploadOpen(false)}
            onSuccess={(_result: UploadResult) => setUploadOpen(false)}
          />
        )}

        {copilotOpen && (
          <ConnectorCopilotModal
            onClose={() => setCopilotOpen(false)}
            onSpecGenerated={(_spec: ConnectorSpec) => {
              setCopilotOpen(false)
              // Refresh connector list after saving
              fetchConnectors().then(setLiveConnectors).catch(console.error)
            }}
          />
        )}

        {/* RECOMMENDED */}
        <section className="section">
          <div className="section-label">推荐数据源</div>
          {state.leftPanel.recommendedBundles.map((bundle) => (
            <BundleRow key={bundle.name} bundle={bundle} />
          ))}
        </section>

        {/* SESSION */}
        <section className="section">
          <div className="section-label">会话状态</div>
          <div className="session-row">
            <span className={`session-status-dot ${sessionStatus === 'running' ? 'running' : ''}`} />
            <span className="session-status-text">
              {error ?? (sessionStatus === 'running' ? '推演运行中' : sessionStatus)}
            </span>
            {currentInputEvents.length > 0 && (
              <span className="session-event-count">{currentInputEvents.length} 条输入</span>
            )}
          </div>
        </section>

        {/* EXTERNAL AGENT */}
        <section className="section">
          <div className="section-label">外部智能体</div>
          <div className="inline-entry">
            <div className="inline-entry-main">
              <span className="inline-entry-title">外部智能体接入口</span>
              <span className="inline-entry-sub">后续支持用户自定义智能体与内置智能体协作接入</span>
            </div>
            <span className="status-pill warning">预留</span>
          </div>
        </section>

      </div>
    </aside>
  )
}
