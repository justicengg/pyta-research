import { useRef, useState } from 'react'

export type UploadResult = {
  rows_parsed: number
  rows_stored: number
  column_mapping: Record<string, string>
  quality_score: number
  unmapped_columns: string[]
}

type Props = {
  defaultSymbol?: string
  defaultMarket?: string
  onClose: () => void
  onSuccess: (result: UploadResult) => void
}

export function UploadModal({ defaultSymbol = '', defaultMarket = 'US', onClose, onSuccess }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [symbol, setSymbol] = useState(defaultSymbol)
  const [market, setMarket] = useState(defaultMarket)
  const [over, setOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<UploadResult | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleFileSelect(f: File) {
    setFile(f)
    setResult(null)
    setUploadError(null)
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.[0]) handleFileSelect(e.target.files[0])
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f) handleFileSelect(f)
  }

  async function handleUpload() {
    if (!file || !symbol.trim()) return
    setUploading(true)
    setUploadError(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('symbol', symbol.trim())
      fd.append('market', market)
      const res = await fetch('/api/v1/upload/market-data', { method: 'POST', body: fd })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: UploadResult = await res.json()
      setResult(data)
      onSuccess(data)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err))
    } finally {
      setUploading(false)
    }
  }

  const dropZoneClass = [
    'upload-drop-zone',
    over ? 'upload-drop-zone--over' : '',
    file ? 'upload-drop-zone--has-file' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className="upload-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="upload-modal-title">
          <span>上传市场数据文件</span>
          <button
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', fontSize: 18 }}
            onClick={onClose}
            aria-label="关闭"
          >×</button>
        </div>

        {/* Drop zone */}
        <div
          className={dropZoneClass}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setOver(true) }}
          onDragLeave={() => setOver(false)}
          onDrop={onDrop}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx,.md,.txt"
            style={{ display: 'none' }}
            onChange={onInputChange}
          />
          {file ? (
            <span>📄 {file.name}</span>
          ) : (
            <span>拖拽文件至此，或点击选择<br /><small style={{ opacity: 0.7 }}>支持 CSV · XLSX · MD · TXT</small></span>
          )}
        </div>

        {/* Symbol + market */}
        <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
          <input
            style={{
              flex: 1,
              background: 'var(--surface-subtle)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-md)',
              padding: '6px 10px',
              fontSize: 'var(--fs-xs)',
              color: 'var(--text-1)',
            }}
            placeholder="标的代码，如 AAPL"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          />
          <select
            style={{
              background: 'var(--surface-subtle)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-md)',
              padding: '6px 8px',
              fontSize: 'var(--fs-xs)',
              color: 'var(--text-1)',
            }}
            value={market}
            onChange={(e) => setMarket(e.target.value)}
          >
            <option value="US">美股 US</option>
            <option value="HK">港股 HK</option>
            <option value="A">A股 A</option>
          </select>
        </div>

        {/* Upload button */}
        <button
          style={{
            background: 'var(--accent)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--r-md)',
            padding: '8px 16px',
            fontSize: 'var(--fs-xs)',
            fontWeight: 600,
            cursor: uploading || !file || !symbol.trim() ? 'not-allowed' : 'pointer',
            opacity: uploading || !file || !symbol.trim() ? 0.5 : 1,
          }}
          onClick={handleUpload}
          disabled={uploading || !file || !symbol.trim()}
        >
          {uploading ? '上传中…' : '上传'}
        </button>

        {uploadError && (
          <p style={{ fontSize: 'var(--fs-xs)', color: '#c44949', margin: 0 }}>上传失败：{uploadError}</p>
        )}

        {/* Result */}
        {result && (
          <div className="upload-result">
            <div className="upload-result-row">
              <span>解析行数</span><strong>{result.rows_parsed}</strong>
            </div>
            <div className="upload-result-row">
              <span>质量评分</span>
              <strong>{(result.quality_score * 100).toFixed(0)}%</strong>
            </div>
            {Object.keys(result.column_mapping).length > 0 && (
              <div style={{ marginTop: 'var(--sp-2)' }}>
                <div style={{ color: 'var(--text-3)', marginBottom: 4, fontSize: 10 }}>字段映射</div>
                {Object.entries(result.column_mapping).map(([k, v]) => (
                  <div key={k} className="upload-result-row">
                    <span>{k}</span><strong>{v}</strong>
                  </div>
                ))}
              </div>
            )}
            {result.unmapped_columns.length > 0 && (
              <div style={{ marginTop: 'var(--sp-2)', fontSize: 10, color: 'var(--text-3)' }}>
                未映射列：{result.unmapped_columns.join(', ')}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
