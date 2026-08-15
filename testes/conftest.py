from collections.abc import Callable, Iterator
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def criar_sessoes() -> Iterator[Callable[[Any], sessionmaker[Session]]]:
    engines = []

    def criar(base: object) -> sessionmaker[Session]:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        base.metadata.create_all(engine)
        engines.append(engine)
        return sessionmaker(bind=engine, expire_on_commit=False)

    yield criar
    for engine in engines:
        engine.dispose()
