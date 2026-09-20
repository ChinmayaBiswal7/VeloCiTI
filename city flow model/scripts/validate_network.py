import cityflow
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

eng = cityflow.Engine("config_5j.json", 1)

print("Engine created successfully.")

# Test setting phases for all 5 junctions
for jid in ["J1", "J2", "J3", "J4", "J5"]:
    eng.set_tl_phase(jid, 0)

for step in range(60):
    eng.next_step()
    if step == 30:
        for jid in ["J1", "J2", "J3", "J4", "J5"]:
            eng.set_tl_phase(jid, 1)

print("Step 60 complete.")
print("Total vehicles:", eng.get_vehicle_count())
print("Average travel time:", eng.get_average_travel_time())
lanes = eng.get_lane_waiting_vehicle_count()
print("Lanes count:", len(lanes))
print("Waiting vehicles summary:", {k: v for k, v in lanes.items() if v > 0})
