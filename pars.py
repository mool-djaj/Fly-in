import sys
from typing import NoReturn, Optional
import pyparsing as pp


class ParseError(Exception):
    ...

class Zone:

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: str = "normal",
        color: str = "none",
        max_drones: Optional[int] = 1,
        hub_role: Optional[str] = None,
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.max_drones = max_drones
        self.hub_role = hub_role


class Connection:

    def __init__(
        self,
        zone1: str,
        zone2: str,
        max_link_capacity: int = 1,
    ) -> None:
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = max_link_capacity


class DroneNetwork:

    def __init__(self) -> None:
        self.nb_drones = 0
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self.start_hub: Optional[str] = None
        self.end_hub: Optional[str] = None


class Parser:

    VALID_ZONE_TYPES = {
        "normal",
        "blocked",
        "restricted",
        "priority",
    }

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.network = DroneNetwork()
        self.line_num = 0

        integer = pp.common.signed_integer
        coordinate = pp.common.signed_integer
        name = pp.Regex(r"[^\s\-\[\]]+")

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
            + integer("count")
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
            + coordinate("x")
            + coordinate("y")
            + metadata
        )

    def _error(self, message: str, raw_line: str = "") -> NoReturn:
        if raw_line:
            raise ParseError(
                f"Error: {message}\n"
                f"Cause: Line {self.line_num}: {raw_line.strip()}"
            )
        raise ParseError(f"Error: {message}")

    def _positive_int(self, value: str, label: str) -> int:
        """Convert a value to a strict positive integer."""
        if not value.isdigit():
            self._error(
                f"{label} must be a positive integer."
            )

        number = int(value)
        if number <= 0:
            self._error(f"{label} must be greater than 0.")

        return number

    def _connection_exists(self, z1: str, z2: str) -> bool:
        """Return True if the undirected connection already exists."""
        for connection in self.network.connections:
            same_order = (
                connection.zone1 == z1
                and connection.zone2 == z2
            )
            reverse_order = (
                connection.zone1 == z2
                and connection.zone2 == z1
            )
            if same_order or reverse_order:
                return True
        return False

    def _get_attrs(
        self,
        parsed: pp.ParseResults,
    ) -> dict[str, str]:
        """Return parsed metadata as a normal string dictionary."""
        if "attrs" not in parsed:
            return {}

        raw_attrs = parsed["attrs"].as_dict()
        return {
            str(key): str(value)
            for key, value in raw_attrs.items()
        }

    def _parse_drones(self, clean_line: str, raw_line: str) -> None:
        """Parse the drone-count line."""
        try:
            parsed = self.drones_rule.parse_string(
                clean_line,
                parse_all=True,
            )
        except pp.ParseBaseException as error:
            self._error(
                f"Invalid drone configuration ({error}).",
                raw_line,
            )

        if self.network.nb_drones != 0:
            self._error(
                "Duplicate drone configuration.",
                raw_line,
            )

        count = int(str(parsed["count"]))
        if count <= 0:
            self._error(
                "Drone count must be positive.",
                raw_line,
            )

        self.network.nb_drones = count

    def _parse_connection(
        self,
        clean_line: str,
        raw_line: str,
    ) -> None:
        """Parse and validate one connection."""
        try:
            parsed = self.connection_rule.parse_string(
                clean_line,
                parse_all=True,
            )
        except pp.ParseBaseException as error:
            self._error(
                f"Invalid connection syntax ({error}).",
                raw_line,
            )

        z1 = str(parsed["z1"])
        z2 = str(parsed["z2"])

        if z1 not in self.network.zones:
            self._error(
                f"Unknown zone '{z1}' in connection.",
                raw_line,
            )

        if z2 not in self.network.zones:
            self._error(
                f"Unknown zone '{z2}' in connection.",
                raw_line,
            )

        if self._connection_exists(z1, z2):
            self._error(
                f"Duplicate connection '{z1}-{z2}'.",
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
            )

        connection = Connection(
            z1,
            z2,
            capacity,
        )
        self.network.connections.append(connection)

    def _parse_zone(
        self,
        clean_line: str,
        raw_line: str,
    ) -> None:
        """Parse and validate one zone."""
        try:
            parsed = self.zone_rule.parse_string(
                clean_line,
                parse_all=True,
            )
        except pp.ParseBaseException as error:
            self._error(
                f"Invalid zone syntax ({error}).",
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
                f"Invalid zone type '{zone_type}'.",
                raw_line,
            )

        is_start = keyword == "start_hub"
        is_end = keyword == "end_hub"

        max_drones: Optional[int]
        if is_start or is_end:
            max_drones = None
        else:
            max_drones = self._positive_int(
                attrs.get("max_drones", "1"),
                f"Zone '{zone_name}' capacity",
            )

        hub_role: Optional[str] = None

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

        zone = Zone(
            name=zone_name,
            x=int(str(parsed["x"])),
            y=int(str(parsed["y"])),
            zone_type=zone_type,
            color=attrs.get("color", "none"),
            max_drones=max_drones,
            hub_role=hub_role,
        )

        self.network.zones[zone_name] = zone

    def _parse_line(
        self,
        clean_line: str,
        raw_line: str,
    ) -> None:
        """Dispatch one non-empty input line to the correct parser."""
        if clean_line.startswith("nb_drones"):
            self._parse_drones(clean_line, raw_line)
            return

        if self.network.nb_drones == 0:
            self._error(
                "Drone count must be defined first.",
                raw_line,
            )

        if clean_line.startswith("connection"):
            self._parse_connection(clean_line, raw_line)
            return

        self._parse_zone(clean_line, raw_line)

    def _validate_final_network(self) -> None:
        """Validate requirements that need the full parsed file."""
        if self.network.nb_drones <= 0:
            self._error(
                "Missing or invalid drone configuration."
            )

        if self.network.start_hub is None:
            self._error("Map is missing a start_hub.")

        if self.network.end_hub is None:
            self._error("Map is missing an end_hub.")

    def parse(self) -> DroneNetwork:
        try:
            with open(
                self.filepath,
                "r",
                encoding="utf-8",
            ) as map_file:
                lines = map_file.readlines()
        except OSError as error:
            raise ParseError(
                f"Error: Cannot open map file "
                f"'{self.filepath}'.\n"
                f"Cause: {error}"
            ) from error

        first_content_seen = False

        for self.line_num, raw_line in enumerate(
            lines,
            start=1,
        ):
            clean_line = raw_line.split("#", 1)[0].strip()

            if not clean_line:
                continue

            if not first_content_seen:
                first_content_seen = True
                if not clean_line.startswith("nb_drones"):
                    self._error(
                        "Drone count must be defined first.",
                        raw_line,
                    )

            self._parse_line(clean_line, raw_line)

        self._validate_final_network()
        return self.network

