*This project has been created as part of the 42 curriculum by akaarich.*

# Fly-in

## Description

Fly-in is a drone-routing simulator that finds collision-free paths through a
network of connected zones. A custom A* implementation finds a minimum-cost
route and several alternatives, then a reservation-based scheduler selects the
earliest valid route for each drone.

The program supports:

- multiple drones moving simultaneously;
- normal, restricted, priority, and blocked zones;
- per-zone `max_drones` capacities;
- per-connection `max_link_capacity` capacities;
- two-turn travel into restricted zones;
- unlimited sharing of the start and end hubs;
- comment lines beginning with `#`;
- an optional Pygame visualizer.

## Instructions

Install the dependencies:

```bash
make install
```

Run the mandatory command-line simulation:

```bash
python3 fly_in.py path/to/map.txt
```

or, with the included sample map:

```bash
make run
```

The command prints the required turn-by-turn simulation output to
standard output. Errors are printed to standard error.
simulation with the graphical visualizer:

```bash
python3 fly_in.py path/to/map.txt
```

Check style and typing:

```bash
make lint
```

## Algorithm explanation

### 1. Graph representation

The parser creates a custom adjacency-list graph:

```python
self.graph: dict[str, list[str]]
```

Each zone name maps to the directly connected zones. No graph/pathfinding
library is used.

### 2. Alternative routes

After A* finds the minimum-cost route, the pathfinder temporarily removes each
edge of that route and searches again. Unique successful results become route
alternatives. This gives the scheduler multiple options without importing a
forbidden graph library.

### 3. Reservation tables

The scheduler plans drones one at a time. Already planned drones reserve future
capacity in two dictionaries:

```python
zone_res[zone][turn] -> number of drones
link_res[connection][turn] -> number of drones
```

A candidate path is accepted only when its zone and connection use stays within
the configured capacities. When a conflict is temporary, the scheduler inserts
wait turns before the move.

### 4. Movement costs

The physical movement costs are:

- `normal`: 1 turn;
- `priority`: 1 turn;
- `restricted`: 2 turns;
- `blocked`: inaccessible.

Priority zones do **not** receive a fake lower movement time. Instead, priority
is used as an A* tie-breaker when routes have the same total `f = g + h` score.
This preserves the required one-turn movement while preferring priority zones.

Restricted movement is represented by an intermediate connection state. If a
drone starts crossing at turn `t`, it occupies the connection at `t + 1` and
must reach the restricted destination at `t + 2`.

### 5. Heuristic

Before routing drones, the program runs a reverse Dijkstra pass from the end
hub. The result stores the exact traffic-free minimum movement cost from every
zone to the destination. A* then uses:

```text
f = g + h
```

where `g` is the path cost already spent and `h` is the precomputed remaining
cost.

### 6. Multi-drone planning and complexity

Drones are planned one at a time. Each candidate route is simulated against
the reservation tables, and the route with the earliest arrival is committed.
The next drone sees those reservations, so it can use another route or wait.

The reverse Dijkstra heuristic is computed once in `O((V + E) log V)`. One A*
search is also `O((V + E) log V)` with a binary heap. If the first route has
`L` links, at most `L` additional A* searches are run. The scheduler then tests
each discovered route for every drone and stores reservations only for turns
that are actually used.

## Parser behavior

The parser validates:

- one `nb_drones:` declaration before zones/connections;
- exactly one `start_hub` and one `end_hub`;
- unique zone names;
- unique undirected connections;
- connections referencing only zones already defined;
- valid zone types;
- positive zone and connection capacities;
- valid integer coordinates;
- valid metadata keys.

Coordinates accept signed integers; drone counts and capacities require strict
positive integers.

## Simulation output

Each printed line represents one simulation turn. Only drones that move during
that turn are shown. A normal move is printed as:

```text
D<ID>-<zone>
```

A drone crossing toward a restricted zone is printed using the connection
state during the transit turn.

Drones that wait are omitted from that turn's line, and drones disappear from
tracking after reaching the end hub.

## Example input

```text
nb_drones: 2

start_hub: start 0 0 [color=green]
end_hub: goal 3 0 [color=gold]
hub: a 1 0 [color=blue]
hub: b 2 0 [color=blue]

connection: start-a
connection: a-b
connection: b-goal
```

## Expected output

One valid output for the map above is:

```text
D1-a
D1-b D2-a
D1-goal D2-b
D2-goal
```

## Visual representation

The optional Pygame visualizer displays the network, configured zone colors,
drone IDs, current turn, and animated drone movement. Controls include:

- `Space`: play/pause;
- left/right arrows: step through turns;
- `R`: restart;
- `1`, `2`, `3`: change theme;
- `F`: enter or leave fullscreen;
- `Esc`: return to windowed mode.

The camera automatically fits the complete map in the window. Regular zone
names use short labels on dense maps, while the start and end hubs keep clear
foreground labels. The visualizer intentionally uses keyboard controls only;
there is no mouse dragging, zooming, or hover logic.

The visualizer is optional so automated evaluation can run the mandatory CLI
without opening a window.

## Project files

- `fly_in.py`: CLI and mandatory simulation output;
- `pars.py`: parser and network data model;
- `path_find.py`: custom A* routing and alternative-path generation;
- `simulator.py`: capacity-aware turn scheduler and reservation tables;
- `drone.py`: planned drone data model;
- `visualizer.py`: optional Pygame visualizer;
- `Makefile`: install, run, visual, test, lint, clean, and re targets;
- `requirements.txt`: Python dependencies.

## Resources

- [Python `heapq` documentation](https://docs.python.org/3/library/heapq.html)
  for priority-queue operations;
- [A* search algorithm](https://en.wikipedia.org/wiki/A*_search_algorithm) for
  shortest-path concepts and admissible heuristics;
- [Dijkstra's algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
  for the reverse distance heuristic;
- [pyparsing documentation](https://pyparsing-docs.readthedocs.io/) for the map
  grammar;
- [Pygame documentation](https://www.pygame.org/docs/) for rendering, input,
  and window management.

AI assistance was used to compare the project with the subject, inspect output
and routing edge cases.
