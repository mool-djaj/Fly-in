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
        
    
    def create_drones(self) -> None:
        path_index = 0

        for i in range(self.network.nb_drones):
            drone = Drone(i + 1)

            drone.path = self.paths[path_index].copy()
            self.drones.append(drone)

            path_index += 1

            if path_index == len(self.paths):
                path_index = 0
                
                
    def _zone_res(self) -> dict[str, int]:
        zone_res: dict[str, int] = {}

        for zone_name in self.network.zones:
            zone_res[zone_name] = 0

        for drone in self.drones:
            current_zone = drone.path[drone.position]
            zone_res[current_zone] += 1

        return zone_res