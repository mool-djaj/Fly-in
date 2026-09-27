import random
import sys

import pygame

from gui_controls import GUI_Controls
from pars import DroneNetwork
from path_find import PathLog

Color = tuple[int, int, int]


class Particle:
    """Small completion particle used by the visualizer."""

    def __init__(self, x: float, y: float, color: Color) -> None:
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.life = 255.0
        self.decay = random.uniform(5, 15)
        self.size = random.uniform(2, 5)

    def update(self) -> None:
        """Advance one particle frame."""
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the particle when it is still alive."""
        if self.life <= 0:
            return
        alpha = max(0, min(255, int(self.life)))
        color = (*self.color, alpha)
        diameter = max(1, int(self.size * 2))
        particle = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        pygame.draw.circle(
            particle,
            color,
            (diameter // 2, diameter // 2),
            max(1, int(self.size)),
        )
        surface.blit(
            particle,
            (int(self.x - self.size), int(self.y - self.size)),
        )


class GUI_Visualizer:
    """Interactive visualization of the network and planned drone paths."""

    def __init__(
        self,
        network: DroneNetwork,
        all_paths: list[PathLog],
    ) -> None:
        self.network = network
        self.paths = all_paths
        pygame.display.init()
        pygame.font.init()
        self.width = 1080
        self.height = 720
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Fly-In Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Courier New", 14, bold=True)
        self.large_font = pygame.font.SysFont("Courier New", 20, bold=True)
        self.turn = 0
        self.max_turn = max(
            (path[-1][0] for path in self.paths if path),
            default=0,
        )
        self.is_playing = False
        self.turn_duration_ms = 800
        self.anim_progress = 0.0
        self.ctrl = GUI_Controls(network, self.width, self.height)
        self.particles: list[Particle] = []
        self.completed_drones: set[int] = set()
        self._run()

    def _draw_background(self) -> None:
        """Draw the panning and zooming background grid."""
        self.screen.fill(self.ctrl.BG_COLOR)
        grid_size = int(60 * self.ctrl.zoom)
        if grid_size <= 10:
            return
        offset_x = int(self.ctrl.cam_x) % grid_size
        offset_y = int(self.ctrl.cam_y) % grid_size
        for x in range(offset_x, self.width, grid_size):
            pygame.draw.line(
                self.screen,
                self.ctrl.GRID_COLOR,
                (x, 0),
                (x, self.height),
                1,
            )
        for y in range(offset_y, self.height, grid_size):
            pygame.draw.line(
                self.screen,
                self.ctrl.GRID_COLOR,
                (0, y),
                (self.width, y),
                1,
            )

    @staticmethod
    def _zone_color(color_name: str) -> Color:
        """Map subject color names to Pygame RGB values."""
        colors: dict[str, Color] = {
            "red": (255, 70, 70),
            "blue": (70, 130, 255),
            "green": (70, 255, 70),
            "yellow": (255, 230, 70),
            "gray": (120, 120, 130),
            "none": (180, 180, 190),
            "purple": (180, 80, 255),
            "black": (50, 50, 60),
            "brown": (150, 100, 60),
            "maroon": (140, 30, 60),
            "orange": (255, 150, 50),
            "gold": (255, 215, 0),
            "darkred": (120, 0, 0),
            "violet": (200, 130, 255),
            "crimson": (220, 20, 60),
            "rainbow": (0, 255, 255),
        }
        return colors.get(color_name.lower(), (180, 180, 190))

    def _draw_static_network(self) -> None:
        """Draw connections and zones."""
        line_width = max(2, int(6 * self.ctrl.zoom))
        for connection in self.network.connections:
            x1, y1 = self.ctrl.get_coords(connection.zone1)
            x2, y2 = self.ctrl.get_coords(connection.zone2)
            pygame.draw.line(
                self.screen,
                self.ctrl.LINE_COLOR,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                line_width,
            )

        for zone_name, zone in self.network.zones.items():
            x, y = self.ctrl.get_coords(zone_name)
            color = self._zone_color(zone.color)
            radius = min(25, max(6, int(12 * self.ctrl.zoom)))
            outline = min(4, max(1, int(2 * self.ctrl.zoom)))
            pygame.draw.circle(
                self.screen,
                color,
                (int(x), int(y)),
                radius,
                outline,
            )
            pygame.draw.circle(
                self.screen,
                (30, 30, 35),
                (int(x), int(y)),
                max(1, radius - outline),
            )
            name_text = self.font.render(
                zone_name,
                True,
                self.ctrl.TEXT_COLOR,
            )
            self.screen.blit(
                name_text,
                name_text.get_rect(center=(x, y - radius - 15)),
            )
            capacity = "∞" if zone.hub_role else str(zone.max_drones)
            cap_text = self.font.render(f"C:{capacity}", True, color)
            self.screen.blit(cap_text, cap_text.get_rect(center=(x, y)))

    def _render_drones(self) -> None:
        """Draw all drones at the current animation time."""
        exact_time = self.turn + self.anim_progress
        for index, path in enumerate(self.paths):
            if not path:
                continue
            if exact_time < path[0][0]:
                continue
            if index in self.completed_drones:
                continue

            x, y = self.ctrl.get_drone_pos(path, exact_time)
            color = self.ctrl.DRONE_COLOR
            center = (int(x), int(y))
            inner = min(10, max(2, int(4 * self.ctrl.zoom)))
            outer = min(18, max(3, int(8 * self.ctrl.zoom)))
            border = min(3, max(1, int(2 * self.ctrl.zoom)))
            pygame.draw.circle(self.screen, (255, 255, 255), center, inner)
            pygame.draw.circle(self.screen, color, center, outer, border)
            label = self.font.render(
                f"D{index + 1}",
                True,
                self.ctrl.TEXT_COLOR,
            )
            self.screen.blit(
                label,
                label.get_rect(center=(x, y - outer - 15)),
            )

            if self.is_playing and exact_time >= path[-1][0]:
                self.completed_drones.add(index)
                end_x, end_y = self.ctrl.get_world_pos(path[-1][1])
                for _ in range(25):
                    self.particles.append(Particle(end_x, end_y, color))

    def _render_particles(self) -> None:
        """Update and draw completion particles."""
        alive: list[Particle] = []
        for particle in self.particles:
            particle.update()
            particle.draw(self.screen)
            if particle.life > 0:
                alive.append(particle)
        self.particles = alive

    def _draw_hud(self) -> None:
        """Draw current turn and controls."""
        hud = pygame.Surface((self.width, 100), pygame.SRCALPHA)
        pygame.draw.rect(hud, (10, 10, 15, 230), hud.get_rect())
        self.screen.blit(hud, (0, self.height - 100))
        turn_label = self.large_font.render(
            f"TURN: {self.turn} / {self.max_turn}",
            True,
            self.ctrl.TEXT_COLOR,
        )
        self.screen.blit(turn_label, (30, self.height - 70))
        status = ">> PLAYING" if self.is_playing else "|| PAUSED"
        status_label = self.font.render(
            status,
            True,
            self.ctrl.TEXT_COLOR,
        )
        self.screen.blit(status_label, (30, self.height - 40))
        controls = (
            "[SPACE] Play/Pause | [R] Restart | [F] Fullscreen | "
            "[ARROWS] Step | [MOUSE] Pan/Zoom"
        )
        control_label = self.font.render(
            controls,
            True,
            (160, 160, 170),
        )
        self.screen.blit(control_label, (340, self.height - 55))

    def _handle_key(self, key: int) -> None:
        """Apply one keyboard action."""
        if pygame.K_1 <= key <= pygame.K_3:
            self.ctrl.apply_theme(key - pygame.K_0)
        elif key == pygame.K_SPACE:
            self.is_playing = not self.is_playing
        elif key == pygame.K_r:
            self.is_playing = False
            self.turn = 0
            self.anim_progress = 0.0
            self.completed_drones.clear()
            self.particles.clear()
        elif key == pygame.K_RIGHT:
            self.is_playing = False
            self.anim_progress = 0.0
            self.turn = min(self.max_turn, self.turn + 1)
        elif key == pygame.K_LEFT:
            self.is_playing = False
            self.anim_progress = 0.0
            self.turn = max(0, self.turn - 1)
            self.completed_drones.clear()
        elif key == pygame.K_f:
            pygame.display.toggle_fullscreen()

    def _run(self) -> None:
        """Run the Pygame event and drawing loop."""
        running = True
        dt = 0.0
        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    self.ctrl.handle_mouse(event)
                    if event.type == pygame.KEYDOWN:
                        self._handle_key(event.key)

                if self.is_playing:
                    self.anim_progress += dt / self.turn_duration_ms
                    if self.anim_progress >= 1.0:
                        self.anim_progress = 0.0
                        if self.turn < self.max_turn:
                            self.turn += 1
                        else:
                            self.is_playing = False
                elif not self.ctrl.is_dragging:
                    self.anim_progress = 0.0

                self._draw_background()
                self._draw_static_network()
                self._render_drones()
                self._render_particles()
                self._draw_hud()
                pygame.display.flip()
                dt = self.clock.tick(60)
        except pygame.error as error:
            print(f"Visualizer error: {error}", file=sys.stderr)
        finally:
            pygame.quit()
