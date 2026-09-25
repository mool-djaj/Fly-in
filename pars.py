import sys
from typing import Dict, List, Set
import pyparsing as pp

# Clear type aliases for readability
ZoneDict = Dict[str, 'Zone']
ConnectionList = List['Connection']

class Zone:
    def __init__(self, name: str, x: int, y: int, max_drones: int, color: str) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.max_drones = max_drones
        self.color = color
        
        # Attributes required by path_find.py
        self.zone_type = "normal"
        self.hub_role = None

        # Assign mechanics based on mapping rules
        if self.color == "green":
            self.hub_role = "start_hub"
            self.max_drones = 9999  # Hubs have infinite capacity
        elif self.color == "red":
            self.hub_role = "end_hub"
            self.max_drones = 9999
        elif self.color == "yellow":
            self.zone_type = "restricted"
        elif self.color == "gray":
            self.zone_type = "blocked"

class Connection:
    def __init__(self, zone1: str, zone2: str) -> None:
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = 1  # Required by path_find.py

class DroneNetwork:
    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.zones: ZoneDict = {}
        self.connections: ConnectionList = []

def parse_network(filepath: str) -> DroneNetwork:
    network = DroneNetwork()
    valid_colors: Set[str] = {"red", "blue", "green", "yellow", "gray", "none"}

    # --- ADVANCED PYPARSING GRAMMAR ---
    integer = pp.Word(pp.nums)
    name_str = pp.Word(pp.alphanums + "_") # Zone names (no hyphens to avoid link conflicts)
    color_str = pp.Word(pp.alphas)
    colon = pp.Suppress(pp.Optional(":"))
    
    # Drones (Handles "nb_drones: 2" or "drones 2")
    prefix_drones = pp.Suppress((pp.CaselessKeyword("nb_drones") | pp.CaselessKeyword("drones")) + colon)
    line_drones = prefix_drones + integer("count")
    
    # Connections (Handles "link: A-B" or "connection A B")
    prefix_conn = pp.Suppress((pp.CaselessKeyword("connection") | pp.CaselessKeyword("link")) + colon)
    line_conn = prefix_conn + name_str("z1") + pp.Suppress(pp.Optional("-")) + name_str("z2")
    
    # Zones (Handles "start_hub: start 0 0 [color=green]" AND "zone: A 5 5 2 [color=yellow]")
    zone_prefix = pp.Suppress(pp.Optional((pp.CaselessKeyword("start_hub") | pp.CaselessKeyword("end_hub") | pp.CaselessKeyword("zone")) + colon))
    capacity_expr = pp.Optional(integer("capacity"), default=9999) # Defaults to 9999 if missing
    
    # Safely strips away "[", "color", "=", and "]" if they exist
    color_expr = pp.Suppress(pp.Optional("[")) + pp.Suppress(pp.Optional(pp.CaselessKeyword("color") + pp.Optional("="))) + color_str("color") + pp.Suppress(pp.Optional("]"))
    
    line_zone = zone_prefix + name_str("name") + integer("x") + integer("y") + capacity_expr + color_expr

    # 1. File I/O
    try:
        with open(filepath, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: Cannot open map file '{filepath}'")
        sys.exit(1)

    # 2. Parsing Loop
    for raw_line in lines:
        line = raw_line.strip()
        
        # Skip empty lines and C-style comments
        if len(line) == 0 or line.startswith("#") or line.startswith("//"):
            continue

        lower_line = line.lower()

        if lower_line.startswith("nb_drones") or lower_line.startswith("drones"):
            try:
                parsed = line_drones.parse_string(line, parse_all=True)
                network.nb_drones = int(parsed.count)
            except pp.ParseException:
                print(f"Syntax Error in drones definition: {line}")
                sys.exit(1)
        
        elif lower_line.startswith("connection") or lower_line.startswith("link"):
            try:
                parsed = line_conn.parse_string(line, parse_all=True)
                z1, z2 = parsed.z1, parsed.z2
                
                if z1 not in network.zones or z2 not in network.zones:
                    print(f"Error: Zones '{z1}' or '{z2}' not defined before linking.")
                    sys.exit(1)
                    
                network.connections.append(Connection(z1, z2))
            except pp.ParseException:
                print(f"Syntax Error in connection definition: {line}")
                sys.exit(1)
        
        else:
            try:
                parsed = line_zone.parse_string(line, parse_all=True)
                name = parsed.name
                x, y = int(parsed.x), int(parsed.y)
                capacity = int(parsed.capacity)
                color = parsed.color.lower()

                if color not in valid_colors:
                    print(f"Error: Invalid color '{color}' in zone '{name}'.")
                    sys.exit(1)
                    
                if name in network.zones:
                    print(f"Error: Duplicate zone '{name}' found.")
                    sys.exit(1)

                network.zones[name] = Zone(name, x, y, capacity, color)
            except pp.ParseException:
                print(f"Syntax Error in zone definition: {line}")
                sys.exit(1)

    # 3. Final Integrity Checks
    if network.nb_drones == 0:
        print("Error: No drones configured.")
        sys.exit(1)
    if len(network.zones) < 2:
        print("Error: Map must contain at least two zones.")
        sys.exit(1)

    return network