from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings
from src.db.models import RawFundamental, RawMacro, RawPrice

engine = None
SessionLocal = None


def configure_engine(database_url: str | None = None):
    global engine, SessionLocal
    engine = create_engine(database_url or settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return engine


configure_engine()


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_latest_trade_date(session: Session, symbol: str, market: str, source: str) -> date | None:
    stmt = (
        select(RawPrice.trade_date)
        .where(RawPrice.symbol == symbol, RawPrice.market == market, RawPrice.source == source)
        .order_by(RawPrice.trade_date.desc())
        .limit(1)
    )
    return session.scalar(stmt)


def get_latest_macro_date(session: Session, series_code: str, market: str, source: str) -> date | None:
    stmt = (
        select(RawMacro.obs_date)
        .where(RawMacro.series_code == series_code, RawMacro.market == market, RawMacro.source == source)
        .order_by(RawMacro.obs_date.desc())
        .limit(1)
    )
    return session.scalar(stmt)


def insert_raw_price(session: Session, rows: list[dict]) -> int:
    session.flush()
    inserted = 0
    for row in rows:
        exists = session.execute(
            select(RawPrice.id).where(
                RawPrice.symbol == row['symbol'],
                RawPrice.market == row['market'],
                RawPrice.trade_date == row['trade_date'],
                RawPrice.source == row['source'],
            )
        ).first()
        if exists:
            continue
        session.add(RawPrice(**row))
        inserted += 1
    return inserted


def insert_raw_fundamental(session: Session, rows: list[dict]) -> int:
    session.flush()
    inserted = 0
    for row in rows:
        exists = session.execute(
            select(RawFundamental.id).where(
                RawFundamental.symbol == row['symbol'],
                RawFundamental.market == row['market'],
                RawFundamental.report_period == row['report_period'],
                RawFundamental.publish_date == row['publish_date'],
                RawFundamental.source == row['source'],
            )
        ).first()
        if exists:
            continue
        session.add(RawFundamental(**row))
        inserted += 1
    return inserted


def insert_raw_macro(session: Session, rows: list[dict]) -> int:
    session.flush()
    inserted = 0
    for row in rows:
        exists = session.execute(
            select(RawMacro.id).where(
                RawMacro.series_code == row['series_code'],
                RawMacro.market == row['market'],
                RawMacro.obs_date == row['obs_date'],
                RawMacro.source == row['source'],
            )
        ).first()
        if exists:
            continue
        session.add(RawMacro(**row))
        inserted += 1
    return inserted
