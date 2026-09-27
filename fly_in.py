import sys

from pars import DroneNetwork, parse_network
from path_find import AStar_Engine, PathLog
from visualizer import GUI_Visualizer


def simulation_lines(paths: list[PathLog]) -> list[str]:
    """Convert paths to the required turn-by-turn output."""
    if not paths:
        return []

    max_turn = max(path[-1][0] for path in paths if path)
    lines: list[str] = []

    for turn in range(1, max_turn + 1):
        moves: list[str] = []
        for drone_id, path in enumerate(paths, start=1):
            states = {time: location for time, location in path}
            if turn not in states:
                continue

            current = states[turn]
            previous = states.get(turn - 1)
            if previous is None:
                earlier = [state for state in path if state[0] < turn]
                if earlier:
                    previous = earlier[-1][1]

            if previous is not None and current == previous:
                continue
            if turn == path[0][0] and current == path[0][1]:
                continue

            moves.append(f"D{drone_id}-{current}")

        lines.append(" ".join(moves))

    return lines


def print_simulation(paths: list[PathLog]) -> None:
    """Print the required simulation output."""
    for line in simulation_lines(paths):
        print(line)


def launch_visualizer(network: DroneNetwork, paths: list[PathLog]) -> None:
    """Open the graphical Fly-in visualizer."""
    try:
        GUI_Visualizer(network, paths)
    except KeyboardInterrupt:
        print("\nVisualizer closed by user.")


def main() -> None:
    """Parse the map, calculate paths, print them, and open the GUI."""
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <map_file>", file=sys.stderr)
        raise SystemExit(1)

    network = parse_network(sys.argv[1])
    paths = AStar_Engine(network).route_all_drones()

    if not paths:
        print(
            "Error: No valid route connects start_hub to end_hub.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print_simulation(paths)
    launch_visualizer(network, paths)


if __name__ == "__main__":
    main()
