import cityflow, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

eng = cityflow.Engine("config_5j.json", 1)
for _ in range(50):
    eng.next_step()

print("5-junction OK!")
print("Vehicles in network:", eng.get_vehicle_count())
print("Avg travel time:", eng.get_average_travel_time())

lw = eng.get_lane_waiting_vehicle_count()
print("Lanes detected:", len(lw))
print("Sample lanes:", list(lw.keys())[:8])
print("Waiting per lane:", {k:v for k,v in lw.items() if v > 0})
