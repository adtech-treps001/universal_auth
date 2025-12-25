@echo off
echo ========================================
echo Universal Auth - Docker Frontend Setup
echo ========================================
echo.

echo Building and starting services...
docker-compose up --build -d frontend backend postgres redis opa

echo.
echo Waiting for services to be ready...
timeout /t 30 /nobreak

echo.
echo Checking service status...
docker-compose ps

echo.
echo ========================================
echo Frontend should be available at:
echo http://localhost:3000
echo ========================================
echo.
echo Backend API available at:
echo http://localhost:8000
echo.
echo To run Playwright tests against Docker frontend:
echo   node playwright-test.js
echo   python simple_playwright_test.py
echo.
echo To stop services:
echo   docker-compose down
echo.
echo To view logs:
echo   docker-compose logs -f frontend
echo ========================================