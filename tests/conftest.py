from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from src.config.settings import settings
from src.db.session import configure_engine


@pytest.fixture()
def test_db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture()
def migrated_db(test_db_url: str):
    versions_dir = Path(__file__).resolve().parents[1] / 'alembic' / 'versions'
    for ghost in versions_dir.glob('._*.py'):
        ghost.unlink(missing_ok=True)
    settings.database_url = test_db_url
    configure_engine(test_db_url)
    cfg = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
    command.upgrade(cfg, 'head')
    return test_db_url
