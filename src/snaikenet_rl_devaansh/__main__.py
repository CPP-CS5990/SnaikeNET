import asyncio
import queue
import selectors
import sys
import threading
from pathlib import Path

import torch
from loguru import logger

from snaikenet_client.client.client import SnaikenetClient
from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.parse_args import parse_client_args
from snaikenet_client.types import ClientDirection

from snaikenet_rl_devaansh.agent import PPOAgentEventHandler

CHECKPOINT_PATH = Path("checkpoint/ppo_agent.ppo")
SAVE_EVERY = 10

def setup_logger(verbose: bool):
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)
    logger.add("logs/rl.agent.log", rotation = "1 MB", level = level)

def save_checkpoint(handler: PPOAgentEventHandler, update_count: int):
    CHECKPOINT_PATH.parent.mkdir(parents = True, exist_ok = True)
    torch.save(
        {
            "network": handler.network.state_dict(),
            "update_count": update_count,
        }, CHECKPOINT_PATH
    )
    logger.info(f"Checkpoint saved at update {update_count}")

def load_checkpoint(handler: PPOAgentEventHandler) -> int:
    if not CHECKPOINT_PATH.exists():
        return 0
    data = torch.load(CHECKPOINT_PATH)
    handler.network.load_state_dict(data["network"])
    logger.info(f"Checkpoint loaded at update {data['update_count']}")
    return data["update_count"]

async def run_client(
    handler: PPOAgentEventHandler,
    direction_queue: queue.Queue,
    server_host: str,
    server_tcp_port: int,
    client_uuid: str | None,
):
    client = SnaikenetClient(
        server_host = server_host,
        server_tcp_port = server_tcp_port,
        event_handler = handler,
    )
    await client.start(client_uuid)
    logger.info("RL agent connected to server")

    handler.send_direction = client.set_direction

    while True:
        await asyncio.sleep(0.01)

def start_network_thread(
        handler: PPOAgentEventHandler,
        direction_queue: queue.Queue,
        server_host: str,
        server_tcp_port: int,
        client_uuid: str | None,
):
    selector = selectors.SelectSelector()
    loop = asyncio.SelectorEventLoop(selector)
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        run_client(handler, direction_queue, server_host, server_tcp_port, client_uuid)
    )

def main():
    args = parse_client_args()
    setup_logger(verbose = args.verbose)

    handler = PPOAgentEventHandler()
    direction_queue: queue.Queue[ClientDirection] = queue.Queue()

    net_thread = threading.Thread(
        target = start_network_thread,
        args = (handler, direction_queue, args.host, args.port, args.reconnect_uuid),
        daemon = True,
    )
    net_thread.start()

    logger.info("RL agent running. Press Ctrl+C to stop.")
    try:
        net_thread.join()
    except KeyboardInterrupt:
        logger.info("Stopping RL agent...")
        if handler.network is not None:
            save_checkpoint(handler, update_count = 0)

if __name__ == "__main__":
    main()

