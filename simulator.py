from drone import Drone
from pars import DroneNetwork


class Simulator:
    def __init__(
        self,
        network: DroneNetwork,
        paths: list[list[str]],
    ) -> None:
        self.network = network
        self.paths = paths
        self.drones: list[Drone] = []

        self.zone_res: dict[str, dict[int, int]] = {}
        for zone_name in self.network.zones:
            self.zone_res[zone_name] = {}

        self.link_res: dict[str, dict[int, int]] = {}
        self.link_capacity: dict[str, int] = {}

        for connection in self.network.connections:
            link = self._link_key(
                connection.zone1,
                connection.zone2,
            )
            self.link_res[link] = {}
            self.link_capacity[link] = connection.max_link_capacity

    def _link_key(self, zone1: str, zone2: str) -> str:
        if zone1 < zone2:
            return f"{zone1}-{zone2}"
        return f"{zone2}-{zone1}"

    def _zone_available(self, zone_name: str, turn: int) -> bool:
        zone = self.network.zones[zone_name]

        if zone.max_drones is None:
            return True

        reserved = self.zone_res[zone_name].get(turn, 0)
        return reserved < zone.max_drones

    def _link_available(self, link: str, turn: int) -> bool:
        reserved = self.link_res[link].get(turn, 0)
        return reserved < self.link_capacity[link]

    def _reserve_zone(self, zone_name: str, turn: int) -> None:
        reserved = self.zone_res[zone_name].get(turn, 0)
        self.zone_res[zone_name][turn] = reserved + 1

    def _reserve_link(self, link: str, turn: int) -> None:
        reserved = self.link_res[link].get(turn, 0)
        self.link_res[link][turn] = reserved + 1

    def _schedule_path(
        self,
        path: list[str],
    ) -> list[tuple[int, str]]:
        if not path:
            return []

        schedule: list[tuple[int, str]] = [(0, path[0])]
        turn = 0
        position = 0

        while position < len(path) - 1:
            current = path[position]
            next_zone = path[position + 1]
            zone = self.network.zones[next_zone]
            link = self._link_key(current, next_zone)

            if zone.zone_type == "restricted":
                link_turn = turn + 1
                arrival_turn = turn + 2

                if (
                    self._link_available(link, link_turn)
                    and self._zone_available(next_zone, arrival_turn)
                ):
                    schedule.append((link_turn, link))
                    schedule.append((arrival_turn, next_zone))
                    turn = arrival_turn
                    position += 1
                else:
                    wait_turn = turn + 1
                    if not self._zone_available(current, wait_turn):
                        return []
                    turn = wait_turn
                    schedule.append((turn, current))
            else:
                next_turn = turn + 1

                if (
                    self._link_available(link, next_turn)
                    and self._zone_available(next_zone, next_turn)
                ):
                    turn = next_turn
                    position += 1
                    schedule.append((turn, next_zone))
                else:
                    if not self._zone_available(current, next_turn):
                        return []
                    turn = next_turn
                    schedule.append((turn, current))

        return schedule

    def _plan_drone(self, drone: Drone) -> bool:
        best_path: list[str] = []
        best_schedule: list[tuple[int, str]] = []

        for path in self.paths:
            schedule = self._schedule_path(path)

            if not schedule:
                continue

            if (
                not best_schedule
                or schedule[-1][0] < best_schedule[-1][0]
            ):
                best_path = path
                best_schedule = schedule

        if not best_schedule:
            return False

        drone.path = best_path.copy()
        drone.schedule = best_schedule.copy()

        previous = ""

        for turn, place in drone.schedule:
            if place in self.link_res:
                self._reserve_link(place, turn)
            else:
                zone = self.network.zones[place]

                if zone.max_drones is not None:
                    self._reserve_zone(place, turn)

                if (
                    previous in self.network.zones
                    and previous != place
                ):
                    link = self._link_key(previous, place)
                    self._reserve_link(link, turn)

            previous = place

        return True

    def plan_drones(self) -> list[Drone]:
        for drone_id in range(1, self.network.nb_drones + 1):
            drone = Drone(drone_id)

            if not self._plan_drone(drone):
                raise RuntimeError(
                    f"Could not plan a valid path for {drone.id}"
                )

            self.drones.append(drone)

        return self.drones
