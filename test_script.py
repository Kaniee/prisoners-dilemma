from sqlalchemy.orm import Session
from game_engine import Session, Strategy, Tournament, Match, Turn, MoveType

def insert_test_data():
    db: Session = Session()

    # Create strategies
strategy1 = Strategy(name="Tit for Tat", docker_image="pd-tit-for-tat")
strategy2 = Strategy(name="Always Defect", docker_image="pd-always-defect")
db.add(strategy1)
db.add(strategy2)
db.commit()
db.refresh(strategy1)
db.refresh(strategy2)

# Create tournament
tournament = Tournament(rounds_per_match=200)
db.add(tournament)
db.commit()
db.refresh(tournament)

# Create game
game = Match(
    tournament_id=tournament.id,
    strategy1_id=strategy1.id,
    strategy2_id=strategy2.id,
    strategy1_score=300,
    strategy2_score=200
)
db.add(game)
db.commit()
db.refresh(game)

# Create moves
moves = [
    Turn(game_id=game.id, round_number=1, strategy1_move=MoveType.C, strategy2_move=MoveType.D),
    Turn(game_id=game.id, round_number=2, strategy1_move=MoveType.D, strategy2_move=MoveType.D),
    Turn(game_id=game.id, round_number=3, strategy1_move=MoveType.C, strategy2_move=MoveType.C),
    # Add more moves as needed
]
db.add_all(moves)
db.commit()

    print("Test data inserted successfully")

if __name__ == "__main__":
    insert_test_data()
