// VeloCiTI Live Firebase Real-Time Synchronization Engine
// Configured with Firebase Project: your-firebase-project

import { initializeApp } from "firebase/app";
import { getAnalytics, isSupported } from "firebase/analytics";
import {
  getFirestore,
  collection,
  doc,
  setDoc,
  getDoc,
  onSnapshot,
  updateDoc
} from "firebase/firestore";

// Web config comes from Vite env vars (see .env.example). The demo fallbacks let the app start without a
// Firebase project: cloud sync then fails quietly and the local simulation keeps running.
const env = import.meta.env;
const firebaseConfig = {
  apiKey: env.VITE_FIREBASE_API_KEY || "demo-api-key",
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN || "demo-velociti.firebaseapp.com",
  projectId: env.VITE_FIREBASE_PROJECT_ID || "demo-velociti",
  storageBucket: env.VITE_FIREBASE_STORAGE_BUCKET || "demo-velociti.appspot.com",
  messagingSenderId: env.VITE_FIREBASE_MESSAGING_SENDER_ID || "000000000000",
  appId: env.VITE_FIREBASE_APP_ID || "1:000000000000:web:demo",
  measurementId: env.VITE_FIREBASE_MEASUREMENT_ID || undefined,
};

// Initialize Firebase App
export const app = initializeApp(firebaseConfig);

// Safe Analytics init (in supported browsers)
export let analytics = null;
if (typeof window !== "undefined" && env.VITE_FIREBASE_MEASUREMENT_ID) {
  isSupported()
    .then((supported) => {
      if (supported) analytics = getAnalytics(app);
    })
    .catch(() => {});
}

// Firestore Database instance (Real-Time Document & Collection Streaming)
export const db = getFirestore(app);

// ── 1. Live Emergency Fleet Synchronization ──────────────────────────────────
/**
 * Broadcast live emergency vehicle positions and progress to Firebase Firestore
 * @param {Array<Object>} fleetList Array of active units with progress, coordinates, speed
 */
export async function syncLiveFleetToFirebase(fleetList) {
  try {
    await setDoc(doc(db, "telemetry", "live_fleet"), {
      fleet: fleetList,
      count: fleetList.length,
      updatedAt: Date.now(),
    }, { merge: true });
  } catch (err) {
    // Offline or permission pending fallback
  }
}

/**
 * Subscribe to live fleet updates streamed from Firebase in real-time
 * @param {Function} callback Called with updated fleet array [ { id, currentPos, progress, speedKmh... } ]
 * @returns {Function} Unsubscribe function
 */
export function subscribeToLiveFleet(callback) {
  try {
    return onSnapshot(doc(db, "telemetry", "live_fleet"), (docSnap) => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        if (data && data.fleet) {
          callback(data.fleet);
        }
      }
    }, () => {});
  } catch (e) {
    return () => {};
  }
}

// ── 2. Emergency Green Corridor Broadcast ───────────────────────────────────
/**
 * Broadcast Green Corridor activation to Firebase
 */
export async function broadcastCorridorToFirebase(corridorState) {
  try {
    await setDoc(doc(db, "telemetry", "active_corridor"), {
      ...corridorState,
      updatedAt: Date.now(),
    });
  } catch (err) {
    // Offline fallback
  }
}

/**
 * Listen to live corridor state across all connected clients in real-time
 */
export function subscribeToCorridor(callback) {
  try {
    return onSnapshot(doc(db, "telemetry", "active_corridor"), (docSnap) => {
      if (docSnap.exists()) {
        callback(docSnap.data());
      }
    }, () => {});
  } catch (e) {
    return () => {};
  }
}

// ── 3. Manual Signal Overrides ──────────────────────────────────────────────
/**
 * Sync operator signal overrides to Firebase
 */
export async function syncSignalOverrideToFirebase(intersectionId, direction, light) {
  try {
    await setDoc(doc(db, "signals", intersectionId), {
      [direction]: { light, manualActive: true, timestamp: Date.now() },
      lastUpdated: Date.now(),
    }, { merge: true });
  } catch (err) {}
}

/**
 * Revert signal override to AI control in Firebase
 */
export async function revertSignalOverrideInFirebase(intersectionId, direction) {
  try {
    await setDoc(doc(db, "signals", intersectionId), {
      [direction]: { light: "red", manualActive: false, timestamp: Date.now() },
      lastUpdated: Date.now(),
    }, { merge: true });
  } catch (err) {}
}

/**
 * Subscribe to all live signal overrides across the city
 */
export function subscribeToSignalOverrides(callback) {
  try {
    return onSnapshot(collection(db, "signals"), (snapshot) => {
      const overrides = {};
      snapshot.forEach((docSnap) => {
        overrides[docSnap.id] = docSnap.data();
      });
      callback(overrides);
    }, () => {});
  } catch (e) {
    return () => {};
  }
}
