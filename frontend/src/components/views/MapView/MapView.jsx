import { useEffect, useRef, useState, useMemo } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  BBSR_INTERSECTIONS,
  BBSR_ROAD_SEGMENTS,
  BBSR_INTERSECTION_MAP,
  ZONE_COLORS,
} from "../../../data/bbsrCityData";
import { getRealRoadRoute, generateInstantRoadGeometry, findFastestEmergencyRoute, resolveJunction } from "../../../services/routingService";
import {
  getAmbulanceSvgHtml,
  generateDynamicEmergencyUnit,
  createInitialRandomFleet,
} from "../../../services/fleetService";
import { syncLiveFleetToFirebase, subscribeToLiveFleet } from "../../../services/firebase";
import "./MapView.css";

// Calculate bearing (angle in degrees 0..360) between two coordinates
function calculateBearing([lat1, lon1], [lat2, lon2]) {
  if (!lat1 || !lat2) return 0;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const l1 = (lat1 * Math.PI) / 180;
  const l2 = (lat2 * Math.PI) / 180;
  const y = Math.sin(dLon) * Math.cos(l2);
  const x = Math.cos(l1) * Math.sin(l2) - Math.sin(l1) * Math.cos(l2) * Math.cos(dLon);
  return (Math.atan2(y, x) * (180 / Math.PI) + 360) % 360;
}

// Interpolate position along an array of lat/lng coordinates based on percentage 0..100
function getInterpolatedPoint(coordsList, pct) {
  if (!coordsList || coordsList.length === 0) return [20.2961, 85.8245];
  if (coordsList.length === 1) return coordsList[0];

  const totalSegments = coordsList.length - 1;
  const currentFraction = (Math.min(100, Math.max(0, pct)) / 100) * totalSegments;
  const segIndex = Math.min(totalSegments - 1, Math.floor(currentFraction));
  const segT = currentFraction - segIndex;

  const p1 = coordsList[segIndex];
  const p2 = coordsList[segIndex + 1] || p1;

  const lat = p1[0] + (p2[0] - p1[0]) * segT;
  const lng = p1[1] + (p2[1] - p1[1]) * segT;
  return [lat, lng];
}

export default function MapView({ intersections, onSelectIntersection, corridor, onCancelCorridor }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersMapRef = useRef({});
  const roadNetworkLayerRef = useRef(null);
  const corridorLayerRef = useRef(null);
  const tracedRouteLayerRef = useRef(null);
  const fleetMarkersRef = useRef({});
  const ambulanceMarkerRef = useRef(null);
  const onSelectRef = useRef(onSelectIntersection);
  const intersectionsRef = useRef(intersections);

  // Selected junction for floating mini detail card
  const [selectedJunction, setSelectedJunction] = useState(null);

  // Traced emergency vehicle state
  const [tracedVehicle, setTracedVehicle] = useState(null);
  const [tracedRouteGeometry, setTracedRouteGeometry] = useState([]);
  const [tracedRouteDistance, setTracedRouteDistance] = useState(0);
  const [isFleetPanelOpen, setIsFleetPanelOpen] = useState(true);

  // Active Green Corridor geometry from prop
  const [roadGeometry, setRoadGeometry] = useState([]);
  const [roadDistance, setRoadDistance] = useState(0);

  // Dynamic next intersection along corridor for navigation display
  const nextJunction = useMemo(() => {
    if (!corridor || !corridor.isActive || !corridor.nodes || corridor.nodes.length === 0) return null;
    const total = corridor.nodes.length;
    const currIdx = Math.min(total - 1, Math.floor(((corridor.progress || 0) / 100) * total));
    const nextIdx = Math.min(total - 1, currIdx + 1);
    const targetNodeId = corridor.nodes[nextIdx] || corridor.nodes[currIdx];
    return BBSR_INTERSECTION_MAP[targetNodeId] || resolveJunction(targetNodeId);
  }, [corridor?.isActive, corridor?.nodes, corridor?.progress]);

  // Dynamic random emergency fleet (no fixed ambulances, random origins & destinations)
  const [fleetUnits, setFleetUnits] = useState(() => createInitialRandomFleet());

  // Live telemetry metrics state for UI fleet cards
  const [fleetMetrics, setFleetMetrics] = useState({});

  // Mutable animation state for 60fps Leaflet updates without React re-render lag
  const fleetLiveRef = useRef({});

  // Synchronize dynamic fleet units with mutable live ref
  useEffect(() => {
    fleetUnits.forEach((unit) => {
      if (!fleetLiveRef.current[unit.id]) {
        fleetLiveRef.current[unit.id] = {
          progress: unit.progress || 0,
          speedKmh: unit.speedKmh || 52,
          coords: unit.denseCoords || [],
          distanceMeters: unit.distanceMeters || 2500,
          currentPos: getInterpolatedPoint(unit.denseCoords, unit.progress || 0),
          isTerminating: false,
          status: unit.status,
          statusBadge: unit.statusBadge,
        };
      }
    });
  }, [fleetUnits]);

  useEffect(() => {
    onSelectRef.current = onSelectIntersection;
    intersectionsRef.current = intersections;
  }, [onSelectIntersection, intersections]);

  // Map simulated intersection properties to BBSR junctions
  const junctionDataMap = useMemo(() => {
    const map = {};
    BBSR_INTERSECTIONS.forEach((junc, idx) => {
      // Find matching intersection in props or synthesize stable simulated stats
      const cleanJuncName = junc.name.toLowerCase().replace(/[^a-z0-9]/g, "");
      const matched = intersections.find((i) => {
        const cleanName = i.name.toLowerCase().replace(/[^a-z0-9]/g, "");
        return cleanName.includes(cleanJuncName) || cleanJuncName.includes(cleanName) || i.id === junc.id;
      });

      if (matched) {
        map[junc.id] = {
          ...junc,
          ...matched,
          zone: junc.zone,
          zoneName: junc.zoneName,
          coords: [junc.lat, junc.lon],
        };
      } else {
        // Dynamic live simulation stats that update over time rather than static red values
        const timeOffset = Math.floor(Date.now() / 3000);
        const dynamicSeed = (idx * 23 + timeOffset * 7) % 100;
        // Congestion is mostly low to medium (green & yellow), with very few critical (red)
        const status = dynamicSeed > 84 ? "critical" : dynamicSeed > 42 ? "medium" : "low";
        const vehicleCount = status === "critical" ? 140 + (dynamicSeed % 40) : status === "medium" ? 65 + (dynamicSeed % 45) : 20 + (dynamicSeed % 35);
        const averageSpeed = status === "critical" ? 18 + (dynamicSeed % 10) : status === "medium" ? 34 + (dynamicSeed % 12) : 48 + (dynamicSeed % 14);
        const congestionPct = status === "critical" ? 72 + (dynamicSeed % 16) : status === "medium" ? 38 + (dynamicSeed % 26) : 15 + (dynamicSeed % 22);

        map[junc.id] = {
          id: junc.id,
          name: junc.name,
          coords: [junc.lat, junc.lon],
          zone: junc.zone,
          zoneName: junc.zoneName,
          status,
          vehicleCount,
          averageSpeed,
          congestionPct,
          lanes: [
            { direction: "North", vehicleCount: Math.round(vehicleCount * 0.28), averageSpeed, light: status === "critical" ? "red" : "green", manualActive: false },
            { direction: "East",  vehicleCount: Math.round(vehicleCount * 0.32), averageSpeed: Math.max(12, averageSpeed - 4), light: status === "critical" ? "red" : "green", manualActive: false },
            { direction: "South", vehicleCount: Math.round(vehicleCount * 0.22), averageSpeed: averageSpeed + 3, light: status === "medium" ? "yellow" : "red", manualActive: false },
            { direction: "West",  vehicleCount: Math.round(vehicleCount * 0.18), averageSpeed: averageSpeed + 5, light: "red", manualActive: false },
          ]
        };
      }
    });
    return map;
  }, [intersections]);

  // 1. Initialize Leaflet Map once
  useEffect(() => {
    window.__inspectIntersectionById = (id) => {
      const data = junctionDataMap[id];
      if (data) {
        onSelectRef.current?.(data, "map");
      }
    };

    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [20.2961, 85.8245],
        zoom: 13,
        zoomControl: false,
      });

      L.control.zoom({ position: "bottomright" }).addTo(map);

      // 100% Free Esri Dark Gray Canvas — NO API KEY, NO WATERMARKS
      // maxNativeZoom: 16 = tiles available up to zoom 16, Leaflet cleanly upscales to 18
      const tileLayer = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        {
          attribution: '&copy; Esri, HERE, Garmin &mdash; Bhubaneswar Smart City GIS',
          maxNativeZoom: 16,
          maxZoom: 18,
        }
      ).addTo(map);

      tileLayer.on("tileerror", () => {
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          attribution: '&copy; OpenStreetMap contributors',
          maxZoom: 18,
        }).addTo(map);
      });

      mapInstanceRef.current = map;

      // Draw Arterial Road Network connecting all real intersections
      const roadGroup = L.featureGroup().addTo(map);
      roadNetworkLayerRef.current = roadGroup;

      BBSR_ROAD_SEGMENTS.forEach((seg) => {
        const fromJ = BBSR_INTERSECTION_MAP[seg.from];
        const toJ = BBSR_INTERSECTION_MAP[seg.to];
        if (!fromJ || !toJ) return;

        const pts = [
          [fromJ.lat, fromJ.lon],
          ...(seg.waypoints || []),
          [toJ.lat, toJ.lon]
        ];

        const isHighway = seg.type === 'nh';
        const isStateHighway = seg.type === 'sh';

        L.polyline(pts, {
          color: isHighway ? "rgba(217,119,87, 0.42)" : isStateHighway ? "rgba(217,119,87, 0.32)" : "rgba(181,177,164, 0.22)",
          weight: isHighway ? 4.5 : isStateHighway ? 3.2 : 2.2,
          opacity: 0.9,
          lineCap: "round",
          lineJoin: "round",
        }).addTo(roadGroup);
      });

      setTimeout(() => map.invalidateSize(), 150);
      setTimeout(() => map.invalidateSize(), 500);
    }

    const handleResize = () => mapInstanceRef.current?.invalidateSize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      delete window.__inspectIntersectionById;
    };
  }, []);

  // 2. Render / Update Traffic Light Markers for All 46 Bhubaneswar Intersections
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const corridorNodes = corridor?.isActive ? (corridor.nodes || []) : [];

    BBSR_INTERSECTIONS.forEach((junc) => {
      const data = junctionDataMap[junc.id] || junc;
      const isCorridorNode = corridorNodes.includes(junc.id) || corridorNodes.includes(junc.name) || corridorNodes.includes(data.name) || corridorNodes.includes(data.id);
      const isCritical = data.status === "critical";
      const isMedium = data.status === "medium";
      const isGreen = !isCritical && !isMedium;

      // Traffic Light Lamp Statuses
      const redClass = isCritical ? "lamp-red active pulse" : "lamp-red";
      const yellowClass = isMedium ? "lamp-yellow active pulse" : "lamp-yellow";
      const greenClass = (isGreen || isCorridorNode) ? "lamp-green active pulse" : "lamp-green";

      const zoneColor = ZONE_COLORS[junc.zone] || "#e6926f";

      // Traffic Light Housing Icon HTML
      const trafficLightHtml = `
        <div class="tl-marker-wrap ${isCorridorNode ? 'corridor-node' : ''}" id="tl-${junc.id}">
          <div class="tl-housing">
            <div class="tl-visor"></div>
            <div class="tl-lens ${redClass}"></div>
            <div class="tl-lens ${yellowClass}"></div>
            <div class="tl-lens ${greenClass}"></div>
          </div>
          <div class="tl-tag" style="border-left-color: ${zoneColor}">
            ${junc.name.split(" ")[0]}
          </div>
        </div>
      `;

      // Hover Tooltip HTML
      const tooltipHtml = `
        <div class="traffic-tooltip-content">
          <div class="tt-header">
            <span class="tt-title">${junc.name}</span>
            <span class="tt-zone" style="background: ${zoneColor}22; color: ${zoneColor}; border: 1px solid ${zoneColor}66;">
              ${junc.zoneName || junc.zone.toUpperCase()}
            </span>
          </div>
          <div class="tt-row">
            <span>Signal State:</span>
            <strong style="color: ${isCorridorNode ? '#63a375' : isCritical ? '#e5534b' : isMedium ? '#dba53a' : '#63a375'}">
              ${isCorridorNode ? 'EMERGENCY PREEMPTION (GREEN)' : isCritical ? '🔴 HEAVY LOAD (RED)' : isMedium ? '🟡 MODERATE (PHASING)' : '🟢 FREE FLOW (GREEN)'}
            </strong>
          </div>
          <div class="tt-grid">
            <div>Vehicles: <strong>${data.vehicleCount || 0}</strong></div>
            <div>Velocity: <strong>${data.averageSpeed || 32} km/h</strong></div>
          </div>
          <div class="tt-hint">Click junction for live node telemetry</div>
        </div>
      `;

      let marker = markersMapRef.current[junc.id];

      if (!marker) {
        const customIcon = L.divIcon({
          className: "traffic-light-div-icon",
          html: trafficLightHtml,
          iconSize: [42, 48],
          iconAnchor: [12, 24],
        });

        marker = L.marker([junc.lat, junc.lon], { icon: customIcon }).addTo(map);

        // Tooltip on Hover
        marker.bindTooltip(tooltipHtml, {
          direction: "top",
          offset: [0, -20],
          className: "leaflet-custom-traffic-tooltip",
          opacity: 0.98,
        });

        // Click to Open Mini Detail Telemetry Card
        marker.on("click", () => {
          setSelectedJunction(data);
        });

        markersMapRef.current[junc.id] = marker;
      } else {
        const el = document.getElementById(`tl-${junc.id}`);
        if (el) {
          el.outerHTML = trafficLightHtml;
        }
        marker.setTooltipContent(tooltipHtml);
      }
    });
  }, [junctionDataMap, corridor]);

  // 3. Render Dynamic Emergency Ambulances on the Map
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Remove any markers for ambulances that have terminated
    const activeIds = new Set(fleetUnits.map(u => u.id));
    Object.keys(fleetMarkersRef.current).forEach((id) => {
      if (!activeIds.has(id)) {
        map.removeLayer(fleetMarkersRef.current[id]);
        delete fleetMarkersRef.current[id];
      }
    });

    fleetUnits.forEach((unit) => {
      const coords = unit.denseCoords || [];
      if (coords.length < 2) return;

      const initialPos = fleetLiveRef.current[unit.id]?.currentPos || getInterpolatedPoint(coords, unit.progress || 0);
      let marker = fleetMarkersRef.current[unit.id];
      const isTraced = tracedVehicle?.id === unit.id;

      if (!marker) {
        marker = L.marker(initialPos, {
          icon: L.divIcon({
            className: "fleet-div-icon",
            html: getAmbulanceSvgHtml(unit, false),
            iconSize: [68, 48],
            iconAnchor: [34, 24],
          }),
          zIndexOffset: 12000,
        }).addTo(map);

        marker.bindTooltip(`
          <div class="fleet-marker-tooltip">
            <div class="fmt-head">
              <strong>${unit.callsign}</strong>
            </div>
            <div class="fmt-route">
              <div class="fmt-route-line"><span class="fmt-badge green">START</span> ${unit.origin}</div>
              <div class="fmt-route-line"><span class="fmt-badge red">DEST</span> ${unit.destination}</div>
            </div>
            <div class="fmt-footer">
              <span style="color:${unit.color}; font-weight:700;">● ${unit.status}</span>
              <span class="fmt-speed">${unit.speedKmh} km/h</span>
            </div>
            <div class="fmt-hint">Click unit to trace AI fastest route across city</div>
          </div>
        `, {
          direction: "top",
          offset: [0, -20],
          className: "leaflet-custom-traffic-tooltip",
        });

        marker.on("click", () => {
          handleSelectEmergencyVehicle(unit);
        });

        fleetMarkersRef.current[unit.id] = marker;
      } else {
        const el = document.getElementById(`amb-marker-${unit.id}`);
        if (el) {
          el.className = `modern-ambulance-marker ${isTraced ? 'is-selected-unit' : ''}`;
        }
      }
    });
  }, [fleetUnits, tracedVehicle]);

  // 3b. Real-Time Continuous Ambulance Movement Loop & Dynamic Destination Termination
  useEffect(() => {
    let lastUiThrottle = 0;

    const intervalId = setInterval(() => {
      const now = Date.now();
      const liveState = fleetLiveRef.current;
      const metricsUpdates = {};
      const terminatedIds = [];

      fleetUnits.forEach((unit) => {
        const uState = liveState[unit.id];
        if (!uState || !uState.coords || uState.coords.length < 2) return;

        if (uState.isTerminating) {
          // If already reached destination, wait 2.5 seconds then mark for removal
          if (now - uState.terminationTime > 2500) {
            terminatedIds.push(unit.id);
          }
          return;
        }

        // Advance progress smoothly based on real vehicle speed and route distance
        const progressDelta = ((uState.speedKmh / (uState.distanceMeters || 2500)) * 0.36) * 100;
        let nextProg = uState.progress + progressDelta;

        if (nextProg >= 100) {
          nextProg = 100;
          uState.isTerminating = true;
          uState.terminationTime = now;
          uState.status = "Delivered • Arrived at Hospital";
          uState.statusBadge = "MISSION COMPLETED";

          // Trigger smooth fade-out and arrival glow
          const el = document.getElementById(`amb-marker-${unit.id}`);
          if (el) {
            el.classList.add("is-terminating");
          }
        }

        uState.progress = nextProg;

        // Subtle realistic speed fluctuation (+/- 2 km/h)
        const speedVar = Math.sin((now / 1500) + unit.id.charCodeAt(unit.id.length - 1)) * 2;
        uState.speedKmh = Math.round(unit.speedKmh + speedVar);

        const currentPos = getInterpolatedPoint(uState.coords, nextProg);
        uState.currentPos = currentPos;

        // Directly update Leaflet marker position for silky smooth movement
        const marker = fleetMarkersRef.current[unit.id];
        if (marker) {
          marker.setLatLng(currentPos);
        }

        // Flip vehicle horizontally based on East/West direction so tires ALWAYS stay on the bottom
        const nextPos = getInterpolatedPoint(uState.coords, Math.min(100, nextProg + 0.6));
        const isHeadingWest = nextPos[1] < currentPos[1];
        const el = document.getElementById(`amb-marker-${unit.id}`);
        if (el) {
          const body = el.querySelector(".amb-vehicle-body");
          if (body) {
            body.style.transform = isHeadingWest ? "scaleX(-1)" : "scaleX(1)";
          }
        }

        // Calculate remaining ETA
        const remainingPct = 100 - nextProg;
        const remainingMeters = (remainingPct / 100) * uState.distanceMeters;
        const etaSec = Math.max(0, Math.round(remainingMeters / (uState.speedKmh / 3.6)));

        metricsUpdates[unit.id] = {
          progress: Math.round(nextProg),
          speed: uState.speedKmh,
          etaSec,
          status: uState.status,
          statusBadge: uState.statusBadge,
        };
      });

      // Terminate arrived ambulances and automatically spawn new dynamic emergency calls
      if (terminatedIds.length > 0) {
        const map = mapInstanceRef.current;
        terminatedIds.forEach(id => {
          if (fleetMarkersRef.current[id]) {
            if (map) map.removeLayer(fleetMarkersRef.current[id]);
            delete fleetMarkersRef.current[id];
          }
          delete liveState[id];
          if (tracedVehicle?.id === id) {
            clearRouteTrace();
          }
        });

        setFleetUnits(prev => {
          const remaining = prev.filter(u => !terminatedIds.includes(u.id));
          // Random target fleet size in the city between 3 and 7 units
          const targetSize = Math.floor(Math.random() * 5) + 3;
          const newUnits = [];
          const currentIds = remaining.map(u => u.id);

          while (remaining.length + newUnits.length < targetSize) {
            const fresh = generateDynamicEmergencyUnit([...currentIds, ...newUnits.map(n => n.id)]);
            newUnits.push(fresh);
          }

          return [...remaining, ...newUnits];
        });
      }

      // Throttle React UI state update to ~250ms for optimal UI rendering
      if (now - lastUiThrottle > 250) {
        lastUiThrottle = now;
        setFleetMetrics((prev) => ({ ...prev, ...metricsUpdates }));
      }
    }, 60);

    return () => clearInterval(intervalId);
  }, [fleetUnits, tracedVehicle]);

  // 3c. Real-Time Emergency Fleet Telemetry Broadcast to Firebase
  useEffect(() => {
    let lastSyncTime = 0;
    const syncInterval = setInterval(() => {
      const now = Date.now();
      if (now - lastSyncTime >= 2000) {
        lastSyncTime = now;
        const liveState = fleetLiveRef.current;
        const fleetList = fleetUnits.map((unit) => {
          const uState = liveState[unit.id] || {};
          return {
            id: unit.id,
            callsign: unit.callsign,
            type: unit.type,
            origin: unit.origin,
            destination: unit.destination,
            progress: Math.round(uState.progress || unit.progress || 0),
            speedKmh: uState.speedKmh || unit.speedKmh || 48,
            currentPos: uState.currentPos || [20.2961, 85.8245],
            status: uState.status || unit.status,
          };
        });

        syncLiveFleetToFirebase(fleetList);
      }
    }, 2000);

    return () => clearInterval(syncInterval);
  }, [fleetUnits]);

  useEffect(() => {
    const unsub = subscribeToLiveFleet((remoteFleet) => {
      // Remote fleet positions connected via Firebase
    });
    return () => unsub?.();
  }, []);

  // 4. Handle Trace Route for Emergency Vehicle
  const handleSelectEmergencyVehicle = async (unit) => {
    setTracedVehicle(unit);

    if (unit.denseCoords && unit.denseCoords.length > 1) {
      setTracedRouteGeometry(unit.denseCoords);
      setTracedRouteDistance(unit.distanceMeters || 2500);
    } else {
      const computed = findFastestEmergencyRoute(unit.startNode, unit.endNode);
      setTracedRouteGeometry(computed.roadCoords);
      setTracedRouteDistance(computed.distanceMeters);
    }

    // Pan smoothly to current live position of vehicle
    const livePos = fleetLiveRef.current[unit.id]?.currentPos;
    if (livePos && mapInstanceRef.current) {
      mapInstanceRef.current.panTo(livePos, { animate: true, duration: 0.8 });
    }
  };

  // 5. Draw Traced Emergency Route on Map
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (tracedRouteLayerRef.current) {
      map.removeLayer(tracedRouteLayerRef.current);
      tracedRouteLayerRef.current = null;
    }

    if (tracedVehicle && tracedRouteGeometry.length > 0) {
      const group = L.featureGroup().addTo(map);
      tracedRouteLayerRef.current = group;

      // Glowing underlayer
      L.polyline(tracedRouteGeometry, {
        color: tracedVehicle.color || "#63a375",
        weight: 10,
        opacity: 0.35,
        lineCap: "round",
        lineJoin: "round",
      }).addTo(group);

      // Main animated dashed corridor line
      const polyline = L.polyline(tracedRouteGeometry, {
        color: "#ffffff",
        weight: 5,
        opacity: 0.95,
        dashArray: "12, 10",
        lineCap: "round",
        lineJoin: "round",
        className: "traced-emergency-polyline",
      }).addTo(group);

      // Add Origin Marker
      const pStart = tracedRouteGeometry[0];
      L.marker(pStart, {
        icon: L.divIcon({
          className: "route-waypoint-icon",
          html: `<div class="route-origin-pin">ORIGIN: ${tracedVehicle.origin.split(" ")[0]}</div>`,
        })
      }).addTo(group);

      // Add Destination Marker
      const pEnd = tracedRouteGeometry[tracedRouteGeometry.length - 1];
      L.marker(pEnd, {
        icon: L.divIcon({
          className: "route-waypoint-icon",
          html: `<div class="route-dest-pin">DEST: ${tracedVehicle.destination.split(" ")[0]}</div>`,
        })
      }).addTo(group);

      // Smoothly pan & fit bounds
      map.fitBounds(polyline.getBounds(), { padding: [80, 80], maxZoom: 15 });
    }
  }, [tracedVehicle, tracedRouteGeometry]);

  // 6. Existing Green Corridor polyline & road geometry (calculated via AI Fastest Path Engine)
  useEffect(() => {
    if (corridor && corridor.isActive) {
      if (corridor.roadCoords && corridor.roadCoords.length > 1) {
        setRoadGeometry(corridor.roadCoords);
        setRoadDistance(corridor.distanceMeters || (corridor.distanceKm ? Math.round(parseFloat(corridor.distanceKm) * 1000) : 3200));
      } else if (corridor.origin || corridor.destination) {
        const computed = findFastestEmergencyRoute(corridor.origin || corridor.originId, corridor.destination || corridor.destId);
        setRoadGeometry(computed.roadCoords);
        setRoadDistance(computed.distanceMeters);
      } else if (corridor.nodes && corridor.nodes.length > 0) {
        const waypoints = corridor.nodes.map(n => {
          const j = resolveJunction(n);
          return [j.lat, j.lon];
        });
        const instant = generateInstantRoadGeometry(waypoints);
        setRoadGeometry(instant.roadCoords);
        setRoadDistance(instant.distanceMeters);
      }
    } else {
      setRoadGeometry([]);
      setRoadDistance(0);
    }
  }, [corridor?.isActive, corridor?.roadCoords, corridor?.nodes, corridor?.origin, corridor?.destination]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (corridorLayerRef.current) {
      map.removeLayer(corridorLayerRef.current);
      corridorLayerRef.current = null;
    }
    if (ambulanceMarkerRef.current) {
      map.removeLayer(ambulanceMarkerRef.current);
      ambulanceMarkerRef.current = null;
    }

    if (corridor && corridor.isActive && roadGeometry.length > 1) {
      const group = L.layerGroup().addTo(map);
      corridorLayerRef.current = group;

      // Outer green glow aura
      L.polyline(roadGeometry, {
        color: "#63a375",
        weight: 12,
        opacity: 0.25,
        lineCap: "round",
        lineJoin: "round",
      }).addTo(group);

      // Core green wave polyline with animated dashes
      const polyline = L.polyline(roadGeometry, {
        color: "#63a375",
        weight: 6,
        opacity: 0.95,
        dashArray: "12, 8",
        lineCap: "round",
        lineJoin: "round",
        className: "traced-emergency-polyline",
      }).addTo(group);

      // Add Origin Marker Pin
      const pStart = roadGeometry[0];
      L.marker(pStart, {
        icon: L.divIcon({
          className: "route-waypoint-icon",
          html: `<div class="route-origin-pin" style="background:#4d8a5f;border:1.5px solid #8fbf9d;box-shadow:0 0 12px rgba(99,163,117,0.7)">🟢 DISPATCH: ${(corridor.origin || "ORIGIN").split(" ")[0]}</div>`,
        }),
        zIndexOffset: 12000,
      }).addTo(group);

      // Add Destination Marker Pin
      const pEnd = roadGeometry[roadGeometry.length - 1];
      L.marker(pEnd, {
        icon: L.divIcon({
          className: "route-waypoint-icon",
          html: `<div class="route-dest-pin" style="background:#c43d36;border:1.5px solid #ee8a84;box-shadow:0 0 12px rgba(229,83,75,0.7)">🏥 DEST: ${(corridor.destination || "DEST").split(" ")[0]}</div>`,
        }),
        zIndexOffset: 12000,
      }).addTo(group);

      // Fit map bounds to show complete emergency corridor
      map.fitBounds(polyline.getBounds(), { padding: [80, 80], maxZoom: 15 });

      const currentPos = getInterpolatedPoint(roadGeometry, corridor.progress || 0);
      const vehicleName = corridor.vehicleType === "fire" ? "FIRE-01" : "CORRIDOR-108";

      const vehicleMarker = L.marker(currentPos, {
        icon: L.divIcon({
          className: "ambulance-custom-icon-wrapper",
          html: getAmbulanceSvgHtml({
            id: vehicleName,
            type: corridor.vehicleType,
            color: "#63a375",
            speedKmh: 58,
          }, true),
          iconSize: [68, 48],
          iconAnchor: [34, 24],
        }),
        zIndexOffset: 25000,
      }).addTo(map);

      ambulanceMarkerRef.current = vehicleMarker;
    }
  }, [corridor?.isActive, roadGeometry]);

  useEffect(() => {
    if (corridor && corridor.isActive && ambulanceMarkerRef.current && roadGeometry.length > 1) {
      const prog = Math.min(100, Math.max(0, corridor.progress || 0));
      const currentPos = getInterpolatedPoint(roadGeometry, prog);
      ambulanceMarkerRef.current.setLatLng(currentPos);

      // Flip vehicle horizontally based on East/West direction so tires ALWAYS stay on the bottom
      const nextProg = Math.min(100, prog + 0.5);
      const nextPos = getInterpolatedPoint(roadGeometry, nextProg);
      const isHeadingWest = nextPos[1] < currentPos[1];
      const vehicleName = corridor.vehicleType === "fire" ? "FIRE-01" : "CORRIDOR-108";
      const el = document.getElementById(`amb-marker-${vehicleName}`);
      if (el) {
        const body = el.querySelector(".amb-vehicle-body");
        if (body) {
          body.style.transform = isHeadingWest ? "scaleX(-1)" : "scaleX(1)";
        }
      }
    }
  }, [corridor?.progress, roadGeometry]);

  const clearRouteTrace = () => {
    setTracedVehicle(null);
    setTracedRouteGeometry([]);
    setTracedRouteDistance(0);
    if (tracedRouteLayerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(tracedRouteLayerRef.current);
      tracedRouteLayerRef.current = null;
    }
  };

  const distanceKm = (roadDistance / 1000).toFixed(1);
  const tracedDistanceKm = (tracedRouteDistance / 1000).toFixed(1);

  return (
    <div className="map-view-container">
      {/* Top Header Bar */}
      <div className="map-overlay-header">
        <div className="map-badge-card">
          <div className="map-badge-title">
            <i className="fas fa-map-marked-alt" style={{ color: "var(--blue)" }} />
            Bhubaneswar Real-Time Traffic GIS (46 City Intersections)
          </div>
        </div>

        <div className="map-badge-card">
          <div className="map-legend">
            <span className="legend-item">
              <span className="signal-dot red"></span> Heavy / Red Light
            </span>
            <span className="legend-item">
              <span className="signal-dot yellow"></span> Moderate / Yellow
            </span>
            <span className="legend-item">
              <span className="signal-dot green"></span> Clear Flow / Green
            </span>
            <span className="legend-item" style={{ marginLeft: "8px" }}>
              <span style={{ color: "#e6926f" }}>━━</span> NH-16
            </span>
            <span className="legend-item">
              <span style={{ color: "#e6926f" }}>━━</span> State Arterials
            </span>
          </div>
        </div>
      </div>

      {/* Floating Emergency Fleet Live Units Dock (Admin Panel) */}
      <div className={`map-fleet-dock ${isFleetPanelOpen ? 'open' : 'minimized'}`}>
        <div className="fleet-dock-header" onClick={() => setIsFleetPanelOpen(!isFleetPanelOpen)}>
          <div className="fleet-dock-title">
            <i className="fas fa-ambulance" style={{ color: "var(--red)" }} />
            <span>Emergency Fleet Live ({fleetUnits.length} Active Dynamic Units)</span>
            <span className="live-sim-badge">DYNAMIC CALLOUTS</span>
          </div>
          <button className="dock-toggle-btn">
            <i className={`fas ${isFleetPanelOpen ? 'fa-chevron-down' : 'fa-chevron-up'}`} />
          </button>
        </div>

        {isFleetPanelOpen && (
          <div className="fleet-dock-body">
            <div className="fleet-dock-sub">Dynamic emergency calls across Bhubaneswar (units automatically terminate on hospital arrival):</div>
            <div className="fleet-units-list">
              {fleetUnits.map((unit) => {
                const isSelected = tracedVehicle?.id === unit.id;
                const metrics = fleetMetrics[unit.id] || {
                  progress: unit.progress || 0,
                  speed: unit.speedKmh || 52,
                  etaSec: unit.etaSec || 25,
                  status: unit.status,
                  statusBadge: unit.statusBadge,
                };

                const isArrived = metrics.progress >= 100;

                return (
                  <div
                    key={unit.id}
                    className={`fleet-unit-card ${isSelected ? 'active-traced' : ''} ${isArrived ? 'unit-arrived' : ''}`}
                    onClick={() => handleSelectEmergencyVehicle(unit)}
                  >
                    {/* Unit Header */}
                    <div className="unit-card-header">
                      <div className="unit-card-icon" style={{ borderColor: unit.color, background: `${unit.color}18` }}>
                        <i className={`fas ${unit.type === 'fire' ? 'fa-fire-extinguisher' : 'fa-ambulance'}`} style={{ color: unit.color, fontSize: '0.9rem' }} />
                      </div>
                      <div className="unit-card-info">
                        <div className="unit-card-callsign">
                          {unit.id}
                          <span
                            className="unit-card-badge"
                            style={{
                              background: isArrived ? '#10b98122' : `${unit.color}22`,
                              color: isArrived ? '#63a375' : unit.color,
                              borderColor: isArrived ? '#10b98155' : `${unit.color}55`
                            }}
                          >
                            <span className="live-status-dot" style={{ background: isArrived ? '#63a375' : unit.color }} />
                            {isArrived ? 'ARRIVED' : (metrics.statusBadge || unit.statusBadge)}
                          </span>
                        </div>
                        <div className="unit-card-driver">{unit.driver}</div>
                      </div>
                      <button className="unit-trace-btn" title="Focus & Trace on Map">
                        <i className={`fas ${isSelected ? 'fa-satellite-dish' : 'fa-route'}`} />
                      </button>
                    </div>

                    {/* Prominent Start & End Points Display */}
                    <div className="unit-card-od">
                      <div className="od-row start-row">
                        <span className="od-pill start-pill">START</span>
                        <span className="od-text" title={unit.origin}>{unit.origin}</span>
                      </div>
                      <div className="od-divider">
                        <span className="od-line" />
                        <i className="fas fa-angle-down od-arrow" />
                      </div>
                      <div className="od-row end-row">
                        <span className="od-pill end-pill">END</span>
                        <span className="od-text" title={unit.destination}>{unit.destination}</span>
                      </div>
                    </div>

                    {/* Real-Time Live Journey Progress Bar */}
                    <div className="unit-card-progress">
                      <div className="unit-prog-meta">
                        <span className="unit-prog-dir">
                          <i className="fas fa-arrow-right" />
                          {isArrived ? 'Delivered to Hospital' : 'En Route Emergency'}
                        </span>
                        <span className="unit-prog-pct">{metrics.progress}%</span>
                      </div>
                      <div className="unit-prog-track">
                        <div
                          className="unit-prog-fill"
                          style={{
                            width: `${metrics.progress}%`,
                            background: isArrived ? '#63a375' : `linear-gradient(90deg, ${unit.color}88, ${unit.color})`,
                            boxShadow: `0 0 10px ${isArrived ? '#63a375' : unit.color}`
                          }}
                        />
                      </div>
                    </div>

                    {/* Telemetry Footer */}
                    <div className="unit-card-footer">
                      <div className="unit-tele-item">
                        <i className="fas fa-tachometer-alt" />
                        <span>{metrics.speed} km/h</span>
                      </div>
                      <div className="unit-tele-item">
                        <i className="fas fa-stopwatch" />
                        <span>{isArrived ? 'DELIVERED' : `~${metrics.etaSec}s ETA`}</span>
                      </div>
                      <div className="unit-tele-live" style={{ color: isArrived ? '#63a375' : unit.color }}>
                        <span className="live-blink-dot" style={{ background: isArrived ? '#63a375' : unit.color }} />
                        {isArrived ? 'COMPLETED' : 'LIVE MOVING'}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Traced Emergency Vehicle Active Telemetry Card */}
      {tracedVehicle && (
        <div className="traced-vehicle-card">
          <div className="tvc-header">
            <div className="tvc-title">
              <span className="tvc-icon">{tracedVehicle.icon}</span>
              <div>
                <div className="tvc-callsign">{tracedVehicle.callsign}</div>
                <div className="tvc-driver">{tracedVehicle.driver} • {tracedVehicle.priority}</div>
              </div>
            </div>
            <button className="tvc-close-btn" onClick={clearRouteTrace} title="Close Route Trace">
              <i className="fas fa-times" />
            </button>
          </div>

          <div className="tvc-route-row">
            <div className="tvc-location-box">
              <div className="tvc-loc-label">START / ORIGIN</div>
              <div className="tvc-loc-name">{tracedVehicle.origin}</div>
            </div>
            <div className="tvc-arrow">&rarr;</div>
            <div className="tvc-location-box">
              <div className="tvc-loc-label">DESTINATION</div>
              <div className="tvc-loc-name">{tracedVehicle.destination}</div>
            </div>
          </div>

          <div className="tvc-stats-grid">
            <div className="tvc-stat">
              <span className="tvc-stat-label">Live Speed</span>
              <strong className="tvc-stat-val">{tracedVehicle.speedKmh} km/h</strong>
            </div>
            <div className="tvc-stat">
              <span className="tvc-stat-label">Route Length</span>
              <strong className="tvc-stat-val">{tracedDistanceKm} km</strong>
            </div>
            <div className="tvc-stat">
              <span className="tvc-stat-label">Estimated Transit</span>
              <strong className="tvc-stat-val">~{tracedVehicle.etaSec}s</strong>
            </div>
            <div className="tvc-stat">
              <span className="tvc-stat-label">AI Corridor Status</span>
              <strong className="tvc-stat-val" style={{ color: "#63a375" }}>READY</strong>
            </div>
          </div>

          <div className="tvc-actions">
            <button
              className="tvc-btn-preempt"
              onClick={() => {
                onCancelCorridor?.();
                onSelectRef.current = onSelectIntersection;
                // Switch to emergency tab with this route preselected
                alert(`🚨 Green Wave activated for ${tracedVehicle.id}! Signals along ${tracedVehicle.origin} to ${tracedVehicle.destination} are prioritized.`);
              }}
            >
              <i className="fas fa-bolt" /> Preempt Traffic Signals (Green Wave)
            </button>
            <button className="tvc-btn-dismiss" onClick={clearRouteTrace}>
              Clear Route Trace
            </button>
          </div>
        </div>
      )}

      {/* Junction Telemetry Mini Popup Card (When Junction is Clicked) */}
      {selectedJunction && (
        <div className="map-junction-popup-card">
          <div className="jpc-header">
            <div className="jpc-tl-preview">
              <div className="jpc-lamp red active"></div>
              <div className="jpc-lamp yellow"></div>
              <div className="jpc-lamp green active"></div>
            </div>
            <div>
              <div className="jpc-name">{selectedJunction.name}</div>
              <span
                className="jpc-zone-pill"
                style={{
                  background: `${ZONE_COLORS[selectedJunction.zone] || '#e6926f'}22`,
                  color: ZONE_COLORS[selectedJunction.zone] || '#e6926f',
                  border: `1px solid ${ZONE_COLORS[selectedJunction.zone] || '#e6926f'}66`
                }}
              >
                {selectedJunction.zoneName || (selectedJunction.zone && selectedJunction.zone.toUpperCase()) || "URBAN SECTOR"}
              </span>
            </div>
            <button className="jpc-close" onClick={() => setSelectedJunction(null)}>
              <i className="fas fa-times" />
            </button>
          </div>

          <div className="jpc-meta-grid">
            <div className="jpc-meta-item">
              <span className="jpc-meta-label">Signal State</span>
              <strong style={{ color: selectedJunction.status === "critical" ? "var(--red)" : selectedJunction.status === "medium" ? "var(--amber)" : "var(--green)" }}>
                {selectedJunction.status === "critical" ? "RED (HOLDING)" : selectedJunction.status === "medium" ? "PHASING / YELLOW" : "EW GREEN (FLOW)"}
              </strong>
            </div>
            <div className="jpc-meta-item">
              <span className="jpc-meta-label">Vehicle Volume</span>
              <strong>{selectedJunction.vehicleCount || 120} Vehicles</strong>
            </div>
            <div className="jpc-meta-item">
              <span className="jpc-meta-label">Clearance Speed</span>
              <strong>{selectedJunction.averageSpeed || 34} km/h</strong>
            </div>
            <div className="jpc-meta-item">
              <span className="jpc-meta-label">Network Load</span>
              <strong style={{ color: selectedJunction.status === "critical" ? "var(--red)" : "var(--blue)" }}>
                {selectedJunction.congestionPct || 65}%
              </strong>
            </div>
          </div>

          {/* Congestion Load Bar */}
          <div className="jpc-load-bar-wrap">
            <div className="jpc-load-bar-head">
              <span>Traffic Load Density</span>
              <span>{selectedJunction.congestionPct || 65}%</span>
            </div>
            <div className="jpc-load-bar-bg">
              <div
                className="jpc-load-bar-fill"
                style={{
                  width: `${selectedJunction.congestionPct || 65}%`,
                  background: selectedJunction.status === "critical" ? "var(--red)" : selectedJunction.status === "medium" ? "var(--amber)" : "var(--green)"
                }}
              />
            </div>
          </div>

          <button
            className="jpc-inspect-btn"
            onClick={() => {
              onSelectIntersection?.(selectedJunction, "map");
              setSelectedJunction(null);
            }}
          >
            <i className="fas fa-sliders-h" /> Inspect Node Diagnostics Matrix &rarr;
          </button>
        </div>
      )}

      {/* Emergency Active HUD on Map */}
      {corridor && corridor.isActive && (
        <div className="corridor-map-hud">
          {corridor.progress >= 100 ? (
            <div className="corridor-arrived-banner">
              <div className="arrived-icon-wrap">
                <i className="fas fa-check-circle" style={{ fontSize: "1.4rem", color: "#63a375" }} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 800, fontSize: "0.85rem", color: "#f4f2ea", letterSpacing: "0.3px" }}>
                  DESTINATION REACHED • MISSION COMPLETED
                </div>
                <div style={{ fontSize: "0.7rem", color: "#d4d0c4", marginTop: "2px" }}>
                  Emergency unit safely delivered to <strong>{corridor.destination}</strong>. Preemption released to AI adaptive control.
                </div>
              </div>
              <button
                className="hud-btn-standdown"
                onClick={onCancelCorridor}
                title="Reset Corridor"
              >
                <i className="fas fa-power-off" /> Stand Down
              </button>
            </div>
          ) : (
            <>
              <div className="hud-top-row">
                <span className="hud-title">
                  <i className={`fas ${corridor.vehicleType === "fire" ? "fa-fire-extinguisher" : corridor.vehicleType === "vip" ? "fa-shield-alt" : "fa-ambulance"}`} />
                  VELOCITI DYNAMIC GREEN CORRIDOR ACTIVE
                </span>
                <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                  <span className="hud-eta">{distanceKm} km Route</span>
                  <span className="hud-speed-badge">
                    <i className="fas fa-tachometer-alt" /> 58 km/h Priority
                  </span>
                  <span className="hud-eta">
                    ETA: {Math.max(1, Math.ceil((100 - (corridor.progress || 0)) * 0.25))}s
                  </span>
                </div>
              </div>

              <div className="hud-sub-row">
                <div className="hud-route">
                  <strong>{corridor.origin}</strong> &rarr; <strong>{corridor.destination}</strong>
                  <span className="hud-signals-count">({corridor.nodes?.length || 4} Signals Preempted)</span>
                </div>
                {nextJunction && (
                  <div className="hud-next-junction">
                    <span className="hud-live-signal-dot"></span>
                    <span>Approaching: <strong>{nextJunction.name}</strong> (FORCED GREEN)</span>
                  </div>
                )}
              </div>

              <div className="hud-progress-bg">
                <div
                  className="hud-progress-fill"
                  style={{
                    width: `${corridor.progress || 0}%`,
                    background: "#d97757",
                    boxShadow: "0 0 10px rgba(99,163,117, 0.7)"
                  }}
                />
              </div>

              <div className="hud-bottom-row">
                <div className="hud-gps-tag">
                  <i className="fas fa-crosshairs" style={{ color: "#e6926f" }} />
                  <span>Smartphone In-Cab Navigation: Active (±2.8m Accuracy)</span>
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  <button
                    className="hud-btn-focus"
                    onClick={() => {
                      if (ambulanceMarkerRef.current && mapInstanceRef.current) {
                        mapInstanceRef.current.setView(ambulanceMarkerRef.current.getLatLng(), 15, { animate: true });
                      }
                    }}
                    title="Center on Emergency Vehicle"
                  >
                    <i className="fas fa-crosshairs" /> Focus
                  </button>
                  <button className="hud-btn-cancel" onClick={onCancelCorridor} title="Cancel Emergency Priority">
                    <i className="fas fa-times" style={{ marginRight: "3px" }} /> Stand Down
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      <div ref={mapContainerRef} className="map-canvas" />
    </div>
  );
}
