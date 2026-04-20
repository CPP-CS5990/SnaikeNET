from snaikenet_client.types import ClientGridStructure


class ClientGameStateFrame:
    def __init__(
        self,
        sequence_number: int,
        player_length: int,
        num_kills: int,
        is_alive: bool,
        is_spectating: bool,
        grid_data: ClientGridStructure,
    ):
        self.is_spectating = is_spectating
        self.sequence_number = sequence_number
        self.player_length = player_length
        self.num_kills = num_kills
        self.is_alive = is_alive
        self.grid_data = grid_data
