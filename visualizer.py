import tkinter as tk
from typing import List, Tuple
from pars import DroneNetwork


class GUI_Visualizer:
    def __init__(self, network: DroneNetwork, all_paths: List[List[Tuple[int, str]]]) -> None:
        self.network = network
        self.paths = all_paths
        self.root = tk.Tk()
        self.root.title("Drone Simulator")
        self.root.geometry("1024x720") # Sets the initia

        self.turn = 0
        self.is_playing = False
        self.speed_ms = 1000  # Default to 1000ms (1 second) per turn
        
        # Calculate the absolute last turn of the simulation
        if self.paths:
            self.max_turn = max([path[-1][0] for path in self.paths if path])
        else:
            self.max_turn = 0

        # Create a canvas that belongs to the 'root' window
        self.canvas = tk.Canvas(self.root, bg="#000000")
        self.canvas.pack(fill=tk.BOTH, expand=True)  
        self._calculate_scale()
        self._draw_static_network()
        self._setup_controls()
        self.root.mainloop()

    def _calculate_scale(self):
        """Finds the min/max X and Y coordinates to scale the map to fit the window."""
        # 1. Extract all X and Y coordinates from the network zones
        xs = [z.x for z in self.network.zones.values()]
        ys = [z.y for z in self.network.zones.values()]
        
        # 2. Find the boundaries of our map
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)
        
        # 3. Add some padding so drones don't fly off the edge of the screen
        self.pad = 190
    

    def _setup_controls(self):
        """Builds the bottom control panel with playback buttons and a speed slider."""
        # 1. Create a Frame to hold the buttons horizontally
        self.control_frame = tk.Frame(self.root, bg="#2d2d2d", pady=10)
        self.control_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # 2. Previous Button
        self.btn_prev = tk.Button(self.control_frame, text="⏪ Prev", command=self.prev_turn, width=10)
        self.btn_prev.pack(side=tk.LEFT, padx=10)

        # 3. Play/Pause Button
        self.btn_play = tk.Button(self.control_frame, text="▶ Play", command=self.toggle_play, width=10)
        self.btn_play.pack(side=tk.LEFT, padx=10)

        # 4. Next Button
        self.btn_next = tk.Button(self.control_frame, text="⏩ Next", command=self.next_turn, width=10)
        self.btn_next.pack(side=tk.LEFT, padx=10)
        
        # 5. Stop/Exit Button
        self.btn_stop = tk.Button(self.control_frame, text="⏹ Exit", command=self.root.destroy, width=10)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        # 6. Speed Slider (Scale)
        self.speed_scale = tk.Scale(self.control_frame, from_=100, to=2000, 
                                    orient=tk.HORIZONTAL, label="Speed (ms)", 
                                    bg="#2d2d2d", fg="white", command=self.update_speed)
        self.speed_scale.set(self.speed_ms)
        self.speed_scale.pack(side=tk.RIGHT, padx=20)

    # --- Button Logic ---
    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.config(text="⏸ Pause")
            self._animate() # Jumpstart the loop
        else:
            self.btn_play.config(text="▶ Play")

    def next_turn(self):
        if self.turn < self.max_turn:
            self.turn += 1
            self.is_playing = False # Pause if user manually clicks next
            self.btn_play.config(text="▶ Play")
            self._render_drones()

    def prev_turn(self):
        if self.turn > 0:
            self.turn -= 1
            self.is_playing = False # Pause if user manually clicks prev
            self.btn_play.config(text="▶ Play")
            self._render_drones()

    def update_speed(self, value):
        self.speed_ms = int(value)
    

    def _render_drones(self):
        """Clears old drones and draws them at their current turn locations."""
        # 1. Wipe the previous frame's drones and text
        self.canvas.delete("drone")
        self.canvas.delete("turn_text")
        
        # 2. Display current turn
        self.canvas.create_text(100, 40, text=f"TURN: {self.turn} / {self.max_turn}", 
                                fill="white", font=("Arial", 20, "bold"), tags="turn_text")
        
        # 3. Colors to differentiate the drones
        colors = ["cyan", "magenta", "yellow", "lime", "orange", "pink"]
        
        # 4. Loop through every drone's path
        for d_id, path in enumerate(self.paths):
            if not path:
                continue
                
            # Find where this specific drone is at the current `self.turn`
            current_loc = path[0][1]  # Default to its starting hub
            for t, loc in path:
                if t <= self.turn:
                    current_loc = loc
                else:
                    break  # We found the most recent location
                    
            # 5. Calculate Pixel Coordinates
            if "-" in current_loc: 
                # EDGE CASE: It is mid-transit on a restricted connection!
                # We draw it exactly halfway between the two zones.
                z1, z2 = current_loc.split("-")
                x1, y1 = self._get_coords(z1)
                x2, y2 = self._get_coords(z2)
                x, y = (x1 + x2) / 2, (y1 + y2) / 2
            else:
                # Normal move: It is safely inside a zone.
                x, y = self._get_coords(current_loc)
                
            # 6. Apply Offsets (so 5 drones in the same zone don't stack invisibly)
            offset_x = (d_id % 3) * 12 - 12
            offset_y = (d_id % 3) * 12 - 12
            
            # 7. Draw the Drone and its ID
            drone_color = colors[d_id % len(colors)]
            r = 8
            
            self.canvas.create_oval(x-r+offset_x, y-r+offset_y, x+r+offset_x, y+r+offset_y, 
                                    fill=drone_color, outline="black", tags="drone")
            
            self.canvas.create_text(x+offset_x, y-15+offset_y, text=f"D{d_id+1}", 
                                    fill=drone_color, tags="drone", font=("Arial", 10, "bold"))

    def _animate(self):
        """The automatic loop that drives the simulation forward."""
        if self.is_playing:
            self._render_drones()
            
            if self.turn < self.max_turn:
                self.turn += 1
                # Ask Tkinter to call _animate again after X milliseconds
                self.root.after(self.speed_ms, self._animate)
            else:
                # Stop playing if we reach the end
                self.is_playing = False
                self.btn_play.config(text="▶ Play")


    def _get_coords(self, zone_name: str) -> Tuple[float, float]:
        """Translates a map's X/Y coordinate into actual screen pixels."""
        z = self.network.zones[zone_name]
        
        # 1. How "wide" and "tall" is the map in its own coordinate system?
        x_range = self.max_x - self.min_x
        y_range = self.max_y - self.min_y
        
        # Prevent division by zero if a map happens to be a perfectly straight line
        scale_x = x_range if x_range else 1
        scale_y = y_range if y_range else 1
        
        # 2. THE MAGIC MATH:
        # (Current - Min) / Range gives a percentage (e.g., 0.5 means it's exactly in the middle)
        # We multiply that percentage by the available screen space (width - padding)
        # Finally, we add the padding back so it doesn't touch the edge.
        
        canvas_width = 1024 # Match your geometry width
        canvas_height = 720 # Match your geometry height
        
        x = self.pad + (z.x - self.min_x) / scale_x * (canvas_width - 2 * self.pad)
        y = self.pad + (z.y - self.min_y) / scale_y * (canvas_height - 2 * self.pad)
        
        return x, y
    
    def _draw_static_network(self):
        """Draws the lines (connections) and circles (zones)."""
        
        # 1. Draw Connections FIRST (so they appear underneath the zones)
        for conn in self.network.connections:
            # Translate the zone names into pixel coordinates
            x1, y1 = self._get_coords(conn.zone1)
            x2, y2 = self._get_coords(conn.zone2)
            
            # Draw a thick gray line between them
            self.canvas.create_line(x1, y1, x2, y2, fill="#555555", width=3)
            
        # 2. Draw Zones (Nodes)
        for name, z in self.network.zones.items():
            x, y = self._get_coords(name)
            
            # Determine the color based on the map metadata, default to white
            color = z.color if z.color != "none" else "white"
            
            # Safety check: if the map asks for a weird color like "super_red", Tkinter will crash.
            # This checks if the color is valid, otherwise falls back to white.
            try:
                self.canvas.winfo_rgb(color)
            except tk.TclError:
                color = "white"
            
            # Draw the circle (radius of 25 pixels)
            r = 30
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline="white", width=2)
            
            # Draw the zone name slightly above the circle
            self.canvas.create_text(x, y-35, text=name, fill="white", font=("Arial", 12, "bold"))
            
            # Draw the capacity limit inside/below the circle
            self.canvas.create_text(x, y, text=f"Cap:{z.max_drones}", fill="black", font=("Arial", 9, "bold"))


# if __name__ == "__main__":
#     from pars import Pars
    
#     # 1. Parse a real map to get the network data
#     # Make sure 'cj.map' is in the same folder, or use the full path
#     test_network = Pars.parse_config('cj.map')
    
#     # 2. Launch the visualizer, passing the network and an empty list for paths
#     fake_paths = [[(0, "hub"), (10, "goal")]]
#     app = GUI_Visualizer(network=test_network, all_paths=fake_paths)