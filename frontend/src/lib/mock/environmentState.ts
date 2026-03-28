/**
 * Environment Bar 交互状态 Mock 数据
 *
 * 覆盖 5 种 UX 状态，用于前端交互开发与视觉验证，无需后端运行。
 *
 * idle         → 系统刚启动，无信号，显示中性基准
 * classifying  → 消息提交中，Layer 1 扫描分类（动效驱动阶段）
 * active       → 环境变量成型，部分 chip 亮起
 * cooling      → 第二轮后，上一轮信号开始衰减
 * conflicted   → 同一类别存在方向相反的信号
 */

import type { SandboxEnvironmentState, SandboxPipelineStage } from '../types/sandbox'

// ── 1. IDLE ─────────────────────────────────────────────────────────────────
// 系统初始状态：5 个 chip 全为 idle，Risk Tone 为 neutral
// UI 应展示：全灰 chip + "— Neutral" badge，传达"系统有先验基准"而非空白

export const mockEnvIdle: SandboxEnvironmentState = {
  sandboxId: 'mock-sandbox-001',
  symbol: 'AAPL',
  market: 'US',
  globalRiskTone: 'neutral',
  updatedAt: new Date().toISOString(),
  version: 0,
  buckets: [
    { type: 'geopolitics',       displayName: '地缘政治',   activeSignals: [], dominantDirection: 'neutral', aggregateStrength: 0, status: 'idle' },
    { type: 'macro_policy',      displayName: '宏观政策',   activeSignals: [], dominantDirection: 'neutral', aggregateStrength: 0, status: 'idle' },
    { type: 'market_sentiment',  displayName: '市场情绪',   activeSignals: [], dominantDirection: 'neutral', aggregateStrength: 0, status: 'idle' },
    { type: 'fundamentals',      displayName: '公司基本面', activeSignals: [], dominantDirection: 'neutral', aggregateStrength: 0, status: 'idle' },
    { type: 'alternative_data',  displayName: '另类数据',   activeSignals: [], dominantDirection: 'neutral', aggregateStrength: 0, status: 'idle' },
  ],
}

// ── 2. CLASSIFYING ──────────────────────────────────────────────────────────
// 消息提交后，Layer 1 正在分类，前端动效阶段
// UI 应展示：逐 chip 扫描 pulse 动效（通过 pipelineStage = 'classifying' 触发）
// 数据结构与 idle 相同，驱动动效的是 pipelineStage，不是 buckets 内容

export const mockEnvClassifying: SandboxEnvironmentState = {
  ...mockEnvIdle,
  version: 1,
}

export const mockPipelineClassifying: SandboxPipelineStage = 'classifying'

// ── 3. ACTIVE ───────────────────────────────────────────────────────────────
// 场景："美联储暗示不降息 + 中东局势升级"
// 宏观政策 + 地缘政治 active，市场情绪通过联动推断 active，其余 idle

export const mockEnvActive: SandboxEnvironmentState = {
  sandboxId: 'mock-sandbox-001',
  symbol: 'AAPL',
  market: 'US',
  globalRiskTone: 'risk_off',
  updatedAt: new Date().toISOString(),
  version: 1,
  buckets: [
    {
      type: 'geopolitics',
      displayName: '地缘政治',
      status: 'active',
      dominantDirection: 'negative',
      aggregateStrength: 4,
      lastUpdatedAt: new Date().toISOString(),
      activeSignals: [
        {
          id: 'sig-geo-001',
          messageId: 'msg-001',
          environmentType: 'geopolitics',
          title: '中东局势升级',
          summary: '中东地区军事冲突再度升级，油价跳涨，全球风险溢价上行',
          direction: 'negative',
          strength: 4,
          horizon: 'short_term',
          relatedSymbols: [],
          relatedMarkets: ['US', 'HK'],
          entities: ['中东', '石油'],
          tags: ['地缘风险', '油价'],
          detectedAt: new Date().toISOString(),
          evidence: [{ kind: 'event', value: '中东局势升级导致油价跳涨 +3.2%' }],
        },
      ],
    },
    {
      type: 'macro_policy',
      displayName: '宏观政策',
      status: 'active',
      dominantDirection: 'negative',
      aggregateStrength: 3,
      lastUpdatedAt: new Date().toISOString(),
      activeSignals: [
        {
          id: 'sig-mac-001',
          messageId: 'msg-001',
          environmentType: 'macro_policy',
          title: '美联储暗示不降息',
          summary: '美联储发言暗示全年维持高利率，流动性收紧预期持续',
          direction: 'negative',
          strength: 3,
          horizon: 'mid_term',
          relatedSymbols: [],
          relatedMarkets: ['US'],
          entities: ['美联储', 'FOMC'],
          tags: ['利率', '流动性'],
          detectedAt: new Date().toISOString(),
          evidence: [{ kind: 'quote', value: '美联储官员："当前利率水平是合适的"' }],
        },
      ],
    },
    {
      type: 'market_sentiment',
      displayName: '市场情绪',
      status: 'active',
      dominantDirection: 'negative',
      aggregateStrength: 3,
      lastUpdatedAt: new Date().toISOString(),
      activeSignals: [
        {
          id: 'sig-sent-001',
          messageId: 'msg-001',
          environmentType: 'market_sentiment',
          title: '避险情绪升温',
          summary: '受地缘与货币政策双重压力，市场整体避险情绪明显上升',
          direction: 'negative',
          strength: 3,
          horizon: 'short_term',
          relatedSymbols: [],
          relatedMarkets: ['US', 'HK'],
          entities: [],
          tags: ['避险', '风险规避'],
          detectedAt: new Date().toISOString(),
          evidence: [{ kind: 'metric', value: 'VIX 上涨至 22.4，高于30日均值' }],
        },
      ],
    },
    {
      type: 'fundamentals',
      displayName: '公司基本面',
      status: 'idle',
      dominantDirection: 'neutral',
      aggregateStrength: 0,
      activeSignals: [],
    },
    {
      type: 'alternative_data',
      displayName: '另类数据',
      status: 'idle',
      dominantDirection: 'neutral',
      aggregateStrength: 0,
      activeSignals: [],
    },
  ],
}

// ── 4. COOLING ───────────────────────────────────────────────────────────────
// 场景：第二轮输入进来，上一轮的地缘政治信号进入衰减
// 地缘政治 cooling，宏观政策仍 active，公司基本面新激活（腾讯财报超预期）

export const mockEnvCooling: SandboxEnvironmentState = {
  sandboxId: 'mock-sandbox-001',
  symbol: 'AAPL',
  market: 'US',
  globalRiskTone: 'mixed',
  updatedAt: new Date().toISOString(),
  version: 2,
  buckets: [
    {
      type: 'geopolitics',
      displayName: '地缘政治',
      status: 'cooling',                  // ← 上轮信号，本轮未更新
      dominantDirection: 'negative',
      aggregateStrength: 2,
      lastUpdatedAt: new Date(Date.now() - 300_000).toISOString(),
      activeSignals: [
        {
          id: 'sig-geo-001',
          messageId: 'msg-001',
          environmentType: 'geopolitics',
          title: '中东局势升级',
          summary: '中东地区军事冲突升级（上轮信号，持续衰减中）',
          direction: 'negative',
          strength: 2,
          horizon: 'short_term',
          relatedSymbols: [],
          relatedMarkets: ['US'],
          entities: [],
          tags: ['地缘风险'],
          detectedAt: new Date(Date.now() - 300_000).toISOString(),
          evidence: [],
        },
      ],
    },
    {
      type: 'macro_policy',
      displayName: '宏观政策',
      status: 'active',
      dominantDirection: 'negative',
      aggregateStrength: 3,
      lastUpdatedAt: new Date().toISOString(),
      activeSignals: mockEnvActive.buckets.find(b => b.type === 'macro_policy')!.activeSignals,
    },
    {
      type: 'market_sentiment',
      displayName: '市场情绪',
      status: 'cooling',
      dominantDirection: 'mixed',
      aggregateStrength: 2,
      lastUpdatedAt: new Date(Date.now() - 200_000).toISOString(),
      activeSignals: [],
    },
    {
      type: 'fundamentals',
      displayName: '公司基本面',
      status: 'active',                   // ← 本轮新激活
      dominantDirection: 'positive',
      aggregateStrength: 4,
      lastUpdatedAt: new Date().toISOString(),
      activeSignals: [
        {
          id: 'sig-fund-001',
          messageId: 'msg-002',
          environmentType: 'fundamentals',
          title: '腾讯财报超预期',
          summary: '腾讯 Q4 净利润同比增长 44%，远超市场预期',
          direction: 'positive',
          strength: 4,
          horizon: 'mid_term',
          relatedSymbols: ['700.HK'],
          relatedMarkets: ['HK'],
          entities: ['腾讯'],
          tags: ['财报', '超预期'],
          detectedAt: new Date().toISOString(),
          evidence: [{ kind: 'metric', value: 'Q4 净利润 487 亿，预期 340 亿' }],
        },
      ],
    },
    {
      type: 'alternative_data',
      displayName: '另类数据',
      status: 'idle',
      dominantDirection: 'neutral',
      aggregateStrength: 0,
      activeSignals: [],
    },
  ],
}

// ── 5. CONFLICTED ────────────────────────────────────────────────────────────
// 场景：市场情绪同时收到"恐慌性抛售"和"技术性超跌反弹"两条相反信号
// UI 应展示：⚡ 信号分裂，bucket 的 dominantDirection = 'mixed'

export const mockEnvConflicted: SandboxEnvironmentState = {
  ...mockEnvActive,
  globalRiskTone: 'mixed',
  version: 3,
  buckets: mockEnvActive.buckets.map(b => {
    if (b.type !== 'market_sentiment') return b
    return {
      ...b,
      dominantDirection: 'mixed' as const,
      aggregateStrength: 2,
      activeSignals: [
        {
          id: 'sig-sent-conflict-a',
          messageId: 'msg-003',
          environmentType: 'market_sentiment' as const,
          title: '恐慌性抛售',
          summary: '市场出现恐慌性集中抛售，短期情绪极度悲观',
          direction: 'negative' as const,
          strength: 4 as const,
          horizon: 'intraday' as const,
          relatedSymbols: [],
          relatedMarkets: ['US'],
          entities: [],
          tags: ['恐慌', '抛售'],
          detectedAt: new Date().toISOString(),
          evidence: [{ kind: 'metric', value: '成交量异常放大 3.2x，买卖比 0.31' }],
        },
        {
          id: 'sig-sent-conflict-b',
          messageId: 'msg-003',
          environmentType: 'market_sentiment' as const,
          title: '技术性超跌反弹信号',
          summary: 'RSI 跌入超卖区间，部分资金开始逆势布局',
          direction: 'positive' as const,
          strength: 2 as const,
          horizon: 'short_term' as const,
          relatedSymbols: [],
          relatedMarkets: ['US'],
          entities: [],
          tags: ['超跌', '反弹'],
          detectedAt: new Date().toISOString(),
          evidence: [{ kind: 'metric', value: 'RSI(14) = 24.7，低于超卖线' }],
        },
      ],
    }
  }),
}

// ── 导出汇总 ─────────────────────────────────────────────────────────────────

export const ENV_MOCK_STATES = {
  idle:        { state: mockEnvIdle,       pipeline: 'idle'           as const },
  classifying: { state: mockEnvClassifying, pipeline: 'classifying'   as const },
  active:      { state: mockEnvActive,     pipeline: 'environment_ready' as const },
  cooling:     { state: mockEnvCooling,    pipeline: 'environment_ready' as const },
  conflicted:  { state: mockEnvConflicted, pipeline: 'environment_ready' as const },
} satisfies Record<string, { state: SandboxEnvironmentState; pipeline: SandboxPipelineStage | 'idle' }>
