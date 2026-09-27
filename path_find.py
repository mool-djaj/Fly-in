import heapq
from typing import Optional

from pars import DroneNetwork

PathLog = list[tuple[int, str]]
QueueItem = tuple[float, int, float, int, str, PathLog]


class Drone:
    """Small model representing one drone and its planned path."""

    def __init__(self, dr_id: int, start_loc: str) -> None:
        self.dr_id = f"D{dr_id}"
        self.dr_loc = start_loc
        self.path: PathLog = []

    def get_next_destination(self) -> Optional[tuple[int, str]]:
        """Return the next planned state when one exists."""
        if self.path:
            return self.path[0]
        return None


class AStar_Engine:
    """Plan collision-free paths using a space-time A* search."""

    def __init__(self, network: DroneNetwork) -> None:
        self.network = network
        self.nodes_checked = 0
        self.start_hub: Optional[str] = None
        self.end_hub: Optional[str] = None
        self.zone_res: dict[str, dict[int, int]] = {}
        self.link_res: dict[str, dict[int, int]] = {}
        self.link_capacity: dict[str, int] = {}
        self.graph: dict[str, list[str]] = {}
        self.costs: dict[str, float] = {
            "priority": 1.0,
            "restricted": 2.0,
            "normal": 1.0,
            "blocked": float("inf"),
        }

        for name, zone in self.network.zones.items():
            if zone.hub_role == "start_hub":
                self.start_hub = name
            elif zone.hub_role == "end_hub":
                self.end_hub = name
            self.graph[name] = []
            self.zone_res[name] = {}

        for connection in self.network.connections:
            self.graph[connection.zone1].append(connection.zone2)
            self.graph[connection.zone2].append(connection.zone1)
            link = self.get_link_key(
                connection.zone1,
                connection.zone2,
            )
            self.link_res[link] = {}
            self.link_capacity[link] = connection.max_link_capacity

        self.heuristics = self._compute_heuristics()

    def get_link_key(self, z1: str, z2: str) -> str:
        """Return one canonical key for an undirected connection."""
        if z1 <= z2:
            return f"{z1}-{z2}"
        return f"{z2}-{z1}"

    def is_valid_move(
        self,
        zone: str,
        turn: int,
        visited: set[tuple[str, int]],
    ) -> bool:
        """Check visited state and destination occupancy at a turn."""
        if (zone, turn) in visited:
            return False
        if zone == self.start_hub or zone == self.end_hub:
            return True
        capacity = self.network.zones[zone].max_drones
        return self.zone_res[zone].get(turn, 0) < capacity

    def _compute_heuristics(self) -> dict[str, float]:
        """Compute exact traffic-free distance to the end with Dijkstra."""
        scores = {name: float("inf") for name in self.network.zones}
        if self.end_hub is None:
            return scores

        scores[self.end_hub] = 0.0
        queue: list[tuple[float, str]] = [(0.0, self.end_hub)]

        while queue:
            distance, current = heapq.heappop(queue)
            if distance > scores[current]:
                continue
            if self.network.zones[current].zone_type == "blocked":
                continue

            # In reverse search, moving from neighbor -> current has the
            # movement cost of entering current.
            move_cost = self.costs[
                self.network.zones[current].zone_type
            ]
            for neighbor in self.graph[current]:
                new_distance = distance + move_cost
                if new_distance < scores[neighbor]:
                    scores[neighbor] = new_distance
                    heapq.heappush(
                        queue,
                        (new_distance, neighbor),
                    )

        return scores

    def shortest_path(
        self,
        start_zone: str,
        target_zone: str,
        start_turn: int = 0,
    ) -> PathLog:
        """Find one reservation-compatible path through space and time."""
        initial_f = self.heuristics.get(start_zone, float("inf"))
        if initial_f == float("inf"):
            return []

        initial_path: PathLog = [(start_turn, start_zone)]
        queue: list[QueueItem] = [
            (initial_f, 0, 0.0, start_turn, start_zone, initial_path)
        ]
        visited: set[tuple[str, int]] = {(start_zone, start_turn)}

        while queue:
            self.nodes_checked += 1
            _, priority_bias, cost, turn, zone, path = heapq.heappop(queue)
            if zone == target_zone:
                return path

            next_turn = turn + 1
            if self.is_valid_move(zone, next_turn, visited):
                visited.add((zone, next_turn))
                wait_cost = cost + 1.0
                wait_f = wait_cost + self.heuristics.get(zone, 0.0)
                heapq.heappush(
                    queue,
                    (
                        wait_f,
                        priority_bias,
                        wait_cost,
                        next_turn,
                        zone,
                        path + [(next_turn, zone)],
                    ),
                )

            for next_zone in self.graph[zone]:
                zone_type = self.network.zones[next_zone].zone_type
                if zone_type == "blocked":
                    continue

                link = self.get_link_key(zone, next_zone)
                transit_turn = turn + 1
                link_booked = self.link_res[link].get(transit_turn, 0)
                if link_booked >= self.link_capacity[link]:
                    continue

                if zone_type == "restricted":
                    arrival_turn = turn + 2
                else:
                    arrival_turn = turn + 1

                if not self.is_valid_move(
                    next_zone,
                    arrival_turn,
                    visited,
                ):
                    continue

                visited.add((next_zone, arrival_turn))
                move_cost = self.costs[zone_type]
                new_cost = cost + move_cost
                new_f = new_cost + self.heuristics.get(next_zone, 0.0)

                new_bias = priority_bias - int(zone_type == "priority")
                new_path = list(path)
                if zone_type == "restricted":
                    new_path.append((transit_turn, link))
                new_path.append((arrival_turn, next_zone))

                heapq.heappush(
                    queue,
                    (
                        new_f,
                        new_bias,
                        new_cost,
                        arrival_turn,
                        next_zone,
                        new_path,
                    ),
                )

        return []

    def book_path(self, path: PathLog) -> None:
        """Reserve every zone and connection used by a chosen path."""
        if not path:
            return

        previous = path[0][1]
        for turn, location in path:
            if "-" in location:
                self.link_res[location][turn] = (
                    self.link_res[location].get(turn, 0) + 1
                )
            else:
                self.zone_res[location][turn] = (
                    self.zone_res[location].get(turn, 0) + 1
                )
                if location != previous and "-" not in previous:
                    link = self.get_link_key(previous, location)
                    self.link_res[link][turn] = (
                        self.link_res[link].get(turn, 0) + 1
                    )
            previous = location

    def route_all_drones(self) -> list[PathLog]:
        """Route every drone, reserving each accepted path in order."""
        if self.start_hub is None or self.end_hub is None:
            return []
        if self.heuristics.get(self.start_hub) == float("inf"):
            return []

        all_paths: list[PathLog] = []
        max_delay = max(1, self.network.nb_drones // 2)

        for _ in range(self.network.nb_drones):
            chosen: PathLog = []
            for offset in range(max_delay + 1):
                candidate = self.shortest_path(
                    self.start_hub,
                    self.end_hub,
                    start_turn=offset,
                )
                if candidate:
                    chosen = candidate
                    break
            if not chosen:
                return []
            self.book_path(chosen)
            all_paths.append(chosen)

        return all_paths
