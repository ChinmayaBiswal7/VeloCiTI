import { useState, useEffect, useRef, useCallback } from "react";
import "./GuidedTour.css";

const TOUR_STORAGE_KEY_PREFIX = "velociti_spotlight_tour_v3_";

// Helper to safely access tracking iframe content window and document
function getTrackingIframe() {
  const iframe = document.querySelector(".vt-iframe");
  if (iframe && iframe.contentWindow) {
    try {
      return {
        win: iframe.contentWindow,
        doc: iframe.contentDocument || iframe.contentWindow.document,
        el: iframe,
      };
    } catch {
      return null;
    }
  }
  return null;
}

// ── 1. Traffic Command Matrix Portal Steps (13 Comprehensive Steps) ──
const TRAFFIC_TOUR_STEPS = [
  {
    targetSelector: ".sb-logo",
    buttonSelector: ".sb-logo",
    viewRequired: "overview",
    triggerButton: "[ 🛡️ VeloCiTI Hub ]",
    triggerLocation: "Left Sidebar Header",
    cardPosition: "top-left",
    title: "VeloCiTI Command Hub",
    badge: "System Core",
    icon: "fa-shield-halved",
    desc: "Autonomous Traffic Management & Multi-Agent CityFlow Control Engine designed for Bhubaneswar Metropolitan Area.",
    example: "Monitors 100 smart sensor nodes across 46 major city junctions with real-time feedback loops.",
  },
  {
    targetSelector: ".sb-status",
    buttonSelector: ".sb-status",
    viewRequired: "overview",
    triggerButton: "[ 🔥 Firebase Live ]",
    triggerLocation: "Left Sidebar Telemetry",
    cardPosition: "top-left",
    title: "Firebase Live Sync",
    badge: "Cloud Telemetry",
    icon: "fa-fire",
    desc: "Continuous bidirectional state sync between edge signal controllers, camera nodes, and emergency corridors.",
    example: "Signal duration changes and preemption overrides reflect across all connected consoles in <100ms.",
  },
  {
    targetSelector: ".tb-portal-switch-btn",
    buttonSelector: ".tb-portal-switch-btn",
    viewRequired: "overview",
    showClickHand: true,
    triggerButton: "[ 🛰️ Vehicle Tracking ]",
    triggerLocation: "Top Bar Actions",
    cardPosition: "top-right",
    title: "Vehicle Tracking Switcher",
    badge: "Portal Navigation",
    icon: "fa-satellite",
    desc: "Seamless one-click switch to the citywide ANPR Vehicle Intelligence, Stolen Blacklist & Journey Reconstruction Hub.",
    example: "Click this top button anytime to open the ANPR tracking map and unplated vehicle re-ID hub.",
  },
  {
    targetSelector: ".kpi-row, .overview-kpi-row",
    buttonSelector: ".kpi-row, .overview-kpi-row",
    viewRequired: "overview",
    triggerButton: "[ 📊 Telemetry Row ]",
    triggerLocation: "Top Overview Metrics",
    cardPosition: "top-right",
    title: "Live Citywide Telemetry KPIs",
    badge: "Real-Time Health",
    icon: "fa-chart-pie",
    desc: "Instant aggregated metrics showing overall city congestion load, average corridor speed, and count of critical hotspots.",
    example: "Color-coded thresholds: Green (<40%), Amber (40-70%), and Red (>70% queue bottleneck).",
  },
  {
    targetSelector: ".city-grid, .grid-container, .city-cell:nth-child(12)",
    buttonSelector: ".city-cell:nth-child(12)",
    viewRequired: "overview",
    triggerButton: "[ 📍 Any Intersection Cell ]",
    triggerLocation: "10x10 Bhubaneswar Matrix Grid",
    cardPosition: "bottom-right",
    showClickHand: true,
    title: "10x10 Node Traffic Matrix",
    badge: "Interactive Grid",
    icon: "fa-table-cells-large",
    desc: "Each cell represents a major Bhubaneswar intersection. Shows real-time congestion load and vehicle queue density.",
    example: "Watch the animated hand pointer click an intersection cell to inspect live CCTV telemetry!",
  },
  {
    targetSelector: ".dv-header, .detail-view",
    buttonSelector: ".city-cell:nth-child(12)",
    viewRequired: "detail",
    autoOpenIntersection: true,
    triggerButton: "[ Clicked: Jaydev Vihar-1 Cell ]",
    triggerLocation: "10x10 Matrix Grid",
    cardPosition: "bottom-right",
    title: "Intersection Console & Live CCTV Feed",
    badge: "Deep Telemetry",
    icon: "fa-sliders",
    desc: "Opened the console for Jaydev Vihar-1! Shows real-time queue density, average corridor speed, and direct CCTV feed access.",
    example: "Click 'Live CCTV Feed' to watch high-resolution camera feeds of vehicles passing through this junction.",
  },
  {
    targetSelector: ".lane-panel, .lanes-grid",
    buttonSelector: ".lane-panel",
    viewRequired: "detail",
    triggerButton: "[ 🛣️ Lane Breakdown & Cameras ]",
    triggerLocation: "Intersection Console Column 2",
    cardPosition: "bottom-left",
    title: "4-Directional Lane Breakdown & Cameras",
    badge: "Lane Analytics",
    icon: "fa-road",
    desc: "Real-time queue monitoring across North, East, South, and West approach corridors with active signal light indicators.",
    example: "Shows vehicle volume in each lane with dynamic queue bars and individual CCTV launch buttons.",
  },
  {
    targetSelector: ".override-panel, .override-grid",
    buttonSelector: ".override-panel",
    viewRequired: "detail",
    triggerButton: "[ 👆 Manual Override Sliders ]",
    triggerLocation: "Intersection Console Column 2",
    cardPosition: "bottom-left",
    title: "Manual Signal Override & AI Revert",
    badge: "Operator Control",
    icon: "fa-hand-pointer",
    desc: "Direct operator override panel allowing manual green, amber, or red light assignment to any directional lane.",
    example: "Operators can instantly intervene during gridlocks and revert all signals back to AI control with one click.",
  },
  {
    targetSelector: ".flow-panel, .flow-compass, .radar-panel",
    buttonSelector: ".flow-panel",
    viewRequired: "detail",
    triggerButton: "[ 🧭 Directional Flow & Radar ]",
    triggerLocation: "Intersection Console Column 3",
    cardPosition: "bottom-left",
    title: "Directional Flow & Radar Telemetry",
    badge: "Flow Dynamics",
    icon: "fa-arrows-alt",
    desc: "Live directional compass and radar balance displaying queue distribution between opposing traffic lanes.",
    example: "Identifies directional flow imbalances to optimize signal green wave offsets.",
  },
  {
    targetSelector: ".sb-nav-btn:nth-child(2)",
    buttonSelector: ".sb-nav-btn:nth-child(2)",
    viewRequired: "map",
    showClickHand: true,
    triggerButton: "[ 🗺️ Live GIS Map ]",
    triggerLocation: "Left Sidebar Navigation",
    cardPosition: "top-right",
    title: "Live GIS City Map & Arterial Heatmap",
    badge: "Spatial Telemetry",
    icon: "fa-map-marked-alt",
    desc: "Geospatial satellite map rendering live vehicle movements, arterial bottlenecks, and active camera poles.",
    example: "Click camera pins across Janpath, Patia, or Jayadev Vihar to inspect live speed and vehicle counts.",
  },
  {
    targetSelector: ".sb-nav-btn:nth-child(3)",
    buttonSelector: ".sb-nav-btn:nth-child(3)",
    viewRequired: "emergency",
    showClickHand: true,
    triggerButton: "[ 🚑 Green Corridor ]",
    triggerLocation: "Left Sidebar Navigation",
    cardPosition: "top-right",
    title: "Ambulance Green Corridor Preemption",
    badge: "Emergency Dispatch",
    icon: "fa-truck-medical",
    desc: "Clears traffic ahead of emergency responders by synchronizing green lights along their path.",
    example: "Demonstrates zero-latency green light routing from Capital Hospital to Bhubaneswar Airport or AIIMS.",
  },
  {
    targetSelector: ".sb-nav-btn:nth-child(4)",
    buttonSelector: ".sb-nav-btn:nth-child(4)",
    viewRequired: "analytics",
    showClickHand: true,
    triggerButton: "[ 📈 Traffic Analytics ]",
    triggerLocation: "Left Sidebar Navigation",
    cardPosition: "bottom-right",
    title: "Live Traffic Analytics & Forecast Curves",
    badge: "Data Intelligence",
    icon: "fa-chart-line",
    desc: "Historical trend analysis, 24-hour congestion curves, vehicle mix doughnut, and predictive traffic load charts.",
    example: "Compare peak morning vs evening congestion loads to optimize long-term city infrastructure.",
  },
  {
    targetSelector: ".sb-nav-btn:nth-child(8)",
    buttonSelector: ".sb-nav-btn:nth-child(8)",
    viewRequired: "webcam",
    showClickHand: true,
    triggerButton: "[ 🎥 Live Webcam / CCTV ]",
    triggerLocation: "Left Sidebar Navigation",
    cardPosition: "top-left",
    title: "Live CCTV & AI Vision Workbench",
    badge: "Computer Vision",
    icon: "fa-video",
    desc: "Test the deep YOLOv8 detection and multi-frame ANPR engine using your webcam, sample videos, or images.",
    example: "Detects cars, bikes, buses, and auto-rickshaws with green bounding boxes and routes to Colab GPU for deep OCR.",
  },
];

// ── 2. Citywide ANPR & Vehicle Tracking Portal Steps (Full Interactive Tab Walkthrough) ──
const TRACKING_TOUR_STEPS = [
  {
    action: "map",
    targetSelector: ".vt-title-row, .vt-title",
    triggerButton: "Header Logo & Title",
    triggerLocation: "Top Portal Header",
    cardPosition: "top-left",
    title: "Citywide ANPR Vehicle Intelligence",
    badge: "Surveillance Hub",
    icon: "fa-satellite-dish",
    desc: "Autonomous cross-camera vehicle journey reconstruction, suspect hotlists, and unplated vehicle re-identification.",
    example: "Monitors vehicle journeys across 46 arterial camera nodes throughout Bhubaneswar.",
  },
  {
    action: "search_demo",
    buttonSelector: "iframe:.track-btn",
    targetSelector: "iframe:.search-inline",
    triggerButton: "Search Input + [ 🔍 TRACK ]",
    triggerLocation: "Top Left Search Bar",
    cardPosition: "search-near",
    showClickHand: true,
    title: "1. Search Plate & Auto Route Mapping",
    badge: "AI Journey Reconstruction",
    icon: "fa-magnifying-glass",
    desc: "Enter any Indian license plate number and click TRACK. The AI correlates sightings across all 46 city cameras and draws the complete chronological journey on the map.",
    example: "Demo: Plotted OD02AB1234 crossing Jayadev Vihar, Vani Vihar, and Master Canteen with timestamps, speeds, and photo snapshots.",
  },
  {
    action: "map",
    buttonSelector: "iframe:.nav-tabs .tab-btn:nth-child(1)",
    targetSelector: "iframe:#map, iframe:.top-right-group",
    triggerButton: "[ 🗺️ Vehicle Map ]",
    triggerLocation: "Top Navigation Bar",
    cardPosition: "bottom-left",
    showClickHand: true,
    title: "2. 46-Node Smart Camera Grid",
    badge: "GIS Telemetry",
    icon: "fa-map-location-dot",
    desc: "Interactive Leaflet satellite map displaying all 46 connected ANPR cameras, speed sensors, and congestion hot spots across Bhubaneswar.",
    example: "Notice the [ 🗺️ Vehicle Map ] button highlighted in the navbar right above.",
  },
  {
    action: "open_live",
    buttonSelector: "iframe:.nav-tabs .tab-btn:nth-child(2)",
    targetSelector: "iframe:#modal-live",
    triggerButton: "[ 📋 Live Detections ]",
    triggerLocation: "Top Navigation Bar",
    cardPosition: "bottom-right",
    showClickHand: true,
    title: "3. Live Camera Detections Feed",
    badge: "Real-Time Ingestion",
    icon: "fa-clipboard-list",
    desc: "Streaming ledger of all license plates read across the city in the last 15 minutes. Displays vehicle photo crop, license plate, camera junction name, vehicle type, speed, and AI OCR confidence score.",
    example: "Notice the [ 📋 Live Detections ] button highlighted in the navbar that launched this live table.",
  },
  {
    action: "open_alerts",
    buttonSelector: "iframe:.nav-tabs .tab-btn:nth-child(3)",
    targetSelector: "iframe:#modal-alerts",
    triggerButton: "[ 🚨 Alerts & Blacklist ]",
    triggerLocation: "Top Navigation Bar",
    cardPosition: "bottom-right",
    showClickHand: true,
    title: "4. Live Security Alerts & Blacklist Hub",
    badge: "Police Hotlist",
    icon: "fa-bell",
    desc: "Monitors suspect vehicles, stolen cars, and route anomalies. Add suspect plates to the Stolen Vehicle Blacklist to trigger audio siren alarms across police consoles the moment they pass any camera.",
    example: "Notice the [ 🚨 Alerts & Blacklist ] button highlighted in the navbar that launched this security hub.",
  },
  {
    action: "open_ghosts",
    buttonSelector: "iframe:.nav-tabs .tab-btn:nth-child(4)",
    targetSelector: "iframe:#modal-ghosts",
    triggerButton: "[ 🚫 Unplated Tracker ]",
    triggerLocation: "Top Navigation Bar",
    cardPosition: "bottom-right",
    showClickHand: true,
    title: "5. Unplated Vehicle Profiling Hub (Ghosts)",
    badge: "Visual AI Re-ID",
    icon: "fa-ban",
    desc: "When suspects hide or remove number plates, our multi-zone visual embedding engine tracks them across city corridors using vehicle color, make, model, body proportions, and geometry.",
    example: "Notice the [ 🚫 Unplated Tracker ] button highlighted in the navbar that launched this visual profiling view.",
  },
  {
    action: "map",
    buttonSelector: "iframe:.nav-tabs a.tab-btn",
    targetSelector: "iframe:.nav-tabs a.tab-btn",
    triggerButton: "[ 🎥 CCTV Workbench ]",
    triggerLocation: "Top Navigation Bar",
    cardPosition: "below-navbar-right",
    showClickHand: true,
    title: "6. CCTV Vision & ANPR Testing Lab",
    badge: "Computer Vision Lab",
    icon: "fa-video",
    desc: "Direct access to the computer vision test workbench. Operators can upload live webcam feeds, street clips, or vehicle snapshots to test the AI detector and GPU plate OCR.",
    example: "Notice the [ 🎥 CCTV Workbench ] button highlighted in the navbar right above this card.",
  },
  {
    action: "open_firebase",
    buttonSelector: ".vt-tabs button:nth-child(2)",
    targetSelector: ".vt-arch-card, .vt-firebase-view",
    triggerButton: "[ 🗄️ Central Cloud DB ]",
    triggerLocation: "Header Navigation Tabs",
    cardPosition: "bottom-right",
    showClickHand: true,
    title: "7. Central Firestore Cloud Architecture",
    badge: "Cloud Innovation",
    icon: "fa-database",
    desc: "Instead of disconnected databases at each junction, all 46 intersections stream sightings into a central Firebase Firestore collection (`vehicle_plates`) with real-time cloud sync.",
    example: "Notice the [ 🗄️ Central Cloud DB ] tab highlighted in the top header that opened this view.",
  },
  {
    action: "back_to_map",
    buttonSelector: ".vt-traffic-btn",
    targetSelector: ".vt-traffic-btn",
    triggerButton: "[ 🚦 Traffic Command ]",
    triggerLocation: "Top Right Header",
    cardPosition: "below-header-right",
    showClickHand: true,
    title: "8. Switch to Traffic Command Matrix",
    badge: "System Navigation",
    icon: "fa-traffic-light",
    desc: "Seamlessly jump back to the 10x10 Traffic Matrix Grid, CityFlow reinforcement learning engine, and Emergency Ambulance Green Corridor.",
    example: "Click 'Traffic Command' anytime to switch between vehicle surveillance and adaptive traffic signal control.",
  },
];

export default function GuidedTour({
  currentPortal = "traffic",
  onSwitchPortal,
  currentView = "overview",
  onNavigate,
  onSelectIntersection,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [cardStyle, setCardStyle] = useState({ bottom: "24px", right: "28px" });
  const [targetRect, setTargetRect] = useState(null);
  const [buttonRect, setButtonRect] = useState(null);
  const activeTargetRef = useRef(null);

  // Select steps corresponding strictly to the current active portal
  const steps = currentPortal === "tracking" ? TRACKING_TOUR_STEPS : TRAFFIC_TOUR_STEPS;
  const storageKey = TOUR_STORAGE_KEY_PREFIX + currentPortal;

  // Trigger automatically once per portal for a new visitor
  useEffect(() => {
    const hasSeenTour = localStorage.getItem(storageKey);
    if (!hasSeenTour) {
      const t = setTimeout(() => {
        setCurrentStepIndex(0);
        setIsOpen(true);
      }, 900);
      return () => clearTimeout(t);
    }
  }, [storageKey]);

  // Spotlight positioning and action dispatcher
  const updateSpotlight = useCallback(() => {
    if (!isOpen) {
      if (activeTargetRef.current) {
        activeTargetRef.current.classList.remove("vt-target-highlight");
        activeTargetRef.current = null;
      }
      return;
    }

    const step = steps[currentStepIndex];
    if (!step) return;

    // ── Execute Actions for Traffic Side ──
    if (step.autoOpenIntersection && onSelectIntersection) {
      onSelectIntersection("Jaydev Vihar-1");
    } else if (step.viewRequired && step.viewRequired !== currentView && onNavigate) {
      onNavigate(step.viewRequired);
    }

    // ── Execute Actions for Tracking Side (Interactive Page Opening) ──
    if (currentPortal === "tracking") {
      const iframeInfo = getTrackingIframe();

      if (step.action === "open_firebase") {
        document.querySelectorAll(".vt-tab-btn")[1]?.click();
        if (iframeInfo && iframeInfo.win && iframeInfo.win.switchView) {
          iframeInfo.win.switchView("map");
          iframeInfo.win.closeJourney?.();
        }
      } else {
        document.querySelectorAll(".vt-tab-btn")[0]?.click();

        if (iframeInfo && iframeInfo.win) {
          if (step.action === "search_demo") {
            iframeInfo.win.switchView?.("map");
            const pin = iframeInfo.doc?.getElementById("pin");
            if (pin) pin.value = "OD02AB1234";
            if (iframeInfo.win.trackPlate) {
              iframeInfo.win.trackPlate("OD02AB1234");
            }
          } else if (step.action === "open_live") {
            iframeInfo.win.switchView?.("live");
          } else if (step.action === "open_alerts") {
            iframeInfo.win.switchView?.("alerts");
          } else if (step.action === "open_ghosts") {
            iframeInfo.win.switchView?.("ghosts");
          } else if (step.action === "map" || step.action === "back_to_map") {
            iframeInfo.win.switchView?.("map");
            iframeInfo.win.closeJourney?.();
          }
        }
      }
    }

    setTimeout(() => {
      if (activeTargetRef.current) {
        activeTargetRef.current.classList.remove("vt-target-highlight");
        activeTargetRef.current = null;
      }

      let el = null;
      let calculatedRect = null;
      let btnRect = null;

      // 1. Resolve buttonRect if step.buttonSelector is provided
      if (step.buttonSelector) {
        if (step.buttonSelector.startsWith("iframe:")) {
          const bSel = step.buttonSelector.replace("iframe:", "").trim();
          const iframeInfo = getTrackingIframe();
          if (iframeInfo && iframeInfo.doc) {
            const bEl = iframeInfo.doc.querySelector(bSel);
            if (bEl && bEl.offsetParent !== null) {
              const ifr = iframeInfo.el.getBoundingClientRect();
              const r = bEl.getBoundingClientRect();
              btnRect = {
                top: ifr.top + r.top,
                left: ifr.left + r.left,
                width: r.width,
                height: r.height,
              };
            }
          }
        } else {
          const bEl = document.querySelector(step.buttonSelector);
          if (bEl && bEl.offsetParent !== null) {
            const r = bEl.getBoundingClientRect();
            btnRect = {
              top: r.top,
              left: r.left,
              width: r.width,
              height: r.height,
            };
          }
        }
      }
      setButtonRect(btnRect);

      // 2. Resolve targetRect for opened page / modal
      if (step.targetSelector.startsWith("iframe:")) {
        const sel = step.targetSelector.replace("iframe:", "").trim();
        const iframeInfo = getTrackingIframe();
        if (iframeInfo && iframeInfo.doc) {
          const selectors = sel.split(",");
          for (const s of selectors) {
            const found = iframeInfo.doc.querySelector(s.trim());
            if (found && found.offsetParent !== null) {
              el = found;
              break;
            }
          }
          if (el) {
            const iframeRect = iframeInfo.el.getBoundingClientRect();
            const r = el.getBoundingClientRect();
            calculatedRect = {
              top: iframeRect.top + r.top,
              left: iframeRect.left + r.left,
              width: r.width,
              height: r.height,
            };
          }
        }
      } else {
        const selectors = step.targetSelector.split(",");
        for (const s of selectors) {
          const found = document.querySelector(s.trim());
          if (found && found.offsetParent !== null) {
            el = found;
            break;
          }
        }
        if (el) {
          el.classList.add("vt-target-highlight");
          activeTargetRef.current = el;
          const rect = el.getBoundingClientRect();
          calculatedRect = {
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height,
          };
        }
      }

      setTargetRect(calculatedRect);

      // 3. Calculate Non-Obstructive Card Position
      let style = { bottom: "24px", right: "28px" };

      if (step.cardPosition === "search-near") {
        // Positioned right under the search bar so it is close and aligned!
        style = { top: "115px", left: "24px" };
      } else if (step.cardPosition === "below-navbar-right") {
        // Positioned down below the navbar so CCTV button is 100% uncovered!
        style = { top: "125px", right: "24px" };
      } else if (step.cardPosition === "below-header-right") {
        // Positioned down below top-right header button so it's uncovered!
        style = { top: "80px", right: "24px" };
      } else if (step.cardPosition === "bottom-right") {
        style = { bottom: "24px", right: "24px" };
      } else if (step.cardPosition === "bottom-left") {
        style = { bottom: "24px", left: "24px" };
      } else if (step.cardPosition === "top-left") {
        style = { top: "85px", left: "24px" };
      } else if (step.cardPosition === "top-right") {
        style = { top: "80px", right: "24px" };
      } else if (calculatedRect) {
        const cardWidth = 360;
        const gap = 16;
        let top = Math.max(20, Math.min(window.innerHeight - 360, calculatedRect.top));
        let left = 24;
        if (calculatedRect.left > window.innerWidth / 2) {
          left = Math.max(20, calculatedRect.left - cardWidth - gap);
        } else {
          left = Math.min(window.innerWidth - cardWidth - 20, calculatedRect.right + gap);
        }
        style = { top: `${top}px`, left: `${left}px` };
      } else {
        style = { bottom: "24px", right: "28px" };
      }

      setCardStyle(style);
    }, 240);
  }, [isOpen, currentStepIndex, steps, currentPortal, currentView, onNavigate, onSelectIntersection]);

  useEffect(() => {
    updateSpotlight();
    window.addEventListener("resize", updateSpotlight);
    window.addEventListener("scroll", updateSpotlight, true);
    return () => {
      window.removeEventListener("resize", updateSpotlight);
      window.removeEventListener("scroll", updateSpotlight, true);
      if (activeTargetRef.current) {
        activeTargetRef.current.classList.remove("vt-target-highlight");
      }
    };
  }, [updateSpotlight]);

  function handleClose() {
    localStorage.setItem(storageKey, "true");
    setIsOpen(false);

    if (currentPortal === "tracking") {
      const iframeInfo = getTrackingIframe();
      if (iframeInfo && iframeInfo.win && iframeInfo.win.switchView) {
        iframeInfo.win.switchView("map");
        iframeInfo.win.closeJourney?.();
      }
      document.querySelectorAll(".vt-tab-btn")[0]?.click();
    }
  }

  function handleNext() {
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex((prev) => prev + 1);
    } else {
      handleClose();
    }
  }

  function handlePrev() {
    if (currentStepIndex > 0) {
      setCurrentStepIndex((prev) => prev - 1);
    }
  }

  function startTourAgain() {
    setCurrentStepIndex(0);
    setIsOpen(true);
  }

  const step = steps[currentStepIndex];

  return (
    <>
      {/* Quick Tour trigger button */}
      {!isOpen && (
        <button
          className="vt-trigger-fab"
          onClick={startTourAgain}
          title={
            currentPortal === "tracking"
              ? "ANPR Tracking Features Walkthrough"
              : "Traffic Command Features Walkthrough"
          }
        >
          <i className="fas fa-crosshairs" />
          {currentPortal === "tracking" ? "Tracking Tour" : "Traffic Tour"}
        </button>
      )}

      {/* Dimmed Background Overlay with SVG Mask and Spotlight Box */}
      {isOpen && (
        <>
          <div className="vt-click-catcher" onClick={handleClose} />

          {/* SVG Dimming Overlay with transparent cutout hole right over target elements */}
          <svg className="vt-spotlight-svg-mask">
            <defs>
              <mask id="vt-spotlight-cutout">
                <rect x="0" y="0" width="100%" height="100%" fill="white" />
                {/* Hole over main target / modal */}
                {targetRect && (
                  <rect
                    x={targetRect.left - 6}
                    y={targetRect.top - 6}
                    width={targetRect.width + 12}
                    height={targetRect.height + 12}
                    rx="10"
                    fill="black"
                  />
                )}
                {/* Hole over navbar button */}
                {buttonRect && (
                  <rect
                    x={buttonRect.left - 4}
                    y={buttonRect.top - 4}
                    width={buttonRect.width + 8}
                    height={buttonRect.height + 8}
                    rx="6"
                    fill="black"
                  />
                )}
              </mask>
            </defs>
            <rect
              x="0"
              y="0"
              width="100%"
              height="100%"
              fill="rgba(3, 7, 18, 0.84)"
              mask="url(#vt-spotlight-cutout)"
            />
          </svg>

          {/* Pulsating Glowing Border directly framing the main target / modal */}
          {targetRect && (
            <div
              className="vt-spotlight-box"
              style={{
                top: `${targetRect.top - 6}px`,
                left: `${targetRect.left - 6}px`,
                width: `${targetRect.width + 12}px`,
                height: `${targetRect.height + 12}px`,
              }}
            />
          )}

          {/* Pulsating Glowing Border directly framing the navbar button */}
          {buttonRect && (
            <div
              className="vt-spotlight-box"
              style={{
                top: `${buttonRect.top - 4}px`,
                left: `${buttonRect.left - 4}px`,
                width: `${buttonRect.width + 8}px`,
                height: `${buttonRect.height + 8}px`,
                borderRadius: "8px",
                borderColor: "#f59e0b",
                boxShadow: "0 0 25px rgba(245, 158, 11, 0.95), inset 0 0 10px rgba(245, 158, 11, 0.4)",
              }}
            />
          )}

          {/* Animated Hand Cursor Indicator pointing to the button or target */}
          {step.showClickHand && (buttonRect || targetRect) && (
            <div
              className="vt-click-hand"
              style={{
                top: buttonRect
                  ? `${buttonRect.top + buttonRect.height * 0.4}px`
                  : `${targetRect.top + targetRect.height * 0.45}px`,
                left: buttonRect
                  ? `${buttonRect.left + buttonRect.width * 0.4}px`
                  : `${targetRect.left + targetRect.width * 0.45}px`,
              }}
            >
              👆
            </div>
          )}

          {/* Non-Obstructive Interactive Card Anchored in Smart Dock Position */}
          <div
            className="vt-tooltip-card"
            style={cardStyle}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header with Badge & Step Counter */}
            <div className="vt-tooltip-header">
              <span className="vt-tooltip-badge">
                <i className="fas fa-bullseye" /> {step.badge}
              </span>
              <span className="vt-step-count">
                {currentStepIndex + 1} / {steps.length}
              </span>
            </div>

            {/* Prominent Button Trigger Banner */}
            {step.triggerButton && (
              <div className="vt-trigger-banner">
                <div className="vt-trigger-meta">
                  <i className="fas fa-arrow-pointer" />
                  <span>BUTTON CLICKED TO SHOW THIS:</span>
                </div>
                <div className="vt-trigger-pill">
                  <span className="vt-trigger-key">{step.triggerButton}</span>
                  {step.triggerLocation && (
                    <span className="vt-trigger-loc">({step.triggerLocation})</span>
                  )}
                </div>
              </div>
            )}

            {/* Body */}
            <div className="vt-tooltip-body">
              <div className="vt-tooltip-title-row">
                <div className="vt-tooltip-icon">
                  <i className={`fas ${step.icon}`} />
                </div>
                <h4 className="vt-tooltip-title">{step.title}</h4>
              </div>

              <p className="vt-tooltip-desc">{step.desc}</p>

              <div className="vt-tooltip-example">
                <i className="fas fa-lightbulb" />
                <div>
                  <strong>Live Demo Action: </strong>
                  <span>{step.example}</span>
                </div>
              </div>
            </div>

            {/* Footer Navigation */}
            <div className="vt-tooltip-footer">
              <button className="vt-btn-skip" onClick={handleClose}>
                Exit
              </button>
              <div className="vt-nav-group">
                {currentStepIndex > 0 && (
                  <button className="vt-btn-back" onClick={handlePrev}>
                    Back
                  </button>
                )}
                <button className="vt-btn-next" onClick={handleNext}>
                  {currentStepIndex === steps.length - 1 ? (
                    <>Got It! <i className="fas fa-check" /></>
                  ) : (
                    <>Next <i className="fas fa-arrow-right" /></>
                  )}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
