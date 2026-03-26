from snaikenet_server.server.server import SnaikenetServer
import asyncio
from loguru import logger


async def main():
    server = SnaikenetServer()
    await server.start()

    asyncio.create_task(log_clients_periodically(server))
    asyncio.create_task(simulate_broadcast(server))
    await server.server_forever()

async def simulate_broadcast(server: SnaikenetServer):
    while True:
        await asyncio.sleep(10)
        message = "Hello clients! This is a broadcast message.".encode("utf-8")
        server.broadcast_all(message)

async def log_clients_periodically(server: SnaikenetServer):
    while True:
        logger.info(server.get_clients_str())
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())