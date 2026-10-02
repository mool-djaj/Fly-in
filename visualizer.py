"""Draw the drone simulation in a Pygame window."""

import math
import os
from typing import Any, Optional

from drone import Drone
from pars import DroneNetwork, Zone


class Visualizer:
    """Display the network and animate drone movements."""

    WIDTH = 1080
    HEIGHT = 720
    PANEL_WIDTH = 220
    TURN_SECONDS = 0.8

    THEMES = {
        1: {
            "background": (18, 24, 38),
            "panel": (27, 36, 53),
            "line": (100, 116, 139),
            "text": (235, 241, 250),
            "muted": (164, 177, 197),
            "outline": (226, 232, 240),
        },
        2: {
            "background": (239, 243, 248),
            "panel": (220, 228, 238),
            "line": (103, 116, 137),
            "text": (24, 34, 49),
            "muted": (78, 92, 112),
            "outline": (47, 60, 78),
        },
        3: {
            "background": (7, 10, 24),
            "panel": (14, 18, 38),
            "line": (29, 191, 255),
            "text": (214, 252, 255),
            "muted": (116, 220, 231),
            "outline": (73, 245, 255),
        },
    }

    TYPE_COLORS = {
        "normal": (72, 126, 214),
        "priority": (43, 190, 124),
        "restricted": (237, 145, 45),
        "blocked": (104, 112, 125),
    }

    DRONE_COLORS = (
        (54, 162, 235),
        (225, 79, 145),
        (152, 104, 230),
        (16, 185, 129),
        (245, 158, 11),
        (239, 68, 68),
    )

    def __init__(
        self,
        network: DroneNetwork,
        drones: list[Drone],
    ) -> None:
        """Prepare the visual state for a planned simulation."""
        self.network = network
        self.drones = drones
        self.pg: Any = None
        self.screen: Any = None
        self.clock: Any = None
        self.font: Any = None
        self.small_font: Any = None
        self.title_font: Any = None

        self.running = False
        self.playing = True
        self.fullscreen = False
        self.theme_number = 1
        self.current_turn = 0
        self.turn_progress = 0.0
        self.max_turn = max(
            (drone.schedule[-1][0] for drone in drones if drone.schedule),
            default=0,
        )
        self.schedules = {
            drone.id: dict(drone.schedule)
            for drone in drones
        }
        self.link_points = self._build_link_points()
        self.world_center, self.world_size = self._world_bounds()

    @staticmethod
    def _link_key(first: str, second: str) -> str:
        """Return one shared name for a two-way connection."""
        return f"{first}-{second}" if first < second else f"{second}-{first}"

    def _build_link_points(self) -> dict[str, tuple[float, float]]:
        """Find the middle point of every connection."""
        points: dict[str, tuple[float, float]] = {}
        for connection in self.network.connections:
            first = self.network.zones[connection.zone1]
            second = self.network.zones[connection.zone2]
            points[self._link_key(first.name, second.name)] = (
                (first.x + second.x) / 2.0,
                (first.y + second.y) / 2.0,
            )
        return points

    def _world_bounds(
        self,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Find the center and size of the complete map."""
        coordinates = [
            (float(zone.x), float(zone.y))
            for zone in self.network.zones.values()
        ]
        if not coordinates:
            return (0.0, 0.0), (1.0, 1.0)
        x_values = [point[0] for point in coordinates]
        y_values = [point[1] for point in coordinates]
        low_x, high_x = min(x_values), max(x_values)
        low_y, high_y = min(y_values), max(y_values)
        return (
            ((low_x + high_x) / 2.0, (low_y + high_y) / 2.0),
            (max(high_x - low_x, 1.0), max(high_y - low_y, 1.0)),
        )

    def _to_screen(self, point: tuple[float, float]) -> tuple[int, int]:
        """Convert a map position into a screen position."""
        width, height = self.screen.get_size()
        graph_width = max(width - self.PANEL_WIDTH - 60, 100)
        graph_height = max(height - 100, 100)
        scale = min(
            graph_width / (self.world_size[0] * 1.15),
            graph_height / (self.world_size[1] * 1.15),
        )
        center_x = self.PANEL_WIDTH + 30 + graph_width / 2.0
        center_y = 40 + graph_height / 2.0
        return (
            round(center_x + (point[0] - self.world_center[0]) * scale),
            round(center_y - (point[1] - self.world_center[1]) * scale),
        )

    def _location(self, name: str) -> Optional[tuple[float, float]]:
        """Return the map position of a zone or connection."""
        if name in self.network.zones:
            zone = self.network.zones[name]
            return float(zone.x), float(zone.y)
        return self.link_points.get(name)

    def _drone_position(
        self,
        drone: Drone,
        simulation_time: float,
    ) -> Optional[tuple[float, float]]:
        """Calculate a drone position during an animated turn."""
        if not drone.schedule or simulation_time > drone.schedule[-1][0]:
            return None
        start_turn = int(math.floor(simulation_time))
        end_turn = min(start_turn + 1, drone.schedule[-1][0])
        progress = simulation_time - start_turn
        schedule = self.schedules[drone.id]
        start = self._location(schedule[start_turn])
        end = self._location(schedule[end_turn])
        if start is None or end is None:
            return None
        smooth = progress * progress * (3.0 - 2.0 * progress)
        return (
            start[0] + (end[0] - start[0]) * smooth,
            start[1] + (end[1] - start[1]) * smooth,
        )

    @staticmethod
    def _short_name(name: str) -> str:
        """Make a short label for a zone name."""
        parts = name.split("_")
        if len(parts) == 1:
            if len(name) <= 6:
                return name
            digits = "".join(
                character for character in name if character.isdigit()
            )
            return f"{name[:3]}{digits}"
        letters = "".join(part[0] for part in parts if part)
        digits = "".join(
            character for character in name if character.isdigit()
        )
        return f"{letters}{digits}"

    def _zone_color(self, zone: Zone) -> tuple[int, int, int]:
        """Choose the display color of a zone."""
        if zone.color.lower() != "none":
            try:
                color = self.pg.Color(zone.color)
                return color.r, color.g, color.b
            except ValueError:
                pass
        return self.TYPE_COLORS.get(zone.zone_type, self.TYPE_COLORS["normal"])

    def _draw_network(self) -> None:
        """Draw every connection and zone."""
        theme = self.THEMES[self.theme_number]
        for connection in self.network.connections:
            first = self.network.zones[connection.zone1]
            second = self.network.zones[connection.zone2]
            start = self._to_screen((float(first.x), float(first.y)))
            end = self._to_screen((float(second.x), float(second.y)))
            width = min(connection.max_link_capacity + 1, 4)
            self.pg.draw.line(self.screen, theme["line"], start, end, width)

        for zone in self.network.zones.values():
            point = self._to_screen((float(zone.x), float(zone.y)))
            color = self._zone_color(zone)
            self.pg.draw.circle(self.screen, color, point, 18)
            outline = 4 if zone.hub_role is not None else 2
            self.pg.draw.circle(
                self.screen,
                theme["outline"],
                point,
                18,
                outline,
            )
            if zone.zone_type == "blocked":
                self.pg.draw.line(
                    self.screen,
                    theme["outline"],
                    (point[0] - 9, point[1] - 9),
                    (point[0] + 9, point[1] + 9),
                    3,
                )
                self.pg.draw.line(
                    self.screen,
                    theme["outline"],
                    (point[0] - 9, point[1] + 9),
                    (point[0] + 9, point[1] - 9),
                    3,
                )
            if zone.hub_role is None:
                label = self.small_font.render(
                    self._short_name(zone.name),
                    True,
                    theme["text"],
                )
                self.screen.blit(
                    label,
                    label.get_rect(center=(point[0], point[1] + 29)),
                )

    def _draw_drones(self, simulation_time: float) -> None:
        """Draw each active drone at its current position."""
        groups: dict[tuple[int, int], list[Drone]] = {}
        for drone in self.drones:
            position = self._drone_position(drone, simulation_time)
            if position is not None:
                point = self._to_screen(position)
                groups.setdefault(point, []).append(drone)

        for point, drones in groups.items():
            for index, drone in enumerate(drones):
                angle = 2.0 * math.pi * index / len(drones)
                radius = 0.0 if len(drones) == 1 else 24.0
                drone_point = (
                    point[0] + round(math.cos(angle) * radius),
                    point[1] + round(math.sin(angle) * radius),
                )
                number = int(drone.id.removeprefix("D"))
                color = self.DRONE_COLORS[
                    (number - 1) % len(self.DRONE_COLORS)
                ]
                self.pg.draw.circle(self.screen, color, drone_point, 11)
                label = self.small_font.render(
                    str(number),
                    True,
                    (255, 255, 255),
                )
                self.screen.blit(label, label.get_rect(center=drone_point))

    def _draw_hubs(self) -> None:
        """Draw labels for the start and end hubs."""
        theme = self.THEMES[self.theme_number]
        for zone in self.network.zones.values():
            if zone.hub_role is None:
                continue
            point = self._to_screen((float(zone.x), float(zone.y)))
            role = zone.hub_role.removesuffix("_hub").upper()
            label = self.small_font.render(
                f"{role}: {zone.name}",
                True,
                theme["text"],
                theme["panel"],
            )
            self.screen.blit(
                label,
                label.get_rect(center=(point[0], point[1] - 31)),
            )

    def _draw_panel(self, simulation_time: float) -> None:
        """Draw simulation details and keyboard controls."""
        theme = self.THEMES[self.theme_number]
        _, height = self.screen.get_size()
        self.pg.draw.rect(
            self.screen,
            theme["panel"],
            (0, 0, self.PANEL_WIDTH, height),
        )
        title = self.title_font.render("Fly-in", True, theme["text"])
        self.screen.blit(title, (20, 20))

        delivered = sum(
            simulation_time >= drone.schedule[-1][0]
            for drone in self.drones
            if drone.schedule
        )
        status = (
            f"Turn  {min(math.ceil(simulation_time), self.max_turn)}"
            f" / {self.max_turn}",
            "Playing" if self.playing else "Paused",
            f"Delivered  {delivered} / {len(self.drones)}",
        )
        for index, line in enumerate(status):
            label = self.font.render(line, True, theme["text"])
            self.screen.blit(label, (20, 78 + index * 25))

        heading = self.font.render("Zone types", True, theme["text"])
        self.screen.blit(heading, (20, 180))
        for index, (zone_type, color) in enumerate(self.TYPE_COLORS.items()):
            y_position = 215 + index * 25
            self.pg.draw.circle(self.screen, color, (29, y_position + 7), 7)
            label = self.small_font.render(zone_type, True, theme["muted"])
            self.screen.blit(label, (44, y_position))

        controls = (
            "Space   Play / pause",
            "←  →       Step turns",
            "R          Replay",
            "1  2  3   Theme",
            "F           Fullscreen",
            "Esc       Windowed mode",
        )
        heading = self.font.render("Controls", True, theme["text"])
        self.screen.blit(heading, (20, 335))
        for index, line in enumerate(controls):
            label = self.small_font.render(line, True, theme["muted"])
            self.screen.blit(label, (20, 370 + index * 25))

    def _draw(self) -> None:
        """Draw one complete animation frame."""
        simulation_time = self.current_turn + self.turn_progress
        theme = self.THEMES[self.theme_number]
        self.screen.fill(theme["background"])
        self._draw_network()
        self._draw_drones(simulation_time)
        self._draw_hubs()
        self._draw_panel(simulation_time)
        self.pg.display.flip()

    def _handle_key(self, key: int) -> None:
        """Handle one keyboard command."""
        if key == self.pg.K_SPACE:
            if self.current_turn >= self.max_turn:
                self.current_turn = 0
            self.playing = not self.playing
        elif key == self.pg.K_RIGHT:
            self.current_turn = min(self.current_turn + 1, self.max_turn)
            self.turn_progress = 0.0
            self.playing = False
        elif key == self.pg.K_LEFT:
            self.current_turn = max(self.current_turn - 1, 0)
            self.turn_progress = 0.0
            self.playing = False
        elif key == self.pg.K_r:
            self.current_turn = 0
            self.turn_progress = 0.0
            self.playing = True
        elif key in (self.pg.K_1, self.pg.K_2, self.pg.K_3):
            self.theme_number = key - self.pg.K_0
        elif key == self.pg.K_f:
            self.fullscreen = not self.fullscreen
            self._set_window()
        elif key == self.pg.K_ESCAPE and self.fullscreen:
            self.fullscreen = False
            self._set_window()

    def _advance(self, elapsed_seconds: float) -> None:
        """Move the animation clock forward."""
        if not self.playing or self.current_turn >= self.max_turn:
            return
        self.turn_progress += elapsed_seconds / self.TURN_SECONDS
        while self.turn_progress >= 1.0:
            self.turn_progress -= 1.0
            self.current_turn += 1
            if self.current_turn >= self.max_turn:
                self.current_turn = self.max_turn
                self.turn_progress = 0.0
                self.playing = False

    def _set_window(self) -> None:
        """Create a window in normal or fullscreen mode."""
        if self.fullscreen:
            self.screen = self.pg.display.set_mode((0, 0), self.pg.FULLSCREEN)
        else:
            self.screen = self.pg.display.set_mode(
                (self.WIDTH, self.HEIGHT),
                self.pg.RESIZABLE,
            )

    def run(self) -> None:
        """Open the window and run the animation loop."""
        os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
        try:
            import pygame
        except ImportError as error:
            raise ImportError(
                "Pygame is required for --visual; run `make install`."
            ) from error

        self.pg = pygame
        try:
            self.pg.init()
            self._set_window()
            self.pg.display.set_caption("Fly-in — Drone Route Visualizer")
            self.clock = self.pg.time.Clock()
            self.font = self.pg.font.SysFont("arial", 17)
            self.small_font = self.pg.font.SysFont("arial", 14)
            self.title_font = self.pg.font.SysFont("arial", 30, bold=True)
            self.running = True
            while self.running:
                elapsed_seconds = self.clock.tick(60) / 1000.0
                for event in self.pg.event.get():
                    if event.type == self.pg.QUIT:
                        self.running = False
                    elif event.type == self.pg.KEYDOWN:
                        self._handle_key(event.key)
                self._advance(elapsed_seconds)
                self._draw()
        except pygame.error as error:
            raise RuntimeError(
                f"Could not run visualization: {error}"
            ) from error
        finally:
            self.pg.quit()
