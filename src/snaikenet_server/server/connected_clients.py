import asyncio

type ClientIdToIndex = dict[str, int]
type AddrToIndex = dict[tuple[str, int], int]


class _ConnectedClient:

    def __init__(self, client_id: str, addr: tuple[str, int]):
        self._client_id = client_id
        self._addr = addr
        self._last_seen = asyncio.get_running_loop().time()

    def get_id(self):
        return self._client_id

    def get_addr(self):
        return self._addr

    def get_last_seen(self):
        return self._last_seen

    def touch(self):
        self._last_seen = asyncio.get_running_loop().time()


class ConnectedClients:
    def __init__(self):
        self._client_id_map: ClientIdToIndex = {}
        self._addr_map: AddrToIndex = {}
        self._clients: list[_ConnectedClient] = []

    def register_client(self, client_id: str, addr: tuple[str, int]):
        client = _ConnectedClient(client_id, addr)
        self._clients.append(client)
        index = len(self._clients) - 1
        self._client_id_map[client_id] = index
        self._addr_map[addr] = index

    def get_client_by_id(self, client_id: str) -> _ConnectedClient | None:
        index = self._client_id_map.get(client_id, None)
        if index is None:
            return None
        return self._clients[index]

    def get_client_by_addr(self, addr: tuple[str, int]) -> _ConnectedClient | None:
        index = self._addr_map.get(addr, None)
        if index is None:
            return None
        return self._clients[index]

    def remove_client_by_id(self, client_id: str):
        index = self._client_id_map.pop(client_id, None)
        if index is None:
            return
        client = self._clients[index]
        self._addr_map.pop(client.get_addr(), None)
        self._clients.pop(index)
        self._defragment_clients()
        return

    def get_client_addrs(self) -> list[tuple[str, int]]:
        return [client.get_addr() for client in self.get_clients()]

    def get_clients(self) -> list[_ConnectedClient]:
        return [client for client in self._clients if client is not None]

    def has_client_id(self, client_id: str) -> bool:
        return client_id in self._client_id_map

    def has_client_addr(self, addr: tuple[str, int]) -> bool:
        return addr in self._addr_map

    def touch_client_by_id(self, client_id: str):
        client = self.get_client_by_id(client_id)
        if client is not None:
            client.touch()

    def touch_client_by_addr(self, addr: tuple[str, int]):
        client = self.get_client_by_addr(addr)
        if client is not None:
            client.touch()

    # Defragments the list of clients so that no "None" clients exist
    def _defragment_clients(self):
        new_clients = []
        for client in self._clients:
            if client is not None:
                new_clients.append(client)

        self._clients = []
        for client in new_clients:
            self.register_client(client.get_id(), client.get_addr())
