import asyncio
import os
import random
import time
from socket import SocketIO
from typing import Self
import docker
import docker.models
import docker.models.configs
import docker.models.containers
from loguru import logger
from .models import MoveType


MISCOMMUNICATION_PROBABILITY = 0.0

class StrategyRunner:
    TIMEOUT_SEC = 0.1

    @classmethod
    async def create(cls, image_name: str, container_name: str) -> Self:
        client = docker.from_env()
        container = await asyncio.to_thread(client.images.pull,
            image_name",
        )
        container = await asyncio.to_thread(client.containers.run,
            image_name,
            name=container_name,
            detach=True,
            stdin_open=True,
            stdout=True,
        )
        logger.debug(f"{container.name} | {image_name} | Started")

        stdin_socket: SocketIO = container.attach_socket(params={"stdin": 1, "stream": 1})  # type: ignore

        return cls(image_name, container, stdin_socket)  # type: ignore

    def __init__(
        self,
        image_name: str,
        container: docker.models.containers.Container,
        stdin_socket: SocketIO,
    ):
        self.image_name = image_name
        self.container = container
        self.stdin_socket = stdin_socket
        self.lines_read = 0

    async def read_move(
        self, opponent_previous_move: MoveType | None = None
    ) -> MoveType | None:
        if opponent_previous_move is not None:
            move_to_print = opponent_previous_move.name

            if move_to_print == MoveType.C.value and random.random() < MISCOMMUNICATION_PROBABILITY:
                move_to_print = MoveType.D.value
            os.write(
                self.stdin_socket.fileno(), f"{move_to_print}\n".encode()
            )
            logger.debug(
                f"{self.container.name} | {self.image_name} | Input: {move_to_print} ({opponent_previous_move.name})"
            )

        start_time = time.time()
        while time.time() - start_time <= self.TIMEOUT_SEC:
            output_lines = self.container.logs().decode().splitlines()
            lines_count = len(output_lines)
            if lines_count <= self.lines_read:
                continue
            if lines_count > self.lines_read + 1:
                logger.warning(
                    f"{self.container.name} | {self.image_name} | Multiple outputs in one round"
                )
            self.lines_read = lines_count
            output = output_lines[-1]
            try:
                move = MoveType(output)
                logger.debug(
                    f"{self.container.name} | {self.image_name} | Output: {output}"
                )
                return move
            except ValueError:
                logger.warning(
                    f"{self.container.name} | {self.image_name} | Invalid output: {output}"
                )
                return None
        logger.warning(
            f"{self.container.name} | {self.image_name} | Timed out after {self.TIMEOUT_SEC} seconds"
        )
        return None

    def cleanup(self):
        self.container.remove(force=True)
        logger.debug(f"{self.container.name} | {self.image_name} | Removed forcefully")
