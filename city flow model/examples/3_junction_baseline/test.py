"""
CityFlow SIH Starter Test
3-junction linear road:  J1 (Agent A) -> J2 (Agent B) -> J3 (Agent C)

Run with:
  source ~/cityflow-env/bin/activate
  cd /mnt/c/D FOLDER/Projects/city flow model/cityflow_sih
  python3 test.py
"""

import cityflow
import os

# Config path relative to this script
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

print("=" * 50)
print("CityFlow SIH -- 3-Junction Test")
print("=" * 50)
print("Config:", config_path)

# Create the simulation engine
eng = cityflow.Engine(config_path, thread_num=1)

# Run 60 steps (1 minute of simulation at 1s/step)
NUM_STEPS = 60
current_phase = 0  # Track phase ourselves (0=green, 1=red)

for step in range(NUM_STEPS):

    # Simple timed phase switch at J2 every 20 steps
    if step % 20 == 0:
        current_phase = 1 - current_phase        # toggle 0 <-> 1
        eng.set_tl_phase("J2", current_phase)

    eng.next_step()

    if step % 10 == 0:
        total_vehicles  = eng.get_vehicle_count()
        lane_waits      = eng.get_lane_waiting_vehicle_count()
        total_waiting   = sum(lane_waits.values())

        print("Step {:3d} | Vehicles: {:3d} | J2 phase: {} | Waiting: {}".format(
            step, total_vehicles, current_phase, total_waiting))

print("=" * 50)
print("Simulation complete:", NUM_STEPS, "steps")
print("Total vehicles in network at end:", eng.get_vehicle_count())
print("Average travel time:", round(eng.get_average_travel_time(), 2), "seconds")
print()
print("Agents:")
print("  J1 = Agent A  (source / spawn point)")
print("  J2 = Agent B  (traffic light controller -- RL agent goes here)")
print("  J3 = Agent C  (destination / sink)")
print()
print("Next step: connect your CCTV/YOLO vehicle counts to control J2 phase!")
