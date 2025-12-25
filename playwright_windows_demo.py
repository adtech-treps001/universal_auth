#!/usr/bin/env python3
"""
Windows Playwright Demo for Universal Auth

This script demonstrates Playwright automation on Windows with visible Chrome browser.
Shows real-time browser automation for testing the Universal Auth frontend.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the parent directory to the path to import our MCP server
sys.path.append(str(Path(__file__).parent.parent))

try:
    from playwright_mcp_server import PlaywrightMCPServer
except ImportError:
    print("❌ Playwright MCP server not found. Please ensure playwright_mcp_server.py is available.")
    print("   You can install Playwright with: pip install playwright")
    print("   Then install browsers with: playwright install")
    sys.exit(1)

async def demo_universal_auth_windows():
    """Demonstrate Universal Auth testing with visible Chrome on Windows"""
    
    print("🎭 Universal Auth Windows Playwright Demo")
    print("=" * 50)
    print("This demo will open Chrome browser and automate the Universal Auth frontend")
    print("You'll see the browser actions happening in real-time!")
    print()
    
    server = PlaywrightMCPServer()
    await server.initialize()
    
    try:
        # Step 1: Launch visible Chrome browser
        print("1️⃣ Launching Chrome browser (visible)...")
        launch_result = await server.launch_browser(headless=False, browser_type="chromium")
        print(f"   Result: {launch_result}")
        
        if not launch_result["success"]:
            print("❌ Failed to launch browser")
            print("   Make sure you have installed Playwright browsers:")
            print("   pip install playwright")
            print("   playwright install")
            return False
        
        print("   ✅ Chrome browser opened!")
        print("   You should see a Chrome window open now.")
        await asyncio.sleep(2)
        
        # Step 2: Navigate to Universal Auth frontend
        print("\\n2️⃣ Navigating to Universal Auth frontend...")
        nav_result = await server.navigate("http://localhost:3000")
        print(f"   Navigation result: {nav_result}")
        
        if not nav_result["success"]:
            print("❌ Failed to navigate to frontend")
            print("   Make sure the frontend is running on http://localhost:3000")
            return False
        
        print("   ✅ Successfully loaded Universal Auth page!")
        await asyncio.sleep(3)
        
        # Step 3: Take initial screenshot
        print("\\n3️⃣ Taking initial screenshot...")
        screenshot_result = await server.screenshot("windows_demo_initial.png")
        print(f"   Screenshot: {screenshot_result}")
        
        # Step 4: Test mobile number input
        print("\\n4️⃣ Testing mobile number input...")
        print("   Looking for mobile input field...")
        
        # Wait for the input to be available
        wait_result = await server.wait_for_selector('input[type="tel"]', timeout=10000)
        print(f"   Wait result: {wait_result}")
        
        if wait_result["success"]:
            print("   ✅ Found mobile input field!")
            
            # Fill mobile number
            print("   Filling mobile number: +919876543210")
            fill_result = await server.fill('input[type="tel"]', "+919876543210")
            print(f"   Fill result: {fill_result}")
            
            await asyncio.sleep(2)
            
            # Take screenshot after filling
            screenshot2_result = await server.screenshot("windows_demo_mobile_filled.png")
            print(f"   Screenshot after filling: {screenshot2_result}")
        
        # Step 5: Test OAuth buttons
        print("\\n5️⃣ Testing OAuth buttons...")
        
        # Try to click Google button
        print("   Looking for Google OAuth button...")
        google_click_result = await server.click('text=Continue with Google')
        print(f"   Google button click: {google_click_result}")
        
        await asyncio.sleep(2)
        
        # Take screenshot after OAuth click
        screenshot3_result = await server.screenshot("windows_demo_oauth_clicked.png")
        print(f"   Screenshot after OAuth: {screenshot3_result}")
        
        # Step 6: Test GitHub button
        print("\\n6️⃣ Testing GitHub OAuth button...")
        github_click_result = await server.click('text=Continue with GitHub')
        print(f"   GitHub button click: {github_click_result}")
        
        await asyncio.sleep(2)
        
        # Step 7: Get page information
        print("\\n7️⃣ Getting page information...")
        
        # Get page title
        js_result = await server.evaluate_javascript("""
            return {
                title: document.title,
                url: window.location.href,
                mobileValue: document.querySelector('input[type="tel"]')?.value || 'Not found',
                buttonCount: document.querySelectorAll('button').length,
                hasLoginForm: !!document.querySelector('form'),
                pageHeight: document.body.scrollHeight,
                pageWidth: document.body.scrollWidth
            };
        """)
        
        if js_result["success"]:
            info = js_result["result"]
            print("   📊 Page Information:")
            print(f"      Title: {info['title']}")
            print(f"      URL: {info['url']}")
            print(f"      Mobile Value: {info['mobileValue']}")
            print(f"      Button Count: {info['buttonCount']}")
            print(f"      Has Login Form: {info['hasLoginForm']}")
            print(f"      Page Size: {info['pageWidth']}x{info['pageHeight']}")
        
        # Step 8: Final screenshot
        print("\\n8️⃣ Taking final screenshot...")
        final_screenshot = await server.screenshot("windows_demo_final.png")
        print(f"   Final screenshot: {final_screenshot}")
        
        # Step 9: Keep browser open for manual inspection
        print("\\n9️⃣ Demo completed!")
        print("   The browser will stay open for 10 seconds so you can inspect the page.")
        print("   You can manually interact with the page during this time.")
        
        for i in range(10, 0, -1):
            print(f"   Closing in {i} seconds... (Press Ctrl+C to keep browser open)")
            await asyncio.sleep(1)
        
        return True
        
    except KeyboardInterrupt:
        print("\\n⏸️ Demo interrupted by user. Browser will remain open.")
        print("   Close the browser manually when you're done.")
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Only close if not interrupted
        if not hasattr(demo_universal_auth_windows, '_interrupted'):
            print("\\n🔄 Cleaning up...")
            close_result = await server.close_browser()
            print(f"   Browser close: {close_result}")

async def main():
    """Main demo function"""
    
    print("🚀 Starting Universal Auth Windows Playwright Demo...")
    print()
    print("Prerequisites:")
    print("✅ Universal Auth frontend running on http://localhost:3000")
    print("✅ Playwright installed (pip install playwright)")
    print("✅ Playwright browsers installed (playwright install)")
    print()
    
    # Check if frontend is accessible
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:3000') as response:
                if response.status == 200:
                    print("✅ Frontend is accessible!")
                else:
                    print(f"⚠️ Frontend returned status {response.status}")
    except ImportError:
        print("⚠️ aiohttp not available, skipping frontend check")
    except Exception as e:
        print(f"⚠️ Could not check frontend: {e}")
        print("   Make sure the frontend is running on http://localhost:3000")
    
    print()
    input("Press Enter to start the demo...")
    
    success = await demo_universal_auth_windows()
    
    if success:
        print("\\n✅ Demo completed successfully!")
        print("\\n📸 Screenshots saved:")
        print("   - windows_demo_initial.png")
        print("   - windows_demo_mobile_filled.png") 
        print("   - windows_demo_oauth_clicked.png")
        print("   - windows_demo_final.png")
        print("\\n🎯 What you saw:")
        print("   1. Chrome browser opened automatically")
        print("   2. Navigated to Universal Auth frontend")
        print("   3. Filled mobile number input")
        print("   4. Clicked OAuth buttons")
        print("   5. Extracted page information")
        print("   6. Took screenshots at each step")
        print("\\n🔧 This demonstrates how Playwright can:")
        print("   - Automate real browser interactions")
        print("   - Test UI components and forms")
        print("   - Take screenshots for debugging")
        print("   - Extract data from web pages")
        print("   - Work with modern React/Next.js applications")
    else:
        print("\\n❌ Demo failed. Check the output above for details.")
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\\n👋 Demo interrupted by user. Goodbye!")
        sys.exit(0)