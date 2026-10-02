
"""Store information about one drone."""


class Drone:
    """Represent a drone and its planned movement."""

    def __init__(self, drone_id: int) -> None:
        """Create a drone with a unique number."""
        self.id = f"D{drone_id}"
        self.path: list[str] = []
        self.schedule: list[tuple[int, str]] = []
