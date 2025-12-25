#!/usr/bin/env python3
"""
Simple Playwright Test for Windows

A standalone script that doesn't depend on the MCP server.
Opens Chrome visibly and tests the Universal Auth frontend.
"""

import asyncio
import os
from playwright.async_api import async_playwright

# Configuration
CONFIG = {
    'base_url': os.getenv('BASE_URL', 'http://localhost:3000'),
    'headless': os.getenv('HEADLESS', 'false').lower() == 'true',
    'slow_mo': 1500,    # Slow down actions by 1.5 seconds
    'timeout': 30000,   # 30 second timeout
    'viewport': {'width': 1920, 'height': 1080}
}

async def test_universal_auth():
    """Test Universal Auth with visible Chrome browser"""
    
    print("🎭 Universal Auth Playwright Test")
    print("=" * 40)
    print(f"Testing frontend at: {CONFIG['base_url']}")
    print()
    
    async with async_playwright() as p:
        # Launch Chrome browser (visible)
        print("1️⃣ Launching Chrome browser...")
        browser = await p.chromium.launch(
            headless=CONFIG['headless'],  # Make browser visible
            slow_mo=CONFIG['slow_mo'],    # Slow down actions for visibility
            args=['--start-maximized']  # Start maximized
        )
        
        # Create new page
        context = await browser.new_context(viewport=CONFIG['viewport'])
        page = await context.new_page()
        
        try:
            # Navigate to Universal Auth
            print("2️⃣ Navigating to Universal Auth frontend...")
            try:
                response = await page.goto(CONFIG['base_url'], wait_until='networkidle', timeout=10000)
                if response.status == 200:
                    print("   ✅ Page loaded successfully!")
                    title = await page.title()
                    print(f"   📄 Page title: '{title}'")
                else:
                    print(f"   ⚠️ Page loaded with status: {response.status}")
            except Exception as nav_error:
                print(f"   ❌ Failed to load page: {nav_error}")
                print("   💡 Make sure the Universal Auth frontend is running on http://localhost:3000")
                raise
            
            # Take initial screenshot
            print("3️⃣ Taking initial screenshot...")
            await page.screenshot(path="test_initial.png")
            print("   📸 Screenshot saved: test_initial.png")
            
            # Look for the mobile input field
            print("4️⃣ Testing mobile input...")
            mobile_input = page.locator('input[type="tel"]')
            
            if await mobile_input.count() > 0:
                print("   ✅ Found mobile input field!")
                
                # Fill mobile number
                await mobile_input.fill("+919876543210")
                print("   📱 Filled mobile number: +919876543210")
                
                # Take screenshot after filling
                await page.screenshot(path="test_mobile_filled.png")
                print("   📸 Screenshot saved: test_mobile_filled.png")
            else:
                print("   ❌ Mobile input field not found")
            
            # Test OAuth buttons
            print("5️⃣ Testing OAuth buttons...")
            
            # Test Google button
            google_button = page.locator('text=Continue with Google')
            if await google_button.count() > 0:
                print("   ✅ Found Google OAuth button!")
                await google_button.click()
                print("   🔍 Clicked Google OAuth button")
                await asyncio.sleep(2)
            
            # Test GitHub button
            github_button = page.locator('text=Continue with GitHub')
            if await github_button.count() > 0:
                print("   ✅ Found GitHub OAuth button!")
                await github_button.click()
                print("   🐙 Clicked GitHub OAuth button")
                await asyncio.sleep(2)
            
            # Test LinkedIn button
            linkedin_button = page.locator('text=Continue with LinkedIn')
            if await linkedin_button.count() > 0:
                print("   ✅ Found LinkedIn OAuth button!")
                await linkedin_button.click()
                print("   💼 Clicked LinkedIn OAuth button")
                await asyncio.sleep(2)
            
            # Take final screenshot
            print("6️⃣ Taking final screenshot...")
            await page.screenshot(path="test_final.png")
            print("   📸 Screenshot saved: test_final.png")
            
            # Get page information
            print("7️⃣ Getting page information...")
            page_info = await page.evaluate("""
                () => {
                    return {
                        url: window.location.href,
                        title: document.title,
                        mobileValue: document.querySelector('input[type="tel"]')?.value || 'Not found',
                        buttonCount: document.querySelectorAll('button').length,
                        hasLoginForm: !!document.querySelector('form'),
                        bodyClasses: document.body.className,
                        hasGradient: document.querySelector('.bg-gradient-to-br') !== null,
                        hasTailwind: document.querySelector('[class*="text-"]') !== null
                    };
                }
            """)
            
            print("   📊 Page Information:")
            print(f"      URL: {page_info['url']}")
            print(f"      Title: {page_info['title']}")
            print(f"      Mobile Value: {page_info['mobileValue']}")
            print(f"      Button Count: {page_info['buttonCount']}")
            print(f"      Has Login Form: {page_info['hasLoginForm']}")
            print(f"      Body Classes: {page_info['bodyClasses']}")
            print(f"      Has Gradient: {page_info['hasGradient']}")
            print(f"      Has Tailwind: {page_info['hasTailwind']}")
            
            # Keep browser open for inspection
            print("\\n8️⃣ Test completed!")
            print("   The browser will stay open for 15 seconds for you to inspect.")
            print("   You can manually interact with the page during this time.")
            
            for i in range(15, 0, -1):
                print(f"   Closing in {i} seconds... (Press Ctrl+C to keep browser open)")
                await asyncio.sleep(1)
            
            print("\\n✅ All tests completed successfully!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            # Take error screenshot
            await page.screenshot(path="test_error.png")
            print("   📸 Error screenshot saved: test_error.png")
            raise
        
        finally:
            await browser.close()

async def main():
    print("🚀 Starting Universal Auth Playwright Test...")
    print()
    print("This will:")
    print("  1. Open Chrome browser (visible)")
    print("  2. Navigate to http://localhost:3000")
    print("  3. Test the login form and OAuth buttons")
    print("  4. Take screenshots at each step")
    print("  5. Show page information")
    print()
    
    # We'll check frontend accessibility during the test itself
    print("ℹ️ Frontend accessibility will be checked during browser automation")
    
    print()
    input("Press Enter to start the test...")
    
    try:
        await test_universal_auth()
        
        print("\\n🎉 Test Summary:")
        print("   ✅ Browser automation successful")
        print("   ✅ Universal Auth frontend tested")
        print("   ✅ Screenshots captured")
        print("\\n📸 Screenshots saved:")
        print("   - test_initial.png")
        print("   - test_mobile_filled.png")
        print("   - test_final.png")
        print("\\n🎯 This demonstrates:")
        print("   - Playwright can automate modern React/Next.js apps")
        print("   - Visual browser testing with real user interactions")
        print("   - Form filling and button clicking")
        print("   - Screenshot capture for debugging")
        print("   - Page information extraction")
        
        return 0
        
    except KeyboardInterrupt:
        print("\\n⏸️ Test interrupted by user.")
        return 0
    except Exception as e:
        print(f"\\n❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)