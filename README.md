# Fly-in

## Description

Fly-in is a drone-routing simulator that finds collision-free paths through a
network of connected zones. It uses a custom space-time A* search: a search
state is not only a zone, but a `(zone, turn)` pair. This lets a drone wait in
place when traffic or capacity constraints temporarily block its route.

The program supports:

- multiple drones moving simultaneously;
- normal, restricted, priority, and blocked zones;
- per-zone `max_drones` capacities;
- per-connection `max_link_capacity` capacities;
- two-turn travel into restricted zones;
- unlimited sharing of the start and end hubs;
- comments beginning with `#`;
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

The normal command prints only the required turn-by-turn simulation output to
standard output. Errors are printed to standard error.

Launch the same simulation with the graphical visualizer:

```bash
python3 fly_in.py path/to/map.txt
```

or:

```bash
make run
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

### 2. Space-time states

A state is represented by both a physical zone and a simulation turn:

```text
(zone, turn)
```

This allows the same physical zone to be considered again at a later time.
Waiting is therefore a normal A* transition instead of a special case outside
the search.

### 3. Reservation tables

Already planned drones reserve future capacity in two dictionaries:

```python
zone_res[zone][turn] -> number of drones
link_res[connection][turn] -> number of drones
```

A new path is accepted only when its zone and connection use stays within the
configured capacities.

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
hub. The result stores the traffic-free minimum movement cost from every zone
to the destination. A* then uses:

```text
f = g + h
```

where `g` is the path cost already spent and `h` is the precomputed remaining
cost.

### 6. Multi-drone planning

Drones are planned one at a time. After one drone receives a valid path, that
path is written into the reservation tables. The next drone performs A* while
respecting those reservations. Small start delays are also considered when
necessary.

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

The existing custom sign handling for the `nb_drones` numeric field is kept in
this project. Coordinate and capacity parsing remains strict.

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
- `F`: toggle fullscreen;
- mouse drag: pan;
- mouse wheel: zoom.

The visualizer is optional so automated evaluation can run the mandatory CLI
without opening a window.

## Project files

- `fly_in.py`: CLI and mandatory simulation output;
- `pars.py`: parser and network data model;
- `path_find.py`: custom space-time A* routing engine;
- `gui_controls.py`: visualizer camera/theme/coordinate helpers;
- `visualizer.py`: optional Pygame visualizer;
- `Makefile`: install, run, visual, test, lint, clean, and re targets;
- `requirements.txt`: Python dependencies.



"
Parser

  |

  v

DroneNetwork

  |

  v

AStar

finds paths

  |

  v

Drone

stores its assigned path

  |

  v

Simulator

moves drones turn by turn

and checks capacities

"