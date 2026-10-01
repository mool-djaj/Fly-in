

class Drone:
    def __init__(self, drone_id: int) -> None:
        self.id = f"D{drone_id}"
        self.path: list[str] = []
        self.schedule: list[tuple[int, str]] = []
