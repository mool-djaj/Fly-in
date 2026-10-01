import heapq
from typing import cast

from pars import DroneNetwork


class AStar:

    def __init__(self, network: DroneNetwork) -> None:
        self.network = network
        self.heuristic: dict[str, float] = {}
        start_hub = cast(str, self.network.start_hub)
        end_hub = cast(str, self.network.end_hub)

        self.start_hub = start_hub
        self.end_hub = end_hub

        self.costs: dict[str, float] = {
            "priority": 1.0,
            "restricted": 2.0,
            "normal": 1.0,
        }

        self.graph: dict[str, list[str]] = {}

        for name in self.network.zones:
            self.graph[name] = []

        for connection in self.network.connections:
            self.graph[connection.zone1].append(connection.zone2)
            self.graph[connection.zone2].append(connection.zone1)

        self.heuristic = self._heuristic(self.end_hub)

    def _heuristic(self, end: str) -> dict[str, float]:
        h_score: dict[str, float] = {
            zone: float("inf")
            for zone in self.graph
        }

        h_score[end] = 0

        queue: list[tuple[float, str]] = []
        heapq.heappush(queue, (0, end))

        while queue:
            cost, current = heapq.heappop(queue)

            if cost > h_score[current]:
                continue

            for neighbor in self.graph[current]:
                if self.network.zones[neighbor].zone_type == "blocked":
                    continue

                move_cost = self.costs[
                    self.network.zones[current].zone_type
                ]

                new_cost = cost + move_cost

                if new_cost < h_score[neighbor]:
                    h_score[neighbor] = new_cost

                    heapq.heappush(
                        queue,
                        (new_cost, neighbor),
                    )

        return h_score

    def find_path(
        self,
        start: str,
        end: str,
        ignored_edges: set[tuple[str, str]],
    ) -> list[str]:

        open_set: list[tuple[float, float, str, list[str]]] = []
        g_score: dict[str, float] = {}

        for zone_name in self.graph:
            g_score[zone_name] = float("inf")
        g_score[start] = 0

        heapq.heappush(open_set, (0, 0, start, [start]))

        while open_set:
            _, _, current,  path = heapq.heappop(open_set)

            if current == end:
                return path

            for neighbor in self.graph[current]:
                if (
                    (current, neighbor) in ignored_edges
                    or (neighbor, current) in ignored_edges
                        ):
                    continue

                neighbor_zone = self.network.zones[neighbor]
                priority_flag = 1

                if neighbor_zone.zone_type == "blocked":
                    continue

                elif neighbor_zone.zone_type == "priority":
                    priority_flag = 0

                new_g = (
                    g_score[current]
                    + self.costs[neighbor_zone.zone_type]
                )

                if new_g < g_score[neighbor]:
                    g_score[neighbor] = new_g

                    f = new_g + self.heuristic[neighbor]
                    new_path = path + [neighbor]

                    heapq.heappush(open_set, (
                        f, priority_flag, neighbor, new_path)
                        )
        return []

    def find_paths(
        self,
        start: str,
        end: str,
    ) -> list[list[str]]:

        paths: list[list[str]] = []

        first_path = self.find_path(
            start,
            end,
            set(),
        )

        if not first_path:
            return []

        paths.append(first_path)

        for i in range(len(first_path) - 1):
            edge = (
                first_path[i],
                first_path[i + 1],
                )

            ignored = {edge}

            new_path = self.find_path(
                start,
                end,
                ignored,
            )

            if new_path and new_path not in paths:
                paths.append(new_path)

        return paths
