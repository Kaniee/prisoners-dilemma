from itertools import combinations_with_replacement
from sqlalchemy.orm import Session
import random
import asyncio
from loguru import logger
from .models import Tournament, Round, Strategy
from .match import MatchRunner


class TournamentRunner:
    def __init__(self, strategy_ids: list[int], rounds_count: int, session: Session):
        strategies = session.query(Strategy).filter(Strategy.id.in_(strategy_ids)).all()
        tournament = Tournament(rounds_count=rounds_count, strategies=strategies)
        session.add(tournament)
        session.commit()
        self.tournament_id = tournament.id

    async def run(self, session: Session):
        tournament = session.get(Tournament, self.tournament_id)
        assert tournament is not None
        rounds_count = tournament.rounds_count
        tournament_strategies = tournament.strategies

        for round_number in range(rounds_count):
            turns_count = round(random.gauss(200, 0))
            round_obj = Round(
                tournament_id=tournament.id,
                round_number=round_number,
                turns_count=turns_count,
            )
            session.add(round_obj)
            session.commit()
            await self.run_round(
                round_obj.id, tournament_strategies, turns_count, session
            )

    async def run_round(
        self,
        round_id: int,
        strategies: list[Strategy],
        turns_count: int,
        session: Session,
    ):
        match_pairs = combinations_with_replacement(strategies, 2)
        create_tasks = [
            asyncio.create_task(
                MatchRunner.create(round_id, strategy_1.id, strategy_2.id, session)
            )
            for strategy_1, strategy_2 in match_pairs
        ]
        match_runners = await asyncio.gather(*create_tasks)

        match_tasks: list[asyncio.Task[None]] = []
        try:
            # Run all matches in parallel
            match_tasks = [
                asyncio.create_task(runner.run(turns_count, session))
                for runner in match_runners
            ]
            await asyncio.gather(*match_tasks)
        except Exception as e:
            logger.error(f"Error running round {round_id}: {str(e)}")
            # Cancel any remaining tasks
            for task in match_tasks:
                if not task.done():
                    task.cancel()
            raise
        finally:
            for runner in match_runners:
                runner.cleanup()
