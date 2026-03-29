"""
PYTA Primary-Market Analysis Schemas
=====================================
一级市场深推演模式的四模块分析结构。

四模块：
  1. 不确定性地图（6 维）
  2. 创始人分析（四层结构）
  3. 关键假设（硬/软分级）
  4. 财务透视（6 指标）
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 模块 1：不确定性地图
# ---------------------------------------------------------------------------


class UncertaintyDimension(str, Enum):
    """6 个不确定性评估维度。"""

    MARKET_VALIDITY = "market_validity"       # 市场是否成立
    TECH_BARRIER = "tech_barrier"             # 技术壁垒
    TEAM_EXECUTION = "team_execution"         # 团队执行力
    COMMERCIALIZATION = "commercialization"   # 商业化路径
    COMPETITION = "competition"               # 竞争格局
    BURN_CYCLE = "burn_cycle"                 # 烧钱周期


class UncertaintyScore(str, Enum):
    """不确定性程度。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MarketType(str, Enum):
    """市场类型，影响推演策略。"""

    NEW_MARKET = "new_market"     # 破坏性/全新市场，市场成立本身是最大不确定性
    RED_OCEAN = "red_ocean"       # 红海，竞争格局和差异化是核心
    BLUE_OCEAN = "blue_ocean"     # 蓝海，市场存在但尚未充分竞争


class DimensionAssessment(BaseModel):
    """单个维度的评估结果。"""

    score: UncertaintyScore
    narrative: str
    key_signals: list[str] = Field(default_factory=list)


class UncertaintyMap(BaseModel):
    """模块 1：不确定性地图。"""

    market_type: MarketType
    assessments: dict[UncertaintyDimension, DimensionAssessment]


# ---------------------------------------------------------------------------
# 模块 2：创始人分析（四层结构）
# ---------------------------------------------------------------------------


class CompanyStage(str, Enum):
    """公司当前所处阶段。"""

    ZERO_TO_ONE = "0_to_1"           # 验证假设、找 PMF、活下去
    ONE_TO_TEN = "1_to_10"           # 规模化已验证的东西、建流程、扩团队
    TEN_TO_HUNDRED = "10_to_100"     # 组织管理、多产品线、资本运作


class FounderArchetype(str, Enum):
    """创始人原型。"""

    VISIONARY = "visionary"           # 破坏者/愿景型：高风险偏好、想象力强、容忍混乱
    OPERATOR = "operator"             # 执行者/运营型：流程导向、数据驱动、团队扩张
    TECHNICAL = "technical"           # 技术型：深度技术壁垒，商业化可能需要补位
    DOMAIN_EXPERT = "domain_expert"   # 行业专家型：第一手行业认知，懂痛点


class StageFit(str, Enum):
    """创始人与公司当前阶段的匹配度。"""

    MATCHED = "matched"                   # 匹配
    MISMATCHED = "mismatched"             # 错位
    NEEDS_COMPLEMENT = "needs_complement" # 需要补位（引入联创或 COO）


class FounderAnalysis(BaseModel):
    """模块 2：创始人分析（四层结构）。"""

    # 第一层：公司阶段
    company_stage: CompanyStage

    # 第二层：创始人原型
    archetype: FounderArchetype

    # 第三层：固定评估维度
    founder_market_fit: UncertaintyScore       # 与赛道的契合度
    execution_signal: str                       # 过往执行记录叙述
    domain_depth: str                           # 对行业核心矛盾的理解
    team_building: UncertaintyScore             # 团队构建能力
    self_awareness: UncertaintyScore            # 自我认知与边界意识

    # 第四层：阶段匹配度
    stage_fit: StageFit
    stage_fit_narrative: str                    # 匹配/错位的具体说明
    key_risks: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 模块 3：关键假设
# ---------------------------------------------------------------------------


class AssumptionLevel(str, Enum):
    """假设级别。"""

    HARD = "hard"   # 硬假设：必须成立，失败触发 PathFork
    SOFT = "soft"   # 软假设：重要但有条件，失败调整评分


class AssumptionStatus(str, Enum):
    """假设当前验证状态。"""

    CONFIRMED = "confirmed"
    UNVERIFIED = "unverified"
    VIOLATED = "violated"


class KeyAssumption(BaseModel):
    """单条假设。"""

    level: AssumptionLevel
    description: str
    status: AssumptionStatus
    time_horizon_months: Optional[int] = None
    triggers_path_fork: bool = False   # 硬假设失败时为 True


class KeyAssumptions(BaseModel):
    """模块 3：关键假设集合。"""

    items: list[KeyAssumption] = Field(default_factory=list)

    @property
    def hard_assumptions(self) -> list[KeyAssumption]:
        return [a for a in self.items if a.level == AssumptionLevel.HARD]

    @property
    def soft_assumptions(self) -> list[KeyAssumption]:
        return [a for a in self.items if a.level == AssumptionLevel.SOFT]

    @property
    def violated_hard(self) -> list[KeyAssumption]:
        return [
            a for a in self.items
            if a.level == AssumptionLevel.HARD and a.status == AssumptionStatus.VIOLATED
        ]


# ---------------------------------------------------------------------------
# 模块 4：财务透视
# ---------------------------------------------------------------------------


class FinancialLens(BaseModel):
    """模块 4：财务透视（量化锚点，不做推演，只做核查）。"""

    arr: Optional[float] = None              # 年度经常性收入（USD）
    arr_growth_narrative: Optional[str] = None
    nrr: Optional[float] = None              # 净收入留存率（%）
    gross_margin: Optional[float] = None     # 毛利率（%）
    monthly_burn: Optional[float] = None     # 月烧钱（USD）
    ltv_cac_ratio: Optional[float] = None    # LTV/CAC 比值
    current_valuation: Optional[float] = None  # 当前估值（USD）
    runway_months: Optional[int] = None      # 剩余 runway（月）
    valuation_narrative: Optional[str] = None  # 估值与指标倍数关系说明


# ---------------------------------------------------------------------------
# PathFork：路径分叉
# ---------------------------------------------------------------------------


class PathForkTrigger(str, Enum):
    """PathFork 触发原因。"""

    HARD_ASSUMPTION_VIOLATED = "hard_assumption_violated"
    CONVERGENCE_FAILED = "convergence_failed"
    MANUAL = "manual"


class PathFork(BaseModel):
    """路径分叉节点：硬假设失败时触发，记录替代路径。"""

    fork_id: str
    trigger: PathForkTrigger
    trigger_assumption: Optional[str] = None   # 触发分叉的假设描述
    scenario_if_holds: str                     # 假设成立时的路径
    scenario_if_fails: str                     # 假设失败时的路径
    recommended_action: str                    # 建议动作


# ---------------------------------------------------------------------------
# 最终报告
# ---------------------------------------------------------------------------


class CompanyAnalysisReport(BaseModel):
    """一级市场公司分析报告（Layer 3 输入）。"""

    sandbox_id: UUID
    company_name: str
    sector: Optional[str] = None
    generated_at: str

    uncertainty_map: UncertaintyMap
    founder_analysis: FounderAnalysis
    key_assumptions: KeyAssumptions
    financial_lens: FinancialLens

    path_forks: list[PathFork] = Field(default_factory=list)
    overall_verdict: str                       # 综合判断
    confidence: float = Field(ge=0, le=1, default=0.0)

    round_id: str
    trace_id: str
