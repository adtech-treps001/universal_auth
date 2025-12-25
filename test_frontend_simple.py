#!/usr/bin/env python3
"""
Simple Frontend Test Script

A basic test script to verify the Universal Auth frontend is working.
This can be run with Docker to test the frontend functionality.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path to import our MCP server
sys.path.append(str(Path(__file__).parent.parent))

try:
    from playwright_mcp_server import PlaywrightMCPServer
except ImportError:
    print("❌ Playwright MCP server not found. Please ensure playwright_mcp_server.py is available.")
    sys.exit(1)

async def test_universal_auth_frontend():
    """Test the Universal Auth frontend"""
    
    print("🎭 Universal Auth Frontend Test")
    print("=" * 40)
    
    server = PlaywrightMCPServer()
    await server.initialize()
    
    try:
        # Step 1: Launch browser
        print("\\n1️⃣ Launching browser...")
        launch_result = await server.launch_browser(headless=True)
        print(f"   Result: {launch_result}")
        
        if not launch_result["success"]:
            print("❌ Failed to launch browser")
            return False
        
        # Step 2: Navigate to frontend
        print("\\n2️⃣ Navigating to frontend...")
        nav_result = await server.navigate("http://localhost:3000")
        print(f"   Navigation result: {nav_result}")
        
        if not nav_result["success"]:
            print("❌ Failed to navigate to frontend")
            return False
        
        # Step 3: Take screenshot
        print("\\n3️⃣ Taking screenshot...")
        screenshot_result = await server.screenshot("frontend_test.png")
        print(f"   Screenshot: {screenshot_result}")
        
        # Step 4: Check page content
        print("\\n4️⃣ Checking page content...")
        content_result = await server.get_page_content()
        
        if content_result["success"]:
            content = content_result["content"]
            print(f"   Page content length: {len(content)} characters")
            
            # Check for key elements
            checks = {
                "Universal Auth title": "Universal Auth" in content,
                "Login form": "login" in content.lower() or "sign" in content.lower(),
                "React app": "react" in content.lower() or "__next" in content,
                "No errors": "error" not in content.lower() or "500" not in content
            }
            
            print("\\n   Content checks:")
            all_passed = True
            for check_name, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"     {status} {check_name}")
                if not passed:
                    all_passed = False
            
            return all_passed
        else:
            print(f"   ❌ Failed to get page content: {content_result}")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        print("\\n5️⃣ Cleaning up...")
        close_result = await server.close_browser()
        print(f"   Browser close: {close_result}")

async def main():
    """Main test function"""
    
    print("🚀 Starting Universal Auth Frontend Test...")
    
    success = await test_universal_auth_frontend()
    
    if success:
        print("\\n✅ All tests passed! Frontend is working correctly.")
        print("\\n📸 Screenshot saved as: frontend_test.png")
        print("\\n🎯 Next steps:")
        print("   1. Open http://localhost:3000 in your browser")
        print("   2. Test the login functionality")
        print("   3. Use Playwright MCP tools in Kiro for interactive testing")
    else:
        print("\\n❌ Some tests failed. Check the output above for details.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)