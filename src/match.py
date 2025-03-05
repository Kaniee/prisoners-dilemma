import asyncio
from typing import Mapping, Self

from loguru import logger
from sqlalchemy.orm import Session

from .models import Match, MoveType, Side, Strategy, Turn
from .strategy import StrategyRunner


class MatchRunner:
    REWARD = {
        MoveType.C: {MoveType.C: 3, MoveType.D: 0},
        MoveType.D: {MoveType.C: 5, MoveType.D: 1},
    }

    OTHER_SIDE = {Side.strategy1: Side.strategy2, Side.strategy2: Side.strategy1}

    @classmethod
    async def create(
        cls, round_id: int, strategy_1_id: int, strategy_2_id: int, session: Session
    ) -> Self:
        # Create match record
        match = Match(
            round_id=round_id, strategy1_id=strategy_1_id, strategy2_id=strategy_2_id
        )
        session.add(match)
        session.commit()

        # Get strategies
        strategy_1 = session.get(Strategy, strategy_1_id)
        assert strategy_1 is not None
        strategy_2 = session.get(Strategy, strategy_2_id)
        assert strategy_2 is not None

        # Initialize runners in parallel
        init_tasks = {
            Side.strategy1: asyncio.create_task(
                StrategyRunner.create(strategy_1.docker_image, f"{match.id}_1")
            ),
            Side.strategy2: asyncio.create_task(
                StrategyRunner.create(strategy_2.docker_image, f"{match.id}_2")
            ),
        }

        strategy_runners: dict[Side, StrategyRunner] = {}
        try:
            # Wait for all initializations to complete
            await asyncio.gather(*init_tasks.values())

            # Collect results
            for side, task in init_tasks.items():
                strategy_runners[side] = await task
        except Exception as e:
            logger.error(
                f"Error initializing strategy runners for match {match.id}: {str(e)}"
            )
            for runner in strategy_runners.values():
                runner.cleanup()
            raise

        return cls(match.id, strategy_runners)

    def __init__(self, match_id: int, strategy_runners: dict[Side, StrategyRunner]):
        self.match_id = match_id
        self.strategy_runners = strategy_runners
        self.last_moves: Mapping[Side, MoveType | None] = {
            Side.strategy1: None,
            Side.strategy2: None,
        }

    async def run(self, turns_count: int, session: Session):
        for turn_number in range(turns_count):
            await self.run_turn(turn_number, session)

    async def run_turn(self, turn_number: int, session: Session):
        # Run both strategy moves in parallel
        move_tasks = {
            side: asyncio.create_task(self._get_strategy_move(side))
            for side in self.strategy_runners.keys()
        }

        moves: dict[Side, MoveType] = {}
        try:
            # Wait for both moves with timeout
            await asyncio.wait(move_tasks.values(), timeout=StrategyRunner.TIMEOUT_SEC)

            # Collect results
            for side, task in move_tasks.items():
                if task.done():
                    result = await task
                    moves[side] = result if result is not None else MoveType.C
                else:
                    moves[side] = MoveType.C
                    task.cancel()
                    logger.warning(f"Move timeout for {side} in match {self.match_id}")
        except Exception as e:
            logger.error(f"Error getting moves in match {self.match_id}: {str(e)}")
            # Default to cooperative moves on error
            moves = {side: MoveType.C for side in self.strategy_runners.keys()}

        # Record moves and scores
        for side in self.strategy_runners.keys():
            move = moves[side]
            other_move = moves[self.OTHER_SIDE[side]]
            score = self.REWARD[move][other_move]
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

    async def _get_strategy_move(self, side: Side) -> MoveType | None:
        runner = self.strategy_runners[side]
        other_side = self.OTHER_SIDE[side]
        return await runner.read_move(self.last_moves[other_side])

    def cleanup(self):
        for runner in self.strategy_runners.values():
            runner.cleanup()
