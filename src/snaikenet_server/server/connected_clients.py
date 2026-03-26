type ClientIDtoAddr = dict[_ConnectedClient, tuple[str, int]]
type AddrToClientID = dict[tuple[str, int], str]

class _ConnectedClient:
    client_id: str
    last_seen: int

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.last_seen = 0

    def __hash__(self):
        return hash(self.client_id)

class ConnectedClients:
    _client_uuid_to_addr: ClientIDtoAddr
    _addr_to_client_uuid: AddrToClientID

    def __init__(self):
        self._client_uuid_to_addr = {}
        self._addr_to_client_uuid = {}

    def register_client(self, client_id: str, addr: tuple[str, int]):
        client = _ConnectedClient(client_id)
        self._client_uuid_to_addr[client] = addr
        self._addr_to_client_uuid[addr] = client_id

    def get_client_addr(self, client_id: str) -> tuple[str, int] | None:
        client = _ConnectedClient(client_id)
        return self._client_uuid_to_addr.get(client)

    def get_client_id(self, addr: tuple[str, int]) -> str | None:
        return self._addr_to_client_uuid.get(addr)

    def remove_client_by_id(self, client_id: str):
        client = _ConnectedClient(client_id)
        addr = self._client_uuid_to_addr.pop(client, None)
        if addr:
            self._addr_to_client_uuid.pop(addr, None)

    def remove_client_by_addr(self, addr: tuple[str, int]):
        client_id = self._addr_to_client_uuid.pop(addr, None)
        if client_id:
            client = _ConnectedClient(client_id)
            self._client_uuid_to_addr.pop(client, None)

    def items(self):
        return self._client_uuid_to_addr.items()

    def get_client_addrs(self) -> list[tuple[str, int]]:
        return list(self._client_uuid_to_addr.values())

    def get_client_ids(self) -> list[str]:
        return list(self._addr_to_client_uuid.values())

    def has_client_id(self, client_id: str) -> bool:
        return _ConnectedClient(client_id) in self._client_uuid_to_addr

    def has_client_addr(self, addr: tuple[str, int]) -> bool:
        return addr in self._addr_to_client_uuid