-- Create enum for moves
CREATE TYPE move_type AS ENUM ('C', 'D');

-- Tournaments table
CREATE TABLE tournaments (
    id SERIAL PRIMARY KEY,
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP,
    rounds_per_match INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    configuration JSONB
);

-- Strategies table
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    docker_image VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(docker_image)
);

-- Tournament participants
CREATE TABLE tournament_participants (
    tournament_id INTEGER REFERENCES tournaments(id),
    strategy_id INTEGER REFERENCES strategies(id),
    total_score INTEGER DEFAULT 0,
    PRIMARY KEY (tournament_id, strategy_id)
);

-- Games table
CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id),
    strategy1_id INTEGER REFERENCES strategies(id),
    strategy2_id INTEGER REFERENCES strategies(id),
    strategy1_score INTEGER NOT NULL,
    strategy2_score INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    UNIQUE(tournament_id, strategy1_id, strategy2_id)
);

-- Moves table
CREATE TABLE moves (
    id SERIAL PRIMARY KEY,
    game_id INTEGER REFERENCES games(id),
    round_number INTEGER NOT NULL,
    strategy1_move move_type NOT NULL,
    strategy2_move move_type NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(game_id, round_number)
);

-- Indexes
CREATE INDEX idx_games_tournament ON games(tournament_id);
CREATE INDEX idx_moves_game ON moves(game_id);
CREATE INDEX idx_tournament_participants_tournament ON tournament_participants(tournament_id);

-- Views
CREATE VIEW tournament_results AS
SELECT 
    t.id as tournament_id,
    s.name as strategy_name,
    tp.total_score,
    COUNT(DISTINCT g.id) as games_played,
    COUNT(DISTINCT CASE WHEN g.strategy1_id = s.id AND g.strategy1_score > g.strategy2_score 
                        OR g.strategy2_id = s.id AND g.strategy2_score > g.strategy1_score 
                   THEN g.id END) as games_won
FROM tournaments t
JOIN tournament_participants tp ON t.id = tp.tournament_id
JOIN strategies s ON tp.strategy_id = s.id
LEFT JOIN games g ON t.id = g.tournament_id 
    AND (g.strategy1_id = s.id OR g.strategy2_id = s.id)
GROUP BY t.id, s.name, tp.total_score;

CREATE VIEW game_history AS
SELECT 
    g.id as game_id,
    t.id as tournament_id,
    s1.name as strategy1_name,
    s2.name as strategy2_name,
    g.strategy1_score,
    g.strategy2_score,
    m.round_number,
    m.strategy1_move,
    m.strategy2_move
FROM games g
JOIN tournaments t ON g.tournament_id = t.id
JOIN strategies s1 ON g.strategy1_id = s1.id
JOIN strategies s2 ON g.strategy2_id = s2.id
JOIN moves m ON g.id = m.game_id
ORDER BY g.id, m.round_number;

-- Insert example strategies
INSERT INTO strategies (name, docker_image) VALUES
    ('Tit for Tat', 'pd-tit-for-tat'),
    ('Always Defect', 'pd-always-defect'),
    ('Always Cooperate', 'pd-always-cooperate'),
    ('Grudger', 'pd-grudger'),
    ('Pavlov', 'pd-pavlov');
