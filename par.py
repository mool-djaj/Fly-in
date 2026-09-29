import re
import sys
from typing import NoReturn, Optional

import pyparsing as pp


class Zone:
    """A zone in the drone network."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        max_drones: int,
        color: str,
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.max_drones = max_drones
        self.color = color
        self.zone_type = "normal"
        self.hub_role: Optional[str] = None


class Connection:
    """An undirected connection between two zones."""

    def __init__(self, zone1: str, zone2: str) -> None:
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = 1


class DroneNetwork:
    """Parsed map containing zones, connections, and drone count."""

    def __init__(self) -> None:
        self.nb_drones = 0
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self.has_start_hub = False
        self.has_end_hub = False


def _die(message: str) -> NoReturn:
    """Print a parsing error and stop execution."""
    print(message, file=sys.stderr)
    raise SystemExit(1)


def _positive_capacity(value: str, line_num: int, label: str) -> int:
    """Parse a strict positive integer capacity."""
    if re.fullmatch(r"\+?\d+", value) is None:
        _die(
            f"Error: {label} must be a positive integer.\n"
            f"Cause: Found '{value}' on line {line_num}."
        )
    capacity = int(value)
    if capacity <= 0:
        _die(
            f"Error: {label} must be greater than 0.\n"
            f"Cause: Found '{value}' on line {line_num}."
        )
    return capacity


def _connection_exists(network: DroneNetwork, z1: str, z2: str) -> bool:
    """Return True if an undirected connection already exists."""
    for connection in network.connections:
        same_order = connection.zone1 == z1 and connection.zone2 == z2
        reverse_order = connection.zone1 == z2 and connection.zone2 == z1
        if same_order or reverse_order:
            return True
    return False


def parse_network(filepath: str) -> DroneNetwork:
    """Parse a Fly-in map file and return a validated network."""
    network = DroneNetwork()

    drone_integer = pp.Regex(r"[+-]*\d+").set_parse_action(
        lambda tokens: (
            (-1) ** tokens[0].count("-")
        ) * int(tokens[0].lstrip("+-"))
    )
    coordinate = pp.Regex(r"[+-]?\d+").set_parse_action(
        lambda tokens: int(tokens[0])
    )

    # A dash separates the two endpoints in a connection, and whitespace
    # separates map fields. Every other non-whitespace character is valid.
    name = pp.Regex(r"[^\s-]+")
    required_colon = pp.Suppress(":")
    attr_key = pp.Word(pp.alphas + "_")
    attr_value = pp.Regex(r"[^\s\[\]=]+")
    attr_pair = pp.Group(attr_key + pp.Suppress("=") + attr_value)
    attrs = pp.Dict(pp.ZeroOrMore(attr_pair))
    metadata = pp.Optional(
        pp.Suppress("[") + attrs("attrs") + pp.Suppress("]")
    )
    trailing_comment = pp.Optional(pp.Suppress(pp.Regex(r"#.*")))

    drones_rule = (
        pp.CaselessKeyword("nb_drones")
        + required_colon
        + drone_integer("count")
        + trailing_comment
    )
    connection_rule = (
        pp.CaselessKeyword("connection")
        + required_colon
        + name("z1")
        + pp.Suppress("-")
        + name("z2")
        + metadata
        + trailing_comment
    )
    zone_prefix = (
        pp.CaselessKeyword("start_hub")
        | pp.CaselessKeyword("end_hub")
        | pp.CaselessKeyword("hub")
    )
    zone_rule = (
        zone_prefix("keyword")
        + required_colon
        + name("name")
        + coordinate("x")
        + coordinate("y")
        + metadata
        + trailing_comment
    )
    valid_zone_types = {"normal", "blocked", "restricted", "priority"}

    try:
        with open(filepath, "r", encoding="utf-8") as map_file:
            lines = map_file.readlines()
    except OSError as error:
        _die(f"Error: Cannot open map file '{filepath}'.\nCause: {error}")

    first_content_seen = False

    for line_num, raw_line in enumerate(lines, start=1):
        clean_line = raw_line.strip()
        if not clean_line or clean_line.startswith("#"):
            continue

        lower_line = clean_line.lower()
        try:
            if not first_content_seen:
                first_content_seen = True
                if not lower_line.startswith("nb_drones"):
                    _die(
                        "Error: Drone count must be defined first.\n"
                        f"Cause: Line {line_num}: {raw_line.strip()}"
                    )

            if lower_line.startswith("nb_drones"):
                parsed = drones_rule.parse_string(clean_line, parse_all=True)
                if network.nb_drones != 0:
                    _die(
                        "Error: Duplicate drone configuration.\n"
                        f"Cause: Line {line_num}: {raw_line.strip()}"
                    )
                if parsed["count"] <= 0:
                    _die(
                        "Error: Drone count must be positive.\n"
                        f"Cause: Line {line_num}: {raw_line.strip()}"
                    )
                network.nb_drones = int(parsed["count"])
                continue

            if network.nb_drones == 0:
                _die(
                    "Error: Drones must be defined first.\n"
                    f"Cause: Line {line_num}: {raw_line.strip()}"
                )

            if lower_line.startswith("connection"):
                parsed = connection_rule.parse_string(
                    clean_line,
                    parse_all=True,
                )
                z1 = str(parsed["z1"])
                z2 = str(parsed["z2"])
                if z1 == z2:
                    _die(
                        "Error: A zone cannot connect to itself.\n"
                        f"Cause: '{z1}-{z2}' on line {line_num}."
                    )
                if z1 not in network.zones or z2 not in network.zones:
                    _die(
                        "Error: Connections may use only defined zones.\n"
                        f"Cause: '{z1}-{z2}' on line {line_num}."
                    )
                if _connection_exists(network, z1, z2):
                    _die(
                        "Error: Duplicate connection.\n"
                        f"Cause: '{z1}-{z2}' on line {line_num}."
                    )

                connection = Connection(z1, z2)
                connection_attrs = (
                    parsed["attrs"].as_dict() if "attrs" in parsed else {}
                )
                invalid = set(connection_attrs) - {"max_link_capacity"}
                if invalid:
                    key = sorted(invalid)[0]
                    _die(
                        f"Error: Invalid connection attribute '{key}'.\n"
                        f"Cause: Line {line_num}: {raw_line.strip()}"
                    )
                if "max_link_capacity" in connection_attrs:
                    connection.max_link_capacity = _positive_capacity(
                        str(connection_attrs["max_link_capacity"]),
                        line_num,
                        "Connection capacity",
                    )
                network.connections.append(connection)
                continue

            parsed = zone_rule.parse_string(clean_line, parse_all=True)
            keyword = str(parsed["keyword"]).lower()
            zone_name = str(parsed["name"])
            zone_attrs = parsed["attrs"].as_dict() if "attrs" in parsed else {}

            invalid = set(zone_attrs) - {"color", "max_drones", "zone"}
            if invalid:
                key = sorted(invalid)[0]
                _die(
                    f"Error: Invalid zone attribute '{key}'.\n"
                    f"Cause: Line {line_num}: {raw_line.strip()}"
                )
            if zone_name in network.zones:
                _die(
                    f"Error: Duplicate zone '{zone_name}'.\n"
                    f"Cause: Line {line_num}: {raw_line.strip()}"
                )

            is_start = keyword == "start_hub"
            is_end = keyword == "end_hub"
            if is_start or is_end:
                capacity = network.nb_drones
            else:
                capacity = _positive_capacity(
                    str(zone_attrs.get("max_drones", "1")),
                    line_num,
                    f"Zone '{zone_name}' capacity",
                )

            zone = Zone(
                zone_name,
                int(parsed["x"]),
                int(parsed["y"]),
                capacity,
                str(zone_attrs.get("color", "none")).lower(),
            )
            zone.zone_type = str(zone_attrs.get("zone", "normal")).lower()
            if zone.zone_type not in valid_zone_types:
                _die(
                    f"Error: Invalid zone type '{zone.zone_type}'.\n"
                    f"Cause: Line {line_num}: {raw_line.strip()}"
                )

            if is_start:
                if network.has_start_hub:
                    _die(
                        "Error: Multiple start hubs detected.\n"
                        f"Cause: Line {line_num}: {raw_line.strip()}"
                    )
                zone.hub_role = "start_hub"
                network.has_start_hub = True
            elif is_end:
                if network.has_end_hub:
                    _die(
                        "Error: Multiple end hubs detected.\n"
                        f"Cause: Line {line_num}: {raw_line.strip()}"
                    )
                zone.hub_role = "end_hub"
                network.has_end_hub = True

            network.zones[zone_name] = zone

        except pp.ParseBaseException as error:
            _die(
                "Error: Invalid syntax.\n"
                f"Cause: Line {line_num}: {raw_line.strip()} ({error})"
            )

    if network.nb_drones <= 0:
        _die("Error: Missing or invalid drone configuration.")
    if len(network.zones) < 2:
        _die("Error: Map must contain at least two zones.")
    if not network.has_start_hub or not network.has_end_hub:
        _die(
            "Error: Map must contain exactly one start_hub and one end_hub."
        )

    return network
