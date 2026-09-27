"""Camera, theme, and coordinate helpers for the Pygame visualizer."""


import pygame

from pars import DroneNetwork


class GUI_Controls:
    """Handle camera movement, themes, and world/screen conversion."""

    def __init__(
        self,
        network: DroneNetwork,
        width: int,
        height: int,
    ) -> None:
        self.network = network
        self.width = width
        self.height = height
        self.zoom = 1.0
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.BG_COLOR = (15, 15, 20)
        self.LINE_COLOR = (70, 70, 90)
        self.TEXT_COLOR = (240, 240, 240)
        self.DRONE_COLOR = (200, 220, 255)
        self.GRID_COLOR = (25, 25, 35)
        self.STAR_COLOR = (100, 100, 120)
        self.apply_theme(3)
        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0
        self.base_pad = 150
        self._calculate_scale()

    def apply_theme(self, theme_index: int) -> None:
        """Update visual colors for a selected theme."""
        if theme_index == 1:
            self.BG_COLOR = (20, 15, 30)
            self.LINE_COLOR = (255, 50, 150)
            self.TEXT_COLOR = (255, 255, 255)
            self.DRONE_COLOR = (0, 255, 255)
            self.GRID_COLOR = (45, 25, 60)
            self.STAR_COLOR = (255, 100, 200)
        elif theme_index == 2:
            self.BG_COLOR = (5, 10, 5)
            self.LINE_COLOR = (0, 150, 0)
            self.TEXT_COLOR = (255, 255, 255)
            self.DRONE_COLOR = (0, 255, 0)
            self.GRID_COLOR = (10, 30, 10)
            self.STAR_COLOR = (0, 100, 0)
        else:
            self.BG_COLOR = (15, 15, 20)
            self.LINE_COLOR = (70, 70, 90)
            self.TEXT_COLOR = (255, 255, 255)
            self.DRONE_COLOR = (200, 220, 255)
            self.GRID_COLOR = (25, 25, 35)
            self.STAR_COLOR = (100, 100, 120)

    def handle_mouse(self, event: pygame.event.Event) -> None:
        """Process drag and scroll events."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.is_dragging = True
                self.drag_start_x, self.drag_start_y = event.pos
            elif event.button == 4:
                self.zoom = min(15.0, self.zoom + 0.2)
            elif event.button == 5:
                self.zoom = max(0.1, self.zoom - 0.2)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_dragging = False
        elif event.type == pygame.MOUSEMOTION and self.is_dragging:
            dx = event.pos[0] - self.drag_start_x
            dy = event.pos[1] - self.drag_start_y
            self.cam_x += dx
            self.cam_y += dy
            self.drag_start_x, self.drag_start_y = event.pos

    def _calculate_scale(self) -> None:
        """Cache coordinate boundaries used for screen scaling."""
        if not self.network.zones:
            return
        xs = [zone.x for zone in self.network.zones.values()]
        ys = [zone.y for zone in self.network.zones.values()]
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)

    def get_coords(self, zone_name: str) -> tuple[float, float]:
        """Convert a zone coordinate to its current screen position."""
        zone = self.network.zones[zone_name]
        x_range = self.max_x - self.min_x or 1
        y_range = self.max_y - self.min_y or 1
        usable_width = self.width - 2 * self.base_pad
        usable_height = self.height - 2 * self.base_pad - 150
        base_x = self.base_pad + (
            (zone.x - self.min_x) / x_range * usable_width
        )
        base_y = self.base_pad + (
            (zone.y - self.min_y) / y_range * usable_height
        )
        screen_x = (
            (base_x - self.width / 2) * self.zoom
            + self.width / 2
            + self.cam_x
        )
        screen_y = (
            (base_y - self.height / 2) * self.zoom
            + self.height / 2
            + self.cam_y
        )
        return screen_x, screen_y

    def get_world_pos(self, location: str) -> tuple[float, float]:
        """Get a position for either a zone or a connection-in-transit."""
        if "-" in location:
            zone1, zone2 = location.split("-", 1)
            x1, y1 = self.get_coords(zone1)
            x2, y2 = self.get_coords(zone2)
            return (x1 + x2) / 2.0, (y1 + y2) / 2.0
        return self.get_coords(location)

    @staticmethod
    def lerp(start: float, end: float, progress: float) -> float:
        """Linearly interpolate between two values."""
        return start + (end - start) * progress

    def get_drone_pos(
        self,
        path: list[tuple[int, str]],
        exact_time: float,
    ) -> tuple[float, float]:
        """Interpolate a drone position along a path for animation."""
        if not path:
            return 0.0, 0.0
        if exact_time <= path[0][0]:
            return self.get_world_pos(path[0][1])
        if exact_time >= path[-1][0]:
            return self.get_world_pos(path[-1][1])

        for index in range(len(path) - 1):
            time1, location1 = path[index]
            time2, location2 = path[index + 1]
            if time1 <= exact_time <= time2:
                gap = time2 - time1
                if gap == 0:
                    return self.get_world_pos(location2)
                progress = (exact_time - time1) / gap
                x1, y1 = self.get_world_pos(location1)
                x2, y2 = self.get_world_pos(location2)
                return (
                    self.lerp(x1, x2, progress),
                    self.lerp(y1, y2, progress),
                )
        return self.get_world_pos(path[-1][1])
