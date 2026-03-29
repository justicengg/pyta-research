"""Unit tests for primary market schemas."""

from uuid import uuid4

import pytest

from src.sandbox.schemas.primary_market import (
    AssumptionLevel,
    AssumptionStatus,
    CompanyAnalysisReport,
    CompanyStage,
    DimensionAssessment,
    FinancialLens,
    FounderAnalysis,
    FounderArchetype,
    KeyAssumption,
    KeyAssumptions,
    MarketType,
    PathFork,
    PathForkTrigger,
    StageFit,
    UncertaintyDimension,
    UncertaintyMap,
    UncertaintyScore,
)


class TestUncertaintyMap:
    def test_all_dimensions_accepted(self):
        assessments = {
            dim: DimensionAssessment(score=UncertaintyScore.HIGH, narrative="test")
            for dim in UncertaintyDimension
        }
        umap = UncertaintyMap(market_type=MarketType.NEW_MARKET, assessments=assessments)
        assert len(umap.assessments) == len(UncertaintyDimension)

    def test_market_type_variants(self):
        for mt in MarketType:
            umap = UncertaintyMap(market_type=mt, assessments={})
            assert umap.market_type == mt


class TestFounderAnalysis:
    def test_stage_fit_matched(self):
        founder = FounderAnalysis(
            company_stage=CompanyStage.ZERO_TO_ONE,
            archetype=FounderArchetype.VISIONARY,
            founder_market_fit=UncertaintyScore.LOW,
            execution_signal="Built 2 prior startups.",
            domain_depth="Deep AI infra expertise.",
            team_building=UncertaintyScore.LOW,
            self_awareness=UncertaintyScore.LOW,
            stage_fit=StageFit.MATCHED,
            stage_fit_narrative="Visionary founder fits 0→1 stage well.",
        )
        assert founder.stage_fit == StageFit.MATCHED

    def test_stage_fit_mismatched(self):
        founder = FounderAnalysis(
            company_stage=CompanyStage.ONE_TO_TEN,
            archetype=FounderArchetype.VISIONARY,
            founder_market_fit=UncertaintyScore.MEDIUM,
            execution_signal="",
            domain_depth="",
            team_building=UncertaintyScore.HIGH,
            self_awareness=UncertaintyScore.HIGH,
            stage_fit=StageFit.MISMATCHED,
            stage_fit_narrative="Visionary at 1→10 stage risks chaos.",
        )
        assert founder.stage_fit == StageFit.MISMATCHED


class TestKeyAssumptions:
    def _make_assumptions(self):
        return KeyAssumptions(items=[
            KeyAssumption(
                level=AssumptionLevel.HARD,
                description="LTV/CAC > 3x",
                status=AssumptionStatus.CONFIRMED,
                triggers_path_fork=True,
            ),
            KeyAssumption(
                level=AssumptionLevel.HARD,
                description="14-month runway to Series B",
                status=AssumptionStatus.VIOLATED,
                triggers_path_fork=True,
            ),
            KeyAssumption(
                level=AssumptionLevel.SOFT,
                description="No big-tech competitor within 18 months",
                status=AssumptionStatus.UNVERIFIED,
            ),
        ])

    def test_hard_assumptions_filter(self):
        ka = self._make_assumptions()
        assert len(ka.hard_assumptions) == 2

    def test_soft_assumptions_filter(self):
        ka = self._make_assumptions()
        assert len(ka.soft_assumptions) == 1

    def test_violated_hard_filter(self):
        ka = self._make_assumptions()
        assert len(ka.violated_hard) == 1
        assert ka.violated_hard[0].description == "14-month runway to Series B"


class TestFinancialLens:
    def test_all_optional(self):
        fl = FinancialLens()
        assert fl.arr is None
        assert fl.ltv_cac_ratio is None

    def test_partial_fill(self):
        fl = FinancialLens(arr=1_200_000, ltv_cac_ratio=4.2, runway_months=18)
        assert fl.arr == 1_200_000
        assert fl.ltv_cac_ratio == 4.2


class TestPathFork:
    def test_path_fork_structure(self):
        fork = PathFork(
            fork_id="fork-001",
            trigger=PathForkTrigger.HARD_ASSUMPTION_VIOLATED,
            trigger_assumption="LTV/CAC > 3x",
            scenario_if_holds="Thesis intact.",
            scenario_if_fails="Re-evaluate commercialization.",
            recommended_action="Verify with primary data.",
        )
        assert fork.trigger == PathForkTrigger.HARD_ASSUMPTION_VIOLATED


class TestCompanyAnalysisReport:
    def test_full_report(self):
        assessments = {
            dim: DimensionAssessment(score=UncertaintyScore.MEDIUM, narrative="ok")
            for dim in UncertaintyDimension
        }
        report = CompanyAnalysisReport(
            sandbox_id=uuid4(),
            company_name="Acme AI",
            sector="AI Infra",
            generated_at="2026-03-29T00:00:00Z",
            uncertainty_map=UncertaintyMap(
                market_type=MarketType.NEW_MARKET,
                assessments=assessments,
            ),
            founder_analysis=FounderAnalysis(
                company_stage=CompanyStage.ZERO_TO_ONE,
                archetype=FounderArchetype.TECHNICAL,
                founder_market_fit=UncertaintyScore.LOW,
                execution_signal="Prior ML research lead.",
                domain_depth="Deep transformer expertise.",
                team_building=UncertaintyScore.MEDIUM,
                self_awareness=UncertaintyScore.LOW,
                stage_fit=StageFit.NEEDS_COMPLEMENT,
                stage_fit_narrative="Technical founder needs business co-founder.",
            ),
            key_assumptions=KeyAssumptions(items=[]),
            financial_lens=FinancialLens(monthly_burn=150_000, runway_months=18),
            overall_verdict="Partial analysis.",
            round_id=str(uuid4()),
            trace_id=str(uuid4()),
        )
        assert report.company_name == "Acme AI"
        assert report.financial_lens.runway_months == 18
