@echo off
title VeloCiTI Full-Stack Launcher
color 0b
echo ================================================================
echo           VELOCITI - VEHICLE LOCATION AND CITY TRAFFIC INTELLIGENCE
echo ================================================================
echo.
echo [1/2] Launching CityFlow Multi-Agent Python Server (Port 5000)...
start "CityFlow Backend Server" cmd /k "%~dp0start-backend.bat"

echo [2/2] Launching VeloCiTI React Dashboard (Port 5173)...
start "VeloCiTI React Vite" cmd /k "%~dp0start-frontend.bat"

echo.
echo ================================================================
echo   Both services are now running:
echo   - React Web Dashboard:  http://localhost:5173/
echo   - CityFlow API Backend: http://localhost:5000/
echo ================================================================
echo You can leave this window open or close it.
timeout /t 5 >nul
