import sys
import time
from typing import Any
from pars import Pars
from path_find import AStar_Engine, Drone


GUI_Visualizer: Any = None
try:
    from visualizer import GUI_Visualizer

    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False


def main() -> int:

    if len(sys.argv) != 2:
        print("Usage: python3 fly_in.py <map_file>")
        return 1

    map_file = sys.argv[1]

    try:
        network = Pars.parse_config(map_file)
        engine = AStar_Engine(network)
        
        start_time = time.perf_counter()
        
        paths = engine.route_all_drones()
        
        end_time = time.perf_counter()
        routing_time = end_time - start_time

        drones: list[Drone] = []
        if engine.start_hub is None:
            raise ValueError("No start hub was defined in the map file.")

        for i, path in enumerate(paths):
            drone = Drone(i + 1, engine.start_hub)
            if path and len(path) > 1:
                drone.path = path[1:]
            drones.append(drone)

        turn_number = 0
        while any(len(drone.path) > 0 for drone in drones):
            turn_number += 1
            turn_moves: list[str] = []

            for drone in drones:
                if len(drone.path) > 0:
                    next_step = drone.get_next_destination()
                    if next_step is None:
                        continue

                    scheduled_turn, dest = next_step
                    if scheduled_turn == turn_number:
                        if drone.dr_loc != dest:
                            turn_moves.append(f"{drone.dr_id}-{dest}")

                        drone.dr_loc = dest
                        drone.path.pop(0)

            if turn_moves:
                print(" ".join(turn_moves))

        print("\n--- BENCHMARK ---")
        print(f"Total Routing Time : {routing_time:.5f} seconds")
        print(f"Total Nodes Checked: {engine.nodes_checked}\n")

        if VISUALIZER_AVAILABLE and GUI_Visualizer is not None:
            print(
                f"[Simulation Complete in {turn_number}"
                " turns. Opening Visualizer...]"
                )
            GUI_Visualizer(network, paths)
        return 0
        
    except (FileNotFoundError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())