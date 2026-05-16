from typing import List, Dict, Set
from pars import DroneNetwork

class Drone:
    def __init__(self, dr_id: int, start_loc: str):
        self.dr_id = f"D{dr_id}" 
        self.dr_loc = start_loc
        self.is_delivered = False
        self.path: List[str] = []
        
    def get_next_destination(self) -> str: 
        """Looks at the very next step in the path without moving yet."""
        if len(self.path) > 0:
            return self.path[0]
        return None

class BFS_Engine:
    def __init__(self, network: DroneNetwork):
        self.network = network
        self.start_hub = None
        self.end_hub = None
        
        for name, zone_obj in self.network.zones.items():
            if zone_obj.hub_role == "start_hub":
                self.start_hub = name
            elif zone_obj.hub_role == "end_hub":
                self.end_hub = name
                
        self.graph: Dict[str, List[str]] = {name: [] for name in self.network.zones}
        
        for conn in self.network.connections:
            self.graph[conn.zone1].append(conn.zone2)
            self.graph[conn.zone2].append(conn.zone1)
            
        self.reservations = {name: {} for name in self.network.zones}

    def shortest_path(self, start_name: str, target_name: str) -> List[str]:
        """Calculates the shortest route using a Queue-based BFS."""
        
        queue = [(start_name, 0, [start_name])]
        visited = {(start_name, 0)}
        
        while len(queue) > 0:
            curr_zone, curr_turn, path = queue.pop(0)
            
            if curr_zone == target_name:
                return path
            next_turn = curr_turn + 1
            
            prev_zone = path[-2] if len(path) >= 2 else None
            
            # Priority 1: Rooms we haven't just visited
            forward_rooms = [z for z in self.graph[curr_zone] if z != prev_zone]
            # Priority 3: The room we just came from
            backward_rooms = [z for z in self.graph[curr_zone] if z == prev_zone]
            
            # Order: Forward > Wait > Backward
            movement_options = forward_rooms + [curr_zone] + backward_rooms
            # Check all rooms connected to the current one
            for next_zone in movement_options:
                if (next_zone, next_turn) not in visited:
                    booked = self.reservations[next_zone].get(next_turn, 0)
                    capacity = self.network.zones[next_zone].max_drones
                    
                    if booked < capacity :
                        visited.add((next_zone, next_turn))
                        new_path = path + [next_zone]
                        queue.append((next_zone, next_turn, new_path))
                    
        return [] # Return empty if no path exists

    def book_path(self, path: List[str]):
        """Records the drone's schedule in the global reservation table."""
        for turn, zone in enumerate(path):
            # turn 0 is current position, turn 1 is first move, etc.
            if turn not in self.reservations[zone]:
                self.reservations[zone][turn] = 0
            self.reservations[zone][turn] += 1

    def route_all_drones(self) -> List[List[str]]:
        """Finds the path for every drone defined in the map."""
        all_drone_paths = []
        # Loop based on the nb_drones parsed from the map file
        for _ in range(self.network.nb_drones):
            path = self.shortest_path(self.start_hub, self.end_hub)
            
            if path:
                self.book_path(path)
                all_drone_paths.append(path)
            
        return all_drone_paths