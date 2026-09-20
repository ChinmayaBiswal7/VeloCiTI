# Firebase Real-Time Cloud Integration Guide

This ANPR & Smart Traffic Intelligence engine is equipped with **real-time Google Firebase Cloud synchronization** (`firebase_sync.py`).

Whenever vehicles are scanned, unplated suspect cars are fingerprinted, or blacklist alerts are triggered, the data is pushed to Firebase collections in the background. External client apps (Traffic Police Mobile App, Ambulance Priority App, PCR Vans) can listen to these collections in real time.

---

## 1. How to Connect Your Firebase Project (3 Easy Steps)

### Step 1: Download Service Account Key
1. Go to your **[Firebase Console](https://console.firebase.google.com/)**.
2. Click **Project Settings (⚙️ Gear Icon)** ➔ **Service Accounts**.
3. Select **Firebase Admin SDK** ➔ Click **Generate new private key**.
4. A JSON file will download.

### Step 2: Place the Key in the Project Folder
Rename that downloaded JSON file to:
```text
serviceAccountKey.json
```
and place it directly in the project root:
```text
c:\D FOLDER\portotype\serviceAccountKey.json
```

### Step 3: Enable Firestore in Firebase Console
1. In Firebase Console, go to **Build** ➔ **Firestore Database**.
2. Click **Create database** (Start in **Test Mode** so your mobile apps can read/write freely during the hackathon).

*That's it!* The Python backend automatically detects `serviceAccountKey.json` and begins streaming live traffic intelligence.

---

## 2. Firebase Cloud Collections & Schema

### 📁 Collection 1: `live_detections`
*Updated on every vehicle passing any camera.*
```json
{
  "plate": "OD02AB1234",
  "camera_id": "CAM_01",
  "confidence": 0.94,
  "speed_kmph": 48.5,
  "vehicle_type": "Car",
  "plate_color": "WHITE",
  "category": "Private Vehicle",
  "violation": "NONE",
  "timestamp": "2026-09-17T10:05:00",
  "image_path": "/api/snapshot/...",
  "last_updated": "2026-09-17T10:05:01"
}
```

---

### 📁 Collection 2: `unplated_alerts` (For Traffic Police App & PCR Vans)
*Created when a vehicle with NO number plate or a covered plate is detected.*
```json
{
  "target_id": "UNPLATED-WHI-HAT-4144",
  "estimated_make": "Volkswagen",
  "estimated_model": "Taigun (Compact SUV / Crossover)",
  "make_confidence": 0.948,
  "dominant_color": "White",
  "distinguishing_features": "Circular Center Chrome Emblem, Dual Horizontal Chrome Louvers, Integrated Roof Rails",
  "first_seen_ts": "2026-09-17T09:50:00",
  "last_seen_ts": "2026-09-17T10:05:00",
  "first_camera": "CAM_01",
  "last_camera": "CAM_02",
  "total_sightings": 2,
  "status": "ACTIVE_INTERCEPT_ALERT"
}
```

---

### 📁 Collection 3: `blacklist_alerts` (For Stolen Vehicles & E-Challan Hit List)
*Triggered when a stolen or wanted car is detected.*
```json
{
  "plate": "OD05XX9999",
  "alert_type": "BLACKLIST_HIT",
  "camera_id": "CAM_04",
  "timestamp": "2026-09-17T10:05:12",
  "message": "Blacklisted vehicle [OD05XX9999] detected at CAM_04. Reason: Stolen vehicle",
  "status": "OPEN",
  "acknowledged": false
}
```

---

### 📁 Collection 4: `traffic_junctions` (For Ambulance Green Corridor App)
*Shows live congestion at each junction.*
```json
{
  "camera_id": "CAM_07",
  "name": "Jaydev Vihar Square",
  "road": "Jaydev Vihar Road",
  "latitude": 20.3051,
  "longitude": 85.8148,
  "congestion_level": "MODERATE",
  "vehicles_per_min": 28,
  "green_corridor_active": false
}
```

---

## 3. How Other Client Apps Listen in Real-Time

### In Flutter / React Native / Android (Traffic Police App):
```javascript
// Real-time listener for stolen car alerts
db.collection("blacklist_alerts")
  .where("status", "==", "OPEN")
  .onSnapshot((snapshot) => {
    snapshot.docChanges().forEach((change) => {
      if (change.type === "added") {
        playPoliceSirenSound();
        showNotification("STOLEN CAR SPOTTED: " + change.doc.data().plate);
      }
    });
  });

// Real-time listener for unplated suspect vehicles
db.collection("unplated_alerts")
  .where("status", "==", "ACTIVE_INTERCEPT_ALERT")
  .onSnapshot((snapshot) => {
    updatePoliceRadarMap(snapshot.docs.map(d => d.data()));
  });
```

### In Ambulance App (Requesting Green Corridor):
```javascript
// When ambulance driver requests clearance at Jaydev Vihar:
await db.collection("traffic_junctions").doc("CAM_07").update({
  green_corridor_active: true
});
```

---

## 4. Checking Cloud Sync Status
You can check the live Firebase status anytime by visiting:
```text
http://127.0.0.1:5050/api/firebase/status
```
