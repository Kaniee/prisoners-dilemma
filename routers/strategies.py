from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.models import Strategy
from database import get_db

router = APIRouter(prefix="/strategies")
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def list_strategies(request: Request, db: Session = Depends(get_db)):
    strategies = db.query(Strategy).all()
    return templates.TemplateResponse(
        "strategies.html", {"request": request, "strategies": strategies}
    )


@router.post("/add")
async def add_strategy(
    name: str = Form(...), docker_image: str = Form(...), db: Session = Depends(get_db)
):
    strategy = Strategy(name=name, docker_image=docker_image)
    db.add(strategy)
    db.commit()
    return {"success": True}


@router.post("/{strategy_id}/rename")
async def rename_strategy(
    strategy_id: int, name: str = Form(...), db: Session = Depends(get_db)
):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    assert strategy is not None
    strategy.name = name
    db.commit()
    return {"success": True}


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    db.query(Strategy).filter(Strategy.id == strategy_id).delete()
    db.commit()
    return {"success": True}
