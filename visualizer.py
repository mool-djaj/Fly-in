import random
import pygame
from pars import DroneNetwork
from gui_controls import GUI_Controls

class Particle:
    def __init__(self, x: float, y: float, color: tuple[int, int, int]) -> None:
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
        particle_surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        pygame.draw.circle(
            particle_surface,
            color_with_alpha,
            (int(self.size), int(self.size)),
            int(self.size),
        )
        surface.blit(particle_surface, (int(self.x - self.size), int(self.y - self.size)))


class GUI_Visualizer:
    def __init__(self, network: DroneNetwork, all_paths: list[list[tuple[int, str]]]) -> None:
        self.network = network
        self.paths = all_paths

        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)

        self.width = 1080
        self.height = 720
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Fly-In Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Courier New", 14, bold=True)
        self.large_font = pygame.font.SysFont("Courier New", 20, bold=True)

        self.turn = 0
        self.max_turn = max((path[-1][0] for path in self.paths if path), default=0)
        self.is_playing = False
        self.turn_duration_ms = 800
        self.anim_progress = 0.0

        # Import all the background math and mouse/theme controllers
        self.ctrl = GUI_Controls(network, self.width, self.height)
        self.particles: list[Particle] = []
        self.completed_drones: set[int] = set()

        self._run()

    def _draw_background(self) -> None:
        self.screen.fill(self.ctrl.BG_COLOR)

        grid_size = int(60 * self.ctrl.zoom)
        if grid_size > 10:
            offset_x = int(self.ctrl.cam_x) % grid_size
            offset_y = int(self.ctrl.cam_y) % grid_size
            for x in range(offset_x, self.width, grid_size):
                pygame.draw.line(self.screen, self.ctrl.GRID_COLOR, (x, 0), (x, self.height), 1)
            for y in range(offset_y, self.height, grid_size):
                pygame.draw.line(self.screen, self.ctrl.GRID_COLOR, (0, y), (self.width, y), 1)

    def _draw_static_network(self) -> None:
        # 1. Wires continue to scale infinitely based on zoom
        line_thickness = max(2, int(6 * self.ctrl.zoom))
        for connection in self.network.connections:
            x1, y1 = self.ctrl.get_coords(connection.zone1)
            x2, y2 = self.ctrl.get_coords(connection.zone2)
            pygame.draw.line(self.screen, self.ctrl.LINE_COLOR, (int(x1), int(y1)), (int(x2), int(y2)), line_thickness)

        for zone_name, zone in self.network.zones.items():
            x, y = self.ctrl.get_coords(zone_name)
            color_map = {
                "red": (255, 70, 70), "blue": (70, 130, 255), "green": (70, 255, 70),
                "yellow": (255, 230, 70), "gray": (120, 120, 130), "none": (180, 180, 190),
            }
            node_color = color_map.get(zone.color.lower(), (180, 180, 190))
            
            # 2. THE LOCK: Room radius will never exceed 25 pixels, regardless of zoom
            radius = min(25, max(6, int(12 * self.ctrl.zoom)))
            
            glow_size = int(radius * 3)
            if glow_size > 5:
                glow_surface = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, (*node_color, 30), (glow_size // 2, glow_size // 2), glow_size // 2)
                self.screen.blit(glow_surface, (x - glow_size // 2, y - glow_size // 2))

            # 3. Outline thickness locks at 4 pixels
            outline_width = min(4, max(1, int(2 * self.ctrl.zoom)))
            pygame.draw.circle(self.screen, node_color, (int(x), int(y)), radius, outline_width)
            pygame.draw.circle(self.screen, (30, 30, 35), (int(x), int(y)), radius - outline_width)

            name_text = self.font.render(zone_name, True, self.ctrl.TEXT_COLOR)
            self.screen.blit(name_text, name_text.get_rect(center=(x, y - radius - 15)))
            
            cap_text = self.font.render(f"C:{zone.max_drones}", True, node_color)
            self.screen.blit(cap_text, cap_text.get_rect(center=(x, y)))

    def _render_drones(self) -> None:
        exact_time = self.turn + self.anim_progress
        for drone_index, path in enumerate(self.paths):
            if not path: continue

            drone_color = self.ctrl.DRONE_COLOR

            if self.is_playing and exact_time > path[0][0]:
                trail_length = 5
                for step in range(trail_length, 0, -1):
                    past_time = max(path[0][0], exact_time - (step * 0.05))
                    trail_x, trail_y = self.ctrl.get_drone_pos(path, past_time)
                    trail_alpha = int(255 * (1 - (step / trail_length)))
                    trail_radius = min(10, max(2, int(4 * self.ctrl.zoom * (1 - (step / trail_length)))))
                    trail_surface = pygame.Surface((trail_radius * 2, trail_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(trail_surface, (*drone_color, trail_alpha), (trail_radius, trail_radius), trail_radius)
                    self.screen.blit(trail_surface, (trail_x - trail_radius, trail_y - trail_radius))

            x, y = self.ctrl.get_drone_pos(path, exact_time)
            
            glow_radius = min(35, int(15 * self.ctrl.zoom))
            if glow_radius > 0:
                glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, (*drone_color, 60), (glow_radius, glow_radius), glow_radius)
                self.screen.blit(glow_surface, (x - glow_radius, y - glow_radius))

            center = (int(x), int(y))
            inner_radius = min(10, max(2, int(4 * self.ctrl.zoom)))
            outer_radius = min(18, max(3, int(8 * self.ctrl.zoom)))
            border_thickness = min(3, max(1, int(2 * self.ctrl.zoom)))

            pygame.draw.circle(self.screen, (255, 255, 255), center, inner_radius)
            pygame.draw.circle(self.screen, drone_color, center, outer_radius, border_thickness)

            # --- THE FIX: Locked exactly to the individual drone ---
            drone_text = self.font.render(f"D{drone_index + 1}", True, self.ctrl.TEXT_COLOR)
            
            # The name is locked perfectly centered, exactly 15 pixels above the drone's outer edge
            text_rect = drone_text.get_rect(center=(x, y - outer_radius - 15))
            self.screen.blit(drone_text, text_rect)
            # --------------------------------------------------------

            if self.is_playing and drone_index not in self.completed_drones and exact_time >= path[-1][0]:
                self.completed_drones.add(drone_index)
                end_x, end_y = self.ctrl.get_world_pos(path[-1][1])
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
        pygame.draw.rect(hud_surface, (10, 10, 15, 230), hud_surface.get_rect())
        pygame.draw.line(hud_surface, self.ctrl.LINE_COLOR, (0, 0), (self.width, 0), 2)
        self.screen.blit(hud_surface, (0, self.height - 100))

        turn_text = self.large_font.render(f"TURN: {self.turn} / {self.max_turn}", True, self.ctrl.TEXT_COLOR)
        self.screen.blit(turn_text, (30, self.height - 70))

        status = ">> PLAYING" if self.is_playing else "|| PAUSED"
        status_color = (0, 255, 120) if self.is_playing else (255, 200, 50)
        status_text = self.font.render(status, True, status_color)
        self.screen.blit(status_text, (30, self.height - 40))

        bar_width = 400
        bar_x = self.width // 2 - bar_width // 2
        bar_y = self.height - 60
        pygame.draw.rect(self.screen, (30, 30, 40), (bar_x, bar_y, bar_width, 12), border_radius=6)

        progress_ratio = 0.0 if self.max_turn <= 0 else min(1.0, (self.turn + self.anim_progress) / self.max_turn)
        current_bar_width = int(bar_width * progress_ratio)
        if current_bar_width > 0:
            pygame.draw.rect(self.screen, self.ctrl.DRONE_COLOR, (bar_x, bar_y, current_bar_width, 12), border_radius=6)

        controls = [
            "[SPACE] Play | [R] Restart",
            "[1-3] Themes | [F] Fullscreen",
            "[L/R Arrows] Step | [MOUSE] Drag Map & Scroll Zoom",
        ]
        for index, text in enumerate(controls):
            ctrl_text = self.font.render(text, True, (160, 160, 170))
            self.screen.blit(ctrl_text, (self.width - 290, self.height - 90 + (index * 18)))

    def _run(self) -> None:
        running = True
        dt = 0.0
        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        
                    self.ctrl.handle_mouse(event)
                    
                    if event.type == pygame.KEYDOWN:
                        if pygame.K_1 <= event.key <= pygame.K_3:
                            self.ctrl.apply_theme(event.key - pygame.K_0)
                        elif event.key == pygame.K_SPACE:
                            self.is_playing = not self.is_playing
                        elif event.key == pygame.K_r:
                            self.is_playing, self.turn, self.anim_progress = False, 0, 0.0
                            self.completed_drones.clear()
                            self.particles.clear()
                        elif event.key == pygame.K_RIGHT:
                            self.is_playing, self.anim_progress = False, 0.0
                            if self.turn < self.max_turn: self.turn += 1
                        elif event.key == pygame.K_LEFT:
                            self.is_playing, self.anim_progress = False, 0.0
                            if self.turn > 0:
                                self.turn -= 1
                                self.completed_drones.clear()
                        elif event.key == pygame.K_f:
                            pygame.display.toggle_fullscreen()

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
        except Exception as error:
            print(f"Visualizer error: {error}")
        finally:
            pygame.quit()