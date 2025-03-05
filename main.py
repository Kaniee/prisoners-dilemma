from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers import strategies, tournaments, matches

app = FastAPI(title="Tournament")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(strategies.router)
app.include_router(tournaments.router)
app.include_router(matches.router)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})
