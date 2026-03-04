from pydantic import ValidationError
import pytest

from src.strategy.schemas import (
    EntryRules,
    ExitRules,
    PositionRules,
    RiskRules,
    StopLossRule,
    ThresholdRule,
    ValuationAnchor,
)


def test_valuation_anchor_valid_roundtrip() -> None:
    payload = {
        'core_metric': 'PE',
        'fair_low': 18.0,
        'fair_high': 25.0,
        'extreme_low': 12.0,
        'extreme_high': 35.0,
    }
    model = ValuationAnchor.model_validate(payload)
    assert model.model_dump() == payload


def test_valuation_anchor_invalid_band_raises() -> None:
    with pytest.raises(ValidationError):
        ValuationAnchor.model_validate({
            'core_metric': 'PB',
            'fair_low': 2.0,
            'fair_high': 1.5,
        })


def test_position_rules_pct_bounds_raises() -> None:
    with pytest.raises(ValidationError):
        PositionRules.model_validate({
            'initial_pct': 1.2,
            'max_pct': 0.8,
            'min_pct': 0.1,
        })


def test_position_rules_valid_tiers() -> None:
    model = PositionRules.model_validate({
        'initial_pct': 0.2,
        'add_tiers': [{'trigger': 'drawdown>=8%', 'pct': 0.05}],
        'reduce_tiers': [{'trigger': 'gain>=15%', 'pct': 0.03}],
        'max_pct': 0.4,
        'min_pct': 0.05,
    })
    assert model.max_pct == 0.4
    assert len(model.add_tiers) == 1


def test_entry_exit_rules_roundtrip() -> None:
    entry = EntryRules.model_validate({
        'trigger_conditions': ['pe<=fair_low', 'roe>=0.12'],
        'filter_conditions': ['not major_earnings_risk'],
    })
    exit_rules = ExitRules.model_validate({
        'take_profit': ThresholdRule(metric='gain_pct', threshold=0.2).model_dump(),
        'stop_loss': StopLossRule(method='pct', value=0.1).model_dump(),
        'thesis_break': 'core thesis invalidated',
    })
    assert entry.trigger_conditions[0] == 'pe<=fair_low'
    assert exit_rules.stop_loss is not None
    assert exit_rules.stop_loss.value == 0.1


def test_risk_rules_boundaries() -> None:
    model = RiskRules.model_validate({
        'stock_max_loss_pct': 0.12,
        'stock_max_position_pct': 0.15,
        'sector_max_pct': 0.35,
        'portfolio_max_drawdown_pct': 0.18,
    })
    assert model.portfolio_max_drawdown_pct == 0.18

    with pytest.raises(ValidationError):
        RiskRules.model_validate({'stock_max_position_pct': -0.1})

