from typing import List, Dict, Set, Tuple
from pars import DroneNetwork, Connection, Zone


class Drone:
    def __init__(self, dr_id: int, start_loc: str):
        self.dr_id = f"D{dr_id}" 
        self.dr_loc = start_loc
        self.is_delivered = False
        self.target_zone = None
        self.path: List[str] = []
        self.turns_in_transit = 0
        
    def get_next_destination(self) -> str: #peeking !!!!!
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
        
        def shortest_path(self, start_name, taget_name):
            
            queue = [(start_name, 0, [])]
            visited = set([(start_name, 0)])
            
            while len(queue) > 0:
                
                curr_zone, curr_turn, path = queue.pop(0)
                
                if curr_zone == curr_turn:
                    return path
                
                next_turn = curr_turn + 1
                
                movement_options = self.graph[current_zone] + [current_zone]
                
                for next_zone in movement_options:
                    
                    if (next_zone, next_turn) not in visited:

                        booked_drones = self.reservations[next_zone].get(next_turn, 0)
                        zone_capacity = self.network.zones[next_zone].max_drones
                
                
                
            
            
            
        
            
           