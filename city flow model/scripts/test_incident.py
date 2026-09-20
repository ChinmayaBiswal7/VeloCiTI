import urllib.request
import json
import time

# 1. Test Incident Injection
req = urllib.request.Request(
    'http://localhost:5000/api/incident',
    data=json.dumps({"junction": "J3", "road": "road_J3_J2", "type": "ACCIDENT", "active": True}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(req)
print("Incident injected:", json.loads(res.read().decode()))

# 2. Check State
with urllib.request.urlopen('http://localhost:5000/api/state') as response:
    data = json.loads(response.read().decode())
    print("Active incidents in state:", data["active_incidents"])
    print("Agent J3 decision reason:", data["agents"]["J3"]["decision_reason"])

# 3. Clear Incident
req_clear = urllib.request.Request(
    'http://localhost:5000/api/incident',
    data=json.dumps({"junction": "J3", "road": "road_J3_J2", "type": "ACCIDENT", "active": False}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
res_clear = urllib.request.urlopen(req_clear)
print("Incident cleared:", json.loads(res_clear.read().decode()))
