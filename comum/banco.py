from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def criar_fabrica_sessoes(banco_url: str) -> sessionmaker[Session]:
    engine = create_engine(
        banco_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def criar_dependencia_sessao(
    fabrica: sessionmaker[Session],
) -> Generator[Session, None, None]:
    sessao = fabrica()
    try:
        yield sessao
    finally:
        sessao.close()


def banco_esta_pronto(fabrica: sessionmaker[Session]) -> bool:
    try:
        with fabrica() as sessao:
            sessao.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
