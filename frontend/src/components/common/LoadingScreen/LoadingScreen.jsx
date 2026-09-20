import { useEffect, useState } from "react";
import "./LoadingScreen.css";

const STEPS = [
  "Connecting to sensors...",
  "Loading intersection data...",
  "Calibrating AI models...",
  "Rendering dashboard...",
  "System ready.",
];

export default function LoadingScreen({ onComplete }) {
  const [pct, setPct] = useState(0);
  const [msgIdx, setMsgIdx] = useState(0);

  useEffect(() => {
    let p = 0;
    const iv = setInterval(() => {
      p += 10;
      setPct(Math.min(100, p));
      setMsgIdx(Math.min(STEPS.length - 1, Math.floor(p / 25)));
      if (p >= 100) {
        clearInterval(iv);
        setTimeout(() => {
          onComplete?.();
        }, 150);
      }
    }, 40);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="ls">
      <div className="ls-box">
        <img className="brand-logo" src="/velociti-logo.jpg" alt="VeloCiTI logo" width="96" height="96" style={{ marginBottom: 12 }} />
        <div className="ls-title">Velo<span>CiTI</span></div>
        <div className="ls-sub">Traffic Headquarters</div>
        <div className="ls-bar-wrap"><div className="ls-bar" style={{ width: `${pct}%` }} /></div>
        <div className="ls-msg">{STEPS[msgIdx]}</div>
      </div>
    </div>
  );
}
