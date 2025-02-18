from itertools import combinations_with_replacement
import os
from socket import SocketIO
import time
from typing import Mapping
import docker
from loguru import logger
from sqlalchemy import (
    Column,
    Table,
    UniqueConstraint,
    create_engine,
    Integer,
    String,
    ForeignKey,
    Enum,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import (
    sessionmaker,
    DeclarativeBase,
    relationship,
    mapped_column,
    Mapped,
)
import enum

DATABASE_URL = "postgresql://tournament_user:tournament_pass@localhost/tournament_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(autocommit=False, bind=engine)


class Base(DeclarativeBase):
    pass


class MoveType(enum.Enum):
    C = "C"
    D = "D"


class Side(enum.Enum):
    strategy1 = 1
    strategy2 = 2


# Association table for many-to-many relationship between Tournament and Strategy
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
    #  = mapped_column(Integer, nullable=False)
    rounds_count: Mapped[int]

    # Relationship with Strategy
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


Base.metadata.create_all(bind=engine)


class TournamentRunner:
    def __init__(self, strategy_ids: list[int], rounds_count: int):
        with Session.begin() as session:
            # Make sure strategies are attached to the session
            strategies = session.query(Strategy).filter(Strategy.id.in_(strategy_ids)).all()
            tournament = Tournament(rounds_count=rounds_count, strategies=strategies)
            session.add(tournament)
            session.flush()
            self.tournament_id: int = tournament.id

    async def run(self):
        with Session() as session:
            tournament = session.get(Tournament, self.tournament_id)
            assert tournament is not None
            rounds_count = tournament.rounds_count
            # Access the attached strategies
            tournament_strategies = tournament.strategies
        for round_number in range(rounds_count):
            turns_count = 200
            with Session.begin() as session:
                round_obj = Round(
                    tournament_id=tournament.id,
                    round_number=round_number,
                    turns_count=turns_count,
                )
                session.add(round_obj)
                session.flush()
                current_round_id = round_obj.id
            await self.run_round(current_round_id, tournament_strategies)

    async def run_round(self, round_id: int, strategies: list[Strategy]):
        match_runners: list[MatchRunner] = []
        # Use combinations to generate all pairs (with replacement if needed)
        for strategy_1, strategy_2 in combinations_with_replacement(strategies, 2):
            # Ensure you're passing the correct strategy IDs
            match_runner = MatchRunner(round_id, strategy_1.id, strategy_2.id)
            match_runners.append(match_runner)

        for match_runner in match_runners:
            await match_runner.run()

class MatchRunner:
    REWARD = {
        MoveType.C: {MoveType.C: 3, MoveType.D: 0},
        MoveType.D: {
            MoveType.C: 5,
            MoveType.D: 1,
        },
    }

    OTHER_SIDE = {Side.strategy1: Side.strategy2, Side.strategy2: Side.strategy1}

    def __init__(self, round_id: int, strategy_1_id: int, strategy_2_id: int):
        with Session.begin() as session:
            # Merge the round and strategies to attach them to the current session
            match = Match(
                round_id=round_id,
                strategy1_id = strategy_1_id,
                strategy2_id = strategy_2_id
            )
            session.add(match)
            session.flush()
            self.match_id = match.id

            strategy_1 = session.get(Strategy, strategy_1_id)
            assert strategy_1 is not None
            strategy_2 = session.get(Strategy, strategy_2_id)
            assert strategy_2 is not None
            self.strategy_runners = {
                Side.strategy1: StrategyRunner(
                    strategy_1.docker_image, f"{self.match_id}_1"
                ),
                Side.strategy2: StrategyRunner(
                    strategy_2.docker_image, f"{self.match_id}_2"
                ),
            }
        self.last_moves: Mapping[Side, MoveType | None] = {
            Side.strategy1: None,
            Side.strategy2: None,
        }

    async def run(self):
        with Session() as session:
            # Get number of rounds from rounds table from the round id
            match = session.get(Match, self.match_id)
            assert match is not None
            round = session.get(Round, match.round_id)
            assert round is not None
            turns_count = round.turns_count
        for turn_number in range(turns_count):
            await self.run_turn(turn_number)
        # self.status = "finished"
        await self.cleanup()
        # self.status = "cleaned_up"

    async def run_turn(self, turn_number: int):
        moves: dict[Side, MoveType] = {}
        for side, strategy_runner in self.strategy_runners.items():
            other_side = self.OTHER_SIDE[side]
            move = await strategy_runner.read_move(self.last_moves[other_side])
            if move is None:
                move = MoveType.C
                logger.warning(f"Invalid move by {side}, defaulting to {move}")
            moves[side] = move

        # Calculate scores
        with Session.begin() as session:
            for side, strategy_runner in self.strategy_runners.items():
                move = moves[side]
                other_move = moves[MatchRunner.OTHER_SIDE[side]]
                score = MatchRunner.REWARD[move][other_move]
                turn = Turn(
                    match_id=self.match_id,
                    turn_number=turn_number,
                    side=side,
                    move=move,
                    score=score,
                )
                session.add(turn)
        self.last_moves = moves

    async def cleanup(self):
        for strategy_runner in self.strategy_runners.values():
            await strategy_runner.cleanup()


class StrategyRunner:
    TIMEOUT_SEC = 0.1

    def __init__(self, image_name: str, container_name: str):
        self.image_name = image_name
        self.client = docker.from_env()
        self.container = self.client.containers.run(
            self.image_name,
            name=container_name,
            detach=True,
            stdin_open=True,
            stdout=True,
        )
        logger.debug(f"{self.container.name} | {self.image_name} | Started")
        self.stdin_socket: SocketIO = self.container.attach_socket(params={"stdin": 1, "stream": 1})  # type: ignore
        self.lines_read = 0

    async def read_move(
        self, opponent_previous_move: MoveType | None = None
    ) -> MoveType | None:
        if opponent_previous_move is not None:
            os.write(
                self.stdin_socket.fileno(), f"{opponent_previous_move.name}\n".encode()
            )
            logger.debug(
                f"{self.container.name} | {self.image_name} | Input: {opponent_previous_move.name}"
            )

        start_time = time.time()
        while time.time() - start_time <= self.TIMEOUT_SEC:
            output_lines = self.container.logs().decode().splitlines()
            lines_count = len(output_lines)
            if lines_count <= self.lines_read:
                # No new output
                continue
            if lines_count > self.lines_read + 1:
                logger.warning(
                    f"{self.container.name} | {self.image_name} | Multiple outputs in one round"
                )
            self.lines_read = lines_count
            output = output_lines[-1]
            try:
                move = MoveType(output)
                logger.debug(
                    f"{self.container.name} | {self.image_name} | Output: {output}"
                )
                return move
            except ValueError:
                logger.warning(
                    f"{self.container.name} | {self.image_name} | Invalid output: {output}"
                )
                return None
        logger.warning(
            f"{self.container.name} | {self.image_name} | Timed out after {self.TIMEOUT_SEC} seconds"
        )
        return None

    async def cleanup(self):
        self.container.stop(timeout=0)
        self.container.remove()
        logger.debug(f"{self.container.name} | {self.image_name} | Stopped and removed")
