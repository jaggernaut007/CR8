import { test, expect } from "@playwright/test";

test.describe("Results Page", () => {
  test("unauthenticated user is redirected to login from results", async ({ page }) => {
    await page.goto("/results/12345678");
    await expect(page).toHaveURL(/\/login/);
  });

  test("results route redirects to login for any job id", async ({ page }) => {
    await page.goto("/results/abcd1234");
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("Content Viewer Security Headers", () => {
  test("CSP allows media and frames from same origin", async ({ page }) => {
    const response = await page.goto("/health");
    const csp = response?.headers()["content-security-policy"] ?? "";
    expect(csp).toContain("media-src 'self'");
    expect(csp).toContain("frame-src 'self'");
  });

  test("X-Frame-Options is SAMEORIGIN", async ({ page }) => {
    const response = await page.goto("/health");
    expect(response?.headers()["x-frame-options"]).toBe("SAMEORIGIN");
  });

  test("view API requires authentication", async ({ page }) => {
    const response = await page.goto("/api/view/12345678/pdf");
    // Should get 401 or redirect since not authenticated
    const status = response?.status() ?? 0;
    expect([401, 302]).toContain(status);
  });
});
