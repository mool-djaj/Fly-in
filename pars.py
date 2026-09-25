import sys
from typing import Dict, List, Set
import pyparsing as pp

ZoneDict = Dict[str, 'Zone']
ConnectionList = List['Connection']

class Zone:
    def __init__(self, name: str, x: int, y: int, max_drones: int, color: str) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.max_drones = max_drones
        self.color = color
        
        self.zone_type = "normal"
        self.hub_role = None

class Connection:
    def __init__(self, zone1: str, zone2: str) -> None:
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = 1

class DroneNetwork:
    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.zones: ZoneDict = {}
        self.connections: ConnectionList = []
        
        self.has_start_hub = False
        self.has_end_hub = False

def parse_network(filepath: str) -> DroneNetwork:
    network = DroneNetwork()

    # --- PYPARSING GRAMMAR ---
    integer = pp.Combine(pp.Optional('-') + pp.Word(pp.nums)).set_parse_action(lambda t: int(t[0]))
    name_str = pp.Word(pp.printables, excludeChars="-:=[]") 
    colon = pp.Suppress(pp.Optional(":"))
    
    attr_key = pp.Word(pp.alphas + "_")
    attr_val = pp.Word(pp.alphanums + "_-")
    attr_pair = pp.Group(attr_key + pp.Suppress("=") + attr_val)
    attrs_dict = pp.Dict(pp.ZeroOrMore(attr_pair))
    opt_brackets = pp.Optional(pp.Suppress("[") + attrs_dict("attrs") + pp.Suppress("]"))

    drones_prefix = pp.CaselessKeyword("nb_drones") | pp.CaselessKeyword("drones")
    rule_drones = drones_prefix + colon + integer("count")

    conn_prefix = pp.CaselessKeyword("connection") | pp.CaselessKeyword("link")
    rule_conn = conn_prefix + colon + name_str("z1") + pp.Suppress("-") + name_str("z2") + opt_brackets

    zone_prefix = pp.CaselessKeyword("start_hub") | pp.CaselessKeyword("end_hub") | pp.CaselessKeyword("hub") | pp.CaselessKeyword("zone")
    rule_zone = zone_prefix("keyword") + colon + name_str("name") + integer("x") + integer("y") + opt_brackets

    valid_zone_types: Set[str] = {"normal", "blocked", "restricted", "priority"}

    # --- FILE PARSING ---
    try:
        with open(filepath, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: Cannot open map file '{filepath}'", file=sys.stderr)
        sys.exit(1)

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        lower_line = line.lower()

        try:
            # 1. PARSE DRONES
            if lower_line.startswith("nb_drones") or lower_line.startswith("drones"):
                parsed = rule_drones.parse_string(line, parse_all=True)
                
                if network.nb_drones != 0:
                    print(f"Error: Duplicate drone configuration.\nCause: Drones already defined. Line {line_num}: {raw_line.strip()}", file=sys.stderr)
                    sys.exit(1)
                    
                if parsed.count <= 0:
                    print(f"Error: Drone count must be a positive integer.\nCause: Found '{parsed.count}' on line {line_num}: {raw_line.strip()}", file=sys.stderr)
                    sys.exit(1)
                network.nb_drones = parsed.count

            # 2. PARSE CONNECTIONS
            elif lower_line.startswith("connection") or lower_line.startswith("link"):
                if network.nb_drones == 0:
                    print(f"Error: Drones must be defined first.\nCause: Found connection before nb_drones on line {line_num}: {raw_line.strip()}", file=sys.stderr)
                    sys.exit(1)

                parsed = rule_conn.parse_string(line, parse_all=True)
                z1, z2 = parsed.z1, parsed.z2
                
                if z1 == z2:
                    print(f"Error: A zone cannot connect to itself.\nCause: Self-loop '{z1}-{z2}' on line {line_num}: {raw_line.strip()}", file=sys.stderr)
                    sys.exit(1)
                
                if z1 not in network.zones or z2 not in network.zones:
                    print(f"Error: Zone '{z1}' or '{z2}' not defined before linking.\nCause: Invalid connection on line {line_num}: {raw_line.strip()}", file=sys.stderr)
                    sys.exit(1)
                
                for existing_conn in network.connections:
                    if (existing_conn.zone1 == z1 and existing_conn.zone2 == z2) or \
                       (existing_conn.zone1 == z2 and existing_conn.zone2 == z1):
                        print(f"Error: Duplicate connection.\nCause: Link '{z1}-{z2}' already exists. Line {line_num}: {raw_line.strip()}", file=sys.stderr)
                        sys.exit(1)

                conn = Connection(z1, z2)
                
                if "attrs" in parsed and "max_link_capacity" in parsed.attrs:
                    cap = int(parsed.attrs["max_link_capacity"])
                    if cap <= 0:
                        print(f"Error: Connection capacity must be > 0.\nCause: Found '{cap}' on line {line_num}: {raw_line.strip()}", file=sys.stderr)
                        sys.exit(1)
                    conn.max_link_capacity = cap
                    
                network.connections.append(conn)

            # 3. PARSE ZONES
            else:
                if network.nb_drones == 0:
                    print(f"Error: Drones must be defined first.\nCause: Found zone before nb_drones on line {line_num}: {raw_line.strip()}", file=sys.stderr)
                    sys.exit(1)

                parsed = rule_zone.parse_string(line, parse_all=True)
                keyword = parsed.keyword.lower()
                name = parsed.name
                x = parsed.x
                y = parsed.y
                
                attrs = parsed.attrs.as_dict() if "attrs" in parsed else {}
                color = attrs.get("color", "none").lower()
                
                # Assign Hub Roles
                is_start = keyword == "start_hub" or color == "green"
                is_end = keyword == "end_hub" or color == "red"

                if is_start or is_end:
                    capacity = 99999
                else:
                    capacity = int(attrs.get("max_drones", 9999))
                    if capacity <= 0:
                        print(f"Error: Zone '{name}' capacity must be > 0.\nCause: Found '{capacity}' on line {line_num}: {raw_line.strip()}", file=sys.stderr)
                        sys.exit(1)
                    
                z = Zone(name, x, y, capacity, color)

                if is_start:
                    if network.has_start_hub:
                        print(f"Error: Multiple start hubs detected.\nCause: Map already has a start hub. Line {line_num}: {raw_line.strip()}", file=sys.stderr)
                        sys.exit(1)
                    z.hub_role = "start_hub"
                    network.has_start_hub = True
                    
                elif is_end:
                    if network.has_end_hub:
                        print(f"Error: Multiple end hubs detected.\nCause: Map already has an end hub. Line {line_num}: {raw_line.strip()}", file=sys.stderr)
                        sys.exit(1)
                    z.hub_role = "end_hub"
                    network.has_end_hub = True

                # Assign & Validate Zone Mechanics
                if "zone" in attrs:
                    z.zone_type = attrs["zone"].lower()
                elif color in ("yellow", "brown", "maroon", "darkred"):
                    z.zone_type = "restricted"
                elif color == "black":
                    z.zone_type = "blocked"
                elif color == "gold":
                    z.zone_type = "priority"
                    
                if z.zone_type not in valid_zone_types:
                    print(f"Error: Invalid zone type '{z.zone_type}'.\nCause: Must be normal, blocked, restricted, or priority. Line {line_num}: {raw_line.strip()}", file=sys.stderr)
                    sys.exit(1)
                    
                if name in network.zones:
                    print(f"Error: Duplicate zone '{name}' found.\nCause: Redefinition on line {line_num}: {raw_line.strip()}", file=sys.stderr)
                    sys.exit(1)

                network.zones[name] = z
                
        except pp.ParseException:
            print(f"Error: Invalid syntax.\nCause: Parsing failed on line {line_num}: {raw_line.strip()}", file=sys.stderr)
            sys.exit(1)
        except ValueError:
            print(f"Error: Invalid data type.\nCause: Expected integer on line {line_num}: {raw_line.strip()}", file=sys.stderr)
            sys.exit(1)

    # --- FINAL INTEGRITY CHECKS ---
    if network.nb_drones <= 0:
        print("Error: Missing or invalid drone configuration.\nCause: Network has 0 drones.", file=sys.stderr)
        sys.exit(1)
    if len(network.zones) < 2:
        print("Error: Incomplete network map.\nCause: Map must contain at least two zones.", file=sys.stderr)
        sys.exit(1)
    if not network.has_start_hub or not network.has_end_hub:
        print("Error: Missing required hubs.\nCause: Map must contain exactly one start_hub and exactly one end_hub.", file=sys.stderr)
        sys.exit(1)

    return network