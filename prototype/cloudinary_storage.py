"""
cloudinary_storage.py - Permanent Cloud Storage for Vehicle Images & CCTV Videos
Uploads vehicle evidence snapshots and video clips directly to Cloudinary CDN.
falls back gracefully to local snapshots if offline or unconfigured.
"""

import os
import time
import hashlib
import threading
import requests

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

# In-memory URL cache: filename -> cloudinary_url
fallback_urls = {
    "ghost_01_sedan.jpg": "https://res.cloudinary.com/me4hfkhj/image/upload/v1789706871/ghost_01_sedan.jpg",
    "ghost_02_suv.jpg": "https://res.cloudinary.com/me4hfkhj/image/upload/v1789706873/ghost_02_suv.jpg",
    "ghost_03_hatch.jpg": "https://res.cloudinary.com/me4hfkhj/image/upload/v1789706877/ghost_03_hatch.jpg",
    "ghost_04_bike.jpg": "https://res.cloudinary.com/me4hfkhj/image/upload/v1789706880/ghost_04_bike.jpg",
    "test_cctv.jpg": "https://res.cloudinary.com/me4hfkhj/image/upload/v1789706881/test_cctv.jpg"
}

def get_cached_url(filename: str):
    return fallback_urls.get(filename)

def upload_image(data_or_path, filename=None, folder="vehicle_snapshots"):
    if filename and filename in fallback_urls:
        return fallback_urls[filename]
    if not (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET):
        return f"/api/snapshot/{filename}" if filename else None
    try:
        ts = int(time.time())
        public_id = os.path.splitext(filename)[0] if filename else f"snap_{ts}"
        to_sign = f"folder={folder}&overwrite=true&public_id={public_id}&timestamp={ts}{CLOUDINARY_API_SECRET}"
        sig = hashlib.sha1(to_sign.encode("utf-8")).hexdigest()
        form_data = {
            "api_key": CLOUDINARY_API_KEY,
            "timestamp": ts,
            "folder": folder,
            "public_id": public_id,
            "overwrite": "true",
            "signature": sig
        }
        files = {}
        if isinstance(data_or_path, (bytes, bytearray)):
            files["file"] = (filename or "upload.jpg", data_or_path, "image/jpeg")
        elif isinstance(data_or_path, str) and os.path.exists(data_or_path):
            files["file"] = open(data_or_path, "rb")
        else:
            files["file"] = data_or_path
        endpoint = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
        resp = requests.post(endpoint, files=files, data=form_data, timeout=15)
        if resp.status_code == 200:
            cdn_url = resp.json().get("secure_url")
            if filename and cdn_url:
                fallback_urls[filename] = cdn_url
            return cdn_url
    except Exception as e:
        print(f"[Cloudinary] Upload error: {e}")
    return f"/api/snapshot/{filename}" if filename else None

def upload_image_async(data_or_path, filename=None, folder="vehicle_snapshots"):
    def _worker():
        upload_image(data_or_path, filename=filename, folder=folder)
    threading.Thread(target=_worker, daemon=True).start()
