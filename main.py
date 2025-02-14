from typing import List
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from lib import SessionLocal, TournamentRunner, Move, TournamentParticipant

# FastAPI server
app = FastAPI()

tournament = None

@app.post("/start_tournament")
async def start_tournament(strategy_images: List[str]):
    global tournament
    tournament = TournamentRunner(strategy_images)
    await tournament.run()
    return {"status": "Tournament completed"}

@app.get("/tournament_results")
async def get_results():
    if tournament is None:
        return {"error": "No tournament has been run"}
    # Fetch results from the database
    db: Session = SessionLocal()
    results = db.query(TournamentParticipant).all()
    return {
        "results": {f"{r.tournament_id}_{r.strategy_id}": r.total_score for r in results},
        "total_scores": {r.strategy_id: r.total_score for r in results}
    }

@app.get("/game_history/{game_id}")
async def get_game_history(game_id: int):
    if tournament is None:
        return {"error": "Game not found"}
    # Fetch game history from the database
    db: Session = SessionLocal()
    moves = db.query(Move).filter(Move.game_id == game_id).all()
    return {
        "moves1": [move.strategy1_move.value for move in moves],
        "moves2": [move.strategy2_move.value for move in moves]
    }

# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prisoner's Dilemma Tournament</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js"></script>
        <style>
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .results-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            .results-table td, .results-table th { border: 1px solid #ddd; padding: 8px; }
            .game-view { margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Prisoner's Dilemma Tournament</h1>
            
            <div id="tournament-controls">
                <h2>Start New Tournament</h2>
                <textarea id="strategy-list" placeholder="Enter Docker image names, one per line"></textarea>
                <button onclick="startTournament()">Start Tournament</button>
            </div>

            <div id="results-view">
                <h2>Tournament Results</h2>
                <div id="results-table"></div>
                <canvas id="scores-chart"></canvas>
            </div>

            <div class="game-view">
                <h2>Game Replay</h2>
                <select id="game-selector"></select>
                <div id="game-history"></div>
                <canvas id="moves-chart"></canvas>
            </div>
        </div>

        <script>
            async function startTournament() {
                const strategies = document.getElementById('strategy-list').value.split('\n');
                const response = await fetch('/start_tournament', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(strategies)
                });
                await updateResults();
            }

            async function updateResults() {
                const response = await fetch('/tournament_results');
                const data = await response.json();
                
                // Update results table
                const resultsTable = document.getElementById('results-table');
                // ... (implement table rendering)

                // Update scores chart
                const scoresChart = new Chart(
                    document.getElementById('scores-chart'),
                    {
                        type: 'bar',
                        data: {
                            labels: Object.keys(data.total_scores),
                            datasets: [{
                                label: 'Total Score',
                                data: Object.values(data.total_scores)
                            }]
                        }
                    }
                );
            }

            async function loadGameHistory(gameId) {
                const response = await fetch(`/game_history/${gameId}`);
                const data = await response.json();
                
                // Update moves chart
                const movesChart = new Chart(
                    document.getElementById('moves-chart'),
                    {
                        type: 'line',
                        data: {
                            labels: Array.from({length: data.moves1.length}, (_, i) => i + 1),
                            datasets: [
                                {
                                    label: 'Player 1',
                                    data: data.moves1.map(move => move === 'C' ? 1 : 0)
                                },
                                {
                                    label: 'Player 2',
                                    data: data.moves2.map(move => move === 'C' ? 1 : 0)
                                }
                            ]
                        }
                    }
                );
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
