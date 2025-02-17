from typing import AsyncGenerator, Generator, List
import pytest
from unittest.mock import Mock, patch

import pytest_asyncio
from lib import (
    TournamentRunner, StrategyRunner, Tournament, Match,
)

@pytest.fixture
def mock_docker() -> Generator[Mock, None, None]:
    with patch('docker.from_env') as mock_docker:
        container_mock: Mock = Mock()
        container_mock.logs.return_value = b'C\n'
        container_mock.exec_run = Mock()
        mock_docker.return_value.containers.run.return_value = container_mock
        yield mock_docker

@pytest.fixture
def mock_db_session() -> Generator[Mock, None, None]:
    with patch('lib.SessionLocal') as mock_session:
        session: Mock = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.refresh = Mock()
        mock_session.return_value = session
        yield session

@pytest_asyncio.fixture
async def strategy_runner() -> AsyncGenerator[StrategyRunner, None]:
    runner = StrategyRunner("test-strategy")
    yield runner
    await runner.cleanup()

@pytest.mark.asyncio
async def test_strategy_runner_initialization(strategy_runner: StrategyRunner) -> None:
    assert strategy_runner.image_name == "test-strategy"
    assert strategy_runner.container is None

@pytest.mark.asyncio
async def test_strategy_runner_start(mock_docker: Mock, strategy_runner: StrategyRunner) -> None:
    await strategy_runner.start()
    mock_docker.return_value.containers.run.assert_called_once_with(
        "test-strategy",
        detach=True,
        stdin_open=True,
        stdout=True
    )

@pytest.mark.asyncio
async def test_strategy_runner_get_move(mock_docker: Mock, strategy_runner: StrategyRunner) -> None:
    await strategy_runner.start()
    move: str = await strategy_runner.read_move("D")
    assert move == "C"
    mock_docker.return_value.containers.run.return_value.exec_run.assert_called_once_with(
        "echo D",
        stdin=True
    )

@pytest.mark.asyncio
async def test_tournament_manager_initialization(mock_db_session: Mock) -> None:
    strategies: List[str] = ["strategy1", "strategy2"]
    manager: TournamentRunner = TournamentRunner(strategies)
    assert len(manager.strategies) == 2
    assert isinstance(manager.strategies["strategy1"], StrategyRunner)
    assert isinstance(manager.strategies["strategy2"], StrategyRunner)

@pytest.mark.asyncio
async def test_play_game(mock_docker: Mock, mock_db_session: Mock) -> None:
    manager: TournamentRunner = TournamentRunner(["strategy1", "strategy2"])
    strategy1: StrategyRunner = manager.strategies["strategy1"]
    strategy2: StrategyRunner = manager.strategies["strategy2"]

    # Mock the moves to test scoring
    mock_docker.return_value.containers.run.return_value.logs.side_effect = [
        b'C\n',  # strategy1 first move
        b'C\n',  # strategy2 first move
        b'D\n',  # strategy1 second move
        b'C\n',  # strategy2 second move
    ]

    score1: int
    score2: int
    moves1: List[str]
    moves2: List[str]
    score1, score2, moves1, moves2 = await manager.play_game(strategy1, strategy2, rounds=2)

    # First round: Both cooperate (3,3)
    # Second round: Defect vs Cooperate (5,0)
    assert score1 == 8  # 3 + 5
    assert score2 == 3  # 3 + 0
    assert moves1 == ['C', 'D']
    assert moves2 == ['C', 'C']

@pytest.mark.asyncio
async def test_run_tournament(mock_docker: Mock, mock_db_session: Mock) -> None:
    manager: TournamentRunner = TournamentRunner(["strategy1", "strategy2"])
    
    # Mock database operations
    mock_db_session.refresh = Mock(side_effect=[
        Tournament(id=1, rounds_per_match=200),
        Match(id=1, tournament_id=1, strategy1_id=1, strategy2_id=2)
    ])

    await manager.run(rounds_per_match=2)

    # Verify tournament creation
    assert mock_db_session.add.call_count > 0
    assert mock_db_session.commit.call_count > 0

@pytest.mark.asyncio
async def test_scoring_rules() -> None:
    # Test all possible move combinations
    assert BOTH_COOPERATE == (3, 3)
    assert BOTH_DEFECT == (1, 1)
    assert COOPERATE_DEFECT == (0, 5)
    assert DEFECT_COOPERATE == (5, 0)

@pytest.mark.asyncio
async def test_cleanup(mock_docker: Mock, strategy_runner: StrategyRunner) -> None:
    await strategy_runner.start()
    await strategy_runner.cleanup()
    
    container_mock: Mock = mock_docker.return_value.containers.run.return_value
    container_mock.stop.assert_called_once()
    container_mock.remove.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling(mock_docker: Mock, strategy_runner: StrategyRunner) -> None:
    # Test behavior when container returns no output
    mock_docker.return_value.containers.run.return_value.logs.return_value = b''
    await strategy_runner.start()
    move: str = await strategy_runner.read_move()
    assert move == 'C'  # Should default to cooperation

@pytest.mark.asyncio
async def test_invalid_move_handling(mock_docker: Mock, strategy_runner: StrategyRunner) -> None:
    # Test behavior with invalid move
    mock_docker.return_value.containers.run.return_value.logs.return_value = b'X\n'
    await strategy_runner.start()
    move: str = await strategy_runner.read_move()
    assert move == 'X'  # Raw output is returned, validation should happen in game logic


