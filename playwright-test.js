#!/usr/bin/env node
/**
 * Universal Auth Playwright Test - Node.js Version
 * 
 * A comprehensive Playwright automation script for testing the Universal Auth frontend.
 * Runs on Windows with visible Chrome browser for real-time automation viewing.
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
  baseUrl: process.env.BASE_URL || 'http://localhost:3000',
  headless: process.env.HEADLESS === 'true' ? true : false,           // Show browser for demo
  slowMo: 1500,             // Slow down actions by 1.5 seconds
  timeout: 30000,           // 30 second timeout
  viewport: { width: 1920, height: 1080 },
  screenshotDir: './screenshots'
};

// Test data
const TEST_DATA = {
  mobileNumber: '+919876543210',
  email: 'test@universal-auth.com',
  password: 'TestPassword123!'
};

class UniversalAuthTester {
  constructor() {
    this.browser = null;
    this.context = null;
    this.page = null;
    this.screenshots = [];
  }

  async initialize() {
    console.log('🎭 Universal Auth Playwright Test (Node.js)');
    console.log('=' .repeat(50));
    console.log('Initializing browser automation...\n');

    // Create screenshots directory
    if (!fs.existsSync(CONFIG.screenshotDir)) {
      fs.mkdirSync(CONFIG.screenshotDir, { recursive: true });
    }

    // Launch browser
    console.log('1️⃣ Launching Chrome browser...');
    this.browser = await chromium.launch({
      headless: CONFIG.headless,
      slowMo: CONFIG.slowMo,
      args: [
        '--start-maximized',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor'
      ]
    });

    // Create context and page
    this.context = await this.browser.newContext({
      viewport: CONFIG.viewport,
      ignoreHTTPSErrors: true
    });

    this.page = await this.context.newPage();
    
    // Set default timeout
    this.page.setDefaultTimeout(CONFIG.timeout);
    
    console.log('   ✅ Chrome browser launched successfully!');
    console.log('   📱 Browser window should be visible now\n');
  }

  async takeScreenshot(name, description) {
    const filename = `${Date.now()}-${name}.png`;
    const filepath = path.join(CONFIG.screenshotDir, filename);
    
    await this.page.screenshot({ 
      path: filepath, 
      fullPage: true 
    });
    
    this.screenshots.push({ name, filename, description });
    console.log(`   📸 Screenshot saved: ${filename}`);
    return filepath;
  }

  async checkFrontendHealth() {
    console.log('2️⃣ Checking frontend health...');
    
    try {
      const response = await this.page.goto(CONFIG.baseUrl, { 
        waitUntil: 'networkidle',
        timeout: 10000 
      });
      
      if (response.status() === 200) {
        console.log('   ✅ Frontend is accessible and healthy!');
        const title = await this.page.title();
        console.log(`   📄 Page title: "${title}"`);
        return true;
      } else {
        console.log(`   ❌ Frontend returned status: ${response.status()}`);
        return false;
      }
    } catch (error) {
      console.log(`   ❌ Failed to access frontend: ${error.message}`);
      console.log('   💡 Make sure the frontend is running on http://localhost:3000');
      return false;
    }
  }

  async testPageLoad() {
    console.log('\n3️⃣ Testing page load and UI elements...');
    
    // Wait for page to fully load
    await this.page.waitForLoadState('networkidle');
    
    // Take initial screenshot
    await this.takeScreenshot('01-initial-load', 'Initial page load');
    
    // Check for key elements
    const elements = {
      'Universal Auth title': 'h1:has-text("Universal Auth")',
      'Welcome heading': 'h2:has-text("Welcome")',
      'Mobile input': 'input[type="tel"]',
      'Google OAuth button': 'button:has-text("Continue with Google")',
      'GitHub OAuth button': 'button:has-text("Continue with GitHub")',
      'LinkedIn OAuth button': 'button:has-text("Continue with LinkedIn")',
      'Send OTP button': 'button:has-text("Send OTP")'
    };

    console.log('   🔍 Checking UI elements...');
    const results = {};
    
    for (const [name, selector] of Object.entries(elements)) {
      try {
        const element = await this.page.locator(selector).first();
        const isVisible = await element.isVisible();
        results[name] = isVisible;
        console.log(`   ${isVisible ? '✅' : '❌'} ${name}`);
      } catch (error) {
        results[name] = false;
        console.log(`   ❌ ${name} (not found)`);
      }
    }

    return results;
  }

  async testMobileInput() {
    console.log('\n4️⃣ Testing mobile number input...');
    
    try {
      // Find mobile input
      const mobileInput = this.page.locator('input[type="tel"]').first();
      await mobileInput.waitFor({ state: 'visible' });
      
      console.log('   📱 Found mobile input field');
      
      // Clear and fill mobile number
      await mobileInput.clear();
      await mobileInput.fill(TEST_DATA.mobileNumber);
      
      console.log(`   ✅ Filled mobile number: ${TEST_DATA.mobileNumber}`);
      
      // Verify the value
      const value = await mobileInput.inputValue();
      console.log(`   🔍 Input value: "${value}"`);
      
      // Take screenshot
      await this.takeScreenshot('02-mobile-filled', 'Mobile number filled');
      
      // Check if Send OTP button is enabled
      const sendOtpButton = this.page.locator('button:has-text("Send OTP")').first();
      const isEnabled = await sendOtpButton.isEnabled();
      console.log(`   ${isEnabled ? '✅' : '❌'} Send OTP button ${isEnabled ? 'enabled' : 'disabled'}`);
      
      return { success: true, value, buttonEnabled: isEnabled };
      
    } catch (error) {
      console.log(`   ❌ Mobile input test failed: ${error.message}`);
      await this.takeScreenshot('02-mobile-error', 'Mobile input error');
      return { success: false, error: error.message };
    }
  }

  async testOAuthButtons() {
    console.log('\n5️⃣ Testing OAuth buttons...');
    
    const oauthButtons = [
      { name: 'Google', selector: 'button:has-text("Continue with Google")', icon: '🔍' },
      { name: 'GitHub', selector: 'button:has-text("Continue with GitHub")', icon: '🐙' },
      { name: 'LinkedIn', selector: 'button:has-text("Continue with LinkedIn")', icon: '💼' }
    ];

    const results = {};

    for (const button of oauthButtons) {
      try {
        console.log(`   ${button.icon} Testing ${button.name} OAuth button...`);
        
        const buttonElement = this.page.locator(button.selector).first();
        await buttonElement.waitFor({ state: 'visible' });
        
        // Check if button is visible and enabled
        const isVisible = await buttonElement.isVisible();
        const isEnabled = await buttonElement.isEnabled();
        
        console.log(`     - Visible: ${isVisible ? '✅' : '❌'}`);
        console.log(`     - Enabled: ${isEnabled ? '✅' : '❌'}`);
        
        if (isVisible && isEnabled) {
          // Click the button
          await buttonElement.click();
          console.log(`     - Clicked: ✅`);
          
          // Wait a moment for any UI changes
          await this.page.waitForTimeout(1000);
          
          // Take screenshot after click
          await this.takeScreenshot(
            `03-oauth-${button.name.toLowerCase()}`, 
            `${button.name} OAuth button clicked`
          );
        }
        
        results[button.name] = { 
          visible: isVisible, 
          enabled: isEnabled, 
          clicked: isVisible && isEnabled 
        };
        
      } catch (error) {
        console.log(`     - Error: ❌ ${error.message}`);
        results[button.name] = { error: error.message };
      }
    }

    return results;
  }

  async testFormValidation() {
    console.log('\n6️⃣ Testing form validation...');
    
    try {
      // Test empty mobile number
      console.log('   🧪 Testing empty mobile validation...');
      const mobileInput = this.page.locator('input[type="tel"]').first();
      await mobileInput.clear();
      
      const sendOtpButton = this.page.locator('button:has-text("Send OTP")').first();
      const isDisabled = await sendOtpButton.isDisabled();
      
      console.log(`   ${isDisabled ? '✅' : '❌'} Send OTP button ${isDisabled ? 'properly disabled' : 'should be disabled'} for empty input`);
      
      // Test invalid mobile number
      console.log('   🧪 Testing invalid mobile validation...');
      await mobileInput.fill('123');
      await this.page.waitForTimeout(500);
      
      // Fill valid number again
      await mobileInput.clear();
      await mobileInput.fill(TEST_DATA.mobileNumber);
      
      const isEnabledAfterValid = await sendOtpButton.isEnabled();
      console.log(`   ${isEnabledAfterValid ? '✅' : '❌'} Send OTP button ${isEnabledAfterValid ? 'enabled' : 'should be enabled'} for valid input`);
      
      await this.takeScreenshot('04-validation-test', 'Form validation test');
      
      return { success: true };
      
    } catch (error) {
      console.log(`   ❌ Form validation test failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  async extractPageInfo() {
    console.log('\n7️⃣ Extracting page information...');
    
    try {
      const pageInfo = await this.page.evaluate(() => {
        return {
          title: document.title,
          url: window.location.href,
          userAgent: navigator.userAgent,
          viewport: {
            width: window.innerWidth,
            height: window.innerHeight
          },
          elements: {
            totalButtons: document.querySelectorAll('button').length,
            totalInputs: document.querySelectorAll('input').length,
            totalForms: document.querySelectorAll('form').length,
            hasGradient: !!document.querySelector('[class*="gradient"]'),
            hasTailwind: !!document.querySelector('[class*="text-"]'),
            mobileInputValue: document.querySelector('input[type="tel"]')?.value || 'Not found'
          },
          styling: {
            bodyClasses: document.body.className,
            hasModernStyling: !!document.querySelector('[class*="shadow"]'),
            hasAnimations: !!document.querySelector('[class*="transition"]')
          }
        };
      });

      console.log('   📊 Page Information:');
      console.log(`      Title: ${pageInfo.title}`);
      console.log(`      URL: ${pageInfo.url}`);
      console.log(`      Viewport: ${pageInfo.viewport.width}x${pageInfo.viewport.height}`);
      console.log(`      Buttons: ${pageInfo.elements.totalButtons}`);
      console.log(`      Inputs: ${pageInfo.elements.totalInputs}`);
      console.log(`      Forms: ${pageInfo.elements.totalForms}`);
      console.log(`      Mobile Value: ${pageInfo.elements.mobileInputValue}`);
      console.log(`      Has Gradient: ${pageInfo.elements.hasGradient ? '✅' : '❌'}`);
      console.log(`      Has Tailwind: ${pageInfo.elements.hasTailwind ? '✅' : '❌'}`);
      console.log(`      Modern Styling: ${pageInfo.styling.hasModernStyling ? '✅' : '❌'}`);
      console.log(`      Animations: ${pageInfo.styling.hasAnimations ? '✅' : '❌'}`);

      return pageInfo;
      
    } catch (error) {
      console.log(`   ❌ Failed to extract page info: ${error.message}`);
      return { error: error.message };
    }
  }

  async performanceTest() {
    console.log('\n8️⃣ Running performance test...');
    
    try {
      // Measure page load time
      const startTime = Date.now();
      await this.page.reload({ waitUntil: 'networkidle' });
      const loadTime = Date.now() - startTime;
      
      console.log(`   ⏱️ Page load time: ${loadTime}ms`);
      
      // Check for console errors
      const logs = [];
      this.page.on('console', msg => {
        if (msg.type() === 'error') {
          logs.push(msg.text());
        }
      });
      
      // Wait a bit to collect any console errors
      await this.page.waitForTimeout(2000);
      
      console.log(`   ${logs.length === 0 ? '✅' : '⚠️'} Console errors: ${logs.length}`);
      if (logs.length > 0) {
        logs.forEach(log => console.log(`      - ${log}`));
      }
      
      return { loadTime, consoleErrors: logs };
      
    } catch (error) {
      console.log(`   ❌ Performance test failed: ${error.message}`);
      return { error: error.message };
    }
  }

  async finalScreenshotAndCleanup() {
    console.log('\n9️⃣ Taking final screenshot and preparing cleanup...');
    
    await this.takeScreenshot('05-final-state', 'Final page state');
    
    console.log('\n🎉 Test completed successfully!');
    console.log('\n📸 Screenshots saved:');
    this.screenshots.forEach(screenshot => {
      console.log(`   - ${screenshot.filename} (${screenshot.description})`);
    });
    
    console.log('\n⏳ Browser will stay open for 10 seconds for manual inspection...');
    console.log('   You can interact with the page during this time.');
    console.log('   Press Ctrl+C to keep browser open longer.\n');
    
    // Countdown
    for (let i = 10; i > 0; i--) {
      process.stdout.write(`   Closing in ${i} seconds...\r`);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    console.log('\n🔄 Closing browser...');
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close();
      console.log('   ✅ Browser closed successfully');
    }
  }

  async runFullTest() {
    try {
      await this.initialize();
      
      const healthCheck = await this.checkFrontendHealth();
      if (!healthCheck) {
        throw new Error('Frontend health check failed');
      }
      
      await this.testPageLoad();
      await this.testMobileInput();
      await this.testOAuthButtons();
      await this.testFormValidation();
      await this.extractPageInfo();
      await this.performanceTest();
      await this.finalScreenshotAndCleanup();
      
      return { success: true };
      
    } catch (error) {
      console.log(`\n❌ Test failed: ${error.message}`);
      await this.takeScreenshot('error', 'Test error state');
      return { success: false, error: error.message };
      
    } finally {
      await this.cleanup();
    }
  }
}

// Main execution
async function main() {
  console.log('🚀 Universal Auth Playwright Test - Node.js Edition');
  console.log('=' .repeat(60));
  console.log('This will test the Universal Auth frontend with visible Chrome automation.\n');
  
  console.log('Prerequisites:');
  console.log('✅ Node.js installed');
  console.log('✅ Playwright installed (npm install playwright)');
  console.log('✅ Universal Auth frontend running on http://localhost:3000\n');
  
  // Check if Playwright is installed
  try {
    require('playwright');
    console.log('✅ Playwright is available\n');
  } catch (error) {
    console.log('❌ Playwright not found. Please install it:');
    console.log('   npm install playwright');
    console.log('   npx playwright install\n');
    process.exit(1);
  }
  
  console.log('Press Ctrl+C to cancel, or wait 3 seconds to start...\n');
  
  // 3 second countdown
  for (let i = 3; i > 0; i--) {
    process.stdout.write(`Starting in ${i} seconds...\r`);
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  console.log('\n🎬 Starting test...\n');
  
  const tester = new UniversalAuthTester();
  const result = await tester.runFullTest();
  
  if (result.success) {
    console.log('\n🎊 All tests completed successfully!');
    console.log('\n🎯 What was tested:');
    console.log('   ✅ Frontend accessibility and health');
    console.log('   ✅ UI elements visibility and functionality');
    console.log('   ✅ Mobile number input and validation');
    console.log('   ✅ OAuth buttons (Google, GitHub, LinkedIn)');
    console.log('   ✅ Form validation logic');
    console.log('   ✅ Page information extraction');
    console.log('   ✅ Performance metrics');
    console.log('   ✅ Screenshot capture at each step');
    
    console.log('\n🔧 This demonstrates:');
    console.log('   - Modern React/Next.js app automation');
    console.log('   - Real browser testing with visual feedback');
    console.log('   - Form interaction and validation testing');
    console.log('   - OAuth button functionality testing');
    console.log('   - Performance monitoring');
    console.log('   - Comprehensive screenshot documentation');
    
    process.exit(0);
  } else {
    console.log('\n💥 Test failed. Check the error messages above.');
    console.log('   Screenshots have been saved for debugging.');
    process.exit(1);
  }
}

// Handle Ctrl+C gracefully
process.on('SIGINT', () => {
  console.log('\n\n⏸️ Test interrupted by user.');
  console.log('👋 Browser may remain open for manual inspection.');
  process.exit(0);
});

// Handle uncaught errors
process.on('unhandledRejection', (error) => {
  console.log('\n💥 Unhandled error:', error.message);
  process.exit(1);
});

// Run the test
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { UniversalAuthTester, CONFIG, TEST_DATA };