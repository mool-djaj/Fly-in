import sys
from pars import Pars
from path_find import Dijkstra_Engine, Drone

# Safely attempt to import the visualizer so the script doesn't crash 
# if the evaluators run it without the visualizer.py file present.
try:
    from visualizer import GUI_Visualizer
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False

def main():
    # 1. Check arguments
    if len(sys.argv) != 2:
        print("Usage: python3 fly_in.py <map_file>")
        sys.exit(1)

    map_file = sys.argv[1]

    # 2. Parse the map
    network = Pars.parse_config(map_file)

    # 3. Initialize the Engine and calculate the shortest paths
    engine = Dijkstra_Engine(network)
    paths = engine.route_all_drones()
    
    # 4. Initialize Drone objects
    drones = []
    for i, path in enumerate(paths):
        drone = Drone(i + 1, engine.start_hub)
        # Skip the 0th turn because all drones start at the hub natively
        if path and len(path) > 1:
            drone.path = path[1:]
        drones.append(drone)

    # 5. Terminal Output Loop (Required by Subject)
    turn_number = 0
    while any(len(d.path) > 0 for d in drones):
        turn_number += 1
        turn_moves = []
        
        for d in drones:
            if len(d.path) > 0:
                scheduled_turn, dest = d.get_next_destination()
                
                # Check if the drone is scheduled to do something on this exact turn
                if scheduled_turn == turn_number:
                    # If it's just "Strategically Waiting", don't print it.
                    # Only append to the output if it actually changes location.
                    if d.dr_loc != dest:
                        turn_moves.append(f"{d.dr_id}-{dest}")
                    
                    # Update drone location and pop the finished step
                    d.dr_loc = dest
                    d.path.pop(0)
        
        # Print all moves for this turn on a single line
        if turn_moves:
            print(" ".join(turn_moves))

    # 6. Launch the Graphical Visualizer
    if VISUALIZER_AVAILABLE:
        print(f"\n[Simulation Complete in {turn_number} turns. Opening Visualizer...]")
        gui = GUI_Visualizer(network, paths)

if __name__ == "__main__":
    main()