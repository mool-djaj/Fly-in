# Fly-in: Space-Time A* Drone Routing Engine

## 🚁 Overview
Fly-in is a custom 3D Space-Time pathfinding engine designed to route a fleet of drones through a complex network of zones without collisions. Built on a modified A* (A-Star) search algorithm, this engine treats **Time** as a physical dimension. This allows drones to dynamically wait in place, navigate around moving traffic, and respect strict zone capacities, priority lanes, and restricted airspace.

## ⚙️ Core Mechanics
*   **Space-Time Traversal:** The algorithm tracks visited states as `(zone, turn)` tuples, allowing a drone to revisit a physical location if doing so at a different time solves a traffic jam.
*   **Dynamic Capacity Ledgers:** Every physical room and connecting wire maintains a time-locked ledger. Drones book reservations in the future, preventing two drones from occupying a single-capacity zone at the exact same turn.
*   **Weighted Heuristics:** Employs a pre-calculated distance map from the destination, factoring in priority zones (cost: `0.9`), standard zones (cost: `1.0`), and restricted zones (cost: `2.0`). 

---

## 🧠 Core Architecture & Data Structures

Understanding how the engine maps Space-Time in memory is critical to understanding the pathfinding logic. Below are the internal states of the primary stacks and dictionaries during runtime.

### 1. The Adjacency List: `self.graph`
* **Type:** `dict[str, list[str]]`
* **Purpose:** The static physical map. It defines which rooms are directly connected.
```json
{
  "start_hub": ["roof1", "hallway1"],
  "roof1": ["start_hub", "roof2"],
  "hallway1": ["start_hub", "end_hub"],
  "roof2": ["roof1", "end_hub"],
  "end_hub": ["hallway1", "roof2"]
}
```

### 2. The Heuristic Radar: `self.heuristics`
* **Type:** `dict[str, float]`
* **Purpose:** The A* compass. Holds the pre-calculated, absolute minimum time cost to reach the `end_hub` assuming zero traffic.
```json
{
  "end_hub": 0.0,
  "roof2": 1.0,
  "hallway1": 2.0,
  "roof1": 2.9,
  "start_hub": 3.9
}
```

### 3. The Zone Traffic Ledger: `self.zone_res`
* **Type:** `dict[str, dict[int, int]]`
* **Purpose:** The 3D Space-Time booking system for physical rooms. Maps `Zone Name -> Turn Number -> Headcount`.
```json
{
  "roof1": { 
      4: 1, 
      5: 2, 
      6: 1 
  },
  "hallway1": {
      2: 1,
      3: 1
  }
}
```

### 4. The Connection Wire Ledger: `self.link_res`
* **Type:** `dict[tuple[str, str], dict[int, int]]`
* **Purpose:** The capacity ledger for the physical wires/doors between rooms. Keys are alphabetically sorted tuples to ensure bidirectionality (`("roof1", "roof2")` is treated identically to `("roof2", "roof1")`).
```python
{
  ("roof1", "roof2"): {
      2: 1, 
      3: 1
  },
  ("hallway1", "start_hub"): {
      1: 2
  }
}
```

### 5. The Space-Time Visited Set: `visited`
* **Type:** `set[tuple[str, int]]`
* **Purpose:** The time-travel memory during the A* search. Prevents the algorithm from getting stuck in infinite wait-loops by recording rooms checked at *specific points in time*.
```python
{
  ("start_hub", 0),
  ("start_hub", 1), 
  ("roof1", 1),
  ("roof1", 2)
}
```

### 6. The Priority Queue: `queue`
* **Type:** `list[tuple[float, float, int, str, list]]`
* **Purpose:** The core sorting mechanism for the A* search, automatically pushing the path with the lowest f-score to the front.
* **Format:** `(f_score, g_cost, current_turn, current_zone, path_history)`
```python
[
  # Priority 1: Best f_score (3.9)
  (3.9, 1.0, 1, "roof1", [(0, "start_hub"), (1, "roof1")]), 
  
  # Priority 2: Higher f_score (4.9)
  (4.9, 1.0, 1, "hallway1", [(0, "start_hub"), (1, "hallway1")])
]
The tuple holds: 
 * (Total A* Score, Time Spent, Current Turn, Current Room, The Path History)
```

### 7. The Final Output: `path`
* **Type:** `list[tuple[int, str]]`
* **Purpose:** The completed flight manifest generated for a Drone, mapping exact turns to physical locations. Restricted zones automatically generate a lock-out transit turn.
```python
[
  (0, "start_hub"),
  (1, "roof1"),
  (2, "roof1-roof2"),  # Transit lock over a restricted wire
  (3, "roof2"),
  (4, "end_hub")
]
```

---

## 🚦 Decision Logic (Move vs. Wait)
During each iteration of the priority queue, the engine evaluates two distinct options to bypass traffic:
1.  **Strategic Waiting:** The drone advances time by `+1` but remains in the current node. The ledger is checked to ensure the current node's capacity is not exceeded on the next turn.
2.  **Neighbor Transit:** The drone advances to a connected neighbor. Base traversal takes `1` turn. Restricted zones take `2` turns and lock the connecting wire (`link_res`) to prevent head-on collisions. Priority zones grant a mathematical advantage (`0.9` cost) in the heuristic queue to encourage grouping, but still consume `1` physical turn.