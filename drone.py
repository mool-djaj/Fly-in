

class Drone:
    def __init__(self, drone_id: int) -> None:
        self.id = f"D{drone_id}"
        self.path: list[str] = []
        self.position = 0

    def current_zone(self) -> str:
        return self.path[self.position]

    def next_zone(self) -> str | None:
        if self.position + 1 >= len(self.path):
            return None
        return self.path[self.position + 1]