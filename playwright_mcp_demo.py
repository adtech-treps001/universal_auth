#!/usr/bin/env python3
"""
Playwright MCP Server Demo for Universal Auth System

This script demonstrates how to use the Playwright MCP server
to automate browser testing of the Universal Auth system.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path to import our MCP server
sys.path.append(str(Path(__file__).parent.parent))

from playwright_mcp_server import PlaywrightMCPServer

async def demo_universal_auth_testing():
    """Demonstrate Playwright MCP server with Universal Auth system"""
    
    print("🎭 Universal Auth Playwright MCP Demo")
    print("=" * 50)
    
    server = PlaywrightMCPServer()
    await server.initialize()
    
    try:
        # Step 1: Launch browser
        print("\\n1️⃣ Launching browser...")
        launch_result = await server.launch_browser(headless=False)
        print(f"   Result: {launch_result}")
        
        if not launch_result["success"]:
            print("❌ Failed to launch browser")
            return
        
        # Step 2: Create a mock Universal Auth login page
        print("\\n2️⃣ Creating mock Universal Auth login page...")
        
        mock_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Universal Auth - Login Demo</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 400px; 
                    margin: 50px auto; 
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                h1 { color: #333; text-align: center; margin-bottom: 30px; }
                .form-group { margin-bottom: 20px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input { 
                    width: 100%; 
                    padding: 12px; 
                    border: 2px solid #ddd; 
                    border-radius: 5px; 
                    font-size: 16px;
                }
                input:focus { border-color: #667eea; outline: none; }
                button { 
                    width: 100%; 
                    padding: 12px; 
                    background: #667eea; 
                    color: white; 
                    border: none; 
                    border-radius: 5px; 
                    font-size: 16px; 
                    cursor: pointer;
                    margin-bottom: 10px;
                }
                button:hover { background: #5a6fd8; }
                .oauth-button {
                    background: #f8f9fa;
                    color: #333;
                    border: 2px solid #ddd;
                }
                .oauth-button:hover { background: #e9ecef; }
                .success { 
                    background: #d4edda; 
                    color: #155724; 
                    padding: 10px; 
                    border-radius: 5px; 
                    margin-top: 20px;
                    display: none;
                }
                .error { 
                    background: #f8d7da; 
                    color: #721c24; 
                    padding: 10px; 
                    border-radius: 5px; 
                    margin-top: 20px;
                    display: none;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Universal Auth</h1>
                
                <form id="loginForm">
                    <div class="form-group">
                        <label for="email">Email:</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    
                    <button type="submit" id="loginBtn">Login</button>
                </form>
                
                <div style="text-align: center; margin: 20px 0; color: #666;">or</div>
                
                <button class="oauth-button" id="googleBtn">🔍 Sign in with Google</button>
                <button class="oauth-button" id="githubBtn">🐙 Sign in with GitHub</button>
                <button class="oauth-button" id="otpBtn">📱 Sign in with Mobile OTP</button>
                
                <div id="successMsg" class="success">Login successful! Welcome to Universal Auth.</div>
                <div id="errorMsg" class="error">Invalid credentials. Please try again.</div>
            </div>
            
            <script>
                document.getElementById('loginForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    const email = document.getElementById('email').value;
                    const password = document.getElementById('password').value;
                    
                    if (email === 'admin@universal-auth.local' && password === 'admin123') {
                        document.getElementById('successMsg').style.display = 'block';
                        document.getElementById('errorMsg').style.display = 'none';
                    } else {
                        document.getElementById('errorMsg').style.display = 'block';
                        document.getElementById('successMsg').style.display = 'none';
                    }
                });
                
                document.getElementById('googleBtn').addEventListener('click', function() {
                    document.getElementById('successMsg').textContent = 'Google OAuth login successful!';
                    document.getElementById('successMsg').style.display = 'block';
                    document.getElementById('errorMsg').style.display = 'none';
                });
                
                document.getElementById('githubBtn').addEventListener('click', function() {
                    document.getElementById('successMsg').textContent = 'GitHub OAuth login successful!';
                    document.getElementById('successMsg').style.display = 'block';
                    document.getElementById('errorMsg').style.display = 'none';
                });
                
                document.getElementById('otpBtn').addEventListener('click', function() {
                    document.getElementById('successMsg').textContent = 'Mobile OTP login initiated!';
                    document.getElementById('successMsg').style.display = 'block';
                    document.getElementById('errorMsg').style.display = 'none';
                });
            </script>
        </body>
        </html>
        """
        
        # Navigate to the mock page
        data_url = f"data:text/html,{mock_html}"
        nav_result = await server.navigate(data_url)
        print(f"   Navigation result: {nav_result}")
        
        # Step 3: Test email/password login
        print("\\n3️⃣ Testing email/password login...")
        
        # Fill email field
        email_result = await server.fill("#email", "admin@universal-auth.local")
        print(f"   Email fill: {email_result}")
        
        # Fill password field
        password_result = await server.fill("#password", "admin123")
        print(f"   Password fill: {password_result}")
        
        # Take screenshot before login
        screenshot1_result = await server.screenshot("universal_auth_before_login.png")
        print(f"   Screenshot before login: {screenshot1_result}")
        
        # Click login button
        login_result = await server.click("#loginBtn")
        print(f"   Login click: {login_result}")
        
        # Wait for success message
        await asyncio.sleep(1)
        
        # Check if login was successful
        success_text_result = await server.get_text("#successMsg")
        print(f"   Success message: {success_text_result}")
        
        # Take screenshot after login
        screenshot2_result = await server.screenshot("universal_auth_after_login.png")
        print(f"   Screenshot after login: {screenshot2_result}")
        
        # Step 4: Test OAuth login
        print("\\n4️⃣ Testing OAuth login...")
        
        # Reload page for fresh test
        await server.navigate(data_url)
        await asyncio.sleep(1)
        
        # Click Google OAuth button
        google_result = await server.click("#googleBtn")
        print(f"   Google OAuth click: {google_result}")
        
        await asyncio.sleep(1)
        
        # Check OAuth success message
        oauth_text_result = await server.get_text("#successMsg")
        print(f"   OAuth success message: {oauth_text_result}")
        
        # Take screenshot of OAuth result
        screenshot3_result = await server.screenshot("universal_auth_oauth_success.png")
        print(f"   OAuth screenshot: {screenshot3_result}")
        
        # Step 5: Test JavaScript evaluation
        print("\\n5️⃣ Testing JavaScript evaluation...")
        
        js_result = await server.evaluate_javascript("""
            return {
                title: document.title,
                url: window.location.href,
                emailValue: document.getElementById('email').value,
                hasLoginForm: !!document.getElementById('loginForm'),
                buttonCount: document.querySelectorAll('button').length
            };
        """)
        print(f"   JavaScript evaluation: {js_result}")
        
        # Step 6: Test page content extraction
        print("\\n6️⃣ Testing page content extraction...")
        
        content_result = await server.get_page_content()
        content_length = len(content_result.get("content", ""))
        print(f"   Page content length: {content_length} characters")
        print(f"   Page URL: {content_result.get('url', 'N/A')}")
        
        # Wait a bit to see the results
        print("\\n⏳ Waiting 5 seconds to observe the browser...")
        await asyncio.sleep(5)
        
        print("\\n✅ Demo completed successfully!")
        print("\\n📸 Screenshots saved:")
        print("   - universal_auth_before_login.png")
        print("   - universal_auth_after_login.png") 
        print("   - universal_auth_oauth_success.png")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Step 7: Clean up
        print("\\n7️⃣ Cleaning up...")
        close_result = await server.close_browser()
        print(f"   Browser close: {close_result}")

async def demo_bdd_integration():
    """Demonstrate integration with BDD testing framework"""
    
    print("\\n🧪 BDD Integration Demo")
    print("=" * 30)
    
    server = PlaywrightMCPServer()
    await server.initialize()
    
    try:
        print("\\n🎯 This demonstrates how Playwright MCP can enhance your BDD tests:")
        print("   1. Interactive browser automation through Kiro")
        print("   2. Real-time debugging with screenshots")
        print("   3. JavaScript execution for complex scenarios")
        print("   4. Cross-browser testing capabilities")
        print("   5. Integration with existing pytest-bdd framework")
        
        print("\\n📋 Your existing BDD framework at universal_auth/tests/bdd/ can now:")
        print("   ✅ Use MCP tools for browser automation")
        print("   ✅ Take screenshots during test failures")
        print("   ✅ Execute custom JavaScript for complex interactions")
        print("   ✅ Test across different browsers (Chrome, Firefox, Safari)")
        print("   ✅ Debug tests interactively through Kiro")
        
        print("\\n🚀 Next steps:")
        print("   1. Restart Kiro to load the Playwright MCP server")
        print("   2. Use Playwright tools directly in Kiro chat")
        print("   3. Enhance your BDD step definitions with MCP calls")
        print("   4. Create interactive test scenarios")
        
    finally:
        await server.cleanup()

async def main():
    """Main demo function"""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--bdd-only":
        await demo_bdd_integration()
    else:
        await demo_universal_auth_testing()
        await demo_bdd_integration()

if __name__ == "__main__":
    asyncio.run(main())