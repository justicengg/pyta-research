from sqlalchemy import inspect
from sqlalchemy import create_engine


def test_alembic_upgrade_creates_tables(migrated_db: str):
    engine = create_engine(migrated_db)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        'raw_price',
        'raw_fundamental',
        'raw_macro',
        'action_queue',
        'execution_log',
        'source_connector',
        'source_event',
        'sandbox_sessions',
        'sandbox_events',
        'agent_snapshots',
        'report_records',
        'checkpoints',
    }.issubset(tables)
