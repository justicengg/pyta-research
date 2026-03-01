from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings
from src.db.models import DerivedFactor, RawFundamental, RawMacro, RawPrice

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
    inserted = 0
    for row in rows:
        try:
            with session.begin_nested():
                session.add(RawPrice(**row))
            inserted += 1
        except IntegrityError:
            pass
    return inserted


def insert_raw_fundamental(session: Session, rows: list[dict]) -> int:
    inserted = 0
    for row in rows:
        try:
            with session.begin_nested():
                session.add(RawFundamental(**row))
            inserted += 1
        except IntegrityError:
            pass
    return inserted


def insert_raw_macro(session: Session, rows: list[dict]) -> int:
    inserted = 0
    for row in rows:
        try:
            with session.begin_nested():
                session.add(RawMacro(**row))
            inserted += 1
        except IntegrityError:
            pass
    return inserted


def get_latest_factor_date(session: Session, symbol: str, market: str) -> date | None:
    stmt = (
        select(DerivedFactor.asof_date)
        .where(DerivedFactor.symbol == symbol, DerivedFactor.market == market)
        .order_by(DerivedFactor.asof_date.desc())
        .limit(1)
    )
    return session.scalar(stmt)


def insert_derived_factors(session: Session, rows: list[dict]) -> int:
    inserted = 0
    for row in rows:
        try:
            with session.begin_nested():
                session.add(DerivedFactor(**row))
            inserted += 1
        except IntegrityError:
            pass
    return inserted
