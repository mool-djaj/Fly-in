import heapq
from typing import Optional
from pars import DroneNetwork


class Drone:
    """Represents a drone and its current route state."""

    def __init__(self, dr_id: int, start_loc: str) -> None:
        self.dr_id = f"D{dr_id}"
        self.dr_loc = start_loc
        self.is_delivered = False
        self.path: list[tuple[int, str]] = []

    def get_next_destination(self) -> Optional[tuple[int, str]]:
        """Return the next scheduled movement, if one exists."""

        if len(self.path) > 0:
            return self.path[0]
        return None


class Dijkstra_Engine:
    """Routes drones through the network with reservation constraints."""

    def __init__(self, network: DroneNetwork) -> None:
        self.network = network
        self.start_hub: Optional[str] = None
        self.end_hub: Optional[str] = None

        # 1. Identify start and end hubs
        for name, zone_obj in self.network.zones.items():
            if zone_obj.hub_role == "start_hub":
                self.start_hub = name
            elif zone_obj.hub_role == "end_hub":
                self.end_hub = name

        # 2. Build adjacency list for quick neighbor lookups
        self.graph: dict[str, list[str]] = {name: [] for name in self.network.zones}
        for conn in self.network.connections:
            self.graph[conn.zone1].append(conn.zone2)
            self.graph[conn.zone2].append(conn.zone1)

        # 3. Time-Space Reservations
        self.zone_res: dict[str, dict[int, int]] = {
            name: {} for name in self.network.zones
        }
        self.link_res: dict[tuple[str, str], dict[int, int]] = {}
        self.link_capacity: dict[tuple[str, str], int] = {}

        # 4. Initialize link dictionaries
        for conn in self.network.connections:
            link = self.get_link_key(conn.zone1, conn.zone2)
            self.link_res[link] = {}
            self.link_capacity[link] = conn.max_link_capacity

    def get_link_key(self, z1: str, z2: str) -> tuple[str, str]:
        """Return a stable dictionary key for a bidirectional link."""

        return (z1, z2) if z1 <= z2 else (z2, z1)

    def shortest_path(
        self, start_zone: str, target_zone: str, start_turn: int = 0
    ) -> list[tuple[int, str]]:
        """Calculate the shortest route while respecting capacities."""

        # Queue stores: (Priority_Cost, Actual_Turn, Current_Zone, Path_History)
        queue: list[tuple[float, int, str, list[tuple[int, str]]]] = [
            (0.0, start_turn, start_zone, [(start_turn, start_zone)])
        ]
        visited = {(start_zone, start_turn)}

        while queue:
            cost, curr_turn, curr_zone, path = heapq.heappop(queue)

            if curr_zone == target_zone:
                return path

            # OPTION A: Strategic Waiting
            wait_turn = curr_turn + 1
            capacity = self.network.zones[curr_zone].max_drones
            booked = self.zone_res[curr_zone].get(wait_turn, 0)

            if booked < capacity or curr_zone in (self.start_hub, self.end_hub):
                if (curr_zone, wait_turn) not in visited:
                    visited.add((curr_zone, wait_turn))
                    heapq.heappush(
                        queue,
                        (
                            cost + 1.0,
                            wait_turn,
                            curr_zone,
                            path
                            + [
                                (wait_turn, curr_zone),
                            ],
                        ),
                    )

            # OPTION B: Move to a neighbor
            for next_zone in self.graph[curr_zone]:
                zone_obj = self.network.zones[next_zone]

                if zone_obj.zone_type == "blocked":
                    continue

                # Check Link Capacity before moving
                link_key = self.get_link_key(curr_zone, next_zone)
                l_capacity = self.link_capacity[link_key]
                l_booked = self.link_res[link_key].get(curr_turn + 1, 0)

                if l_booked >= l_capacity:
                    continue  # Connection is full, skip this option

                # Calculate movement costs
                turns_to_cross = 2 if zone_obj.zone_type == "restricted" else 1
                next_turn = curr_turn + turns_to_cross
                move_cost = 0.9 if zone_obj.zone_type == "priority" else turns_to_cross
                new_cost = cost + move_cost

                # Check Zone Capacity
                z_capacity = zone_obj.max_drones
                z_booked = self.zone_res[next_zone].get(next_turn, 0)

                if z_booked < z_capacity or next_zone == self.end_hub:
                    if (next_zone, next_turn) not in visited:
                        visited.add((next_zone, next_turn))

                        new_path = list(path)

                        # Handle restricted zones.
                        if turns_to_cross == 2:
                            transit_turn = curr_turn + 1
                            link_name = f"{curr_zone}-{next_zone}"
                            new_path.append((transit_turn, link_name))

                        new_path.append((next_turn, next_zone))

                        heapq.heappush(
                            queue, (new_cost, next_turn, next_zone, new_path)
                        )

        return []

    def book_path(self, path: list[tuple[int, str]]) -> None:
        """Records the drone's schedule in the global reservation tables."""
        for turn, location in path:
            if "-" in location:
                # It's a connection transit
                z1, z2 = location.split("-")
                link_key = self.get_link_key(z1, z2)
                self.link_res[link_key][turn] = self.link_res[link_key].get(turn, 0) + 1
            else:
                # It's a standard zone
                self.zone_res[location][turn] = self.zone_res[location].get(turn, 0) + 1

    def route_all_drones(self) -> list[list[tuple[int, str]]]:
        """Finds and books the path for every drone defined in the map."""
        all_drone_paths: list[list[tuple[int, str]]] = []
        # Try staggered start offsets to reduce immediate congestion.
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
                # No path found even after trying offsets; skip this drone.
                pass

        return all_drone_paths
