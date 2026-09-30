import sys

from pars import Parser
from path_find import AStar
from simulator import Simulator


class FlyIn:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def run(self) -> None:
        network = Parser(self.filename).parse()

        astar = AStar(network)

        paths = astar.find_paths(
            astar.start_hub,
            astar.end_hub,
        )

        simulator = Simulator(network, paths)

        simulator.plan_drones()

        self._print_turns(simulator)

    def _print_turns(self, simulator: Simulator) -> None:
        max_turn = 0

        for drone in simulator.drones:
            if drone.schedule:
                max_turn = max(
                    max_turn,
                    drone.schedule[-1][0],
                )

        for turn in range(1, max_turn + 1):
            moves: list[str] = []

            for drone in simulator.drones:
                if turn >= len(drone.schedule):
                    continue

                current = drone.schedule[turn][1]
                previous = drone.schedule[turn - 1][1]

                if current == previous:
                    continue

                moves.append(
                    f"{drone.id}-{current}"
                )

            print(" ".join(moves))


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <map_file>")
        raise SystemExit(1)

    app = FlyIn(sys.argv[1])
    app.run()


if __name__ == "__main__":
    main()