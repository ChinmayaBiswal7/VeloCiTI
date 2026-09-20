<p align="center"><img src="frontend/public/velociti-logo.jpg" width="160" alt="VeloCiTI logo"></p>

# VeloCiTI

**Vehicle Location and City Traffic Intelligence.** An AI traffic-management platform for emergency green corridors, adaptive signal control and vehicle intelligence, built as a Smart India Hackathon prototype for Bhubaneswar.

## What it does

- **Adaptive signal control.** Multi-agent traffic-signal simulation (CityFlow) across 100 junctions, with congestion scoring and manual override.
- **Emergency green corridor.** Routes an ambulance along the fastest path and pre-empts the signals ahead of it.
- **Live GIS map, analytics and incidents.** City-wide congestion, fleet tracking and incident response on one dashboard.
- **Vehicle intelligence (ANPR).** Number-plate recognition and re-identification of vehicles without plates, in three modes:
  - **Live camera:** each second of a webcam feed is split into 24 frames, tracked (YOLOv8 + BoT-SORT), quality-gated (image-quality metrics + Random Forest), read with OCR and voted across frames.
  - **Image analysis:** upload vehicle photos. Each vehicle gets a *plated* card (plate, decoded state/RTO, registration record) or a *no-plate* card (type, colour, make/model, damage, occupants, clothing, cross-camera re-identification). Fields the model is unsure about are left blank rather than guessed.
  - **Video analysis:** upload a clip and get the same cards per vehicle, plus the scene conditions (glare, fog, rain, defocus) that were detected.

## Repository layout

| Path | Contents |
|---|---|
| `frontend/` | React 19 + Vite dashboard |
| `city flow model/` | Flask backend: CityFlow signal simulation, tracking API, webcam / image / video pipelines |
| `prototype/` | ANPR and vehicle-intelligence modules (YOLOv8, EasyOCR, quality gate, re-identification) |
| `docs/` | Mobile app designs |

## Quick start

Requires Python 3.10+ and Node.js 18+.

```bash
# 1. Backend (port 5000)
cd "city flow model"
pip install -r requirements.txt
python server_standalone.py

# 2. Frontend (port 5173), in a second terminal
cd frontend
npm install
npm run dev
```

On Windows, `start.bat` launches both. Open http://localhost:5173.

### Signing in

Sign-in is verified by the backend. Accounts come from the `TEAM_MEMBERS` environment variable (a JSON list with hashed passwords), so no credentials live in the source or the browser bundle. Generate the value with:

```bash
python "city flow model/scripts/make_team_members.py" you@example.com:your-password
```

Without `TEAM_MEMBERS`, only the public demo account `demo@velociti.dev` / `velociti-demo` can sign in. Repeated failed attempts from one client are temporarily locked out.

### One-time model download

YOLOv8 weights download automatically on first use. The vision-language model used for make/model, damage and clothing recognition (about 1.7 GB) is loaded offline, so download it once:

```bash
python -c "from huggingface_hub import snapshot_download; snapshot_download('openai/clip-vit-large-patch14', allow_patterns=['*.json','*.txt','model.safetensors'])"
```

Without it the app still works; those attribute fields are simply left blank.

## Configuration

Nothing below is required to run locally. Copy the example files and fill them in as needed:

| File | Purpose |
|---|---|
| `frontend/.env.example` | Firebase web config for live cloud sync (`VITE_FIREBASE_*`) |
| `prototype/firebase_config.example.json` | Backend Firebase sync (copy to `firebase_config.json`) |
| `.env.example` | Team accounts (`TEAM_MEMBERS`), Cloudinary storage, remote AI service URL, CLIP model id |

Secrets and local configuration are git-ignored.

## Notes

- **Registration records are simulated.** No live Vahan/Parivahan API is connected. Only the state and RTO office decoded from the plate are real; owner details are generated from the plate text and are labelled as simulated in the UI.
- A plate is only reported when the read reaches 60% confidence and forms a valid Indian registration with a real state code. Anything weaker is shown as unreadable.

## Deployment

- **Docker / Render:** the multi-stage `Dockerfile` builds the frontend and serves it with the Flask backend through Gunicorn; `render.yaml` is a Render blueprint.
- **Firebase Hosting:** `deploy-firebase.bat` builds and deploys the frontend (run `firebase use --add` once to select your project).

## Licence

MIT. See `frontend/LICENSE`.
