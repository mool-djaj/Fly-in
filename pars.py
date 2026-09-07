from typing import Any, TypedDict
import pyparsing as pp


class ZoneData(TypedDict):

    hub_role: str
    x: int
    y: int
    zone_type: str
    max_drones: int
    color: str


class ConnectionData(TypedDict):

    zone1: str
    zone2: str
    max_link_capacity: int


class Zone:
    """Represents a zone in the drone network.

    Attributes:
        name (str): The unique name of the zone (no dashes or spaces allowed).
        hub_role (str): The role of the hub ('start_hub', 'end_hub', or 'hub').
        x (int): The X coordinate.
        y (int): The Y coordinate.
        zone_type (str): Type of zone
        ('normal', 'blocked', 'restricted', 'priority').
        max_drones (int): The maximum number of drones this zone can hold.
        color (str): Optional color metadata for visualizers.
        current_drones (int):
        Tracks the number of drones currently in the zone.
    """

    def __init__(self, name: str, data: ZoneData) -> None:
        """Initialize a zone with its parsed data payload."""
        self.name: str = name
        self.hub_role: str = data["hub_role"]
        self.x: int = data["x"]
        self.y: int = data["y"]
        self.zone_type: str = data["zone_type"]
        self.max_drones: int = data["max_drones"]
        self.color: str = data["color"]
        self.current_drones: int = 0


class Connection:
    """Represents a connection between two zones.

    Attributes:
        zone1 (str): Name of the first connected zone.
        zone2 (str): Name of the second connected zone.
        max_link_capacity (int):
        Max drones that can traverse this link simultaneously.
        current_traffic (int): Tracks active traffic on the link.
    """

    def __init__(self, data: ConnectionData) -> None:
        """Initialize a connection with its parsed data payload."""
        self.zone1: str = data["zone1"]
        self.zone2: str = data["zone2"]
        self.max_link_capacity: int = data["max_link_capacity"]
        self.current_traffic: int = 0


class DroneNetwork:
    """Container for parsed zones and connections.

    Attributes:
        nb_drones (int): Total number of drones in the simulation.
        zones (dict[str, Zone]): Dictionary mapping zone names to Zone objects.
        connections (list[Connection]): List of all valid network connections.
    """

    def __init__(self) -> None:
        """Initialize an empty drone network."""
        self.nb_drones: int = 0
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []

    def add_zone(self, zone: Zone) -> None:
        """Add a parsed zone to the network."""
        self.zones[zone.name] = zone

    def add_connection(self, connection: Connection) -> None:
        """Add a parsed connection to the network."""
        self.connections.append(connection)


class Pars:
    """Parse a map file into a :class:`DroneNetwork` using strict pyparsing."""

    _safe_name_chars = "".join(c for c in pp.printables if c not in "-[]")
    _safe_val_chars = "".join(c for c in pp.printables if c not in "]")
    _integer = (
        pp.Combine(pp.Optional("-") + pp.Word(pp.nums))
        .set_parse_action(lambda t: int(t[0]))
    )
    _name = pp.Word(_safe_name_chars)
    _meta_key = pp.Word(pp.alphanums + "_")
    _meta_value = pp.Word(_safe_val_chars)
    _meta_pair = pp.Group(_meta_key + pp.Suppress("=") + _meta_value)
    _metadata = (
        pp.Suppress("[") + pp.Dict(pp.ZeroOrMore(_meta_pair))("meta") +
        pp.Suppress("]")
        )
    _nb_drones_rule = (
        pp.CaselessKeyword("nb_drones") +
        pp.Suppress(":") + _integer("count")
        )

    _zone_rule = (
        pp.Word(pp.alphanums + "_")("role")
        + pp.Suppress(":")
        + _name("name")
        + _integer("x")
        + _integer("y")
        + pp.Optional(_metadata)
    )

    _conn_rule = (
        pp.CaselessKeyword("connection")
        + pp.Suppress(":")
        + _name("z1")
        + pp.Suppress("-")
        + _name("z2")
        + pp.Optional(_metadata)
    )

    @staticmethod
    def parse_config(filename: str) -> DroneNetwork:
        """Parse a map file into a network structure using pyparsing.

        Args:
            filename (str): Path to the map configuration file.

        Returns:
            DroneNetwork: Parsed network data structure.

        Raises:
            ValueError: If the file content violates grammar or constraints.
            FileNotFoundError: If the file does not exist.
            OSError: If the file cannot be opened.
        """
        parsed_data = DroneNetwork()
        nb_drones_seen = False
        start_seen = False
        end_seen = False

        with open(filename, "r", encoding="utf-8") as file_handle:
            for line_num, raw_line in enumerate(file_handle, start=1):
                line = raw_line.strip()
                if "#" in line:
                    line = line.split("#", 1)[0].strip()

                if not line:
                    continue

                try:
                    if line.lower().startswith("nb_drones:"):
                        result = (
                            Pars._nb_drones_rule
                            .parse_string(line, parse_all=True)
                            )
                        if result.count < 0:
                            raise ValueError(
                                f"Line {line_num}"
                                ":nb_drones must be a positive integer."
                                )
                        parsed_data.nb_drones = result.count
                        nb_drones_seen = True
                        continue

                    if not nb_drones_seen:
                        raise ValueError(
                            f"Line {line_num}:"
                            " nb_drones must be at the top of the map.")

                    if line.lower().startswith("connection:"):
                        result = (
                            Pars._conn_rule
                            .parse_string(line, parse_all=True)
                            )
                        parsed_data.add_connection(
                            Pars._build_connection(
                                line_num, result, parsed_data
                                )
                        )
                        continue

                    if ":" in line:
                        result = (
                            Pars._zone_rule
                            .parse_string(line, parse_all=True)
                            )

                        role = result.role.lower()
                        if role not in {"start_hub", "end_hub", "hub"}:
                            raise ValueError(
                                f"Line {line_num}"
                                ": Unknown prefix '{role}'."
                                )

                        if role == "start_hub":
                            if start_seen:
                                raise ValueError(
                                    f"Line {line_num}"
                                    ": Multiple 'start_hub' zones defined."
                                    )
                            start_seen = True
                        elif role == "end_hub":
                            if end_seen:
                                raise ValueError(
                                    f"Line {line_num}"
                                    ": Multiple 'end_hub' zones defined."
                                    )
                            end_seen = True

                        parsed_data.add_zone(
                            Pars._build_zone(line_num, result, parsed_data)
                            )
                        continue

                    raise ValueError(
                        f"Line {line_num}"
                        ": Invalid format, missing ':'."
                        )

                except pp.ParseException as error:
                    raise ValueError(
                        f"Line {line_num}"
                        ": Syntax error -> "
                        "{error.msg}\nContent: '{line}'"
                        ) from error

        if not start_seen:
            raise ValueError("Map is missing a 'start_hub'.")
        if not end_seen:
            raise ValueError("Map is missing an 'end_hub'.")

        return parsed_data

    @staticmethod
    def _build_zone(
        line_num: int,
        result: Any,
        parsed_data: DroneNetwork
    ) -> Zone:
        """Map pyparsing results safely into a Zone object.

        Args:
            line_num (int)
            : Current line number for error tracking.
            result (Any): The ParseResults object from pyparsing.
            parsed_data (DroneNetwork)
            : The network object to validate duplicates against.

        Returns:
            Zone: A constructed Zone object.
        """
        name = result.name
        if name in parsed_data.zones:
            raise ValueError(f"Line {line_num}: Duplicate zone name '{name}'.")

        meta = result.meta.as_dict() if "meta" in result else {}

        zone_type = meta.get("zone", "normal")
        if zone_type not in {"normal", "blocked", "restricted", "priority"}:
            raise ValueError(
                f"Line {line_num}"
                ": Invalid zone type '{zone_type}'."
                )

        default_capacity = (
            999 if result.role in {"start_hub", "end_hub"} else 1
            )

        try:
            max_drones = int(meta.get("max_drones", default_capacity))
        except ValueError as error:
            raise ValueError(
                f"Line {line_num}"
                ": max_drones must be an integer."
                ) from error

        if max_drones <= 0:
            raise ValueError(
                f"Line {line_num}"
                ": max_drones must be a positive integer."
                )

        data_zone: ZoneData = {
            "hub_role": result.role,
            "x": result.x,
            "y": result.y,
            "zone_type": zone_type,
            "color": meta.get("color", "none"),
            "max_drones": max_drones,
        }
        return Zone(name, data_zone)

    @staticmethod
    def _build_connection(
        line_num: int,
        result: Any,
        parsed_data: DroneNetwork
    ) -> Connection:
        """Map pyparsing results safely into a Connection object.

        Args:
            line_num (int): Current line number for error tracking.
            result (Any): The ParseResults object from pyparsing.
            parsed_data (DroneNetwork):
            The network object to validate unknown zones against.

        Returns:
            Connection: A constructed Connection object.
        """
        z1, z2 = result.z1, result.z2

        if z1 not in parsed_data.zones or z2 not in parsed_data.zones:
            raise ValueError(
                f"Line {line_num}"
                ": Connection references unknown zone(s)."
                )

        if z1 == z2:
            raise ValueError(
                f"Line {line_num}"
                ": A zone cannot connect to itself '{z1}-{z2}'."
                )

        for existing in parsed_data.connections:
            if {existing.zone1, existing.zone2} == {z1, z2}:
                raise ValueError(
                    f"Line {line_num}"
                    ": Duplicate connection detected '{z1}-{z2}'."
                    )

        meta = result.meta.as_dict() if "meta" in result else {}

        try:
            link_capacity = int(meta.get("max_link_capacity", 1))
        except ValueError as error:
            raise ValueError(
                f"Line {line_num}"
                ": max_link_capacity must be an integer."
                ) from error

        if link_capacity <= 0:
            raise ValueError(
                f"Line {line_num}"
                ": max_link_capacity must be a positive integer."
                )

        data_conn: ConnectionData = {
            "zone1": z1,
            "zone2": z2,
            "max_link_capacity": link_capacity,
        }
        return Connection(data_conn)
