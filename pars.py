from typing import TypedDict


class ZoneData(TypedDict):
    """Typed payload used to construct a zone."""

    hub_role: str
    x: int
    y: int
    zone_type: str
    max_drones: int
    color: str


class ConnectionData(TypedDict):
    """Typed payload used to construct a connection."""

    zone1: str
    zone2: str
    max_link_capacity: int


class Zone:
    """Represents a zone in the drone network."""

    def __init__(self, name: str, data: ZoneData) -> None:
        self.name: str = name
        self.hub_role: str = data["hub_role"]
        self.x: int = data["x"]
        self.y: int = data["y"]
        self.zone_type: str = data["zone_type"]
        self.max_drones: int = data["max_drones"]
        self.color: str = data["color"]
        self.current_drones: int = 0


class Connection:
    """Represents a connection between two zones."""

    def __init__(self, data: ConnectionData) -> None:
        self.zone1: str = data["zone1"]
        self.zone2: str = data["zone2"]
        self.max_link_capacity: int = data["max_link_capacity"]
        self.current_traffic: int = 0


class DroneNetwork:
    """Container for parsed zones and connections."""

    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the network."""

        self.zones[zone.name] = zone

    def add_connection(self, connection: Connection) -> None:
        """Add a connection to the network."""

        self.connections.append(connection)


class Pars:
    """Parse a map file into a :class:`DroneNetwork`."""

    @staticmethod
    def parse_config(filename: str) -> DroneNetwork:
        """Parse a map file into a network structure.

        Args:
            filename: Path to the map configuration file.

        Returns:
            Parsed network data.

        Raises:
            ValueError: If the file content is invalid.
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
                if not line or line.startswith("#"):
                    continue

                if ":" not in line:
                    raise ValueError(f"Line {line_num}: Invalid format, missing ':'.")

                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()

                if key == "nb_drones":
                    try:
                        drone_count = int(value)
                    except ValueError as error:
                        raise ValueError(
                            f"Line {line_num}: nb_drones must be an integer."
                        ) from error

                    if drone_count < 0:
                        raise ValueError(
                            f"Line {line_num}: nb_drones must be a positive integer."
                        )

                    parsed_data.nb_drones = drone_count
                    nb_drones_seen = True
                    continue

                if not nb_drones_seen:
                    raise ValueError(
                        f"Line {line_num}: nb_drones must be at the top of the map."
                    )

                if key in {"start_hub", "end_hub", "hub"}:
                    zone = Pars._parse_zone_line(line_num, key, value, parsed_data)
                    if key == "start_hub":
                        if start_seen:
                            raise ValueError(
                                f"Line {line_num}: Multiple 'start_hub' zones defined."
                            )
                        start_seen = True
                    elif key == "end_hub":
                        if end_seen:
                            raise ValueError(
                                f"Line {line_num}: Multiple 'end_hub' zones defined."
                            )
                        end_seen = True

                    parsed_data.add_zone(zone)
                    continue

                if key == "connection":
                    parsed_data.add_connection(
                        Pars._parse_connection_line(line_num, value, parsed_data)
                    )
                    continue

                raise ValueError(f"Line {line_num}: Unknown prefix '{key}'.")

        if not start_seen:
            raise ValueError("ther is no start_hub :(")
        if not end_seen:
            raise ValueError("ther is no end_hub :(")

        return parsed_data

    @staticmethod
    def _split_core_and_metadata(line_num: int, value: str) -> tuple[str, str]:
        """Split a config value into core text and optional metadata."""

        core_str = value
        meta_str = ""
        if "[" in value and "]" in value:
            parts = value.split("[", 1)
            core_str = parts[0].strip()
            meta_str = parts[1].replace("]", "").strip()
        elif "[" in value or "]" in value:
            raise ValueError(f"Line {line_num}: Mismatched brackets in metadata.")

        return core_str, meta_str

    @staticmethod
    def _parse_metadata(line_num: int, meta_str: str) -> dict[str, str]:
        """Parse metadata key/value pairs from a bracketed segment."""

        metadata: dict[str, str] = {}
        if not meta_str:
            return metadata

        for pair in meta_str.split():
            if "=" not in pair:
                raise ValueError(f"Line {line_num}: Invalid metadata format '{pair}'.")
            key, value = pair.split("=", 1)
            metadata[key] = value

        return metadata

    @staticmethod
    def _parse_zone_line(
        line_num: int,
        role: str,
        value: str,
        parsed_data: DroneNetwork,
    ) -> Zone:
        """Parse a zone line into a Zone object."""

        core_str, meta_str = Pars._split_core_and_metadata(line_num, value)
        core_parts = core_str.split()
        if len(core_parts) != 3:
            raise ValueError(
                f"Line {line_num}: Invalid hub format. Expected '<name> <x> <y>'."
            )

        name = core_parts[0]
        if "-" in name:
            raise ValueError(f"Line {line_num}: Zone names cannot contain '-'.")

        if name in parsed_data.zones:
            raise ValueError(f"Line {line_num}: Duplicate zone name '{name}'.")

        try:
            x = int(core_parts[1])
            y = int(core_parts[2])
        except ValueError as error:
            raise ValueError(
                f"Line {line_num}: Coordinates must be integers."
            ) from error

        metadata = Pars._parse_metadata(line_num, meta_str)
        zone_type = metadata.get("zone", "normal")
        if zone_type not in {"normal", "blocked", "restricted", "priority"}:
            raise ValueError(f"Line {line_num}: Invalid zone type '{zone_type}'.")

        default_capacity = 999 if role in {"start_hub", "end_hub"} else 1
        try:
            max_drones = int(metadata.get("max_drones", str(default_capacity)))
        except ValueError as error:
            raise ValueError(
                f"Line {line_num}: max_drones must be a positive integer."
            ) from error

        if max_drones <= 0:
            raise ValueError(f"Line {line_num}: max_drones must be a positive integer.")

        data_zone: ZoneData = {
            "hub_role": role,
            "x": x,
            "y": y,
            "zone_type": zone_type,
            "color": metadata.get("color", "none"),
            "max_drones": max_drones,
        }
        return Zone(name, data_zone)

    @staticmethod
    def _parse_connection_line(
        line_num: int,
        value: str,
        parsed_data: DroneNetwork,
    ) -> Connection:
        """Parse a connection line into a Connection object."""

        core_str, meta_str = Pars._split_core_and_metadata(line_num, value)
        core_parts = core_str.split("-")
        if len(core_parts) != 2:
            raise ValueError(
                f"Line {line_num}: Invalid connection format. Expected 'zone1-zone2'."
            )

        zone1 = core_parts[0].strip()
        zone2 = core_parts[1].strip()
        if zone1 not in parsed_data.zones or zone2 not in parsed_data.zones:
            raise ValueError(f"Line {line_num}: Connection references unknown zone(s).")

        if zone1 == zone2:
            raise ValueError(
                f"Line {line_num}: A zone cannot connect to itself '{zone1}-{zone2}'."
            )

        for existing_connection in parsed_data.connections:
            if {existing_connection.zone1, existing_connection.zone2} == {zone1, zone2}:
                raise ValueError(
                    f"Line {line_num}: Duplicate connection detected '{zone1}-{zone2}'."
                )

        metadata = Pars._parse_metadata(line_num, meta_str)
        try:
            link_capacity = int(metadata.get("max_link_capacity", "1"))
        except ValueError as error:
            raise ValueError(
                f"Line {line_num}: max_link_capacity must be a positive integer."
            ) from error

        if link_capacity <= 0:
            raise ValueError(
                f"Line {line_num}: max_link_capacity must be a positive integer."
            )

        data_conn: ConnectionData = {
            "zone1": zone1,
            "zone2": zone2,
            "max_link_capacity": link_capacity,
        }
        return Connection(data_conn)
