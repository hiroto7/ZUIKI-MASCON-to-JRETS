import { expect, test } from "@playwright/test";

const pageUrl = new URL("../../web/index.html", import.meta.url).href;

const baseStatus = {
  notch: "N",
  raw_notch: "N",
  notch_order: [
    "P5",
    "P4",
    "P3",
    "P2",
    "P1",
    "N",
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8",
    "EB",
  ],
  profile: "default",
  profiles: [
    { id: "default", label: "標準", selected: true },
    { id: "tobu", label: "東武", selected: false },
    { id: "seibu", label: "西武", selected: false },
  ],
  max_power: "P5",
  max_brake: "B8",
  controller_count: 1,
  pressed_buttons: [],
  show_accessibility: false,
  accessibility_granted: true,
  build_label: "v2.2.0 (abcdef0)",
};

async function render(page, status) {
  await page.goto(pageUrl);
  await page.evaluate((value) => window.ZuikiStatusUi.renderStatus(value), status);
}

test("neutral driving state", async ({ page }) => {
  await render(page, baseStatus);
  await expect(page).toHaveScreenshot("neutral.png");
});

test("power notch and active buttons", async ({ page }) => {
  await render(page, {
    ...baseStatus,
    notch: "P4",
    raw_notch: "P4",
    pressed_buttons: ["A", "LEFT", "ZR"],
  });
  await expect(page).toHaveScreenshot("power-inputs.png");
});

test("emergency brake", async ({ page }) => {
  await render(page, {
    ...baseStatus,
    notch: "EB",
    raw_notch: "EB",
  });
  await expect(page).toHaveScreenshot("emergency-brake.png");
});

test("disconnected with accessibility warning", async ({ page }) => {
  await render(page, {
    ...baseStatus,
    controller_count: 0,
    show_accessibility: true,
    accessibility_granted: false,
  });
  await expect(page).toHaveScreenshot("disconnected-warning.png");
});

test("changes train profile", async ({ page }) => {
  await page.addInitScript((status) => {
    window.pywebview = {
      api: {
        change_profile: async (profileId) => {
          window.selectedProfile = profileId;
          return {
            ...status,
            profile: profileId,
            profiles: status.profiles.map((profile) => ({
              ...profile,
              selected: profile.id === profileId,
            })),
          };
        },
      },
    };
  }, baseStatus);
  await render(page, baseStatus);

  await page.getByRole("button", { name: "西武" }).click();

  await expect(page.getByRole("button", { name: "西武" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(await page.evaluate(() => window.selectedProfile)).toBe("seibu");
});

test("applies the latest profile after rapid changes", async ({ page }) => {
  await page.addInitScript((status) => {
    window.profileCalls = [];
    window.pywebview = {
      api: {
        change_profile: async (profileId) => {
          window.profileCalls.push(profileId);
          if (profileId === "seibu") {
            await new Promise((resolve) => window.setTimeout(resolve, 50));
          }
          return {
            ...status,
            profile: profileId,
            profiles: status.profiles.map((profile) => ({
              ...profile,
              selected: profile.id === profileId,
            })),
          };
        },
      },
    };
  }, baseStatus);
  await render(page, baseStatus);

  await page.getByRole("button", { name: "西武" }).click();
  await page.getByRole("button", { name: "東武" }).click();

  await expect(page.getByRole("button", { name: "東武" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(await page.evaluate(() => window.profileCalls)).toEqual([
    "seibu",
    "tobu",
  ]);
});
