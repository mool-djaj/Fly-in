"""Regression tests for the Fly-in pathfinding algorithm."""

from pathlib import Path
from typing import Optional

import pytest

from pars import Connection, DroneNetwork, Zone, parse_network
from path_find import AStar_Engine


def add_zone(
        network: DroneNetwork, name: str, zone_type: str = "normal",
        hub_role: Optional[str] = None) -> None:
    """Add a zone to an in-memory test network."""
    zone = Zone(name, 0, 0, 1, "none")
    zone.zone_type = zone_type
    zone.hub_role = hub_role
    network.zones[name] = zone


def connect(network: DroneNetwork, zone1: str, zone2: str) -> None:
    """Connect two zones in an in-memory test network."""
    network.connections.append(Connection(zone1, zone2))


def test_priority_never_beats_a_shorter_route() -> None:
    """Priority is a tie-breaker and must not increase the turn count."""
    network = DroneNetwork()
    network.nb_drones = 1
    add_zone(network, "start", hub_role="start_hub")
    add_zone(network, "end", hub_role="end_hub")

    for index in range(1, 11):
        add_zone(network, f"normal_{index}")
    for index in range(1, 12):
        add_zone(network, f"priority_{index}", zone_type="priority")

    connect(network, "start", "normal_1")
    for index in range(1, 10):
        connect(network, f"normal_{index}", f"normal_{index + 1}")
    connect(network, "normal_10", "end")

    connect(network, "start", "priority_1")
    for index in range(1, 11):
        connect(network, f"priority_{index}", f"priority_{index + 1}")
    connect(network, "priority_11", "end")

    path = AStar_Engine(network).route_all_drones()[0]

    assert path[-1][0] == 11
    assert path[1][1] == "normal_1"


def test_priority_wins_when_route_lengths_are_equal() -> None:
    """An equal-length route through a priority zone is preferred."""
    network = DroneNetwork()
    network.nb_drones = 1
    add_zone(network, "start", hub_role="start_hub")
    add_zone(network, "a_normal")
    add_zone(network, "z_priority", zone_type="priority")
    add_zone(network, "end", hub_role="end_hub")
    connect(network, "start", "a_normal")
    connect(network, "a_normal", "end")
    connect(network, "start", "z_priority")
    connect(network, "z_priority", "end")

    path = AStar_Engine(network).route_all_drones()[0]

    assert path[-1][0] == 2
    assert path[1][1] == "z_priority"


def test_unreachable_network_returns_cleanly() -> None:
    """An unreachable destination returns no routes instead of crashing."""
    network = DroneNetwork()
    network.nb_drones = 1
    add_zone(network, "start", hub_role="start_hub")
    add_zone(network, "blocked", zone_type="blocked")
    add_zone(network, "end", hub_role="end_hub")
    connect(network, "start", "blocked")
    connect(network, "blocked", "end")

    assert AStar_Engine(network).route_all_drones() == []


@pytest.mark.parametrize(
    ("map_path", "target"),
    [
        ("maps/easy/01_linear_path.txt", 6),
        ("maps/easy/02_simple_fork.txt", 8),
        ("maps/easy/03_basic_capacity.txt", 6),
        ("maps/medium/01_dead_end_trap.txt", 12),
        ("maps/medium/02_circular_loop.txt", 15),
        ("maps/medium/03_priority_puzzle.txt", 12),
        ("maps/hard/01_maze_nightmare.txt", 30),
        ("maps/hard/02_capacity_hell.txt", 35),
        ("maps/hard/03_ultimate_challenge.txt", 45),
    ],
)
def test_mandatory_map_benchmarks(map_path: str, target: int) -> None:
    """Mandatory maps remain within the subject's turn targets."""
    network = parse_network(str(Path(map_path)))
    engine = AStar_Engine(network)
    paths = engine.route_all_drones()

    assert len(paths) == network.nb_drones
    assert max(path[-1][0] for path in paths) <= target

    for name, turns in engine.zone_res.items():
        zone = network.zones[name]
        if zone.hub_role is None:
            assert all(count <= zone.max_drones for count in turns.values())

    for name, turns in engine.link_res.items():
        capacity = engine.link_capacity[name]
        assert all(count <= capacity for count in turns.values())
