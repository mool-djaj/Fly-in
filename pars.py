"""Read and validate Fly-in map files."""

from typing import NoReturn

import pyparsing as pp


class ParseError(Exception):
    """Report an invalid map file."""

    pass


class Zone:
    """Store the settings of one zone."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: str = "normal",
        color: str = "none",
        max_drones: int | None = 1,
        hub_role: str | None = None,
    ) -> None:
        """Create a zone."""
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.max_drones = max_drones
        self.hub_role = hub_role


class Connection:
    """Store a connection between two zones."""

    def __init__(
        self,
        zone1: str,
        zone2: str,
        max_link_capacity: int = 1,
    ) -> None:
        """Create a connection."""
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = max_link_capacity


class DroneNetwork:
    """Store all parsed zones, connections, and drones."""

    def __init__(self) -> None:
        """Create an empty drone network."""
        self.nb_drones = 0
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self.start_hub: str | None = None
        self.end_hub: str | None = None


class Parser:
    """Parse a map file and check its rules."""

    VALID_ZONE_TYPES = {
        "normal",
        "blocked",
        "restricted",
        "priority",
    }

    def __init__(self, filepath: str) -> None:
        """Prepare the grammar for the given map file."""
        self.filepath = filepath
        self.network = DroneNetwork()
        self.line_num = 0

        self.integer = pp.common.signed_integer
        name = pp.Regex(r"[^\s-]+")

        attr_key = pp.Word(pp.alphas + "_")
        attr_value = pp.Regex(r"[^\s\[\]=]+")
        attr_pair = pp.Group(
            attr_key + pp.Suppress("=") + attr_value
        )
        attrs = pp.Dict(pp.ZeroOrMore(attr_pair))
        metadata = pp.Optional(
            pp.Suppress("[")
            + attrs("attrs")
            + pp.Suppress("]")
        )

        self.drones_rule = (
            pp.Keyword("nb_drones")
            + pp.Suppress(":")
            + self.integer("count")
        )

        self.connection_rule = (
            pp.Keyword("connection")
            + pp.Suppress(":")
            + name("z1")
            + pp.Suppress("-")
            + name("z2")
            + metadata
        )

        zone_prefix = (
            pp.Keyword("start_hub")
            | pp.Keyword("end_hub")
            | pp.Keyword("hub")
        )

        self.zone_rule = (
            zone_prefix("keyword")
            + pp.Suppress(":")
            + name("name")
            + self.integer("x")
            + self.integer("y")
            + metadata
        )

    def _error(
        self,
        message: str,
        raw_line: str = "",
    ) -> NoReturn:
        """Raise a clear parser error."""
        if raw_line:
            raise ParseError(
                f"Error: {message}\n"
                f"Cause: Line {self.line_num}: "
                f"{raw_line.strip()}"
            )

        raise ParseError(
            f"Error: {message}\n"
            "Cause: End of file."
        )

    def _positive_int(
        self,
        value: str,
        label: str,
        raw_line: str,
    ) -> int:
        """Read a positive integer or report a clear error."""
        try:
            parsed = self.integer.parse_string(
                value,
                parse_all=True,
            )
        except pp.ParseBaseException:
            self._error(
                f"{label} must be an integer.",
                raw_line,
            )

        number = int(parsed[0])

        if number <= 0:
            self._error(
                f"{label} must be greater than 0.",
                raw_line,
            )

        return number

    def _connection_exists(
        self,
        zone1: str,
        zone2: str,
    ) -> bool:
        """Check whether two zones are already connected."""
        for connection in self.network.connections:
            same_order = (
                connection.zone1 == zone1
                and connection.zone2 == zone2
            )
            reverse_order = (
                connection.zone1 == zone2
                and connection.zone2 == zone1
            )

            if same_order or reverse_order:
                return True

        return False

    def _get_attrs(
        self,
        parsed: pp.ParseResults,
    ) -> dict[str, str]:
        """Return metadata values from a parsed line."""
        if "attrs" not in parsed:
            return {}

        raw_attrs = parsed["attrs"].as_dict()

        return {
            str(key): str(value)
            for key, value in raw_attrs.items()
        }

    def _parse_drones(
        self,
        clean_line: str,
        raw_line: str,
    ) -> None:
        """Read the number of drones."""
        try:
            parsed = self.drones_rule.parse_string(
                clean_line,
                parse_all=True,
            )
        except pp.ParseBaseException:
            self._error(
                "Invalid drone configuration. Expected "
                "'nb_drones: <positive_integer>'.",
                raw_line,
            )

        if self.network.nb_drones != 0:
            self._error(
                "Duplicate drone configuration.",
                raw_line,
            )

        count = int(parsed["count"])

        if count <= 0:
            self._error(
                "Drone count must be greater than 0.",
                raw_line,
            )

        self.network.nb_drones = count

    def _parse_connection(
        self,
        clean_line: str,
        raw_line: str,
    ) -> None:
        """Read and validate one connection."""
        try:
            parsed = self.connection_rule.parse_string(
                clean_line,
                parse_all=True,
            )
        except pp.ParseBaseException:
            self._error(
                "Invalid connection syntax. Expected "
                "'connection: <zone1>-<zone2> [metadata]'.",
                raw_line,
            )

        zone1 = str(parsed["z1"])
        zone2 = str(parsed["z2"])

        if zone1 not in self.network.zones:
            self._error(
                f"Unknown zone '{zone1}' in connection. "
                "Connections may only use previously defined zones.",
                raw_line,
            )

        if zone2 not in self.network.zones:
            self._error(
                f"Unknown zone '{zone2}' in connection. "
                "Connections may only use previously defined zones.",
                raw_line,
            )

        if self._connection_exists(zone1, zone2):
            self._error(
                f"Duplicate connection '{zone1}-{zone2}'.",
                raw_line,
            )

        attrs = self._get_attrs(parsed)
        invalid = set(attrs) - {"max_link_capacity"}

        if invalid:
            key = sorted(invalid)[0]
            self._error(
                f"Invalid connection attribute '{key}'.",
                raw_line,
            )

        capacity = 1

        if "max_link_capacity" in attrs:
            capacity = self._positive_int(
                attrs["max_link_capacity"],
                "Connection capacity",
                raw_line,
            )

        self.network.connections.append(
            Connection(
                zone1,
                zone2,
                capacity,
            )
        )

    def _parse_zone(
        self,
        clean_line: str,
        raw_line: str,
    ) -> None:
        """Read and validate one zone."""
        if ":" in clean_line:
            body = clean_line.split(":", 1)[1].strip()
            if body:
                zone_name = body.split()[0]
                if "-" in zone_name:
                    self._error(
                        f"Invalid zone name '{zone_name}': "
                        "dashes are not allowed.",
                        raw_line,
                    )

        try:
            parsed = self.zone_rule.parse_string(
                clean_line,
                parse_all=True,
            )
        except pp.ParseBaseException:
            self._error(
                "Invalid zone syntax. Expected "
                "'<type>: <name> <integer> <integer> [metadata]'.",
                raw_line,
            )

        keyword = str(parsed["keyword"])
        zone_name = str(parsed["name"])
        attrs = self._get_attrs(parsed)

        invalid = set(attrs) - {
            "color",
            "max_drones",
            "zone",
        }

        if invalid:
            key = sorted(invalid)[0]
            self._error(
                f"Invalid zone attribute '{key}'.",
                raw_line,
            )

        if zone_name in self.network.zones:
            self._error(
                f"Duplicate zone '{zone_name}'.",
                raw_line,
            )

        zone_type = attrs.get("zone", "normal")

        if zone_type not in self.VALID_ZONE_TYPES:
            self._error(
                f"Invalid zone type '{zone_type}'. "
                "Expected normal, blocked, restricted, or priority.",
                raw_line,
            )

        is_start = keyword == "start_hub"
        is_end = keyword == "end_hub"

        max_drones: int | None

        if is_start or is_end:
            max_drones = None
        else:
            max_drones = self._positive_int(
                attrs.get("max_drones", "1"),
                f"Zone '{zone_name}' capacity",
                raw_line,
            )

        hub_role: str | None = None

        if is_start:
            if self.network.start_hub is not None:
                self._error(
                    "Multiple start hubs detected.",
                    raw_line,
                )

            self.network.start_hub = zone_name
            hub_role = "start_hub"

        elif is_end:
            if self.network.end_hub is not None:
                self._error(
                    "Multiple end hubs detected.",
                    raw_line,
                )

            self.network.end_hub = zone_name
            hub_role = "end_hub"

        self.network.zones[zone_name] = Zone(
            name=zone_name,
            x=int(parsed["x"]),
            y=int(parsed["y"]),
            zone_type=zone_type,
            color=attrs.get("color", "none"),
            max_drones=max_drones,
            hub_role=hub_role,
        )

    def _parse_line(
        self,
        clean_line: str,
        raw_line: str,
    ) -> None:
        """Send one map line to the correct parser."""
        if clean_line.startswith("nb_drones"):
            self._parse_drones(
                clean_line,
                raw_line,
            )
            return

        if self.network.nb_drones == 0:
            self._error(
                "Drone count must be defined first.",
                raw_line,
            )

        if clean_line.startswith("connection"):
            self._parse_connection(
                clean_line,
                raw_line,
            )
            return

        if clean_line.startswith(
            ("hub", "start_hub", "end_hub")
        ):
            self._parse_zone(
                clean_line,
                raw_line,
            )
            return

        self._error(
            "Unknown line type.",
            raw_line,
        )

    def _validate_final_network(self) -> None:
        """Check that the map has all required settings."""
        if self.network.nb_drones <= 0:
            self._error(
                "Missing or invalid drone configuration."
            )

        if self.network.start_hub is None:
            self._error(
                "Map is missing a start_hub."
            )

        if self.network.end_hub is None:
            self._error(
                "Map is missing an end_hub."
            )

    def parse(self) -> DroneNetwork:
        """Parse the complete file and return its network."""
        first_content_seen = False

        try:
            with open(
                self.filepath,
                "r",
            ) as map_file:
                for self.line_num, raw_line in enumerate(
                    map_file,
                    start=1,
                ):
                    clean_line = raw_line.split(
                        "#",
                        1,
                    )[0].strip()

                    if not clean_line:
                        continue

                    if not first_content_seen:
                        first_content_seen = True

                        if not clean_line.startswith(
                            "nb_drones"
                        ):
                            self._error(
                                "The first definition must be "
                                "'nb_drones'.",
                                raw_line,
                            )

                    self._parse_line(
                        clean_line,
                        raw_line,
                    )

        except OSError as error:
            raise ParseError(
                f"Error: Cannot open map file "
                f"'{self.filepath}'.\n"
                f"Cause: {error}"
            ) from error

        self._validate_final_network()
        return self.network
