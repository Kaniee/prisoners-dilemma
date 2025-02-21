from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers import strategies, tournaments, matches

# from pydantic import BaseModel
# from datetime import datetime
# from game_engine import (
#     Session,
#     Strategy,
#     Tournament,
#     Round,
#     Match,
#     Turn,
#     TournamentRunner,
# )
# from sqlalchemy import case, func

app = FastAPI(title="Tournament")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(strategies.router)
app.include_router(tournaments.router)
app.include_router(matches.router)


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})


# class StrategyBase(BaseModel):
#     name: str
#     docker_image: str


# class StrategyCreate(StrategyBase):
#     pass


# class StrategyUpdate(BaseModel):
#     name: str


# class StrategyResponse(StrategyBase):
#     id: int
#     created_at: datetime

#     class Config:
#         from_attributes = True


# @app.get("/strategies", response_model=list[StrategyResponse])
# async def get_strategies():
#     with Session() as session:
#         strategies = session.query(Strategy).all()
#         return strategies


# @app.post("/strategies", response_model=StrategyResponse)
# async def create_strategy(strategy: StrategyCreate):
#     with Session.begin() as session:
#         db_strategy = Strategy(**strategy.model_dump())
#         session.add(db_strategy)
#         session.flush()
#         return db_strategy


# @app.put("/strategies/{strategy_id}", response_model=StrategyResponse)
# async def update_strategy(strategy_id: int, strategy: StrategyUpdate):
#     with Session.begin() as session:
#         db_strategy = session.get(Strategy, strategy_id)
#         if not db_strategy:
#             raise HTTPException(status_code=404, detail="Strategy not found")
#         db_strategy.name = strategy.name
#         return db_strategy


# @app.delete("/strategies/{strategy_id}")
# async def delete_strategy(strategy_id: int):
#     with Session.begin() as session:
#         db_strategy = session.get(Strategy, strategy_id)
#         if not db_strategy:
#             raise HTTPException(status_code=404, detail="Strategy not found")
#         session.delete(db_strategy)
#         return {"status": "success"}


# class TournamentCreate(BaseModel):
#     strategy_ids: list[int]
#     rounds_count: int


# class TournamentResponse(BaseModel):
#     id: int
#     start_time: datetime
#     end_time: datetime | None
#     status: str
#     rounds_count: int
#     strategy_count: int

#     class Config:
#         from_attributes = True


# @app.get("/tournaments", response_model=list[TournamentResponse])
# async def get_tournaments():
#     with Session() as session:
#         tournaments = session.query(Tournament).all()
#         return [
#             TournamentResponse(**tournament.__dict__, strategy_count=len(tournament.strategies))
#             for tournament in tournaments
#         ]


# @app.post("/tournaments", response_model=TournamentResponse)
# async def create_tournament(tournament: TournamentCreate):
#     runner = TournamentRunner(tournament.strategy_ids, tournament.rounds_count)
#     await runner.run()
#     with Session() as session:
#         tournament_id = runner.tournament_id
#         tournament_row = session.get(Tournament, tournament_id)
#         assert tournament_row is not None
#         response = TournamentResponse(
#             **tournament_row.__dict__,
#             strategy_count=len(tournament_row.strategies)
#         )
#         return response


# class RoundResults(BaseModel):
#     round_number: int | None
#     strategy1_name: str
#     strategy2_name: str
#     strategy1_score: int
#     strategy2_score: int


# class TournamentDetailsResponse(TournamentResponse):
#     rounds_count_current: int
#     strategy_results: dict[int, int]


# @app.get("/tournaments/{tournament_id}")
# async def get_tournament_details(tournament_id: int, round_number: int | None = None):
#     with Session() as session:
#         tournament = session.get(Tournament, tournament_id)
#         if not tournament:
#             raise HTTPException(status_code=404, detail="Tournament not found")

#         round_count_current = (
#             session.query(func.count(Round.id))
#             .filter(Round.tournament_id == tournament_id)
#             .scalar()
#         )

#         strategy_id_expr = case(
#             (Turn.side == "strategy1", Match.strategy1_id),
#             else_=Match.strategy2_id,
#         ).label("strategy_id")

#         total_score_expr = func.sum(Turn.score).label("total_score")

#         score_query = (
#             session.query(strategy_id_expr, total_score_expr)
#             .join(Match, Turn.match_id == Match.id)
#             .join(Round, Match.round_id == Round.id)
#             .filter(Round.tournament_id == tournament_id)
#         )

#         if round_number is not None:
#             score_query = score_query.filter(Round.round_number == round_number)

#         score_query = score_query.group_by(strategy_id_expr)
#         score_query = score_query.order_by(total_score_expr)

#         results = score_query.all()


#         result_dict: dict[int, int] = {}
#         for result in results:
#             result_dict[result.strategy_id] = result.total_score

#         response = TournamentDetailsResponse(
#             **tournament.__dict__,
#             strategy_count=len(tournament.strategies),
#             strategy_results=result_dict,
#             rounds_count_current=round_count_current
#         )

#         return response


# class MoveResponse(BaseModel):
#     side: str
#     move: str
#     score: int
#     accumulative_score: int
#     created_at: datetime


# class TurnResponse(BaseModel):
#     turn_number: int
#     moves: list[MoveResponse]

#     class Config:
#         from_attributes = True


# class MatchResponse(BaseModel):
#     id: int
#     round_id: int
#     strategy1: StrategyResponse
#     strategy2: StrategyResponse
#     start_time: datetime
#     end_time: datetime | None
#     status: str
#     turns: list[TurnResponse]


# @app.get("/matches/{match_id}", response_model=MatchResponse)
# async def get_match_details(match_id: int):
#     with Session() as session:
#         match = session.get(Match, match_id)
#         if not match:
#             raise HTTPException(status_code=404, detail="Match not found")

#         strategy_1 = session.get(Strategy, match.strategy1_id)
#         if not strategy_1:
#             raise HTTPException(status_code=500, detail="Strategy 1 not found")
#         strategy_2 = session.get(Strategy, match.strategy2_id)
#         if not strategy_2:
#             raise HTTPException(status_code=500, detail="Strategy 2 not found")

#         turns = (
#             session.query(Turn)
#             .filter(Turn.match_id == match_id)
#             .order_by(Turn.turn_number, Turn.side)
#             .all()
#         )

#         grouped_moves: list[list[MoveResponse]] = []
#         for turn in turns:
#             turn_number: int = turn.turn_number
#             try:
#                 moves = grouped_moves[turn_number]
#             except IndexError:
#                 moves: list[MoveResponse] = []
#                 grouped_moves.append(moves)

#             if turn.turn_number == 0:
#                 previous_score = 0
#             else:
#                 previous_turn = grouped_moves[turn_number - 1]
#                 previous_move = previous_turn[len(moves)]
#                 previous_score = previous_move.accumulative_score

#             new_accumulative_score = previous_score + turn.score
#             moves.append(
#                 MoveResponse(
#                     side=turn.side,
#                     move=turn.move,
#                     score=turn.score,
#                     created_at=turn.created_at,
#                     accumulative_score=new_accumulative_score,
#                 )
#             )

#         turns_response = [
#             TurnResponse(turn_number=turn_number, moves=moves)
#             for turn_number, moves in enumerate(grouped_moves)
#         ]
#         strategy_1_response = StrategyResponse(**strategy_1.__dict__)
#         strategy_2_response = StrategyResponse(**strategy_2.__dict__)
#         response = MatchResponse(
#             id=match.id,
#             round_id=match.round_id,
#             strategy1=strategy_1_response,
#             strategy2=strategy_2_response,
#             start_time=match.start_time,
#             end_time=match.end_time,
#             status=match.status,
#             turns=turns_response,
#         )

#         return response
