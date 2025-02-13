import docker
import pandas as pd
from typing import List, Tuple
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Scoring constants
BOTH_COOPERATE = (3, 3)
BOTH_DEFECT = (1, 1)
COOPERATE_DEFECT = (0, 5)
DEFECT_COOPERATE = (5, 0)

class Strategy:
    def __init__(self, image_name: str):
        self.image_name = image_name
        self.client = docker.from_env()
        self.container = None

    async def start(self):
        self.container = self.client.containers.run(
            self.image_name,
            detach=True,
            stdin_open=True,
            stdout=True
        )

    async def get_move(self, opponent_last_move: str = None) -> str:
        if opponent_last_move:
            self.container.exec_run(f"echo {opponent_last_move}", stdin=True)
        
        output = self.container.logs().decode().strip()
        if not output:
            print(f"Warning: No output returned from {self.image_name}, defaulting to 'C'")
            return 'C'
        print(f"{self.image_name} played: {output}")
        return output[-1]  # Get last character (C or D)

    async def cleanup(self):
        if self.container:
            self.container.stop()
            self.container.remove()

class Tournament:
    def __init__(self, strategies: List[str]):
        self.strategies = {name: Strategy(name) for name in strategies}
        self.results = pd.DataFrame(0, 
                                  index=strategies,
                                  columns=strategies)
        self.game_history = {}

    async def play_game(self, strategy1: Strategy, strategy2: Strategy, 
                       rounds: int = 200) -> Tuple[int, int]:
        moves1, moves2 = [], []
        score1, score2 = 0, 0

        await strategy1.start()
        await strategy2.start()

        for _ in range(rounds):
            move1 = await strategy1.get_move(moves2[-1] if moves2 else None)
            move2 = await strategy2.get_move(moves1[-1] if moves1 else None)

            moves1.append(move1)
            moves2.append(move2)

            # Calculate scores
            if move1 == 'C' and move2 == 'C':
                s1, s2 = BOTH_COOPERATE
            elif move1 == 'D' and move2 == 'D':
                s1, s2 = BOTH_DEFECT
            elif move1 == 'C' and move2 == 'D':
                s1, s2 = COOPERATE_DEFECT
            else:  # D, C
                s1, s2 = DEFECT_COOPERATE

            score1 += s1
            score2 += s2

        await strategy1.cleanup()
        await strategy2.cleanup()

        return score1, score2, moves1, moves2

    async def run_tournament(self, rounds_per_match: int = 200):
        for name1, strategy1 in self.strategies.items():
            for name2, strategy2 in self.strategies.items():
                if name1 != name2:
                    print(f"Running {name1} vs {name2}")
                    score1, score2, moves1, moves2 = await self.play_game(
                        strategy1, strategy2, rounds_per_match
                    )
                    
                    self.results.loc[name1, name2] = score1
                    self.results.loc[name2, name1] = score2
                    
                    # Store game history
                    game_id = f"{name1}_vs_{name2}"
                    self.game_history[game_id] = {
                        "moves1": moves1,
                        "moves2": moves2,
                        "score1": score1,
                        "score2": score2
                    }

# FastAPI server
app = FastAPI()

tournament = None

@app.post("/start_tournament")
async def start_tournament(strategy_images: List[str]):
    global tournament
    tournament = Tournament(strategy_images)
    await tournament.run_tournament()
    return {"status": "Tournament completed"}

@app.get("/tournament_results")
async def get_results():
    if tournament is None:
        return {"error": "No tournament has been run"}
    return {
        "results": tournament.results.to_dict(),
        "total_scores": tournament.results.sum().to_dict()
    }

@app.get("/game_history/{game_id}")
async def get_game_history(game_id: str):
    if tournament is None or game_id not in tournament.game_history:
        return {"error": "Game not found"}
    return tournament.game_history[game_id]

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
