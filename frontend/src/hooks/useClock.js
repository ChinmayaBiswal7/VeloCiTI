import { useState, useEffect } from "react";
export function useClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => { const id = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(id); }, []);
  return {
    time: now.toLocaleTimeString("en-IN", { hour12:false }),
    date: now.toLocaleDateString("en-IN", { weekday:"short", day:"numeric", month:"short", year:"numeric" }),
  };
}
