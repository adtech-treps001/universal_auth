@echo off
echo Universal Auth Simple Playwright Test
echo =======================================
echo.
echo This will run a simple Playwright test that opens Chrome and tests the Universal Auth frontend.
echo.
echo Prerequisites:
echo   1. Python installed
echo   2. Universal Auth frontend running on http://localhost:3000
echo.
echo Installing required packages...
pip install playwright aiohttp

echo.
echo Installing Playwright browsers...
playwright install chromium

echo.
echo Starting test...
python simple_playwright_test.py

echo.
echo Test completed! Check the screenshots in this folder.
pause