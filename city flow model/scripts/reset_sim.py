import urllib.request
import json

req = urllib.request.Request(
    'http://localhost:5000/api/control',
    data=json.dumps({"cmd": "reset"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
urllib.request.urlopen(req)
print("Simulation reset ready for user.")
