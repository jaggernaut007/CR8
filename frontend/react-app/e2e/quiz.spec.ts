import { test, expect } from "@playwright/test";

test.describe("Quiz Routes", () => {
  test("unauthenticated user is redirected to login from quiz page", async ({ page }) => {
    await page.goto("/quiz/12345678");
    await expect(page).toHaveURL(/\/login/);
  });

  test("unauthenticated user is redirected to login from quiz results", async ({ page }) => {
    await page.goto("/quiz/12345678/results");
    await expect(page).toHaveURL(/\/login/);
  });

  test("quiz generate API requires authentication", async ({ page }) => {
    const response = await page.request.post("/api/quiz/generate", {
      data: { job_id: "test-job", question_count: 20 },
    });
    expect(response.status()).toBe(401);
  });

  test("quiz fetch API requires authentication", async ({ page }) => {
    const response = await page.request.get("/api/quiz/12345678");
    expect(response.status()).toBe(401);
  });

  test("quiz submit API requires authentication", async ({ page }) => {
    const response = await page.request.post("/api/quiz/12345678/submit", {
      data: { responses: [] },
    });
    expect(response.status()).toBe(401);
  });

  test("quiz results API requires authentication", async ({ page }) => {
    const response = await page.request.get("/api/quiz/12345678/results");
    expect(response.status()).toBe(401);
  });

  test("quiz by-job API requires authentication", async ({ page }) => {
    const response = await page.request.get("/api/quiz/by-job/12345678");
    expect(response.status()).toBe(401);
  });
});
