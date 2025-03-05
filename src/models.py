import enum
from sqlalchemy import (
    Column,
    Table,
    UniqueConstraint,
    Integer,
    String,
    ForeignKey,
    Enum,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship, mapped_column, Mapped

import database


class Base(DeclarativeBase):
    pass


class MoveType(enum.Enum):
    C = "C"
    D = "D"


class Side(enum.Enum):
    strategy1 = 1
    strategy2 = 2


# Association table for many-to-many relationship
tournament_strategies = Table(
    "tournament_strategies",
    Base.metadata,
    Column("tournament_id", Integer, ForeignKey("tournaments.id", ondelete="CASCADE")),
    Column("strategy_id", Integer, ForeignKey("strategies.id", ondelete="CASCADE")),
)


class Tournament(Base):
    __tablename__ = "tournaments"

    id = mapped_column(Integer, primary_key=True, index=True)
    start_time = mapped_column(TIMESTAMP, server_default=func.now())
    end_time = mapped_column(TIMESTAMP)
    status = mapped_column(String(20), nullable=False, default="in_progress")
    rounds_count: Mapped[int]
    strategies = relationship("Strategy", secondary=tournament_strategies)


class Strategy(Base):
    __tablename__ = "strategies"

    id = mapped_column(Integer, primary_key=True, index=True)
    name = mapped_column(String(255), nullable=False)
    docker_image = mapped_column(String(255), nullable=False, unique=True)
    created_at = mapped_column(TIMESTAMP, server_default=func.now())


class Round(Base):
    __tablename__ = "rounds"

    id = mapped_column(Integer, primary_key=True, index=True)
    tournament_id = mapped_column(
        Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False
    )
    round_number = mapped_column(Integer, nullable=False)
    turns_count = mapped_column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("tournament_id", "round_number"),)


class Match(Base):
    __tablename__ = "matches"

    id = mapped_column(Integer, primary_key=True, index=True)
    round_id = mapped_column(
        Integer, ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False
    )
    strategy1_id = mapped_column(Integer, ForeignKey("strategies.id"))
    strategy2_id = mapped_column(Integer, ForeignKey("strategies.id"))
    start_time = mapped_column(TIMESTAMP, server_default=func.now())
    end_time = mapped_column(TIMESTAMP)
    status = mapped_column(String(20), nullable=False, default="in_progress")

    __table_args__ = (UniqueConstraint("round_id", "strategy1_id", "strategy2_id"),)


class Turn(Base):
    __tablename__ = "turns"

    id = mapped_column(Integer, primary_key=True, index=True)
    match_id = mapped_column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    turn_number = mapped_column(Integer, nullable=False)
    side = mapped_column(Enum(Side), nullable=False)
    move = mapped_column(Enum(MoveType), nullable=False)
    score = mapped_column(Integer, nullable=False)
    created_at = mapped_column(TIMESTAMP, server_default=func.now())

    __table_args__ = (UniqueConstraint("match_id", "turn_number", "side"),)


Base.metadata.create_all(bind=database.engine)
