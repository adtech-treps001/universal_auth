@echo off
echo ========================================
echo Universal Auth Playwright Test Runner
echo ========================================
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo Node.js version:
node --version
echo.

REM Check if we're in the right directory
if not exist "playwright-test.js" (
    echo ERROR: playwright-test.js not found
    echo Please run this script from the universal_auth directory
    pause
    exit /b 1
)

REM Install dependencies if node_modules doesn't exist
if not exist "node_modules" (
    echo Installing Node.js dependencies...
    npm install
    echo.
    
    echo Installing Playwright browsers...
    npx playwright install chromium
    echo.
)

REM Check if frontend is running
echo Checking if frontend is running on http://localhost:3000...
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Frontend doesn't seem to be running on http://localhost:3000
    echo Please make sure to start the frontend first:
    echo   cd universal_auth/frontend
    echo   npm run dev
    echo.
    echo Press any key to continue anyway, or Ctrl+C to cancel...
    pause >nul
)

echo.
echo ========================================
echo Starting Playwright Test
echo ========================================
echo.
echo This will:
echo - Open Chrome browser visibly
echo - Navigate to http://localhost:3000
echo - Test all UI components automatically
echo - Take screenshots at each step
echo - Show real-time automation
echo.
echo Press Ctrl+C to cancel, or any key to start...
pause >nul

echo.
echo Starting test...
node playwright-test.js

echo.
echo ========================================
echo Test completed!
echo ========================================
echo Check the screenshots folder for captured images.
echo.
pause