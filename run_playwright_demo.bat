@echo off
echo Universal Auth Playwright Demo for Windows
echo ==========================================
echo.
echo This will run a Playwright demo that opens Chrome and tests the Universal Auth frontend.
echo Make sure you have:
echo   1. Python installed
echo   2. Playwright installed (pip install playwright)
echo   3. Playwright browsers installed (playwright install)
echo   4. Universal Auth frontend running on http://localhost:3000
echo.
pause

echo Installing required packages...
pip install playwright aiohttp

echo Installing Playwright browsers...
playwright install chromium

echo Starting demo...
python playwright_windows_demo.py

pause