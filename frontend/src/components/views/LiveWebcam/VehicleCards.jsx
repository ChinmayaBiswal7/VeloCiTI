import { useEffect } from "react";
import "./AnalysisPanels.css";

const STATUS = {
  PLATED: { label: "Plated", tone: "ok" },
  UNREADABLE: { label: "Plate unreadable", tone: "warn" },
  NO_PLATE: { label: "No plate", tone: "bad" },
};

const blank = (v) => (v ? v : "—");

function formatPlate(text) {
  const m = /^([A-Z]{2})(\d{2})([A-Z]{1,3})(\d{4})$/.exec(text || "");
  return m ? `${m[1]} ${m[2]} ${m[3]} ${m[4]}` : text;
}

function Row({ label, value, sub }) {
  return (
    <div className="vc-row">
      <span className="vc-row-label">{label}</span>
      <span className="vc-row-value">
        {blank(value)}
        {sub ? <em>{sub}</em> : null}
      </span>
    </div>
  );
}

export function VehicleCardGrid({ cards, onOpen }) {
  if (!cards.length) return <div className="ap-empty">No vehicles found</div>;
  return (
    <div className="vc-grid">
      {cards.map((c) => {
        const s = STATUS[c.plate_status];
        return (
          <button key={c.id} className={`vc-tile vc-${s.tone}`} onClick={() => onOpen(c)}>
            <img src={c.crop_b64} alt="" />
            <div className="vc-tile-body">
              <span className={`vc-chip vc-chip-${s.tone}`}>{s.label}</span>
              {c.is_emergency && <span className="vc-chip vc-chip-bad">Emergency</span>}
              <strong>{c.vehicle_type}</strong>
              <span className="vc-tile-id">
                {c.plate_status === "PLATED" ? formatPlate(c.plate.text) : c.reid?.ghost_id}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function DetectedVehicle({ card }) {
  const v = card.visual;
  const mm = v.make_model;
  return (
    <>
      <Row label="Vehicle type" value={card.vehicle_type} />
      <Row label="Body" value={v.body_type} />
      <Row label="Colour" value={v.color} sub={v.secondary_color && v.secondary_color !== v.color ? v.secondary_color : ""} />
      <Row
        label="Make / model"
        value={mm.label}
        sub={mm.label ? `${Math.round(mm.confidence * 100)}%` : ""}
      />
      <Row label="Damage" value={v.damage?.label} sub={v.damage ? `${Math.round(v.damage.confidence * 100)}%` : ""} />
      <Row
        label="Occupants visible"
        value={v.occupants.checked ? String(v.occupants.count) : ""}
      />
    </>
  );
}

function PlatedCard({ card }) {
  const p = card.plate;
  const d = p.decoded;
  const reg = p.registry;
  const rec = reg.record;
  return (
    <>
      <div className="vc-plate-wrap">
        <div className="vc-plate">
          <span className="vc-plate-ind">IND</span>
          <span className="vc-plate-text">{formatPlate(p.text)}</span>
        </div>
        <div className="vc-plate-meta">
          <span className="vc-chip vc-chip-ok">Valid MoRTH format</span>
          <span>Confidence {Math.round(p.confidence * 100)}%</span>
        </div>
      </div>

      {p.alerts?.length > 0 && (
        <div className="vc-alert">
          <i className="fas fa-triangle-exclamation" /> Alert raised for this plate ({p.alerts.length})
        </div>
      )}

      <div className="vc-section">Decoded from the plate</div>
      <Row label="State" value={d?.state} />
      <Row label="RTO office" value={d?.rto_office} sub={d?.rto_code} />
      <Row label="Series / number" value={d ? `${d.series} ${d.number}` : ""} />
      <Row label="Plate colour" value={p.color} sub={p.category} />

      <div className="vc-section">Registration record</div>
      <div className="vc-sim">
        <i className="fas fa-flask" /> {reg.notice}
      </div>
      <Row label="Owner" value={rec.owner_name} />
      <Row label="Father's name" value={rec.father_name} />
      <Row label="Address" value={rec.registered_address} />
      <Row label="Maker / model" value={`${rec.vehicle_maker} ${rec.vehicle_model}`} />
      <Row label="Class / fuel" value={`${rec.vehicle_class} / ${rec.fuel_type}`} />
      <Row label="Registered" value={rec.registration_date} />
      <Row label="Insurance" value={rec.insurance_company} sub={`valid to ${rec.insurance_valid_upto}`} />
      <Row label="Fitness / PUCC" value={`${rec.fitness_valid_upto} / ${rec.pucc_valid_upto}`} />
      <Row label="Status" value={rec.blacklist_status} />

      <div className="vc-section">Seen by the camera</div>
      <DetectedVehicle card={card} />
    </>
  );
}

function UnplatedCard({ card }) {
  const r = card.reid;
  return (
    <>
      <div className="vc-ghost">
        <span className="vc-ghost-id">{r?.ghost_id}</span>
        {r && r.is_new === false && <span className="vc-chip vc-chip-ok">Matched an earlier sighting</span>}
        {r && r.is_new === true && <span className="vc-chip vc-chip-warn">New vehicle</span>}
      </div>
      {card.plate_hint && (
        <div className="vc-sim">
          A plate-like region was read as "{card.plate_hint.text}" ({Math.round(card.plate_hint.confidence * 100)}%
          confidence) but the read is too unreliable or not a valid Indian registration, so it is not trusted.
        </div>
      )}
      <Row label="Camera" value={card.camera_id} />
      {r?.match_score != null && <Row label="Match score" value={r.match_score.toFixed(2)} sub="re-identification" />}

      <div className="vc-section">Vehicle</div>
      <DetectedVehicle card={card} />

      <div className="vc-section">People</div>
      {card.people?.length ? (
        card.people.map((p) => (
          <div className="vc-person" key={p.index}>
            <b>Person {p.index}</b>
            <Row label="Clothing" value={p.clothing_style} sub={p.clothing_style ? `${Math.round(p.clothing_confidence * 100)}%` : ""} />
            <Row label="Upper body colour" value={p.upper_color} />
            {card.yolo_type === "Motorbike" && <Row label="Helmet" value={p.helmet} />}
          </div>
        ))
      ) : (
        <div className="vc-none">No people visible</div>
      )}
      <div className="vc-foot">A dash means not visible or below the confidence threshold.</div>
    </>
  );
}

export function VehicleCardModal({ card, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const s = STATUS[card.plate_status];
  return (
    <div className="vc-overlay" onClick={onClose}>
      <div className={`vc-card vc-${s.tone}`} onClick={(e) => e.stopPropagation()}>
        <div className="vc-head">
          <div>
            <span className={`vc-chip vc-chip-${s.tone}`}>
              {card.plate_status === "PLATED" ? "Plated vehicle" : card.plate_status === "UNREADABLE" ? "Plate unreadable" : "No number plate"}
            </span>
            {card.is_emergency && <span className="vc-chip vc-chip-bad">Emergency vehicle</span>}
          </div>
          <button className="vc-close" onClick={onClose} aria-label="Close">
            <i className="fas fa-xmark" />
          </button>
        </div>
        <img className="vc-crop" src={card.crop_b64} alt="Vehicle" />
        {card.plate_status === "PLATED" ? <PlatedCard card={card} /> : <UnplatedCard card={card} />}
      </div>
    </div>
  );
}
