import urllib.request
import json
import time

# 1. Start simulation
req = urllib.request.Request(
    'http://localhost:5000/api/control',
    data=json.dumps({"cmd": "start"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
urllib.request.urlopen(req)

time.sleep(3)

# 2. Fetch state
with urllib.request.urlopen('http://localhost:5000/api/state') as response:
    data = json.loads(response.read().decode())
    print("Sim Step:", data["step"])
    print("Total Vehicles Active:", data["total_vehicles"])
    print("Total Queued:", data["total_waiting"])
    print("Mean Speed:", data["avg_speed"])
    print("Agents Active:", list(data["agents"].keys()))
    for jid, ag in data["agents"].items():
        print(f"[{jid}] Phase: {ag['current_phase']}, Density: {ag['overall_density']}, Queued: {ag['total_queue']}, Reason: {ag['decision_reason']}")
