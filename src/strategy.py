import os
import time
from socket import SocketIO
import docker
from loguru import logger
from .models import MoveType

class StrategyRunner:
    TIMEOUT_SEC = 0.1

    def __init__(self, image_name: str, container_name: str):
        self.image_name = image_name
        self.client = docker.from_env()
        self.container = self.client.containers.run(
            self.image_name,
            name=container_name,
            detach=True,
            stdin_open=True,
            stdout=True,
        )
        logger.debug(f"{self.container.name} | {self.image_name} | Started")
        self.stdin_socket: SocketIO = self.container.attach_socket(params={"stdin": 1, "stream": 1})  # type: ignore
        self.lines_read = 0

    async def read_move(self, opponent_previous_move: MoveType | None = None) -> MoveType | None:
        if opponent_previous_move is not None:
            os.write(self.stdin_socket.fileno(), f"{opponent_previous_move.name}\n".encode())
            logger.debug(f"{self.container.name} | {self.image_name} | Input: {opponent_previous_move.name}")

        start_time = time.time()
        while time.time() - start_time <= self.TIMEOUT_SEC:
            output_lines = self.container.logs().decode().splitlines()
            lines_count = len(output_lines)
            if lines_count <= self.lines_read:
                continue
            if lines_count > self.lines_read + 1:
                logger.warning(f"{self.container.name} | {self.image_name} | Multiple outputs in one round")
            self.lines_read = lines_count
            output = output_lines[-1]
            try:
                move = MoveType(output)
                logger.debug(f"{self.container.name} | {self.image_name} | Output: {output}")
                return move
            except ValueError:
                logger.warning(f"{self.container.name} | {self.image_name} | Invalid output: {output}")
                return None
        logger.warning(f"{self.container.name} | {self.image_name} | Timed out after {self.TIMEOUT_SEC} seconds")
        return None

    async def cleanup(self):
        self.container.stop(timeout=0)
        self.container.remove()
        logger.debug(f"{self.container.name} | {self.image_name} | Stopped and removed")
