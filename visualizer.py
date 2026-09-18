import random
from typing import Optional
import pygame
from pars import Connection, DroneNetwork, Zone, ZoneData


class Particle:

    def __init__(
            self,
            x: float,
            y: float,
            color: tuple[int, int, int]
            ) -> None:
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.life = 255.0
        self.decay = random.uniform(5, 15)
        self.size = random.uniform(2, 5)

    def update(self) -> None:

        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay

    def draw(self, surface: pygame.Surface) -> None:

        if self.life <= 0:
            return

        alpha = max(0, min(255, int(self.life)))
        color_with_alpha = (*self.color, alpha)
        diameter = int(self.size * 2)
        particle_surface = (
            pygame.Surface((diameter, diameter),
                           pygame.SRCALPHA)
                           )
        pygame.draw.circle(
            particle_surface,
            color_with_alpha,
            (int(self.size), int(self.size)),
            int(self.size),
        )
        surface.blit(
            particle_surface,
            (int(self.x - self.size), int(self.y - self.size))
        )


class GUI_Visualizer:

    def __init__(
        self, network: DroneNetwork, all_paths: list[list[tuple[int, str]]]
    ) -> None:
        self.network = network
        self.paths = all_paths

        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)

        self.width = 1280
        self.height = 720
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Drone Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Courier New", 14, bold=True)
        self.large_font = pygame.font.SysFont("Courier New", 20, bold=True)

        self.turn = 0
        self.max_turn = max(
            (path[-1][0] for path in self.paths if path),
            default=0
            )
        self.is_playing = False
        self.turn_duration_ms = 800
        self.anim_progress = 0.0

        self.zoom = 1.0
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        self.particles: list[Particle] = []
        self.stars = [
            (
                random.randint(0, self.width),
                random.randint(0, self.height),
                random.uniform(0.1, 0.4),
            )
            for _ in range(150)
        ]
        self.completed_drones: set[int] = set()

        self.raw_drone_sprite: Optional[pygame.Surface] = None
        self.cached_sprite: Optional[pygame.Surface] = None
        self.cached_zoom = 0.0
        self.current_sprite_index = 1

        self._apply_theme(4)
        self._load_sprite(self.current_sprite_index)
        self._calculate_scale()
        self._run()

    def _apply_theme(self, theme_index: int) -> None:
        """Apply one of the built-in color themes."""

        if theme_index == 5:
            self.BG_COLOR = (20, 15, 30)
            self.LINE_COLOR = (255, 50, 150)
            self.TEXT_COLOR = (0, 255, 255)
            self.DRONE_COLOR = (0, 255, 255)
            self.GRID_COLOR = (45, 25, 60)
            self.STAR_COLOR = (255, 100, 200)
        elif theme_index == 6:
            self.BG_COLOR = (5, 10, 5)
            self.LINE_COLOR = (0, 150, 0)
            self.TEXT_COLOR = (0, 255, 0)
            self.DRONE_COLOR = (0, 255, 0)
            self.GRID_COLOR = (10, 30, 10)
            self.STAR_COLOR = (0, 100, 0)
        else:
            self.BG_COLOR = (15, 15, 20)
            self.LINE_COLOR = (70, 70, 90)
            self.TEXT_COLOR = (240, 240, 240)
            self.DRONE_COLOR = (200, 220, 255)
            self.GRID_COLOR = (25, 25, 35)
            self.STAR_COLOR = (100, 100, 120)

    def _load_sprite(self, index: int) -> None:

        self.current_sprite_index = index
        filenames = [f"graphics/drone{index}.png"]
        if index == 1:
            filenames.append("graphics/drone.png")

        self.raw_drone_sprite = None
        for filename in filenames:
            try:
                self.raw_drone_sprite = (
                    pygame.image.load(filename)
                    .convert_alpha()
                    )
                break
            except FileNotFoundError:
                continue

        self.cached_zoom = 0.0
        self.cached_sprite = None

    def _calculate_scale(self) -> None:

        if not self.network.zones:
            self.min_x = self.max_x = self.min_y = self.max_y = 0
            self.base_pad = 150
            return

        xs = [zone.x for zone in self.network.zones.values()]
        ys = [zone.y for zone in self.network.zones.values()]
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)
        self.base_pad = 150

    def _get_coords(self, zone_name: str) -> tuple[float, float]:

        zone = self.network.zones[zone_name]
        x_range = self.max_x - self.min_x or 1
        y_range = self.max_y - self.min_y or 1

        base_x = self.base_pad + (zone.x - self.min_x) / x_range * (
            self.width - 2 * self.base_pad
        )
        base_y = self.base_pad + (zone.y - self.min_y) / y_range * (
            self.height - 2 * self.base_pad - 150
        )

        screen_x = (
            (base_x - self.width / 2) *
            self.zoom + self.width / 2 + self.cam_x
            )
        screen_y = (
            (base_y - self.height / 2) *
            self.zoom + self.height / 2 + self.cam_y
            )
        return screen_x, screen_y

    def _get_world_pos(self, loc_str: str) -> tuple[float, float]:

        if "-" in loc_str:
            zone1, zone2 = loc_str.split("-")
            x1, y1 = self._get_coords(zone1)
            x2, y2 = self._get_coords(zone2)
            return (x1 + x2) / 2.0, (y1 + y2) / 2.0
        return self._get_coords(loc_str)

    def _lerp(self, start: float, end: float, t: float) -> float:

        return start + (end - start) * t

    def _get_drone_pos(
        self, path: list[tuple[int, str]], exact_time: float
    ) -> tuple[float, float]:

        if not path:
            return 0.0, 0.0
        if exact_time <= path[0][0]:
            return self._get_world_pos(path[0][1])
        if exact_time >= path[-1][0]:
            return self._get_world_pos(path[-1][1])

        for index in range(len(path) - 1):
            time_1, location_1 = path[index]
            time_2, location_2 = path[index + 1]
            if time_1 <= exact_time <= time_2:
                gap = time_2 - time_1
                if gap == 0:
                    return self._get_world_pos(location_2)
                fraction = (exact_time - time_1) / gap
                start_x, start_y = self._get_world_pos(location_1)
                end_x, end_y = self._get_world_pos(location_2)
                return self._lerp(start_x, end_x, fraction), self._lerp(
                    start_y, end_y, fraction
                )

        return self._get_world_pos(path[-1][1])

    def _draw_background(self) -> None:

        self.screen.fill(self.BG_COLOR)
        for star_x, star_y, depth in self.stars:
            px = (star_x + self.cam_x * depth) % self.width
            py = (star_y + self.cam_y * depth) % self.height
            pygame.draw.circle(
                self.screen,
                self.STAR_COLOR,
                (int(px), int(py)),
                max(1, int(2 * depth))
            )

        grid_size = int(60 * self.zoom)
        if grid_size > 10:
            offset_x = int(self.cam_x) % grid_size
            offset_y = int(self.cam_y) % grid_size
            for x in range(offset_x, self.width, grid_size):
                pygame.draw.line(
                    self.screen, self.GRID_COLOR, (x, 0), (x, self.height), 1
                )
            for y in range(offset_y, self.height, grid_size):
                pygame.draw.line(
                    self.screen, self.GRID_COLOR, (0, y), (self.width, y), 1
                )

    def _draw_static_network(self) -> None:

        for connection in self.network.connections:
            x1, y1 = self._get_coords(connection.zone1)
            x2, y2 = self._get_coords(connection.zone2)
            pygame.draw.aaline(
                self.screen,
                self.LINE_COLOR,
                (x1, y1),
                (x2, y2)
                )

        for zone_name, zone in self.network.zones.items():
            x, y = self._get_coords(zone_name)
            color_map = {
                "red": (255, 70, 70),
                "blue": (70, 130, 255),
                "green": (70, 255, 70),
                "yellow": (255, 230, 70),
                "gray": (120, 120, 130),
                "none": (180, 180, 190),
            }
            node_color = color_map.get(zone.color.lower(), (180, 180, 190))
            radius = int(25 * self.zoom)
            if radius <= 5:
                continue

            glow_surface = pygame.Surface(
                (radius * 3, radius * 3),
                pygame.SRCALPHA
                )
            pygame.draw.circle(
                glow_surface,
                (*node_color, 30),
                (radius * 1.5, radius * 1.5),
                radius * 1.5,
            )
            self.screen.blit(
                glow_surface,
                (x - radius * 1.5, y - radius * 1.5)
                )

            outline_width = max(1, int(2 * self.zoom))
            pygame.draw.circle(
                self.screen,
                node_color,
                (int(x), int(y)),
                radius,
                outline_width,
            )
            pygame.draw.circle(
                self.screen,
                (30, 30, 35),
                (int(x), int(y)),
                radius - outline_width,
            )

            name_text = self.font.render(
                zone_name,
                True,
                self.TEXT_COLOR
                )
            self.screen.blit(
                name_text,
                name_text.get_rect(center=(x, y - radius - 15))
                )
            cap_text = self.font.render(
                f"C:{zone.max_drones}",
                True, node_color
                )
            self.screen.blit(cap_text, cap_text.get_rect(center=(x, y)))

    def _render_drones(self) -> None:

        exact_time = self.turn + self.anim_progress
        for drone_index, path in enumerate(self.paths):
            if not path:
                continue

            drone_color = self.DRONE_COLOR
            offset_x = (drone_index % 3) * (12 * self.zoom) - (12 * self.zoom)
            offset_y = (drone_index % 3) * (12 * self.zoom) - (12 * self.zoom)

            if self.is_playing and exact_time > path[0][0]:
                trail_length = 5
                for step in range(trail_length, 0, -1):
                    past_time = max(path[0][0], exact_time - (step * 0.05))
                    trail_x, trail_y = self._get_drone_pos(path, past_time)
                    trail_alpha = int(255 * (1 - (step / trail_length)))
                    trail_radius = max(
                        2, int(6 * self.zoom * (1 - (step / trail_length)))
                    )
                    trail_surface = pygame.Surface(
                        (trail_radius * 2, trail_radius * 2), pygame.SRCALPHA
                    )
                    pygame.draw.circle(
                        trail_surface,
                        (*drone_color, trail_alpha),
                        (trail_radius, trail_radius),
                        trail_radius,
                    )
                    self.screen.blit(
                        trail_surface,
                        (
                            trail_x + offset_x - trail_radius,
                            trail_y + offset_y - trail_radius,
                        ),
                    )

            x, y = self._get_drone_pos(path, exact_time)
            glow_radius = int(22 * self.zoom)
            if glow_radius > 0:
                glow_surface = pygame.Surface(
                    (glow_radius * 2, glow_radius * 2), pygame.SRCALPHA
                )
                pygame.draw.circle(
                    glow_surface,
                    (*drone_color, 60),
                    (glow_radius, glow_radius),
                    glow_radius,
                )
                self.screen.blit(
                    glow_surface,
                    (x + offset_x - glow_radius, y + offset_y - glow_radius),
                )

            if self.raw_drone_sprite is not None:
                target_size = max(16, int(48 * self.zoom))
                if self.cached_zoom != self.zoom or self.cached_sprite is None:
                    self.cached_sprite = pygame.transform.smoothscale(
                        self.raw_drone_sprite,
                        (target_size, target_size),
                    )
                    self.cached_zoom = self.zoom

                sprite = self.cached_sprite
                if sprite is not None:
                    sprite_rect = sprite.get_rect(
                        center=(int(x + offset_x), int(y + offset_y))
                    )
                    self.screen.blit(sprite, sprite_rect)
            else:
                center = (int(x + offset_x), int(y + offset_y))
                pygame.draw.circle(
                    self.screen,
                    (255, 255, 255),
                    center,
                    max(2, int(4 * self.zoom))
                )
                pygame.draw.circle(
                    self.screen,
                    drone_color,
                    center,
                    max(3, int(7 * self.zoom)), 1
                )

            drone_text = self.font.render(
                f"D{drone_index + 1}",
                True, self.TEXT_COLOR
                )
            self.screen.blit(
                drone_text,
                (x + offset_x - 10, y + offset_y - (25 * self.zoom))
            )

            if (
                self.is_playing
                and drone_index not in self.completed_drones
                and exact_time >= path[-1][0]
            ):
                self.completed_drones.add(drone_index)
                end_x, end_y = self._get_world_pos(path[-1][1])
                for _ in range(25):
                    self.particles.append(Particle(end_x, end_y, drone_color))

    def _render_particles(self) -> None:

        for particle in reversed(self.particles):
            particle.update()
            particle.draw(self.screen)
            if particle.life <= 0:
                self.particles.remove(particle)

    def _draw_hud(self) -> None:

        hud_surface = pygame.Surface((self.width, 100), pygame.SRCALPHA)
        pygame.draw.rect(
            hud_surface, (10, 10, 15, 230), hud_surface.get_rect()
            )
        pygame.draw.line(hud_surface, (70, 70, 90), (0, 0), (self.width, 0), 2)
        self.screen.blit(hud_surface, (0, self.height - 100))

        turn_text = self.large_font.render(
            f"TURN: {self.turn} / {self.max_turn}",
            True,
            self.TEXT_COLOR,
        )
        self.screen.blit(turn_text, (30, self.height - 70))

        status = ">> PLAYING" if self.is_playing else "|| PAUSED"
        status_color = (0, 255, 120) if self.is_playing else (255, 200, 50)
        status_text = self.font.render(status, True, status_color)
        self.screen.blit(status_text, (30, self.height - 40))

        bar_width = 400
        bar_x = self.width // 2 - bar_width // 2
        bar_y = self.height - 60
        pygame.draw.rect(
            self.screen,
            (30, 30, 40),
            (bar_x, bar_y, bar_width, 12),
            border_radius=6
        )

        progress_ratio = (
            0.0
            if self.max_turn <= 0
            else min(1.0, (self.turn + self.anim_progress) / self.max_turn)
        )
        current_bar_width = int(bar_width * progress_ratio)
        if current_bar_width > 0:
            pygame.draw.rect(
                self.screen,
                self.DRONE_COLOR,
                (bar_x, bar_y, current_bar_width, 12),
                border_radius=6,
            )

        controls = [
            "[SPACE] Play/Pause | [R] Restart",
            "[1-3] Sprites | [4-6] Themes",
            "[LEFT/RIGHT] Step Turns",
            "[MOUSE] Drag/Scroll",
        ]
        for index, text in enumerate(controls):
            ctrl_text = self.font.render(text, True, (160, 160, 170))
            self.screen.blit(
                ctrl_text, (self.width - 290, self.height - 90 + (index * 18))
            )

    def _run(self) -> None:

        running = True
        dt = 0.0
        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if pygame.K_1 <= event.key <= pygame.K_3:
                            self._load_sprite(event.key - pygame.K_0)
                        elif pygame.K_4 <= event.key <= pygame.K_6:
                            self._apply_theme(event.key - pygame.K_0)
                        elif event.key == pygame.K_SPACE:
                            self.is_playing = not self.is_playing
                        elif event.key == pygame.K_r:
                            self.is_playing = False
                            self.turn = 0
                            self.anim_progress = 0.0
                            self.completed_drones.clear()
                            self.particles.clear()
                        elif event.key == pygame.K_RIGHT:
                            self.is_playing = False
                            self.anim_progress = 0.0
                            if self.turn < self.max_turn:
                                self.turn += 1
                        elif event.key == pygame.K_LEFT:
                            self.is_playing = False
                            self.anim_progress = 0.0
                            if self.turn > 0:
                                self.turn -= 1
                                if self.turn < self.max_turn:
                                    self.completed_drones.clear()
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            self.is_dragging = True
                            self.drag_start_x, self.drag_start_y = event.pos
                        elif event.button == 4:
                            self.zoom = min(3.0, self.zoom + 0.1)
                        elif event.button == 5:
                            self.zoom = max(0.3, self.zoom - 0.1)
                    elif event.type == pygame.MOUSEBUTTONUP:
                        if event.button == 1:
                            self.is_dragging = False
                    elif event.type == pygame.MOUSEMOTION and self.is_dragging:
                        dx = event.pos[0] - self.drag_start_x
                        dy = event.pos[1] - self.drag_start_y
                        self.cam_x += dx
                        self.cam_y += dy
                        self.drag_start_x, self.drag_start_y = event.pos

                if self.is_playing:
                    self.anim_progress += dt / self.turn_duration_ms
                    if self.anim_progress >= 1.0:
                        self.anim_progress = 0.0
                        if self.turn < self.max_turn:
                            self.turn += 1
                        else:
                            self.is_playing = False
                elif not self.is_dragging:
                    self.anim_progress = 0.0

                self._draw_background()
                self._draw_static_network()
                self._render_drones()
                self._render_particles()
                self._draw_hud()

                pygame.display.flip()
                dt = self.clock.tick(60)
        except Exception as error:
            print(f"Visualizer error: {error}")
        finally:
            pygame.quit()


if __name__ == "__main__":
    test_network = DroneNetwork()

    start_data: ZoneData = {
        "hub_role": "start_hub",
        "x": 0,
        "y": 0,
        "zone_type": "normal",
        "max_drones": 5,
        "color": "green",
    }
    mid_data: ZoneData = {
        "hub_role": "normal",
        "x": 5,
        "y": 5,
        "zone_type": "normal",
        "max_drones": 2,
        "color": "blue",
    }
    end_data: ZoneData = {
        "hub_role": "end_hub",
        "x": 10,
        "y": 10,
        "zone_type": "normal",
        "max_drones": 5,
        "color": "yellow",
    }

    test_network.add_zone(Zone("hub_start", start_data))
    test_network.add_zone(Zone("waypoint", mid_data))
    test_network.add_zone(Zone("hub_end", end_data))

    test_network.add_connection(
        Connection(
            {
                "zone1": "hub_start",
                "zone2": "waypoint",
                "max_link_capacity": 2,
            }
        )
    )
    test_network.add_connection(
        Connection(
            {
                "zone1": "waypoint",
                "zone2": "hub_end",
                "max_link_capacity": 2,
            }
        )
    )

    test_paths = [
        [
            (0, "hub_start"),
            (1, "hub_start-waypoint"),
            (2, "waypoint"),
            (3, "waypoint-hub_end"),
            (4, "hub_end"),
        ],
        [
            (0, "hub_start"),
            (1, "hub_start"),
            (2, "hub_start-waypoint"),
            (3, "waypoint"),
            (4, "waypoint-hub_end"),
            (5, "hub_end"),
        ],
    ]

    print("Launching advanced visualizer test...")
    GUI_Visualizer(network=test_network, all_paths=test_paths)
