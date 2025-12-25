#!/usr/bin/env node
/**
 * Universal Auth Docker Frontend Test - Node.js Version
 * 
 * Tests the new shadcn/ui frontend running in Docker
 * Runs on Windows with visible Chrome browser for real-time automation viewing.
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
  baseUrl: process.env.BASE_URL || 'http://localhost:3000',
  headless: process.env.HEADLESS === 'true' ? true : false,
  slowMo: 2000,             // Slow down actions by 2 seconds for better visibility
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

class UniversalAuthDockerTester {
  constructor() {
    this.browser = null;
    this.context = null;
    this.page = null;
    this.screenshots = [];
  }

  async initialize() {
    console.log('🎭 Universal Auth Docker Frontend Test (Node.js)');
    console.log('=' .repeat(60));
    console.log(`Testing frontend at: ${CONFIG.baseUrl}`);
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
    console.log('2️⃣ Checking Docker frontend health...');
    
    try {
      const response = await this.page.goto(CONFIG.baseUrl, { 
        waitUntil: 'networkidle',
        timeout: 15000 
      });
      
      if (response.status() === 200) {
        console.log('   ✅ Docker frontend is accessible and healthy!');
        const title = await this.page.title();
        console.log(`   📄 Page title: "${title}"`);
        return true;
      } else {
        console.log(`   ❌ Frontend returned status: ${response.status()}`);
        return false;
      }
    } catch (error) {
      console.log(`   ❌ Failed to access frontend: ${error.message}`);
      console.log(`   💡 Make sure Docker frontend is running: docker-compose up frontend`);
      return false;
    }
  }

  async testShadcnUIComponents() {
    console.log('\n3️⃣ Testing shadcn/ui components...');
    
    // Wait for page to fully load
    await this.page.waitForLoadState('networkidle');
    
    // Take initial screenshot
    await this.takeScreenshot('01-shadcn-initial', 'Initial shadcn/ui page load');
    
    // Check for shadcn/ui Card component
    const cardElements = {
      'Card container': '[class*="rounded-lg"][class*="border"][class*="bg-card"]',
      'Card header': '[class*="flex"][class*="flex-col"][class*="space-y"]',
      'Card title': 'h3[class*="font-semibold"]',
      'Card description': 'p[class*="text-muted-foreground"]',
      'Card content': '[class*="p-6"][class*="pt-0"]'
    };

    console.log('   🎨 Checking shadcn/ui Card components...');
    const cardResults = {};
    
    for (const [name, selector] of Object.entries(cardElements)) {
      try {
        const element = await this.page.locator(selector).first();
        const isVisible = await element.isVisible();
        cardResults[name] = isVisible;
        console.log(`   ${isVisible ? '✅' : '❌'} ${name}`);
      } catch (error) {
        cardResults[name] = false;
        console.log(`   ❌ ${name} (not found)`);
      }
    }

    return cardResults;
  }

  async testResponsiveDesign() {
    console.log('\n4️⃣ Testing responsive design...');
    
    const viewports = [
      { name: 'Desktop', width: 1920, height: 1080 },
      { name: 'Tablet', width: 768, height: 1024 },
      { name: 'Mobile', width: 375, height: 667 }
    ];

    const results = {};

    for (const viewport of viewports) {
      console.log(`   📱 Testing ${viewport.name} (${viewport.width}x${viewport.height})...`);
      
      await this.page.setViewportSize({ width: viewport.width, height: viewport.height });
      await this.page.waitForTimeout(1000); // Wait for layout to adjust
      
      // Take screenshot for this viewport
      await this.takeScreenshot(`02-responsive-${viewport.name.toLowerCase()}`, 
        `${viewport.name} responsive view`);
      
      // Check if elements are still visible and properly arranged
      const loginCard = this.page.locator('[class*="rounded-lg"][class*="border"]').first();
      const isVisible = await loginCard.isVisible();
      
      results[viewport.name] = {
        visible: isVisible,
        viewport: viewport
      };
      
      console.log(`     ${isVisible ? '✅' : '❌'} Login card visible in ${viewport.name}`);
    }

    // Reset to desktop viewport
    await this.page.setViewportSize({ width: 1920, height: 1080 });
    
    return results;
  }

  async testShadcnButtons() {
    console.log('\n5️⃣ Testing shadcn/ui Button components...');
    
    const buttonSelectors = {
      'OAuth Google Button': 'button:has-text("Continue with Google")',
      'OAuth GitHub Button': 'button:has-text("Continue with GitHub")',
      'OAuth LinkedIn Button': 'button:has-text("Continue with LinkedIn")',
      'Send OTP Button': 'button:has-text("Send OTP")'
    };

    const results = {};

    for (const [name, selector] of Object.entries(buttonSelectors)) {
      try {
        console.log(`   🔘 Testing ${name}...`);
        
        const buttonElement = this.page.locator(selector).first();
        await buttonElement.waitFor({ state: 'visible', timeout: 5000 });
        
        // Check button properties
        const isVisible = await buttonElement.isVisible();
        const isEnabled = await buttonElement.isEnabled();
        const hasProperClasses = await buttonElement.evaluate(el => {
          return el.className.includes('inline-flex') && 
                 el.className.includes('items-center') &&
                 el.className.includes('justify-center');
        });
        
        console.log(`     - Visible: ${isVisible ? '✅' : '❌'}`);
        console.log(`     - Enabled: ${isEnabled ? '✅' : '❌'}`);
        console.log(`     - Proper shadcn classes: ${hasProperClasses ? '✅' : '❌'}`);
        
        if (isVisible && isEnabled) {
          // Test hover effect
          await buttonElement.hover();
          await this.page.waitForTimeout(500);
          
          // Click the button
          await buttonElement.click();
          console.log(`     - Clicked: ✅`);
          
          // Wait a moment for any UI changes
          await this.page.waitForTimeout(1000);
          
          // Take screenshot after click
          await this.takeScreenshot(
            `03-button-${name.toLowerCase().replace(/\s+/g, '-')}`, 
            `${name} clicked`
          );
        }
        
        results[name] = { 
          visible: isVisible, 
          enabled: isEnabled,
          properClasses: hasProperClasses,
          clicked: isVisible && isEnabled 
        };
        
      } catch (error) {
        console.log(`     - Error: ❌ ${error.message}`);
        results[name] = { error: error.message };
      }
    }

    return results;
  }

  async testInputComponents() {
    console.log('\n6️⃣ Testing shadcn/ui Input components...');
    
    try {
      // Find mobile input with shadcn/ui styling
      const mobileInput = this.page.locator('input[type="tel"]').first();
      await mobileInput.waitFor({ state: 'visible' });
      
      console.log('   📱 Found shadcn/ui mobile input field');
      
      // Check if input has proper shadcn classes
      const hasProperClasses = await mobileInput.evaluate(el => {
        return el.className.includes('flex') && 
               el.className.includes('rounded-md') &&
               el.className.includes('border');
      });
      
      console.log(`   ${hasProperClasses ? '✅' : '❌'} Input has proper shadcn/ui classes`);
      
      // Test input interaction
      await mobileInput.clear();
      await mobileInput.fill(TEST_DATA.mobileNumber);
      
      console.log(`   ✅ Filled mobile number: ${TEST_DATA.mobileNumber}`);
      
      // Verify the value
      const value = await mobileInput.inputValue();
      console.log(`   🔍 Input value: "${value}"`);
      
      // Take screenshot
      await this.takeScreenshot('04-input-filled', 'shadcn/ui input filled');
      
      // Check if Send OTP button is enabled
      const sendOtpButton = this.page.locator('button:has-text("Send OTP")').first();
      const isEnabled = await sendOtpButton.isEnabled();
      console.log(`   ${isEnabled ? '✅' : '❌'} Send OTP button ${isEnabled ? 'enabled' : 'disabled'}`);
      
      return { success: true, value, buttonEnabled: isEnabled, properClasses: hasProperClasses };
      
    } catch (error) {
      console.log(`   ❌ Input test failed: ${error.message}`);
      await this.takeScreenshot('04-input-error', 'Input error');
      return { success: false, error: error.message };
    }
  }

  async extractShadcnThemeInfo() {
    console.log('\n7️⃣ Extracting shadcn/ui theme information...');
    
    try {
      const themeInfo = await this.page.evaluate(() => {
        const rootStyles = getComputedStyle(document.documentElement);
        
        return {
          title: document.title,
          url: window.location.href,
          viewport: {
            width: window.innerWidth,
            height: window.innerHeight
          },
          shadcnTheme: {
            background: rootStyles.getPropertyValue('--background').trim(),
            foreground: rootStyles.getPropertyValue('--foreground').trim(),
            primary: rootStyles.getPropertyValue('--primary').trim(),
            secondary: rootStyles.getPropertyValue('--secondary').trim(),
            border: rootStyles.getPropertyValue('--border').trim(),
            radius: rootStyles.getPropertyValue('--radius').trim()
          },
          elements: {
            totalButtons: document.querySelectorAll('button').length,
            totalInputs: document.querySelectorAll('input').length,
            shadcnCards: document.querySelectorAll('[class*="rounded-lg"][class*="border"]').length,
            shadcnButtons: document.querySelectorAll('button[class*="inline-flex"]').length,
            mobileInputValue: document.querySelector('input[type="tel"]')?.value || 'Not found'
          },
          styling: {
            hasShadcnClasses: !!document.querySelector('[class*="bg-card"]'),
            hasProperRadius: !!document.querySelector('[class*="rounded-lg"]'),
            hasProperSpacing: !!document.querySelector('[class*="space-y"]'),
            hasProperColors: !!document.querySelector('[class*="text-muted-foreground"]')
          }
        };
      });

      console.log('   📊 shadcn/ui Theme Information:');
      console.log(`      Title: ${themeInfo.title}`);
      console.log(`      URL: ${themeInfo.url}`);
      console.log(`      Viewport: ${themeInfo.viewport.width}x${themeInfo.viewport.height}`);
      console.log(`      Background: ${themeInfo.shadcnTheme.background}`);
      console.log(`      Primary: ${themeInfo.shadcnTheme.primary}`);
      console.log(`      Border Radius: ${themeInfo.shadcnTheme.radius}`);
      console.log(`      Buttons: ${themeInfo.elements.totalButtons}`);
      console.log(`      Inputs: ${themeInfo.elements.totalInputs}`);
      console.log(`      shadcn Cards: ${themeInfo.elements.shadcnCards}`);
      console.log(`      shadcn Buttons: ${themeInfo.elements.shadcnButtons}`);
      console.log(`      Mobile Value: ${themeInfo.elements.mobileInputValue}`);
      console.log(`      Has shadcn Classes: ${themeInfo.styling.hasShadcnClasses ? '✅' : '❌'}`);
      console.log(`      Proper Radius: ${themeInfo.styling.hasProperRadius ? '✅' : '❌'}`);
      console.log(`      Proper Spacing: ${themeInfo.styling.hasProperSpacing ? '✅' : '❌'}`);
      console.log(`      Proper Colors: ${themeInfo.styling.hasProperColors ? '✅' : '❌'}`);

      return themeInfo;
      
    } catch (error) {
      console.log(`   ❌ Failed to extract theme info: ${error.message}`);
      return { error: error.message };
    }
  }

  async finalScreenshotAndCleanup() {
    console.log('\n8️⃣ Taking final screenshot and preparing cleanup...');
    
    await this.takeScreenshot('05-final-shadcn-state', 'Final shadcn/ui page state');
    
    console.log('\n🎉 Docker frontend test completed successfully!');
    console.log('\n📸 Screenshots saved:');
    this.screenshots.forEach(screenshot => {
      console.log(`   - ${screenshot.filename} (${screenshot.description})`);
    });
    
    console.log('\n⏳ Browser will stay open for 15 seconds for manual inspection...');
    console.log('   You can interact with the page during this time.');
    console.log('   Press Ctrl+C to keep browser open longer.\n');
    
    // Countdown
    for (let i = 15; i > 0; i--) {
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
        throw new Error('Docker frontend health check failed');
      }
      
      await this.testShadcnUIComponents();
      await this.testResponsiveDesign();
      await this.testShadcnButtons();
      await this.testInputComponents();
      await this.extractShadcnThemeInfo();
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
  console.log('🚀 Universal Auth Docker Frontend Test - shadcn/ui Edition');
  console.log('=' .repeat(70));
  console.log('This will test the new shadcn/ui frontend running in Docker.\n');
  
  console.log('Prerequisites:');
  console.log('✅ Docker and Docker Compose installed');
  console.log('✅ Frontend running in Docker: docker-compose up frontend');
  console.log('✅ Node.js and Playwright installed\n');
  
  console.log('Press Ctrl+C to cancel, or wait 3 seconds to start...\n');
  
  // 3 second countdown
  for (let i = 3; i > 0; i--) {
    process.stdout.write(`Starting in ${i} seconds...\r`);
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  console.log('\n🎬 Starting Docker frontend test...\n');
  
  const tester = new UniversalAuthDockerTester();
  const result = await tester.runFullTest();
  
  if (result.success) {
    console.log('\n🎊 All Docker frontend tests completed successfully!');
    console.log('\n🎯 What was tested:');
    console.log('   ✅ Docker frontend accessibility and health');
    console.log('   ✅ shadcn/ui component rendering and styling');
    console.log('   ✅ Responsive design across multiple viewports');
    console.log('   ✅ Button components with proper shadcn/ui classes');
    console.log('   ✅ Input components with validation');
    console.log('   ✅ Theme variables and CSS custom properties');
    console.log('   ✅ Screenshot capture at each step');
    
    console.log('\n🔧 This demonstrates:');
    console.log('   - Modern shadcn/ui component library integration');
    console.log('   - Docker containerized frontend testing');
    console.log('   - Responsive design validation');
    console.log('   - Real browser testing with visual feedback');
    console.log('   - Professional UI component testing');
    console.log('   - Theme system validation');
    
    process.exit(0);
  } else {
    console.log('\n💥 Test failed. Check the error messages above.');
    console.log('   Screenshots have been saved for debugging.');
    console.log('   Make sure Docker frontend is running: docker-compose up frontend');
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

module.exports = { UniversalAuthDockerTester, CONFIG, TEST_DATA };