import { test, expect } from '@playwright/test'

test.describe('Basic App Functionality', () => {
  test('homepage loads correctly', async ({ page }) => {
    await page.goto('/')
    
    // Check that the page loads
    await expect(page).toHaveTitle(/IoT|Dashboard|Next/)
    
    // Wait for the page to be fully loaded
    await page.waitForLoadState('networkidle')
    
    // Basic content check
    await expect(page.locator('body')).toBeVisible()
  })

  test('navigation works correctly', async ({ page }) => {
    await page.goto('/')
    
    // Test that navigation doesn't throw errors
    await page.waitForLoadState('networkidle')
    
    // Check console for errors
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })
    
    // Navigate and check for errors
    await page.reload()
    await page.waitForLoadState('networkidle')
    
    // Allow for some framework warnings but no real errors
    const criticalErrors = errors.filter(error => 
      !error.includes('Warning') && 
      !error.includes('DevTools') &&
      !error.includes('favicon')
    )
    
    expect(criticalErrors).toHaveLength(0)
  })

  test('responsive design works', async ({ page }) => {
    // Test desktop view
    await page.setViewportSize({ width: 1200, height: 800 })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 })
    await page.reload()
    await page.waitForLoadState('networkidle')
    
    // Basic check that page still renders
    await expect(page.locator('body')).toBeVisible()
  })
})

test.describe('Performance', () => {
  test('page loads within reasonable time', async ({ page }) => {
    const start = Date.now()
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const loadTime = Date.now() - start
    
    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000)
  })
})