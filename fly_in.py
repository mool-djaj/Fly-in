import sys
from pars import parse_network
from path_find import AStar_Engine
from visualizer import GUI_Visualizer
import time


def main() -> None:
    if len(sys.argv) != 2:
        print("Error: Missing map file argument.")
        print(f"Usage: python3 {sys.argv[0]} <path_to_map.txt>")
        sys.exit(1)

    start = time.process_time()
    map_filepath = sys.argv[1]

    print(f"[*] Parsing map: {map_filepath}...")
    network = parse_network(map_filepath)
    print(f"[+] Map parsed successfully! Drones: {network.nb_drones}, Zones: {len(network.zones)}")

    print("[*] Calculating Space-Time A* routes...")
    
    pathfinder = AStar_Engine(network)
    
    all_paths = pathfinder.route_all_drones() 

    if not all_paths:
        print("[-] Error: Could not find valid paths for the network.")
        sys.exit(1)

    print(f"[+] Routes calculated for {len(all_paths)} drones. Launching visualizer...")
    end = time.process_time()
    print(f"benchmark:{end - start}")


    try:
        GUI_Visualizer(network, all_paths)
    except KeyboardInterrupt:
        print("\n[*] Visualizer closed by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
