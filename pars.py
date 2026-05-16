import sys
import os
from typing import Any, Dict, List, Set, Tuple


class Zone:
    def __init__(self, name: str, data: Dict):
        self.name = name
        self.hub_role = data["hub_role"]
        self.x = data["x"]
        self.y = data["y"]
        self.zone_type = data["zone_type"]
        self.max_drones = data["max_drones"]
        self.color = data["color"]
        self.current_drones = 0 


class Connection:
    def __init__(self, data: Dict):
        self.zone1 = data["zone1"]
        self.zone2 = data["zone2"]
        self.max_link_capacity = data["max_link_capacity"]
        self.current_traffic = 0


class DroneNetwork:
    def __init__(self):
        self.nb_drones = 0
        self.zones: Dict[str, Zone] = {}
        self.connections: List[Connection] = []

    def add_zone(self, zone: Zone):
        self.zones[zone.name] = zone

    def add_connection(self, connection: Connection):
        self.connections.append(connection)
     

class Pars:
    
    @staticmethod
    def parse_config(filename: str) -> DroneNetwork:

        parsed_data = DroneNetwork()
        dr_nb_finder = False
        start_flage = 0
        end_flage = 0
        
        try:
            with open(filename, 'r') as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if ':' not in line:
                        raise ValueError(
                            f"Line {line_num}: Invalid format, missing ':'.")
                        
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if key == "nb_drones":
                        if int(value) < 0:
                            raise ValueError(f"Line {line_num}: nb_drones must be a positive integer.")
                        parsed_data.nb_drones = int(value)
                        dr_nb_finder = True
                        
                    elif dr_nb_finder == False:
                        raise ValueError(f"Line {line_num}: nb_drones must be at the top of the map.")
                   
                   
                    elif key in ["start_hub", "end_hub", "hub"]:
                        if key == "start_hub":
                            if start_flage == 1:
                                raise ValueError(f"Line {line_num}: Multiple 'start_hub' zones defined.")
                            start_flage = 1
                        elif key == "end_hub":
                            if end_flage == 1:
                                raise ValueError(f"Line {line_num}: Multiple 'end_hub' zones defined.")
                            end_flage = 1
                        core_str = value
                        meta_str = ""
                        if "[" in value and "]" in value:
                            parts = value.split("[", 1)
                            core_str = parts[0].strip()
                            meta_str = parts[1].replace("]","").strip()
                        elif "[" in value or "]" in value:
                            raise ValueError(f"ther is '[' ore ']' in line {line_num}")
                        
                        core_parts = core_str.split(" ")
                        if len(core_parts) != 3:
                            raise ValueError(f"Line {line_num}: Invalid hub format. Expected '<name> <x> <y>'.")                       
                        
                        name = core_parts[0]
                        if "-" in name:
                            raise ValueError(f"Line {line_num}: Zone names cannot contain '-'.")
                        
                        if name in parsed_data.zones:
                            raise ValueError(f"Line {line_num}: Duplicate zone name '{name}'.")
                        
                        try:
                            x, y = int(core_parts[1]), int(core_parts[2])
                        except ValueError:
                            raise ValueError(f"Line {line_num}: Coordinates must be integers.")
                        
                        metadata = {}
                        if meta_str:
                            meta_lst = meta_str.split()
                            
                            for pair in meta_lst:
                                if "=" not in pair:
                                    raise ValueError(f"Line {line_num}: Invalid metadata format '{pair}'.")
                                key_m, key_val = pair.split("=", 1)
                                metadata[key_m] = key_val
                                
                        z_type = metadata.get("zone", "normal")
                        if z_type not in ["normal", "blocked", "restricted", "priority"]:
                                raise ValueError(f"Line {line_num}: Invalid zone type '{z_type}'.")
                        
                        default_cap = 999 if key in ["start_hub", "end_hub"] else 1
                        try:
                            max_drones = int(metadata.get("max_drones", default_cap))
                            if max_drones <= 0:
                                raise ValueError()
                        except ValueError:
                            raise ValueError(f"Line {line_num}: max_drones must be a positive integer.")

                        data_zone = {
                            "hub_role": key,  
                            "x": x,
                            "y": y,
                            "zone_type": z_type,
                            "color": metadata.get("color", "none"),
                            "max_drones": max_drones
                        }
                        new_zone = Zone(name, data_zone)
                        parsed_data.add_zone(new_zone)

                    
                    elif key == "connection":
                        core_str = value
                        meta_str = ""
                        
                        if "[" in value and "]" in value:
                            parts = value.split("[", 1)
                            core_str = parts[0].strip()
                            meta_str = parts[1].replace("]", "").strip()
                        elif "[" in value or "]" in value:
                            raise ValueError(f"Line {line_num}: Mismatched brackets in metadata.")

                        core_parts = core_str.split("-")
                        if len(core_parts) != 2:
                            raise ValueError(f"Line {line_num}: Invalid connection format. Expected 'zone1-zone2'.")
                        
                        z1 = core_parts[0].strip()
                        z2 = core_parts[1].strip()

                        if z1 not in parsed_data.zones or z2 not in parsed_data.zones:
                            raise ValueError(f"Line {line_num}: Connection references unknown zone(s).")


                        new_link_set = {z1, z2}
                        if len(new_link_set) == 1:
                            raise ValueError(f"Line {line_num}: A zone cannot connect to itself '{z1}-{z2}'.")
                        
                        for existing_conn in parsed_data.connections:
                            if {existing_conn.zone1, existing_conn.zone2} == new_link_set:
                                raise ValueError(f"Line {line_num}: Duplicate connection detected '{z1}-{z2}'.")

                        metadata = {}
                        if meta_str:
                            meta_lst = meta_str.split(" ")
                            for pair in meta_lst:
                                if "=" not in pair:
                                    raise ValueError(f"Line {line_num}: Invalid metadata format '{pair}'.")
                                key_m, key_val = pair.split("=", 1)
                                metadata[key_m] = key_val

                        try:
                            link_cap = int(metadata.get("max_link_capacity", 1))
                            if link_cap <= 0:
                                raise ValueError()
                        except ValueError:
                            raise ValueError(f"Line {line_num}: max_link_capacity must be a positive integer.")

                        data_conn = {
                            "zone1": z1,
                            "zone2": z2,
                            "max_link_capacity": link_cap
                        }
                        
                        new_conn = Connection(data_conn)
                        parsed_data.add_connection(new_conn)
                    else:
                        raise ValueError(f"Line {line_num}: Unknown prefix '{key}'.")
                
                
                
                if start_flage == 0:
                    raise ValueError(f"ther is no start_hub :(")
                elif end_flage == 0:
                    raise ValueError(f"ther is no end_hub :(")
             
                                                
        except Exception as e:
                print(f"WAAAAAAAA : {e}", file=sys.stderr)
                sys.exit(1)
    
        return parsed_data

# if __name__ == '__main__':

#     network = Pars.parse_config('cj.map')
#     # print(f"{network.zones.items()}")
    
#     i = int(network.nb_drones)
#     print(i)
#     # zone = network.zones["hub"]
#     # print(zone.x)
    
#     # conn = network.connections[0]
#     # print(conn.zone2)