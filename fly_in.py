import sys

from pars import Parser
from path_find import AStar
from simulator import Simulator


class FlyIn:

    def __init__(self, filename: str, visual: bool = False) -> None:
        """Store the input filename and optional visual-mode flag."""
        self.filename = filename
        self.visual = visual

    def run(self) -> None:
        """Parse, find paths, plan drones, and display the result."""
        network = Parser(self.filename).parse()
        astar = AStar(network)

        paths = astar.find_paths(
            astar.start_hub,
            astar.end_hub,
        )

        if not paths:
            raise RuntimeError("No path exists between start and end.")

        simulator = Simulator(network, paths)
        simulator.plan_drones()

        self._print_moves(simulator)
        sys.stdout.flush()

        if not self.visual:
            return

        try:
            from visualizer import Visualizer
            visualizer = Visualizer(network, simulator.drones)
            visualizer.run()
        except ImportError as error:
            raise RuntimeError(
                f"Visualization unavailable: {error}"
            ) from error

    def _print_moves(self, simulator: Simulator) -> None:
        """Print drone movements turn by turn."""
        if not simulator.drones:
            return

        max_turn = max(
            (
                drone.schedule[-1][0]
                for drone in simulator.drones
                if drone.schedule
            ),
            default=0,
        )
        schedules = {
            drone.id: dict(drone.schedule)
            for drone in simulator.drones
        }

        for turn in range(1, max_turn + 1):
            moves: list[str] = []
            for drone in simulator.drones:
                current = schedules[drone.id].get(turn)
                previous = schedules[drone.id].get(turn - 1)
                if current is None or previous is None:
                    continue

                if current != previous:
                    moves.append(f"{drone.id}-{current}")

            print(" ".join(moves))


def main() -> None:
    """Start the Fly-in program."""
    if len(sys.argv) not in (2, 3) or (
        len(sys.argv) == 3 and sys.argv[2] != "--visual"
    ):
        print(
            f"Usage: {sys.argv[0]} <map_file> [--visual]",
            file=sys.stderr,
        )
        raise SystemExit(1)

    try:
        app = FlyIn(sys.argv[1], visual="--visual" in sys.argv[2:])
        app.run()
    except KeyboardInterrupt:
        raise SystemExit(0)
    except Exception as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
