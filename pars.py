import sys
import os
from typing import Any, Dict, List, Set, Tuple


def parse_config(filename: str) -> Dict[str, Any]:

    parsed_data: Dict[str, Any] = {
        "nb_drones": 0,
        "zones": {},
        "connections": []
    }
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
                    parsed_data["nb_drones"] = int(value)
                elif key in ["start_hub", "end_hub", "hub"]:
                    core_str = value
                    meta_str = ""
                    if "[" in value and "]" in value:
                        parts = value.split("[", 1)
                        core_str = parts[0].strip()

    except Exception as e:
        print(f"waaaaaaa : {e}")
        