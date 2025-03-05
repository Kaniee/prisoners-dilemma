from operator import itemgetter
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import case, func
from sqlalchemy.orm import Session
from src.models import Round, Side, Strategy, Tournament, Match, Turn
from database import get_db
from src.tournament import TournamentRunner

router = APIRouter(prefix="/tournaments")
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def list_tournaments(request: Request, db: Session = Depends(get_db)):
    tournaments = db.query(Tournament).all()
    strategies = db.query(Strategy).all()
    return templates.TemplateResponse(
        "tournaments.html",
        {"request": request, "tournaments": tournaments, "strategies": strategies},
    )


@router.post("/start")
async def start_tournament(
    request: Request,
    background_tasks: BackgroundTasks,
    strategy_ids: list[int] = Form(..., alias="strategy_ids[]"),
    rounds_count: int = Form(...),
    db: Session = Depends(get_db),
):
    print("Received strategy_ids:", strategy_ids)
    tournament_runner = TournamentRunner(
        strategy_ids=strategy_ids, rounds_count=rounds_count, session=db
    )
    # Add the tournament execution to background tasks
    background_tasks.add_task(tournament_runner.run, db)

    return RedirectResponse(
        url=f"/tournaments/{tournament_runner.tournament_id}", status_code=303
    )


@router.get("/{tournament_id}")
async def tournament_detail(
    request: Request,
    tournament_id: int,
    round_number: int | None = None,
    session: Session = Depends(get_db),
):
    tournament = session.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    query = session.query(Match, Turn).join(Turn)
    if round_number is not None:
        query = query.filter(Match.round_id == round_number)

    round_count_current = (
        session.query(func.count(Round.id))
        .filter(Round.tournament_id == tournament_id)
        .scalar()
    )

    strategy1_expr = func.sum(
        case((Turn.side == Side.strategy1, Turn.score), else_=0)
    ).label("strategy1_score")
    strategy2_expr = func.sum(
        case((Turn.side == Side.strategy2, Turn.score), else_=0)
    ).label("strategy2_score")

    score_query = (
        session.query(
            Match.strategy1_id,
            Match.strategy2_id,
            Match.id,
            strategy1_expr,
            strategy2_expr,
        )
        .join(Match, Turn.match_id == Match.id)
        .join(Round, Match.round_id == Round.id)
        .filter(Round.tournament_id == tournament_id)
    )

    if round_number is not None:
        score_query = score_query.filter(Round.round_number == round_number)

    score_query = score_query.group_by(Match.strategy1_id, Match.strategy2_id, Match.id)

    results: dict[tuple[int, int], dict[str, int]] = {}
    strategy_lookup = {strategy.id: strategy for strategy in tournament.strategies}
    strategy_scores: dict[int, int] = dict.fromkeys(strategy_lookup.keys(), 0)
    for (
        strategy1_id,
        strategy2_id,
        match_id,
        strategy1_score,
        strategy2_score,
    ) in score_query.all():
        key = (strategy1_id, strategy2_id)
        strategy_scores[strategy1_id] += strategy1_score
        strategy_scores[strategy2_id] += strategy2_score
        if key not in results:
            results[key] = {
                "strategy1_result": strategy1_score,
                "strategy2_result": strategy2_score,
                "match_id": match_id,
            }
        else:
            results_key = results[key]
            results_key["strategy1_result"] += strategy1_score
            results_key["strategy2_result"] += strategy1_score
            results_key["match_id"] = -1

    strategy_scores = {
        id_: score
        for id_, score in sorted(
            strategy_scores.items(), key=itemgetter(1), reverse=True
        )
    }

    return templates.TemplateResponse(
        "tournament_detail.html",
        {
            "request": request,
            "tournament": tournament,
            "results": results,
            "round_count_current": round_count_current,
            "round_number": round_number,
            "strategy_scores": strategy_scores,
            "strategy_lookup": strategy_lookup,
        },
    )
