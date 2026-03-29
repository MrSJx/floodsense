# 🌊 FloodSense — Terrain-Aware Flood Prediction & Simulation Web Platform

> **Agro Pune Hackathon | Team: AIT Computer Science**

## Overview

FloodSense is a web platform that:
- Ingests Digital Elevation Model (DEM) data of Maharashtra terrain
- Pulls real-time + forecast rainfall data from weather APIs
- Simulates how water flows and accumulates across terrain
- Predicts flood-risk zones for the next 6 / 12 / 24 / 72 hours
- Displays everything on an interactive map with color-coded risk overlays
- Provides early warning alerts for villages, farmland, and roads in flood zones

## Target Region
**Maharashtra** (focus district: Kolhapur or Raigad — historically flood-prone)

## Primary Users
Farmers, local government, disaster management teams

## Tech Stack
- **Frontend:** React (Vite) + Leaflet + Recharts
- **Backend:** Python FastAPI + RichDEM + XGBoost
- **Data:** SRTM DEM, Open-Meteo API, India WRIS river data

## Getting Started

### Backend
```bash
cd backend
pip install -r ../requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Project Structure
```
floodsense/
├── frontend/          # React + Vite frontend
├── backend/           # FastAPI backend
├── notebooks/         # Jupyter notebooks for EDA & model training
├── requirements.txt   # Python dependencies
├── package.json       # Node dependencies
└── README.md          # This file
```

---
*Generated for AIT Computer Science Team | Agro Pune Hackathon*
*FloodSense v1.0 — Terrain-Aware Flood Prediction Platform*
