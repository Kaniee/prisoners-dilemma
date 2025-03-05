from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from src.models import Match, Side, Strategy, Turn

router = APIRouter(prefix="/matches")
templates = Jinja2Templates(directory="templates")


@router.get("/{match_id}")
async def match_detail(request: Request, match_id: int, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    turns1 = (
        db.query(Turn)
        .filter(Turn.match_id == match_id)
        .filter(Turn.side == Side.strategy1)
        .order_by(Turn.turn_number)
        .all()
    )
    turns2 = (
        db.query(Turn)
        .filter(Turn.match_id == match_id)
        .filter(Turn.side == Side.strategy2)
        .order_by(Turn.turn_number)
        .all()
    )
    strategy1 = db.get(Strategy, match.strategy1_id)
    strategy2 = db.get(Strategy, match.strategy2_id)

    turns = list(zip(turns1, turns2, strict=True))
    for idx, (turn1, turn2) in enumerate(turns):
        assert turn1.turn_number == turn2.turn_number == idx

    return templates.TemplateResponse(
        "match_detail.html",
        {
            "request": request,
            "match": match,
            "turns": turns,
            "strategy1": strategy1,
            "strategy2": strategy2,
        },
    )
