import heapq
from typing import Optional
from pars import DroneNetwork


class Drone:

    def __init__(self, dr_id: int, start_loc: str) -> None:
        self.dr_id = f"D{dr_id}"
        self.dr_loc = start_loc
        self.is_delivered = False
        self.path: list[tuple[int, str]] = []

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

        for name, zone_obj in self.network.zones.items():
            if zone_obj.hub_role == "start_hub":
                self.start_hub = name
            elif zone_obj.hub_role == "end_hub":
                self.end_hub = name

        self.graph: dict[str, list[str]] = {name: [] for name in self.network.zones}
        for conn in self.network.connections:
            self.graph[conn.zone1].append(conn.zone2)
            self.graph[conn.zone2].append(conn.zone1)

        self.zone_res: dict[str, dict[int, int]] = {
            name: {} for name in self.network.zones
        }
        self.link_res: dict[tuple[str, str], dict[int, int]] = {}
        self.link_capacity: dict[tuple[str, str], int] = {}

        for conn in self.network.connections:
            link = self.get_link_key(conn.zone1, conn.zone2)
            self.link_res[link] = {}
            self.link_capacity[link] = conn.max_link_capacity

        self.heuristics = self._compute_heuristics()

    def get_move_cost(self, zone_type: str) -> float:

        if zone_type == "priority":
            return 0.9
        if zone_type == "restricted":
            return 2.0
        return 1.0
    
    def is_valid_move(self, zone: str, turn: int, visited: set) -> bool:

        if (zone, turn) in visited:
            return False

        capacity = self.network.zones[zone].max_drones
        booked = self.zone_res[zone].get(turn, 0)
        return booked < capacity or zone in (self.start_hub, self.end_hub)

    def _compute_heuristics(self) -> dict[str, float]:

        heuristics: dict[str, float] = {zone: float("inf") for zone in self.network.zones}
        if not self.end_hub:
            return heuristics

        heuristics[self.end_hub] = 0.0
        queue: list[tuple[float, str]] = [(0.0, self.end_hub)]

        while queue:
            current_dist, curr_zone = heapq.heappop(queue)
            if current_dist > heuristics[curr_zone]:
                continue

            for neighbor in self.graph[curr_zone]:

                zone_obj = self.network.zones[curr_zone]

                move_cost = self.get_move_cost(zone_obj.zone_type)
                new_dist = current_dist + move_cost
                
                if new_dist < heuristics[neighbor]:
                    heuristics[neighbor] = new_dist
                    heapq.heappush(queue, (new_dist, neighbor))
                    
        return heuristics

    def get_link_key(self, z1: str, z2: str) -> tuple[str, str]:

        return (z1, z2) if z1 <= z2 else (z2, z1)



    def shortest_path(
        self, start_zone: str, target_zone: str, start_turn: int = 0
    ) -> list[tuple[int, str]]:

        initial_f = self.heuristics.get(start_zone, 0.0)
        queue: list[tuple[float, float, int, str, list[tuple[int, str]]]] = [
            (initial_f, 0.0, start_turn, start_zone, [(start_turn, start_zone)])
        ]
        visited = {(start_zone, start_turn)}

        max_turn_limit = 10000

        while queue:
            self.nodes_checked += 1
            f_score, cost, curr_turn, curr_zone, path = heapq.heappop(queue)

            if curr_zone == target_zone:
                return path
                
            if curr_turn > max_turn_limit:
                continue

            wait_turn = curr_turn + 1
            if self.is_valid_move(curr_zone, wait_turn, visited):
                visited.add((curr_zone, wait_turn))
                new_cost = cost + 1.0
                new_f = new_cost + self.heuristics.get(curr_zone, 0.0)
                heapq.heappush(
                    queue,
                        (
                            new_f,
                            new_cost,
                            wait_turn,
                            curr_zone,
                            path + [(wait_turn, curr_zone)],
                        ),
                    )

            for next_zone in self.graph[curr_zone]:
                zone_obj = self.network.zones[next_zone]

                if zone_obj.zone_type == "blocked":
                    continue

                link_key = self.get_link_key(curr_zone, next_zone)
                l_capacity = self.link_capacity[link_key]
                l_booked = self.link_res[link_key].get(curr_turn + 1, 0)

                if l_booked >= l_capacity:
                    continue
                turns_to_cross = 2 if zone_obj.zone_type == "restricted" else 1                
                next_turn = curr_turn + turns_to_cross
                move_cost = self.get_move_cost(zone_obj.zone_type)
                new_cost = cost + move_cost
                new_f = new_cost + self.heuristics.get(next_zone, 0.0)

                if self.is_valid_move(next_zone, next_turn, visited):
                        visited.add((next_zone, next_turn))
                        new_path = list(path)

                        if turns_to_cross == 2:
                            transit_turn = curr_turn + 1
                            link_name = f"{curr_zone}-{next_zone}"
                            new_path.append((transit_turn, link_name))

                        new_path.append((next_turn, next_zone))
                        heapq.heappush(
                            queue, (new_f, new_cost, next_turn, next_zone, new_path)
                        )


        return []

    def book_path(self, path: list[tuple[int, str]]) -> None:

        if not path:
            return
        prev_lock = path[0][1]
        
        for turn, location in path:
            if "-" in location:
                z1, z2 = location.split("-")
                link_key = self.get_link_key(z1, z2)
                self.link_res[link_key][turn] = self.link_res[link_key].get(turn, 0) + 1
            else:
                self.zone_res[location][turn] = self.zone_res[location].get(turn, 0) + 1
                if location != prev_lock and "-" not in prev_lock:
                    link_key = self.get_link_key(prev_lock, location)
                    if link_key in self.link_res:
                        self.link_res[link_key][turn] = self.link_res[link_key].get(turn, 0) + 1
            prev_lock = location


    def route_all_drones(self) -> list[list[tuple[int, str]]]:

        all_drone_paths: list[list[tuple[int, str]]] = []

        max_offset = max(1, self.network.nb_drones // 2)

        for _ in range(self.network.nb_drones):
            chosen_path: list[tuple[int, str]] = []

            for offset in range(0, max_offset + 1):
                if self.start_hub is None or self.end_hub is None:
                    break

                path = self.shortest_path(
                    self.start_hub, self.end_hub, start_turn=offset
                )

                if path:
                    chosen_path = path
                    break

            if chosen_path:
                self.book_path(chosen_path)
                all_drone_paths.append(chosen_path)
            else:
                raise ValueError(
                    f"Could not find a valid route for drone {len(all_drone_paths) + 1}. "
                    "The network may be deadlocked or the end zone is unreachable."
                )

        return all_drone_paths