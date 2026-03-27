import time

type ClientToAddr = dict[str, int]
type AddrToClient = dict[tuple[str, int], int]

class _ConnectedClient:
    _client_id: str
    _addr: tuple[str, int]
    last_seen: float

    def __init__(self, client_id: str, addr: tuple[str, int]):
        self._client_id = client_id
        self._addr = addr
        self.last_seen = time.time()

    def get_id(self):
        return self._client_id

    def get_addr(self):
        return self._addr

    def touch(self):
        self.last_seen = time.time()

class ConnectedClients:
    _client_id_map: ClientToAddr
    _addr_map: AddrToClient
    _clients: list[_ConnectedClient]

    def __init__(self):
        self._client_id_map = {}
        self._addr_map = {}
        self._clients = []

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

    def pop_client_by_id(self, client_id: str) -> _ConnectedClient | None:
        index = self._client_id_map.pop(client_id, None)
        if index is None:
            return None
        client = self._clients[index]
        self._addr_map.pop(client.get_addr(), None)
        return client

    def remove_client_by_addr(self, addr: tuple[str, int]):
        index = self._addr_map.pop(addr, None)
        if index is None:
            return None
        client = self._clients[index]
        self._client_id_map.pop(client.get_id(), None)
        return client

    def get_client_addrs(self) -> list[tuple[str, int]]:
        return [client.get_addr() for client in self._clients]

    def get_clients(self) -> list[_ConnectedClient]:
        return list(self._clients)

    def has_client_id(self, client_id: str) -> bool:
        return _ConnectedClient(client_id) in self._client_id_map

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
