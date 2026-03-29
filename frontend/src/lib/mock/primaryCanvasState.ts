import type { PrimaryCanvasState } from '../types/primaryCanvas'

export const mockPrimaryCanvasState: PrimaryCanvasState = {
  companyName: 'Acme AI',
  sector: 'AI Infra',
  uncertaintyMap: {
    marketType: 'new_market',
    assessments: {
      market_validity: {
        score: 'high',
        narrative: '企业 AI Infra 市场尚在形成阶段，主流采购决策路径未定型，市场是否能快速规模化仍是核心风险。',
        keySignals: ['头部客户采购意愿强，但预算审批周期长', '竞品融资频繁但商业落地分散'],
      },
      tech_barrier: {
        score: 'low',
        narrative: '核心模型推理加速技术有较深护城河，专利布局完整，竞争对手复制周期预计 18 个月以上。',
        keySignals: ['3 项核心专利已授权', '团队有前 Google Brain 核心成员'],
      },
      team_execution: {
        score: 'medium',
        narrative: '技术团队顶尖，但 GTM 经验薄弱，销售和渠道搭建仍在早期。',
        keySignals: ['CTO 背景强', 'VP Sales 入职 3 个月，管道建设中'],
      },
      commercialization: {
        score: 'high',
        narrative: '从技术验证到企业批量采购的路径尚不清晰，POC 转化率偏低。',
        keySignals: ['POC 转化率约 22%', '平均合同周期 6 个月'],
      },
      competition: {
        score: 'medium',
        narrative: '直接竞争者较少，但大厂内部有类似项目，18 个月内推出的风险存在。',
        keySignals: ['AWS 有内部 roadmap 传言', '已知直接竞品 2 家，融资均 < $10M'],
      },
      burn_cycle: {
        score: 'medium',
        narrative: '当前 runway 18 个月，与 B 轮目标时间线基本匹配，但销售周期偏长存在压力。',
        keySignals: ['月烧钱 $150K', '预计 14 个月内需完成 B 轮'],
      },
    },
  },
  founderAnalysis: {
    companyStage: '0_to_1',
    archetype: 'technical',
    founderMarketFit: 'low',
    executionSignal: '联合创始人曾主导 Google Brain 推理优化项目，有从 0 到产品化的完整经历。',
    domainDepth: '对 AI 推理效率的核心技术矛盾有第一手认知，是行业内少数真正理解 memory bandwidth 瓶颈的团队。',
    teamBuilding: 'medium',
    selfAwareness: 'low',
    stageFit: 'needs_complement',
    stageFitNarrative: '技术型创始人在 0→1 阶段技术壁垒极强，但缺乏商业化经验，需要引入有 enterprise SaaS 背景的业务联创或强力 CRO。',
    keyRisks: [
      '商业化路径依赖单一技术优势，护城河一旦被大厂复制风险高',
      '创始人对销售周期和客户预算审批流程认知不足',
    ],
  },
  keyAssumptions: {
    items: [
      {
        level: 'hard',
        description: '企业客户 LTV/CAC > 3x，获客效率可持续',
        status: 'violated',
        triggersPathFork: true,
      },
      {
        level: 'hard',
        description: '在 14 个月 runway 内完成 B 轮融资或达到盈亏平衡',
        status: 'unverified',
        timeHorizonMonths: 14,
        triggersPathFork: true,
      },
      {
        level: 'soft',
        description: '大厂不会在 18 个月内推出直接竞争产品',
        status: 'unverified',
        timeHorizonMonths: 18,
        triggersPathFork: false,
      },
      {
        level: 'soft',
        description: 'AI Infra 赛道监管环境保持中性',
        status: 'confirmed',
        triggersPathFork: false,
      },
    ],
  },
  financialLens: {
    arr: 480000,
    arrGrowthNarrative: 'ARR 过去 6 个月环比增长 18%，增速稳定但绝对值偏低',
    nrr: 112,
    grossMargin: 71,
    monthlyBurn: 150000,
    ltvCacRatio: 2.1,
    currentValuation: 18000000,
    runwayMonths: 18,
    valuationNarrative: '当前估值约 37x ARR，偏高，需要未来 12 个月 ARR 翻倍支撑',
  },
  pathForks: [
    {
      forkId: 'fork-001',
      triggerAssumption: '企业客户 LTV/CAC > 3x，获客效率可持续',
      scenarioIfHolds: '获客效率改善，商业化路径成立，B 轮融资路径清晰。',
      scenarioIfFails: '需重新评估 GTM 策略，考虑 PLG 路径或聚焦更高 LTV 的行业垂直市场。',
      recommendedAction: '立即用真实客户数据验证，优先完成 3 个企业 POC 转化，获取 12 个月 LTV 数据。',
    },
  ],
  overallVerdict: 'HIGH RISK: 1 hard assumption violated — PathFork triggered. LTV/CAC 当前低于门槛，需在 90 天内验证获客效率。',
  confidence: 0.61,
}
