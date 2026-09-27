"""Regression tests for the Fly-in map parser."""

from pathlib import Path

import pytest

from pars import DroneNetwork, parse_network


def parse_map(tmp_path: Path, source: str) -> DroneNetwork:
    """Write and parse a temporary map."""
    map_path = tmp_path / "test.map"
    map_path.write_text(source)
    return parse_network(str(map_path))


def test_colors_are_visual_only(tmp_path: Path) -> None:
    """Colors must not change hub roles or zone types."""
    network = parse_map(
        tmp_path,
        """nb_drones: 2
start_hub: start 0 0 [color=red]
hub: green_room 1 0 [color=green]
hub: red:room 2 0 [color=red]
hub: yellow=room 3 0 [color=yellow]
hub: black.room 4 0 [color=black]
hub: gold_room 5 0 [color=gold]
end_hub: end 6 0 [color=green]
connection: start-green_room
connection: green_room-red:room
connection: red:room-yellow=room
connection: yellow=room-black.room
connection: black.room-gold_room
connection: gold_room-end
""",
    )

    assert network.zones["start"].hub_role == "start_hub"
    assert network.zones["end"].hub_role == "end_hub"
    for name in (
        "green_room",
        "red:room",
        "yellow=room",
        "black.room",
        "gold_room",
    ):
        assert network.zones[name].hub_role is None
        assert network.zones[name].zone_type == "normal"


def test_explicit_zone_type_controls_movement_type(tmp_path: Path) -> None:
    """Only zone metadata should select a non-normal zone type."""
    network = parse_map(
        tmp_path,
        """nb_drones: 1
start_hub: start 0 0
hub: danger 1 0 [zone=restricted color=blue]
hub: obstacle 2 0 [zone=blocked color=pink]
hub: preferred 3 0 [zone=priority color=gray]
end_hub: end 4 0
connection: start-danger
connection: danger-obstacle
connection: obstacle-preferred
connection: preferred-end
""",
    )

    assert network.zones["danger"].zone_type == "restricted"
    assert network.zones["obstacle"].zone_type == "blocked"
    assert network.zones["preferred"].zone_type == "priority"


@pytest.mark.parametrize(
    "source",
    [
        """nb_drones: 1
start_hub start 0 0
end_hub: end 1 0
connection: start-end
""",
        """nb_drones: 1
start_hub: start 0 0
end_hub: end 1 0
connection start-end
""",
        """nb_drones: 1
start_hub: start 0 0
zone: middle 1 0
end_hub: end 2 0
connection: start-middle
connection: middle-end
""",
        """nb_drones: 1
start_hub: start 0 0
end_hub: end 1 0
link: start-end
""",
    ],
)
def test_invalid_zone_and_connection_syntax_is_rejected(
        tmp_path: Path, source: str) -> None:
    """Zone and connection keywords require the subject syntax."""
    with pytest.raises(SystemExit):
        parse_map(tmp_path, source)


def test_drone_number_sign_behavior_is_unchanged(tmp_path: Path) -> None:
    """Keep the existing drone-count behavior outside this fix's scope."""
    network = parse_map(
        tmp_path,
        """nb_drones: --2
start_hub: start 0 0
end_hub: end 1 0
connection: start-end
""",
    )

    assert network.nb_drones == 2
