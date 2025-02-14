from itertools import combinations_with_replacement
import os
from socket import SocketIO
import time
import docker
from loguru import logger
from sqlalchemy import Table, create_engine, Column, Integer, String, ForeignKey, Enum, TIMESTAMP, JSON, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, joinedload
import enum

DATABASE_URL = "postgresql://tournament_user:tournament_pass@localhost/tournament_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class MoveType(enum.Enum):
    C = "C"
    D = "D"

# Association table for many-to-many relationship between Tournament and Strategy
tournament_strategies = Table(
    "tournament_strategies",
    Base.metadata,
    Column("tournament_id", Integer, ForeignKey("tournaments.id", ondelete="CASCADE")),
    Column("strategy_id", Integer, ForeignKey("strategies.id", ondelete="CASCADE")),
)

class Tournament(Base):
    __tablename__ = "tournaments"
    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(TIMESTAMP, server_default=func.now())
    end_time = Column(TIMESTAMP)
    rounds_per_match = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default='in_progress')

    # Add relationship to strategies
    strategies = relationship("Strategy", secondary=tournament_strategies)

class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    docker_image = Column(String(255), nullable=False, unique=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"
    tournament_id = Column(Integer, ForeignKey('tournaments.id'), primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), primary_key=True)
    total_score = Column(Integer, default=0)

class Game(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'))
    strategy1_id = Column(Integer, ForeignKey('strategies.id'))
    strategy2_id = Column(Integer, ForeignKey('strategies.id'))
    strategy1_score = Column(Integer, nullable=False)
    strategy2_score = Column(Integer, nullable=False)
    start_time = Column(TIMESTAMP, server_default=func.now())
    end_time = Column(TIMESTAMP)
    status = Column(String(20), nullable=False, default='in_progress')

    # Relationships
    strategy1 = relationship("Strategy", foreign_keys=[strategy1_id])
    strategy2 = relationship("Strategy", foreign_keys=[strategy2_id])

    def __init__(self, tournament: Tournament, strategy1: Strategy, strategy2: Strategy):
        self.tournament = tournament
        self.strategy1 = strategy1
        self.strategy2 = strategy2
        self.strategy1_score = 0
        self.strategy2_score = 0
        self.status = "created"


class Move(Base):
    __tablename__ = "moves"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey('games.id'))
    round_number = Column(Integer, nullable=False)
    strategy1_move = Column(Enum(MoveType), nullable=False)
    strategy2_move = Column(Enum(MoveType), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

Base.metadata.create_all(bind=engine)


class TournamentRunner:
    def __init__(self, strategies: list[Strategy], rounds_per_match: int = 200):
        with SessionLocal() as db:
            tournament = Tournament(rounds_per_match=rounds_per_match)
            tournament.strategies = strategies
            db.add(tournament)
            db.commit()
            self.tournament_id = tournament.id

    async def run(self):
        with SessionLocal() as db:
            tournament: Tournament = db.query(Tournament).options(
                joinedload(Tournament.strategies)
            ).get(self.tournament_id) # type: ignore
            for strategy1, strategy2 in combinations_with_replacement(tournament.strategies, 2):
                match_runner = MatchRunner(tournament, strategy1, strategy2)
                await match_runner.run()

class MatchRunner:
    REWARD = {
        (MoveType.C, MoveType.C): (3, 3),
        (MoveType.D, MoveType.D): (1, 1),
        (MoveType.C, MoveType.D): (0, 5),
        (MoveType.D, MoveType.C): (5, 0)
    }

    def __init__(self, tournament: Tournament, strategy1: Strategy, strategy2: Strategy):
        self.tournament = tournament
        with SessionLocal() as db:
            self.game = Game(tournament, db.merge(strategy1), db.merge(strategy2))
            db.add(self.game)
            db.commit()
            db.refresh(self.game)
        self.strategy_runner1 = StrategyRunner(strategy1.docker_image, f"{self.game.id}_1")
        self.strategy_runner2 = StrategyRunner(strategy2.docker_image, f"{self.game.id}_2")
        self.moves: list[Move] = []
        self.status = "ready"
        

    async def run(self):
        for _ in range(self.tournament.rounds_per_match):
            await self.run_round()
        self.status = "finished"
        await self.cleanup()
        self.status = "cleaned_up"

    async def run_round(self):
        if self.moves:
            last_move1 = MoveType(self.moves[-1].strategy1_move)
            last_move2 = MoveType(self.moves[-1].strategy2_move)
        else:
            last_move1 = None
            last_move2 = None
            self.status = "running"

        move_type1 = await self.strategy_runner1.read_move(last_move2)
        move_type2 = await self.strategy_runner2.read_move(last_move1)

        if move_type1 is None:
            move_type1 = MoveType.C
            logger.warning(f"Invalid move by strategy 1, defaulting to {move_type1}")
        if move_type2 is None:
            move_type2 = MoveType.C
            logger.warning(f"Invalid move by strategy 2, defaulting to {move_type2}")

        move = Move(
            game_id=self.game.id,
            round_number=len(self.moves),
            strategy1_move=move_type1,
            strategy2_move=move_type2
        )
        self.moves.append(move)
        
        # Calculate scores
        reward1, reward2 = self.REWARD[(move_type1, move_type2)]
        self.game.strategy1_score += reward1
        self.game.strategy2_score += reward2

    async def cleanup(self):
        await self.strategy_runner1.cleanup()
        await self.strategy_runner2.cleanup()
    
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
        self.stdin_socket: SocketIO = self.container.attach_socket(params={'stdin': 1, 'stream': 1}) # type: ignore
        self.lines_read = 0

    async def read_move(self, opponent_previous_move: MoveType | None = None) -> MoveType | None:
        if opponent_previous_move is not None:
            os.write(self.stdin_socket.fileno(), f"{opponent_previous_move.name}\n".encode())
            logger.debug(f"{self.container.name} | {self.image_name} | Input: {opponent_previous_move.name}")

        start_time = time.time()
        while time.time() - start_time <= self.TIMEOUT_SEC:
            output_lines = self.container.logs().decode().splitlines()
            lines_count = len(output_lines)
            if lines_count <= self.lines_read:
                # No new output
                continue
            if lines_count > self.lines_read + 1:
                logger.warning(f"{self.container.name} | {self.image_name} | Multiple outputs in one round")
            self.lines_read = lines_count
            output = output_lines[-1]
            try:
                move = MoveType(output)
                logger.debug(f"{self.container.name} | {self.image_name} | Output: {output}")
                return move
            except ValueError:
                logger.warning(f"{self.container.name} | {self.image_name} | Invalid output: {output}")
                return None
        logger.warning(f"{self.container.name} | {self.image_name} | Timed out after {self.TIMEOUT_SEC} seconds")
        return None

    async def cleanup(self):
        self.container.stop(timeout=0)
        self.container.remove()
        logger.debug(f"{self.container.name} | {self.image_name} | Stopped and removed")
