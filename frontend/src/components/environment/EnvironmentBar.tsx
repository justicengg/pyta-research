import { useEffect, useRef, useState } from 'react'
import type { SandboxEnvironmentType, SandboxEnvironmentState, SandboxPipelineStage } from '../../lib/types/sandbox'

type Props = {
  state: SandboxEnvironmentState | null
  pipelineStage?: SandboxPipelineStage | 'idle'
}

type BucketDef = {
  type: SandboxEnvironmentType
  label: string
}

const ENV_BUCKETS: BucketDef[] = [
  { type: 'geopolitics',      label: '地缘政治' },
  { type: 'macro_policy',     label: '宏观政策' },
  { type: 'market_sentiment', label: '市场情绪' },
  { type: 'fundamentals',     label: '公司基本面' },
  { type: 'alternative_data', label: '另类数据' },
]

const DIRECTION_ICON: Record<string, string> = {
  positive: '↑',
  negative: '↓',
  mixed:    '↕',
  neutral:  '—',
}

const RISK_TONE_LABEL: Record<string, string> = {
  risk_on:  '↑ 风险偏好',
  risk_off: '↓ 风险规避',
  mixed:    '↕ 信号分化',
  neutral:  '— 中性基准',
}

// 每个 chip 的扫描延迟（ms），模拟 Layer 1 逐类别分类的过程
const SCAN_DELAYS_MS = [0, 280, 560, 840, 1120]
// 单个 chip 扫描动效持续时长
const SCAN_DURATION_MS = 500

export function EnvironmentBar({ state, pipelineStage = 'idle' }: Props) {
  const riskTone = state?.globalRiskTone ?? 'neutral'
  const isClassifying = pipelineStage === 'classifying'

  // scanIndex：当前正在扫描的 chip 索引，-1 表示未扫描
  const [scanIndex, setScanIndex] = useState<number>(-1)
  const scanTimersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  useEffect(() => {
    // 清掉上一轮的 timer
    scanTimersRef.current.forEach(clearTimeout)
    scanTimersRef.current = []

    if (!isClassifying) {
      setScanIndex(-1)
      return
    }

    // 逐 chip 顺序触发扫描 pulse
    ENV_BUCKETS.forEach((_, i) => {
      const startTimer = setTimeout(() => {
        setScanIndex(i)
        const endTimer = setTimeout(() => {
          setScanIndex(prev => (prev === i ? -1 : prev))
        }, SCAN_DURATION_MS)
        scanTimersRef.current.push(endTimer)
      }, SCAN_DELAYS_MS[i])
      scanTimersRef.current.push(startTimer)
    })

    // 全部扫描完后 reset
    const totalDuration = SCAN_DELAYS_MS[SCAN_DELAYS_MS.length - 1] + SCAN_DURATION_MS + 200
    const resetTimer = setTimeout(() => setScanIndex(-1), totalDuration)
    scanTimersRef.current.push(resetTimer)

    return () => {
      scanTimersRef.current.forEach(clearTimeout)
    }
  }, [isClassifying])

  return (
    <div
      className={`env-band${isClassifying ? ' env-band--classifying' : ''}`}
      aria-label="市场环境层"
    >
      {/* 左侧：全局风险基调 */}
      <div className={`env-risk-badge env-risk-badge--${riskTone}`}>
        {RISK_TONE_LABEL[riskTone] ?? '— 中性基准'}
      </div>

      <div className="env-band-divider" />

      {/* 右侧：5 个环境类别 chip */}
      <div className="env-chip-row">
        {ENV_BUCKETS.map((def, i) => {
          const bucket    = state?.buckets.find(b => b.type === def.type)
          const status    = bucket?.status ?? 'idle'
          const direction = bucket?.dominantDirection ?? 'neutral'
          const count     = bucket?.activeSignals.length ?? 0
          const isScanning = isClassifying && scanIndex === i

          // 信号冲突：active 且方向为 mixed 且有多条信号
          const isConflicted = status === 'active' && direction === 'mixed' && count > 1

          let chipClass = `env-chip env-chip--${status}`
          if (isScanning)   chipClass += ' env-chip--scanning'
          if (isConflicted) chipClass += ' env-chip--conflicted'

          return (
            <div
              key={def.type}
              className={chipClass}
              data-env-type={def.type}
              title={def.label}
            >
              <span className="env-chip-dot" />
              <span className="env-chip-label">{def.label}</span>

              {/* 扫描中：显示省略动画 */}
              {isScanning && (
                <span className="env-chip-scan-indicator" aria-hidden="true" />
              )}

              {/* 活跃/衰减：显示方向 + 信号数 */}
              {!isScanning && status !== 'idle' && count > 0 && (
                <span className="env-chip-signal">
                  {isConflicted ? (
                    <span className="env-chip-dir env-chip-dir--mixed" title="信号方向冲突">⚡</span>
                  ) : (
                    <span className={`env-chip-dir env-chip-dir--${direction}`}>
                      {DIRECTION_ICON[direction] ?? '—'}
                    </span>
                  )}
                  <span>{count}</span>
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
