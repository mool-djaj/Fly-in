import heapq
from typing import Optional
from pars import DroneNetwork


class AStar:

    def __init__(self, network: DroneNetwork) -> None:
        self.network = network

        self.start_hub: Optional[str] = None
        self.end_hub: Optional[str] = None

        self.costs: dict[str, float] = {
            "priority": 1.0,
            "restricted": 2.0,
            "normal": 1.0,
        }

        self.graph: dict[str, list[str]] = {}

        for name, zone in self.network.zones.items():
            if zone.hub_role == "start_hub":
                self.start_hub = name
            elif zone.hub_role == "end_hub":
                self.end_hub = name
            self.graph[name] = []

        for connection in self.network.connections:
            self.graph[connection.zone1].append(connection.zone2)
            self.graph[connection.zone2].append(connection.zone1)

    def _heuristic(self, zone_name: str) -> float:
        return 0.0

    def find_path(
        self,
        start: str,
        end: str,
        ignored_edges: set[tuple[str, str]],
    ) -> list[str]:

        open_set: list[tuple[float, float, str, list[str]]] = []
        g_score: dict[str, float] = {}

        for zone in self.graph:
            g_score[zone] = float("inf")
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

                zone = self.network.zones[neighbor]
                priority_flage = 1

                if zone.zone_type == "blocked":
                    continue

                elif zone.zone_type == "priority":
                    priority_flage = 0

                new_g = g_score[current] + self.costs[zone.zone_type]

                if new_g < g_score[neighbor]:
                    g_score[neighbor] = new_g

                    f = new_g + self._heuristic(neighbor)
                    new_path = path + [neighbor]

                    heapq.heappush(open_set, (
                        f, priority_flage, neighbor, new_path)
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

