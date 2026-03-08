"""Pre-defined strategy card templates for quick card creation.

Each template provides a complete set of JSONB rule defaults that align with
the DecisionAdvisor rule engine (src/decision/advisor.py).

Rule engine mapping:
  - exit_rules.take_profit  → R2b (take_profit_hit)
  - exit_rules.stop_loss    → supplementary; R1 uses card.stop_loss_price column
  - exit_rules.thesis_break → R1b (thesis_break)
  - entry_rules             → R4b (entry_signal_hit)
  - valuation_anchor        → R4b via _valuation_below_fair_low
  - review_cadence          → R6 (review_due)
  - position_rules / risk_rules → informational for Phase 7+
"""
from __future__ import annotations

import copy
from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    'value_basic': {
        'label': '价值型（基础）',
        'expected_cycle': 'long',
        'review_cadence': 'monthly',
        'position_rules': {
            'initial_pct': 0.05,
            'add_tiers': [],
            'reduce_tiers': [],
            'max_pct': 0.15,
            'min_pct': 0.0,
        },
        'entry_rules': {
            'trigger_conditions': ['valuation_below_fair_low'],
            'filter_conditions': ['always_true'],
        },
        'exit_rules': {
            'take_profit': {'metric': 'unrealized_pnl_pct', 'threshold': 0.30},
            'stop_loss': {'method': 'fixed_pct', 'value': 0.10},
            'thesis_break': None,
        },
        'risk_rules': {
            'stock_max_loss_pct': 0.10,
            'stock_max_position_pct': 0.15,
            'sector_max_pct': 0.30,
            'portfolio_max_drawdown_pct': 0.15,
        },
    },
    'momentum': {
        'label': '动量型',
        'expected_cycle': 'short',
        'review_cadence': 'weekly',
        'position_rules': {
            'initial_pct': 0.05,
            'add_tiers': [{'trigger': 'breakout_confirmed', 'pct': 0.03}],
            'reduce_tiers': [{'trigger': 'momentum_fade', 'pct': 0.03}],
            'max_pct': 0.12,
            'min_pct': 0.0,
        },
        'entry_rules': {
            'trigger_conditions': ['valuation_below_fair_low'],
            'filter_conditions': ['always_true'],
        },
        'exit_rules': {
            'take_profit': {'metric': 'unrealized_pnl_pct', 'threshold': 0.20},
            'stop_loss': {'method': 'trailing_pct', 'value': 0.08},
            'thesis_break': None,
        },
        'risk_rules': {
            'stock_max_loss_pct': 0.08,
            'stock_max_position_pct': 0.12,
            'sector_max_pct': 0.25,
            'portfolio_max_drawdown_pct': 0.12,
        },
    },
    'defensive': {
        'label': '防守型',
        'expected_cycle': 'long',
        'review_cadence': 'quarterly',
        'position_rules': {
            'initial_pct': 0.04,
            'add_tiers': [],
            'reduce_tiers': [],
            'max_pct': 0.10,
            'min_pct': 0.0,
        },
        'entry_rules': {
            'trigger_conditions': ['valuation_below_fair_low'],
            'filter_conditions': ['always_true'],
        },
        'exit_rules': {
            'take_profit': {'metric': 'unrealized_pnl_pct', 'threshold': 0.15},
            'stop_loss': {'method': 'fixed_pct', 'value': 0.05},
            'thesis_break': 'drawdown_breach',
        },
        'risk_rules': {
            'stock_max_loss_pct': 0.05,
            'stock_max_position_pct': 0.10,
            'sector_max_pct': 0.20,
            'portfolio_max_drawdown_pct': 0.10,
        },
    },
    'balanced': {
        'label': '均衡型',
        'expected_cycle': 'medium',
        'review_cadence': 'monthly',
        'position_rules': {
            'initial_pct': 0.05,
            'add_tiers': [{'trigger': 'price_below_fair_low', 'pct': 0.03}],
            'reduce_tiers': [],
            'max_pct': 0.12,
            'min_pct': 0.0,
        },
        'entry_rules': {
            'trigger_conditions': ['valuation_below_fair_low'],
            'filter_conditions': ['always_true'],
        },
        'exit_rules': {
            'take_profit': {'metric': 'unrealized_pnl_pct', 'threshold': 0.25},
            'stop_loss': {'method': 'fixed_pct', 'value': 0.08},
            'thesis_break': None,
        },
        'risk_rules': {
            'stock_max_loss_pct': 0.08,
            'stock_max_position_pct': 0.12,
            'sector_max_pct': 0.25,
            'portfolio_max_drawdown_pct': 0.12,
        },
    },
}


def get_template(name: str) -> dict[str, Any]:
    """Return a deep copy of the template by name. Raises KeyError if not found."""
    if name not in TEMPLATES:
        raise KeyError(f'Unknown template: {name}. Available: {list(TEMPLATES.keys())}')
    return copy.deepcopy(TEMPLATES[name])


def list_templates() -> list[dict[str, str]]:
    """Return a list of available template names with labels."""
    return [{'name': k, 'label': v['label']} for k, v in TEMPLATES.items()]


def apply_overrides(template: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge overrides into template rule fields. Only known rule keys are merged."""
    rule_keys = {'position_rules', 'entry_rules', 'exit_rules', 'risk_rules', 'valuation_anchor'}
    for key, value in overrides.items():
        if key in rule_keys and isinstance(value, dict) and isinstance(template.get(key), dict):
            template[key] = _deep_merge(template[key], value)
        else:
            template[key] = value
    return template


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
