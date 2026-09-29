from drone import Drone
from pars import DroneNetwork


class Simulator:

    def __init__(
        self,
        network: DroneNetwork,
        path: list[str],
    ) -> None:
        self.network = network
        self.path = path
        self.drones: list[Drone] = []
        self.turn = 0

        self.link_res: dict[str, dict[int, int]] = {}
        self.link_capacity: dict[str, int] = {}

        for connection in self.network.connections:
            link = self._link_key(
                connection.zone1,
                connection.zone2,
            )
            self.link_res[link] = {}
            self.link_capacity[link] = connection.max_link_capacity

        self.zone_res: dict[str, dict[int, int]] = {}

        for zone_name in self.network.zones:
            self.zone_res[zone_name] = {}

    def _link_key(self, zone1: str, zone2: str) -> str:
        if zone1 < zone2:
            return f"{zone1}-{zone2}"
        return f"{zone2}-{zone1}"

    def _zone_occupancy(self) -> dict[str, int]:
        zone_occupancy: dict[str, int] = {}

        for zone_name in self.network.zones:
            zone_occupancy[zone_name] = 0

        for drone in self.drones:
            current_zone = drone.path[drone.position]
            zone_occupancy[current_zone] += 1

        return zone_occupancy

    def _reserve_zone(self, zone_name: str, turn: int) -> None:
        current = self.zone_res[zone_name].get(turn, 0)
        self.zone_res[zone_name][turn] = current + 1

    def _reserve_link(
        self,
        link: str,
        turn: int,
    ) -> None:

        reserved = self.link_res[link].get(turn, 0)
        self.link_res[link][turn] = reserved + 1

    def _zone_available(self, zone_name: str, turn: int) -> bool:
        zone = self.network.zones[zone_name]

        if zone.max_drones is None:
            return True

        reserved = self.zone_res[zone_name].get(turn, 0)

        return reserved < zone.max_drones

    def _link_available(
        self,
        link: str,
        turn: int,
    ) -> bool:

        reserved = self.link_res[link].get(turn, 0)
        return reserved < self.link_capacity[link]

    def _schedule_path(
        self,
        path: list[str],
    ) -> list[tuple[int, str]]:
        schedule: list[tuple[int, str]] = []

        turn = 0
        position = 0

        schedule.append((turn, path[position]))

        while position < len(path) - 1:
            current = path[position]
            next_zone = path[position + 1]

            link = self._link_key(current, next_zone)
            next_turn = turn + 1

            if (
                self._link_available(link, next_turn)
                and self._zone_available(next_zone, next_turn)
            ):
                turn = next_turn
                position += 1
                schedule.append((turn, next_zone))
            else:
                turn = next_turn
                schedule.append((turn, current))

        return schedule
