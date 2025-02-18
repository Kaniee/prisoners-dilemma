from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.models import Tournament, Match, Turn
from database import get_db

router = APIRouter(prefix="/tournaments")
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def list_tournaments(request: Request, db: Session = Depends(get_db)):
    tournaments = db.query(Tournament).all()
    return templates.TemplateResponse(
        "tournaments.html",
        {"request": request, "tournaments": tournaments}
    )

@router.get("/{tournament_id}")
async def tournament_detail(
    request: Request,
    tournament_id: int,
    round_number: int | None = None,
    db: Session = Depends(get_db)
):
    tournament = db.get(Tournament, tournament_id)
    
    # Get results matrix
    results = {}
    query = db.query(Match, Turn).join(Turn)
    if round_number is not None:
        query = query.filter(Match.round_id == round_number)
    
    matches = query.all()
    
    for match, turn in matches:
        key = (match.strategy1_id, match.strategy2_id)
        if key not in results:
            results[key] = {"total_score": 0, "matches": 0}
        results[key]["total_score"] += turn.score
        results[key]["matches"] += 1
    
    return templates.TemplateResponse(
        "tournament_detail.html",
        {
            "request": request,
            "tournament": tournament,
            "results": results,
            "round_number": round_number
        }
    )

