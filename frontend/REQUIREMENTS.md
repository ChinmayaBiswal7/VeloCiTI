# VeloCiTI — Setup & Requirements Guide

## ✅ System Requirements

| Requirement | Minimum Version | Download Link |
|---|---|---|
| **Node.js** | v18.0.0 or higher | https://nodejs.org/en/download |
| **npm** | v9.0.0 or higher (comes with Node.js) | (bundled with Node.js) |
| **Git** | Any recent version | https://git-scm.com/downloads |
| **Browser** | Chrome / Edge / Firefox (latest) | — |
| **Internet** | Required (for map tiles + AI model load) | — |

---

## 🚀 Run on Any Laptop — Step by Step

### Step 1: Install Node.js
Download and install from: **https://nodejs.org/en/download**
> Choose the **LTS (Long Term Support)** version.

Verify installation:
```bash
node --version
npm --version
```

---

### Step 2: Clone the Repository
```bash
git clone https://github.com/maxlovesher/VeloCiTI
cd SIH-Dashboard-
```

---

### Step 3: Install All Dependencies
```bash
npm install
```
> This automatically installs everything listed below from `package.json`.

---

### Step 4: Start the Development Server
```bash
npm run dev
```

Open your browser at: **http://localhost:5173/**

---

## 📦 Project Dependencies (Auto-installed via npm install)

### Runtime Dependencies
| Package | Version | Purpose |
|---|---|---|
| `react` | ^19.2.8 | Core UI framework |
| `react-dom` | ^19.2.8 | React DOM renderer |
| `leaflet` | ^1.9.4 | Live GIS map engine |
| `chart.js` | ^4.5.1 | Traffic analytics charts |
| `react-chartjs-2` | ^5.3.1 | React wrapper for Chart.js |
| `gsap` | ^3.15.0 | Smooth animations |

### Dev Dependencies
| Package | Version | Purpose |
|---|---|---|
| `vite` | ^8.2.0 | Fast build & dev server |
| `@vitejs/plugin-react` | ^6.0.4 | Vite React plugin |
| `oxlint` | ^1.75.0 | Code linting |

### External CDN (loaded automatically in browser)
| Library | Purpose |
|---|---|
| `TensorFlow.js` | Edge AI vehicle detection |
| `COCO-SSD Model` | Pre-trained object detection |
| `FontAwesome 6` | UI icons |

---

## 🛑 Common Issues & Fixes

| Error | Fix |
|---|---|
| `node is not recognized` | Install Node.js from nodejs.org and restart terminal |
| `npm install` fails | Run `npm cache clean --force` then retry |
| Port 5173 already in use | Run `npx vite --port 5174` instead |
| Map not loading | Check internet connection (map tiles need internet) |
| AI detection not showing | Allow browser to load TensorFlow.js from CDN |

---

## ⚡ Quick Commands Reference

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```
