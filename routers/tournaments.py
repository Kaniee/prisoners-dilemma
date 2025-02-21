from fastapi import APIRouter, Form, HTTPException, Request, Depends
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
        {"request": request, "tournaments": tournaments, "strategies": strategies}
    )

@router.post("/start")
async def start_tournament(
    request: Request,
    strategy_ids: list[int] = Form(..., alias="strategy_ids[]"),
    rounds_count: int = Form(...),
    db: Session = Depends(get_db)
):
    print("Received strategy_ids:", strategy_ids)
    tournament_runner = TournamentRunner(strategy_ids=strategy_ids, rounds_count=rounds_count, session=db)
    await tournament_runner.run(db)
    
    return RedirectResponse(url="/tournaments", status_code=303)

@router.get("/{tournament_id}")
async def tournament_detail(
    request: Request,
    tournament_id: int,
    round_number: int | None = None,
    session: Session = Depends(get_db)
):
    tournament = session.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    results = {}
    query = session.query(Match, Turn).join(Turn)
    if round_number is not None:
        query = query.filter(Match.round_id == round_number)
    
    round_count_current = (
        session.query(func.count(Round.id))
        .filter(Round.tournament_id == tournament_id)
        .scalar()
    )

    strategy1_expr = func.sum(case((Turn.side == Side.strategy1, Turn.score), else_=0)).label("strategy1_score")
    strategy2_expr = func.sum(case((Turn.side == Side.strategy2, Turn.score), else_=0)).label("strategy2_score")

    score_query = (
        session.query(Match.strategy1_id, Match.strategy2_id, Match.id, strategy1_expr, strategy2_expr)
        .join(Match, Turn.match_id == Match.id)
        .join(Round, Match.round_id == Round.id)
        .filter(Round.tournament_id == tournament_id)
    )

    if round_number is not None:
        score_query = score_query.filter(Round.round_number == round_number)

    score_query = score_query.group_by(Match.strategy1_id, Match.strategy2_id, Match.id)
    
    for strategy1_id, strategy2_id, match_id, strategy1_score, strategy2_score in score_query.all():
        key = (strategy1_id, strategy2_id)
        results[key] = {
            "strategy1_result": strategy1_score,
            "strategy2_result": strategy2_score,
            "match_id": match_id,
        }
    
    return templates.TemplateResponse(
        "tournament_detail.html",
        {
            "request": request,
            "tournament": tournament,
            "results": results,
            "round_count_current": round_count_current,
            "round_number": round_number
        }
    )
