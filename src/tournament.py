from itertools import combinations_with_replacement
from sqlalchemy.orm import Session
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
            turns_count = 200
            round_obj = Round(
                tournament_id=tournament.id,
                round_number=round_number,
                turns_count=turns_count,
            )
            session.add(round_obj)
            session.commit()
            await self.run_round(round_obj.id, tournament_strategies, turns_count, session)

    async def run_round(self, round_id: int, strategies: list[Strategy], turns_count: int, session: Session):
        match_runners: list[MatchRunner] = []
        for strategy_1, strategy_2 in combinations_with_replacement(strategies, 2):
            match_runner = MatchRunner(round_id, strategy_1.id, strategy_2.id, session)
            match_runners.append(match_runner)

        for match_runner in match_runners:
            await match_runner.run(turns_count, session=session)
