import sys
from pars import Pars
from path_find import BFS_Engine, Drone

def main():
    # 1. Check for the map file argument
    if len(sys.argv) != 2:
        print("Usage: python3 fly_in.py <map_file>")
        sys.exit(1)

    map_file = sys.argv[1]

    # 2. Parse the map file into a network object
    # This uses your Pars.parse_config method
    network = Pars.parse_config(map_file) #

    # 3. Initialize the Engine and calculate the shortest paths
    # We use the simple BFS logic for now
    engine = BFS_Engine(network) #
    
    # We need a list to store our active Drone objects
    drones = []
    
    # 4. Create Drone objects and assign their paths
    for i in range(network.nb_drones):
        # Create a drone starting at the hub
        new_drone = Drone(i + 1, engine.start_hub) #
        
        # Calculate the path for this drone
        # Note: shortest_path returns ['hub', 'roof1', 'goal']
        full_path = engine.shortest_path(engine.start_hub, engine.end_hub)
        engine.book_path(full_path)
        # We skip the first element ('hub') because they start there.
        # Their first move should be to the next room.
        new_drone.path = full_path[1:] 
        
        drones.append(new_drone)

    # 5. The Simulation Loop (Turn-by-Turn)
    # This keeps running as long as any drone still has steps to take
    i = 0
    while any(len(d.path) > 0 for d in drones):
        turn_moves = []
        i += 1
        for d in drones:
            if len(d.path) > 0:
                # Peek at the next destination
                dest = d.get_next_destination() #
                
                # Move the drone
                turn_moves.append(f"{d.dr_id}-{dest}")
                    
                d.dr_loc = dest
                     
                
                # Record the move in the required format: D1-room                
                # Remove the step from the drone's path
                d.path.pop(0)
        
        # Print all moves for this turn on a single line
        if turn_moves:
            print(" ".join(turn_moves))
    print(f"turns:{i}")

if __name__ == "__main__":
    main()