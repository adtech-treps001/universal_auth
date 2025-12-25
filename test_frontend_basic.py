#!/usr/bin/env python3
"""
Basic Frontend Test Script

A simple test script to verify the Universal Auth frontend is accessible.
"""

import asyncio
from playwright.async_api import async_playwright

async def test_frontend():
    """Test the Universal Auth frontend"""
    
    print("🎭 Universal Auth Frontend Basic Test")
    print("=" * 40)
    
    async with async_playwright() as p:
        try:
            # Launch browser
            print("\\n1️⃣ Launching browser...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to frontend
            print("\\n2️⃣ Navigating to frontend...")
            response = await page.goto("http://localhost:3000")
            print(f"   Status: {response.status}")
            print(f"   URL: {response.url}")
            
            if response.status != 200:
                print(f"❌ Frontend returned status {response.status}")
                return False
            
            # Wait for page to load
            await page.wait_for_load_state('networkidle')
            
            # Get page title
            title = await page.title()
            print(f"   Title: {title}")
            
            # Take screenshot
            print("\\n3️⃣ Taking screenshot...")
            await page.screenshot(path="frontend_test.png")
            print("   Screenshot saved: frontend_test.png")
            
            # Check page content
            print("\\n4️⃣ Checking page content...")
            content = await page.content()
            
            checks = {
                "Has title": bool(title),
                "Contains Universal Auth": "Universal Auth" in content,
                "Contains login elements": any(term in content.lower() for term in ["login", "sign in", "authentication"]),
                "No 500 errors": "500" not in content,
                "Has React elements": "__next" in content or "react" in content.lower()
            }
            
            print("\\n   Content checks:")
            all_passed = True
            for check_name, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"     {status} {check_name}")
                if not passed:
                    all_passed = False
            
            # Try to find specific elements
            print("\\n5️⃣ Checking UI elements...")
            try:
                # Look for login form elements
                login_elements = await page.query_selector_all('input, button, form')
                print(f"   Found {len(login_elements)} interactive elements")
                
                # Check for specific text
                welcome_text = await page.query_selector('text=Universal Auth')
                if welcome_text:
                    print("   ✅ Found Universal Auth text")
                else:
                    print("   ❌ Universal Auth text not found")
                    all_passed = False
                    
            except Exception as e:
                print(f"   ⚠️ Element check failed: {e}")
            
            await browser.close()
            return all_passed
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False

async def main():
    """Main test function"""
    
    print("🚀 Starting Universal Auth Frontend Test...")
    
    success = await test_frontend()
    
    if success:
        print("\\n✅ All tests passed! Frontend is working correctly.")
        print("\\n📸 Screenshot saved as: frontend_test.png")
        print("\\n🎯 Frontend is accessible at: http://localhost:3000")
        print("\\n🔧 You can now:")
        print("   1. Open http://localhost:3000 in your browser")
        print("   2. Test the login functionality manually")
        print("   3. Use Playwright MCP tools in Kiro for automated testing")
    else:
        print("\\n❌ Some tests failed. Check the output above for details.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)