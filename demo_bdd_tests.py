#!/usr/bin/env python3
"""
BDD Testing Demonstration for Universal Auth System

This script demonstrates the BDD testing capabilities with Playwright
by running mock scenarios that don't require the full system.
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def create_mock_auth_page():
    """Create a comprehensive mock authentication page for testing"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Universal Auth - Login</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .auth-container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                padding: 40px;
                width: 100%;
                max-width: 400px;
            }
            .logo {
                text-align: center;
                margin-bottom: 30px;
            }
            .logo h1 {
                color: #333;
                font-size: 28px;
                font-weight: 600;
            }
            .logo p {
                color: #666;
                margin-top: 8px;
            }
            .auth-form {
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 500;
            }
            .form-group input {
                width: 100%;
                padding: 12px 16px;
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
            }
            .btn {
                width: 100%;
                padding: 12px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                margin-bottom: 12px;
            }
            .btn-primary {
                background: #667eea;
                color: white;
            }
            .btn-primary:hover {
                background: #5a6fd8;
                transform: translateY(-1px);
            }
            .btn-oauth {
                background: white;
                color: #333;
                border: 2px solid #e1e5e9;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
            }
            .btn-oauth:hover {
                border-color: #667eea;
                transform: translateY(-1px);
            }
            .divider {
                text-align: center;
                margin: 30px 0;
                position: relative;
                color: #666;
            }
            .divider::before {
                content: '';
                position: absolute;
                top: 50%;
                left: 0;
                right: 0;
                height: 1px;
                background: #e1e5e9;
            }
            .divider span {
                background: white;
                padding: 0 20px;
            }
            .otp-section {
                display: none;
                margin-top: 20px;
            }
            .otp-input {
                text-align: center;
                font-size: 24px;
                letter-spacing: 8px;
                font-weight: 600;
            }
            .message {
                padding: 12px 16px;
                border-radius: 8px;
                margin-bottom: 20px;
                display: none;
            }
            .message.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .message.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .dashboard {
                display: none;
                text-align: center;
            }
            .dashboard h2 {
                color: #333;
                margin-bottom: 20px;
            }
            .user-info {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .loading {
                display: none;
                text-align: center;
                padding: 20px;
            }
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="auth-container">
            <div class="logo">
                <h1>🔐 Universal Auth</h1>
                <p>Secure authentication for modern applications</p>
            </div>
            
            <div id="message" class="message" data-testid="message"></div>
            <div id="loading" class="loading" data-testid="loading">
                <div class="spinner"></div>
                <p>Authenticating...</p>
            </div>
            
            <div id="login-section" class="login-section">
                <form id="email-form" class="auth-form">
                    <div class="form-group">
                        <label for="email">Email Address</label>
                        <input type="email" id="email" name="email" placeholder="Enter your email" required data-testid="email-input">
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" placeholder="Enter your password" required data-testid="password-input">
                    </div>
                    <button type="submit" class="btn btn-primary" data-testid="login-button">Sign In</button>
                </form>
                
                <div class="divider">
                    <span>or continue with</span>
                </div>
                
                <div class="oauth-providers">
                    <button class="btn btn-oauth" data-provider="google" data-testid="google-signin">
                        <span>🔍</span> Sign in with Google
                    </button>
                    <button class="btn btn-oauth" data-provider="github" data-testid="github-signin">
                        <span>🐙</span> Sign in with GitHub
                    </button>
                    <button class="btn btn-oauth" data-provider="linkedin" data-testid="linkedin-signin">
                        <span>💼</span> Sign in with LinkedIn
                    </button>
                </div>
                
                <div class="divider">
                    <span>or use mobile</span>
                </div>
                
                <button class="btn btn-oauth" id="mobile-otp-btn" data-testid="mobile-otp-button">
                    <span>📱</span> Sign in with Mobile OTP
                </button>
            </div>
            
            <div id="mobile-otp-section" class="otp-section">
                <div class="form-group">
                    <label for="mobile">Mobile Number</label>
                    <input type="tel" id="mobile" name="mobile" placeholder="+91 9876543210" data-testid="mobile-input">
                </div>
                <button type="button" class="btn btn-primary" id="send-otp-btn" data-testid="send-otp">Send OTP</button>
                
                <div id="otp-input-section" style="display: none;">
                    <div class="form-group">
                        <label for="otp">Enter OTP</label>
                        <input type="text" id="otp" name="otp" placeholder="123456" maxlength="6" class="otp-input" data-testid="otp-input">
                    </div>
                    <button type="button" class="btn btn-primary" id="verify-otp-btn" data-testid="verify-otp">Verify OTP</button>
                </div>
                
                <button type="button" class="btn btn-oauth" id="back-to-login" style="margin-top: 20px;">
                    ← Back to Login
                </button>
            </div>
            
            <div id="dashboard" class="dashboard" data-testid="dashboard">
                <h2>🎉 Welcome to Universal Auth!</h2>
                <div class="user-info" data-testid="user-info">
                    <p><strong>Authentication Successful</strong></p>
                    <p id="user-details" data-testid="user-details"></p>
                </div>
                <button class="btn btn-oauth" id="logout-btn" data-testid="logout-button">
                    Sign Out
                </button>
            </div>
        </div>
        
        <script>
            // Mock authentication system
            const mockUsers = {
                'admin@universal-auth.local': { password: 'admin123', name: 'Admin User', role: 'admin' },
                'user@example.com': { password: 'password123', name: 'Test User', role: 'user' }
            };
            
            const mockOTPs = {
                '+919876543210': '123456',
                '+919999999999': '654321'
            };
            
            let currentUser = null;
            
            // Utility functions
            function showMessage(text, type = 'success') {
                const message = document.getElementById('message');
                message.textContent = text;
                message.className = `message ${type}`;
                message.style.display = 'block';
                setTimeout(() => message.style.display = 'none', 5000);
            }
            
            function showLoading(show = true) {
                document.getElementById('loading').style.display = show ? 'block' : 'none';
            }
            
            function showSection(sectionId) {
                ['login-section', 'mobile-otp-section', 'dashboard'].forEach(id => {
                    document.getElementById(id).style.display = id === sectionId ? 'block' : 'none';
                });
            }
            
            function authenticateUser(userData, provider = 'email') {
                showLoading(true);
                
                setTimeout(() => {
                    showLoading(false);
                    currentUser = { ...userData, provider };
                    
                    document.getElementById('user-details').innerHTML = `
                        <strong>Name:</strong> ${userData.name}<br>
                        <strong>Provider:</strong> ${provider}<br>
                        <strong>Role:</strong> ${userData.role || 'user'}
                    `;
                    
                    showSection('dashboard');
                    showMessage(`Welcome ${userData.name}! Authentication via ${provider} successful.`);
                }, 1500);
            }
            
            // Email/Password authentication
            document.getElementById('email-form').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                
                if (mockUsers[email] && mockUsers[email].password === password) {
                    authenticateUser(mockUsers[email], 'email');
                } else {
                    showMessage('Invalid email or password. Try admin@universal-auth.local / admin123', 'error');
                }
            });
            
            // OAuth authentication
            document.querySelectorAll('[data-provider]').forEach(button => {
                button.addEventListener('click', function() {
                    const provider = this.dataset.provider;
                    showLoading(true);
                    
                    // Simulate OAuth flow
                    setTimeout(() => {
                        showLoading(false);
                        const userData = {
                            name: `${provider.charAt(0).toUpperCase() + provider.slice(1)} User`,
                            email: `user@${provider}.com`,
                            role: 'user'
                        };
                        authenticateUser(userData, provider);
                    }, 2000);
                });
            });
            
            // Mobile OTP flow
            document.getElementById('mobile-otp-btn').addEventListener('click', function() {
                showSection('mobile-otp-section');
            });
            
            document.getElementById('send-otp-btn').addEventListener('click', function() {
                const mobile = document.getElementById('mobile').value;
                
                if (!mobile.match(/^\\+91[6-9]\\d{9}$/)) {
                    showMessage('Please enter a valid Indian mobile number (+91XXXXXXXXXX)', 'error');
                    return;
                }
                
                if (mockOTPs[mobile]) {
                    document.getElementById('otp-input-section').style.display = 'block';
                    showMessage(`OTP sent to ${mobile}. Use: ${mockOTPs[mobile]}`);
                } else {
                    showMessage('Mobile number not registered. Try +919876543210', 'error');
                }
            });
            
            document.getElementById('verify-otp-btn').addEventListener('click', function() {
                const mobile = document.getElementById('mobile').value;
                const otp = document.getElementById('otp').value;
                
                if (mockOTPs[mobile] === otp) {
                    const userData = {
                        name: 'Mobile User',
                        mobile: mobile,
                        role: 'user'
                    };
                    authenticateUser(userData, 'mobile-otp');
                } else {
                    showMessage('Invalid OTP. Please try again.', 'error');
                }
            });
            
            // Navigation
            document.getElementById('back-to-login').addEventListener('click', function() {
                showSection('login-section');
                document.getElementById('otp-input-section').style.display = 'none';
            });
            
            document.getElementById('logout-btn').addEventListener('click', function() {
                currentUser = null;
                showSection('login-section');
                showMessage('You have been signed out successfully.');
                
                // Reset forms
                document.getElementById('email-form').reset();
                document.getElementById('mobile').value = '';
                document.getElementById('otp').value = '';
                document.getElementById('otp-input-section').style.display = 'none';
            });
            
            // Auto-focus on email input
            document.getElementById('email').focus();
        </script>
    </body>
    </html>
    """

def run_bdd_demo():
    """Run BDD testing demonstration"""
    print("🎭 Universal Auth BDD Testing Demonstration")
    print("=" * 50)
    
    mock_html = create_mock_auth_page()
    
    with sync_playwright() as p:
        print("🚀 Launching browser...")
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page()
        
        try:
            print("📄 Loading mock authentication page...")
            page.goto(f"data:text/html,{mock_html}")
            
            # Test 1: Email/Password Authentication
            print("\\n🧪 Test 1: Email/Password Authentication")
            print("  📧 Filling email and password...")
            page.fill('[data-testid="email-input"]', 'admin@universal-auth.local')
            page.fill('[data-testid="password-input"]', 'admin123')
            
            print("  🔘 Clicking login button...")
            page.click('[data-testid="login-button"]')
            
            print("  ⏳ Waiting for authentication...")
            page.wait_for_selector('[data-testid="dashboard"]', state='visible', timeout=10000)
            
            user_details = page.locator('[data-testid="user-details"]').text_content()
            print(f"  ✅ Login successful! User: {user_details}")
            
            # Logout
            print("  🚪 Logging out...")
            page.click('[data-testid="logout-button"]')
            page.wait_for_selector('[data-testid="dashboard"]', state='hidden')
            print("  ✅ Logout successful!")
            
            time.sleep(2)
            
            # Test 2: OAuth Authentication
            print("\\n🧪 Test 2: OAuth Authentication (Google)")
            print("  🔍 Clicking Google sign-in...")
            page.click('[data-testid="google-signin"]')
            
            print("  ⏳ Waiting for OAuth flow...")
            page.wait_for_selector('[data-testid="dashboard"]', state='visible', timeout=10000)
            
            user_details = page.locator('[data-testid="user-details"]').text_content()
            print(f"  ✅ OAuth login successful! User: {user_details}")
            
            # Logout
            page.click('[data-testid="logout-button"]')
            page.wait_for_selector('[data-testid="dashboard"]', state='hidden')
            
            time.sleep(2)
            
            # Test 3: Mobile OTP Authentication
            print("\\n🧪 Test 3: Mobile OTP Authentication")
            print("  📱 Clicking Mobile OTP...")
            page.click('[data-testid="mobile-otp-button"]')
            
            print("  📞 Entering mobile number...")
            page.fill('[data-testid="mobile-input"]', '+919876543210')
            
            print("  📤 Sending OTP...")
            page.click('[data-testid="send-otp"]')
            
            print("  ⏳ Waiting for OTP input...")
            page.wait_for_selector('[data-testid="otp-input"]', state='visible')
            
            print("  🔢 Entering OTP...")
            page.fill('[data-testid="otp-input"]', '123456')
            
            print("  ✅ Verifying OTP...")
            page.click('[data-testid="verify-otp"]')
            
            page.wait_for_selector('[data-testid="dashboard"]', state='visible', timeout=10000)
            
            user_details = page.locator('[data-testid="user-details"]').text_content()
            print(f"  ✅ OTP authentication successful! User: {user_details}")
            
            # Test 4: Error Handling
            print("\\n🧪 Test 4: Error Handling")
            page.click('[data-testid="logout-button"]')
            page.wait_for_selector('[data-testid="dashboard"]', state='hidden')
            
            print("  ❌ Testing invalid credentials...")
            page.fill('[data-testid="email-input"]', 'wrong@example.com')
            page.fill('[data-testid="password-input"]', 'wrongpassword')
            page.click('[data-testid="login-button"]')
            
            # Wait for error message
            page.wait_for_selector('[data-testid="message"]', state='visible')
            error_message = page.locator('[data-testid="message"]').text_content()
            print(f"  ✅ Error handling working: {error_message}")
            
            print("\\n🎉 All BDD tests completed successfully!")
            print("\\n📋 Test Summary:")
            print("  ✅ Email/Password Authentication")
            print("  ✅ OAuth Authentication (Google)")
            print("  ✅ Mobile OTP Authentication")
            print("  ✅ Error Handling")
            print("  ✅ User Interface Interactions")
            print("  ✅ State Management")
            
            print("\\n⏸️  Press Enter to close browser...")
            input()
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
        finally:
            browser.close()

def show_bdd_capabilities():
    """Show BDD testing capabilities"""
    print("\\n🎭 Universal Auth BDD Testing Capabilities")
    print("=" * 50)
    
    capabilities = {
        "🔐 Authentication Testing": [
            "Email/Password login flows",
            "OAuth provider integration (Google, GitHub, LinkedIn)",
            "Mobile OTP authentication",
            "Multi-factor authentication",
            "Progressive profiling",
            "Session management"
        ],
        "👨‍💼 Admin Panel Testing": [
            "User management operations",
            "Project configuration",
            "System settings",
            "Access control verification",
            "Dashboard navigation",
            "Bulk operations"
        ],
        "🌐 External Integration Testing": [
            "Embedded widget authentication",
            "Redirect-based auth flows",
            "Popup authentication",
            "Cross-domain authentication",
            "API integration testing",
            "Webhook verification"
        ],
        "🔒 Security Testing": [
            "Authentication bypass attempts",
            "CSRF protection verification",
            "XSS prevention testing",
            "Rate limiting verification",
            "Input validation testing",
            "Session security"
        ],
        "⚡ Performance Testing": [
            "Page load time measurement",
            "Authentication flow performance",
            "Concurrent user simulation",
            "Memory usage monitoring",
            "Network request analysis",
            "Browser performance metrics"
        ],
        "🎯 Cross-Browser Testing": [
            "Chromium-based browsers",
            "Firefox compatibility",
            "WebKit (Safari) testing",
            "Mobile browser testing",
            "Responsive design verification",
            "Accessibility compliance"
        ]
    }
    
    for category, features in capabilities.items():
        print(f"\\n{category}")
        for feature in features:
            print(f"  ✅ {feature}")
    
    print("\\n🛠️ Technical Features:")
    print("  ✅ Playwright browser automation")
    print("  ✅ pytest-bdd framework integration")
    print("  ✅ Gherkin feature files")
    print("  ✅ Step definition reusability")
    print("  ✅ Mock and integration test modes")
    print("  ✅ Screenshot and video recording")
    print("  ✅ Parallel test execution")
    print("  ✅ Comprehensive reporting")
    print("  ✅ CI/CD integration ready")
    print("  ✅ Docker containerization")

def main():
    """Main entry point"""
    print("🎭 Universal Auth BDD Testing System")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--capabilities":
        show_bdd_capabilities()
        return
    
    print("This demonstration shows the BDD testing capabilities")
    print("of the Universal Auth System using Playwright.")
    print("\\nThe demo will:")
    print("  1. Launch a browser with a mock authentication page")
    print("  2. Test email/password authentication")
    print("  3. Test OAuth authentication (Google)")
    print("  4. Test mobile OTP authentication")
    print("  5. Test error handling")
    print("\\nPress Enter to start the demo, or Ctrl+C to exit...")
    
    try:
        input()
        run_bdd_demo()
    except KeyboardInterrupt:
        print("\\n🛑 Demo cancelled by user")
    except Exception as e:
        print(f"\\n💥 Demo error: {e}")

if __name__ == "__main__":
    main()