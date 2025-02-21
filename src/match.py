from typing import Mapping
from loguru import logger
from sqlalchemy.orm import Session
from .models import Match, Turn, Side, MoveType, Strategy
from .strategy import StrategyRunner

class MatchRunner:
    REWARD = {
        MoveType.C: {MoveType.C: 3, MoveType.D: 0},
        MoveType.D: {MoveType.C: 5, MoveType.D: 1},
    }

    OTHER_SIDE = {Side.strategy1: Side.strategy2, Side.strategy2: Side.strategy1}

    def __init__(self, round_id: int, strategy_1_id: int, strategy_2_id: int, session: Session):
        match = Match(
            round_id=round_id,
            strategy1_id=strategy_1_id,
            strategy2_id=strategy_2_id
        )
        session.add(match)
        session.commit()
        self.match_id = match.id

        strategy_1 = session.get(Strategy, strategy_1_id)
        assert strategy_1 is not None
        strategy_2 = session.get(Strategy, strategy_2_id)
        assert strategy_2 is not None
        
        self.strategy_runners = {
            Side.strategy1: StrategyRunner(strategy_1.docker_image, f"{self.match_id}_1"),
            Side.strategy2: StrategyRunner(strategy_2.docker_image, f"{self.match_id}_2"),
        }
        self.last_moves: Mapping[Side, MoveType | None] = {
            Side.strategy1: None,
            Side.strategy2: None,
        }

    async def run(self, turns_count: int, session: Session):
        for turn_number in range(turns_count):
            await self.run_turn(turn_number, session)
        await self.cleanup()

    async def run_turn(self, turn_number: int, session: Session):
        moves: dict[Side, MoveType] = {}
        for side, strategy_runner in self.strategy_runners.items():
            other_side = self.OTHER_SIDE[side]
            move = await strategy_runner.read_move(self.last_moves[other_side])
            if move is None:
                move = MoveType.C
                logger.warning(f"Invalid move by {side}, defaulting to {move}")
            moves[side] = move

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
        session.commit()
        self.last_moves = moves

    async def cleanup(self):
        for strategy_runner in self.strategy_runners.values():
            await strategy_runner.cleanup()
