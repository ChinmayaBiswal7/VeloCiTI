import React from "react";
import ReactDOM from "react-dom/client";
import "./chartSetup.js";
import "./index.css";
import App from "./App.jsx";
import "./theme.css";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "center",
          justifyContent: "center", height: "100vh", background: "#1f1e1d",
          color: "#f4f2ea", fontFamily: "Inter, monospace", gap: "16px", padding: "32px"
        }}>
          <div style={{ fontSize: "2.5rem" }}>⚠️</div>
          <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e5534b" }}>VeloCiTI failed to load</div>
          <div style={{ fontSize: "0.85rem", color: "#b5b1a4", maxWidth: "600px", textAlign: "center" }}>
            {String(this.state.error?.message || this.state.error)}
          </div>
          <div style={{ fontSize: "0.8rem", color: "#7c786c" }}>
            Make sure you ran <code style={{ background: "#292826", padding: "2px 8px", borderRadius: "4px" }}>npm install</code> and have a working internet connection for map tiles &amp; AI model.
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: "8px", padding: "8px 24px", background: "#d97757", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "0.9rem" }}
          >
            🔄 Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
