import heapq
from typing import Optional
from pars import DroneNetwork

PathLog = list[tuple[int, str]]
QueueItem = tuple[float, float, int, str, PathLog]
PRIORITY_PREFERENCE = 0.000001


class Drone:
    def __init__(self, dr_id: int, start_loc: str) -> None:
        self.dr_id = f"D{dr_id}"
        self.dr_loc = start_loc
        self.path: PathLog = []

    def get_next_destination(self) -> Optional[tuple[int, str]]:
        if len(self.path) > 0:
            return self.path[0]
        return None


class AStar_Engine:
    def __init__(self, network: DroneNetwork) -> None:
        self.network = network
        self.nodes_checked = 0
        self.start_hub: Optional[str] = None
        self.end_hub: Optional[str] = None

        self.zone_res: dict[str, dict[int, int]] = {}
        self.link_res: dict[str, dict[int, int]] = {}
        self.link_capacity: dict[str, int] = {}
        self.graph: dict[str, list[str]] = {}

        self.costs = {
            "priority": 1.0, "restricted": 2.0, "normal": 1.0,
            "blocked": 999.0
            }

        for name, zone in self.network.zones.items():
            if zone.hub_role == "start_hub":
                self.start_hub = name
            if zone.hub_role == "end_hub":
                self.end_hub = name

            self.graph[name] = []
            self.zone_res[name] = {}

        for conn in self.network.connections:
            self.graph[conn.zone1].append(conn.zone2)
            self.graph[conn.zone2].append(conn.zone1)

            link_name = self.get_link_key(conn.zone1, conn.zone2)
            self.link_res[link_name] = {}
            self.link_capacity[link_name] = conn.max_link_capacity

        self.heuristics = self._compute_heuristics()

    def get_link_key(self, z1: str, z2: str) -> str:
        if z1 <= z2:
            return f"{z1}-{z2}"
        else:
            return f"{z2}-{z1}"

    def is_valid_move(
            self, zone: str, turn: int,
            visited: set[tuple[str, int]]) -> bool:
        if (zone, turn) in visited:
            return False

        if zone == self.start_hub:
            return True
        if zone == self.end_hub:
            return True

        capacity = self.network.zones[zone].max_drones
        booked = self.zone_res[zone].get(turn, 0)

        if booked < capacity:
            return True

        return False

    def _compute_heuristics(self) -> dict[str, float]:
        h_scores = {z: float("inf") for z in self.network.zones}

        if self.end_hub is None:
            return h_scores

        h_scores[self.end_hub] = 0.0
        queue = [(0.0, self.end_hub)]

        while len(queue) > 0:
            dist, current = heapq.heappop(queue)

            if dist > h_scores[current]:
                continue

            if self.network.zones[current].zone_type == "blocked":
                continue

            for neighbor in self.graph[current]:
                zone_type = self.network.zones[current].zone_type
                move_cost = self.costs.get(zone_type, 1.0)
                new_dist = dist + move_cost

                if new_dist < h_scores[neighbor]:
                    h_scores[neighbor] = new_dist
                    heapq.heappush(queue, (new_dist, neighbor))

        return h_scores

    def shortest_path(
            self, start_zone: str, target_zone: str, start_turn: int = 0
            ) -> PathLog:

        initial_f = self.heuristics.get(start_zone, float("inf"))

        if initial_f == float("inf"):
            return []

        queue: list[QueueItem] = [
            (initial_f, 0.0, start_turn, start_zone, [(start_turn, start_zone)]
             )
        ]
        visited: set[tuple[str, int]] = set()

        while len(queue) > 0:
            self.nodes_checked += 1
            f, cost, turn, zone, path = heapq.heappop(queue)

            if zone == target_zone:
                return path

            next_turn = turn + 1
            if self.is_valid_move(zone, next_turn, visited):
                visited.add((zone, next_turn))
                new_cost = cost + 1.0
                new_f = new_cost + self.heuristics.get(zone, 0.0)
                heapq.heappush(queue, (
                    new_f, new_cost, next_turn, zone, path
                    + [(next_turn, zone)]))

            for n_zone in self.graph[zone]:
                z_type = self.network.zones[n_zone].zone_type

                if z_type == "blocked":
                    continue

                link_key = self.get_link_key(zone, n_zone)
                l_capacity = self.link_capacity[link_key]
                l_booked = self.link_res[link_key].get(next_turn, 0)

                if l_booked >= l_capacity:
                    continue

                if z_type == "restricted":
                    arrive_t = turn + 2
                else:
                    arrive_t = turn + 1

                new_cost = cost + self.costs.get(z_type, 1.0)
                new_f = new_cost + self.heuristics.get(n_zone, 0.0)

                if z_type == "priority":
                    new_f -= PRIORITY_PREFERENCE

                if self.is_valid_move(n_zone, arrive_t, visited):
                    visited.add((n_zone, arrive_t))
                    new_path = list(path)

                    if z_type == "restricted":
                        transit_turn = turn + 1
                        new_path.append((transit_turn, link_key))

                    new_path.append((arrive_t, n_zone))
                    heapq.heappush(
                        queue, (new_f, new_cost, arrive_t, n_zone, new_path))

        return []

    def book_path(self, path: PathLog) -> None:
        if len(path) == 0:
            return

        prev_loc = path[0][1]

        for turn, loc in path:
            if "-" in loc:
                self.link_res[loc][turn] = self.link_res[loc].get(turn, 0) + 1
            else:
                self.zone_res[loc][turn] = self.zone_res[loc].get(turn, 0) + 1

                if loc != prev_loc:
                    if "-" not in prev_loc:
                        link = self.get_link_key(prev_loc, loc)
                        self.link_res[link][turn] = (
                            self.link_res[link].get(turn, 0) + 1)

            prev_loc = loc

    def route_all_drones(self) -> list[PathLog]:
        all_paths: list[PathLog] = []
        max_delay = max(1, self.network.nb_drones // 2)

        for _ in range(self.network.nb_drones):
            chosen = []

            for offset in range(max_delay + 1):
                if self.start_hub is None:
                    break
                if self.end_hub is None:
                    break

                path = self.shortest_path(
                    self.start_hub, self.end_hub, start_turn=offset
                    )
                if len(path) > 0:
                    chosen = path
                    break

            if len(chosen) > 0:
                self.book_path(chosen)
                all_paths.append(chosen)
            else:
                return []

        return all_paths
