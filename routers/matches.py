from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.models import Match, Strategy, Turn
from database import get_db

router = APIRouter(prefix="/matches")
templates = Jinja2Templates(directory="templates")

@router.get("/{match_id}")
async def match_detail(
    request: Request,
    match_id: int,
    db: Session = Depends(get_db)
):
    match = db.get(Match, match_id)
    assert match is not None
    turns = db.query(Turn).filter(Turn.match_id == match_id).order_by(Turn.turn_number).all()
    strategy1 = db.get(Strategy, match.strategy1_id)
    strategy2 = db.get(Strategy, match.strategy2_id)
    
    return templates.TemplateResponse(
        "match_detail.html",
        {"request": request, "match": match, "turns": turns, "strategy1": strategy1, "strategy2": strategy2}
    )

