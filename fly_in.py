import sys
from pars import Parser , DroneNetwork , ParseError
from path_find import AStar

def main() -> None:
    """Parse a map passed on the command line."""
    if len(sys.argv) != 2:
        print(
            f"Usage: {sys.argv[0]} <map_file>",
            file=sys.stderr,
        )
        raise SystemExit(1)

    try:
        network = Parser(sys.argv[1]).parse()
        astar = AStar(network)
        path = astar.find_paths(astar.start_hub , astar.end_hub)
    except ParseError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    print(
        f"Path = {path}"
        f"\n"
        f"Parsed successfully: {network.nb_drones} drones, "
        f"{len(network.zones)} zones, "
        f"{len(network.connections)} connections."
    )


if __name__ == "__main__":
    main()
