import json
import sys
from datetime import date
from pathlib import Path

from src.cli import main
from src.db.session import configure_engine, get_session, insert_raw_price


def test_quality_cli_generates_report(migrated_db: str, monkeypatch):
    configure_engine(migrated_db)
    with get_session() as session:
        insert_raw_price(
            session,
            [
                {
                    'symbol': 'SPY',
                    'market': 'US',
                    'trade_date': date(2026, 1, 1),
                    'open': 1,
                    'high': 2,
                    'low': 0.5,
                    'close': 1.5,
                    'volume': 100,
                    'adj_factor': None,
                    'source': 'yfinance',
                }
            ],
        )

    out = Path(migrated_db.replace('sqlite:///', '')).with_name('quality.json')
    monkeypatch.setattr(
        sys,
        'argv',
        ['prog', 'quality', 'check', '--table', 'raw_price', '--date', '2026-01-01', '--out', str(out)],
    )
    main()

    payload = json.loads(out.read_text(encoding='utf-8'))
    assert payload['table'] == 'raw_price'
    assert 'issue_count' in payload
