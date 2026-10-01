import sys
from pars import Parser
from path_find import AStar
from simulator import Simulator
from visualizer import Visualizer


class FlyIn:

    def __init__(self, filename: str) -> None:
        self.filename = filename

    def run(self) -> None:
        network = Parser(self.filename).parse()
        astar = AStar(network)

        paths = astar.find_paths(astar.start_hub, astar.end_hub)
        if not paths:
            raise RuntimeError("No path exists between start and end.")

        simulator = Simulator(network, paths)
        drones = simulator.plan_drones()

        self._print_moves(simulator)
        sys.stdout.flush()

        Visualizer(network, drones).run()

    def _print_moves(self, simulator: Simulator) -> None:
        schedules = {
            drone.id: dict(drone.schedule)
            for drone in simulator.drones
        }
        max_turn = max(
            (drone.schedule[-1][0]
             for drone in simulator.drones if drone.schedule),
            default=0,
        )

        for turn in range(1, max_turn + 1):
            moves: list[str] = []
            for drone in simulator.drones:
                previous = schedules[drone.id].get(turn - 1)
                current = schedules[drone.id].get(turn)
                if current is not None and previous != current:
                    moves.append(f"{drone.id}-{current}")
            print(" ".join(moves))


def main() -> None:
    if len(sys.argv) != 2:
        print(
            f"Usage: {sys.argv[0]} <map_file>",
            file=sys.stderr,
        )
        raise SystemExit(1)

    try:
        FlyIn(sys.argv[1]).run()
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
