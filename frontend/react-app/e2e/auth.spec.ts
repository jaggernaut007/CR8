import { test, expect } from "@playwright/test";

test.describe("Auth Flow", () => {
  test("login page renders with sign in form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Sign In" })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
  });

  test("unauthenticated user is redirected to login", async ({ page }) => {
    await page.goto("/dashboard");
    // Should redirect to login since no auth
    await expect(page).toHaveURL(/\/login/);
  });

  test("toggle between sign in and create account", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByRole("heading", { name: "Create Account" })).toBeVisible();
    await expect(page.getByLabel("Display Name")).toBeVisible();

    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page.getByRole("heading", { name: "Sign In" })).toBeVisible();
  });

  test("shows error on invalid login", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("bad@example.com");
    await page.getByLabel("Password").fill("wrongpass");
    await page.getByRole("button", { name: "Sign In" }).click();

    // Should show some error message (exact text depends on backend)
    await expect(page.getByTestId("auth-error")).toBeVisible({ timeout: 5000 });
  });

  test("how it works section is visible", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByText("How it works")).toBeVisible();
    await expect(page.getByText("Upload")).toBeVisible();
    await expect(page.getByText("Generate")).toBeVisible();
    await expect(page.getByText("Learn", { exact: true })).toBeVisible();
  });
});
