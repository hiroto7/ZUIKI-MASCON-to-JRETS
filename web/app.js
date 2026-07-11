const POLL_INTERVAL_MS = 100;
let selectedProfileId = null;
let profileRequestId = 0;

async function requestProfileChange(profileId) {
  const requestId = ++profileRequestId;
  selectedProfileId = profileId;
  renderProfileSelection();

  try {
    const status = await window.pywebview.api.change_profile(profileId);
    if (requestId === profileRequestId) {
      selectedProfileId = null;
      renderStatus(status);
    }
  } catch (error) {
    console.error("Failed to change profile", error);
    if (requestId === profileRequestId) selectedProfileId = null;
  }
}

function toneForNotch(notch) {
  if (notch === "EB") return "emergency";
  if (notch.startsWith("P")) return "power";
  if (notch.startsWith("B")) return "brake";
  return "neutral";
}

function renderProfiles(profiles) {
  const list = document.querySelector("#profile-list");
  for (const profile of profiles) {
    let button = list.querySelector(`[data-profile="${profile.id}"]`);
    if (!button) {
      button = document.createElement("button");
      button.type = "button";
      button.className = "profile-button";
      button.dataset.profile = profile.id;
      button.addEventListener("click", () => requestProfileChange(profile.id));
      list.append(button);
    }
    button.textContent = profile.label;
    button.dataset.selectedByStatus = String(profile.selected);
  }
  renderProfileSelection();
}

function renderProfileSelection() {
  for (const button of document.querySelectorAll(".profile-button")) {
    const selected = selectedProfileId
      ? button.dataset.profile === selectedProfileId
      : button.dataset.selectedByStatus === "true";
    button.setAttribute("aria-pressed", String(selected));
  }
}

function renderNotchTrack(status) {
  const track = document.querySelector("#notch-track");
  track.style.setProperty("--notch-count", status.notch_order.length);
  track.replaceChildren(
    ...[...status.notch_order].reverse().map((notch) => {
      const step = document.createElement("span");
      step.className = "notch-step";
      step.textContent = notch;
      step.dataset.tone = toneForNotch(notch);
      if (notch === status.notch) step.classList.add("notch-step--active");
      return step;
    }),
  );
}

function renderPressedButtons(buttons) {
  const container = document.querySelector("#pressed-buttons");
  if (buttons.length === 0) {
    const empty = document.createElement("span");
    empty.className = "empty-state";
    empty.textContent = "ボタン入力はありません";
    container.replaceChildren(empty);
    return;
  }

  container.replaceChildren(
    ...buttons.map((name) => {
      const chip = document.createElement("span");
      chip.className = "button-chip";
      chip.textContent = name;
      return chip;
    }),
  );
}

function renderStatus(status) {
  const tone = toneForNotch(status.notch);
  document.querySelector("#notch-card").dataset.tone = tone;
  document.querySelector("#current-notch").textContent = status.notch;
  document.querySelector("#raw-notch").textContent = status.raw_notch;
  document.querySelector("#profile-limit").textContent =
    `${status.max_power} / ${status.max_brake}`;
  document.querySelector("#build-label").textContent = status.build_label;

  const connection = document.querySelector("#connection");
  const connected = status.controller_count > 0;
  connection.classList.toggle("connection--online", connected);
  connection.classList.toggle("connection--offline", !connected);
  document.querySelector("#connection-label").textContent = connected
    ? `コントローラー ${status.controller_count}台`
    : "コントローラー未接続";

  const accessibility = document.querySelector("#accessibility-panel");
  accessibility.hidden =
    !status.show_accessibility || status.accessibility_granted;

  renderProfiles(status.profiles);
  renderPressedButtons(status.pressed_buttons);
  renderNotchTrack(status);
}

async function pollStatus() {
  try {
    renderStatus(await window.pywebview.api.get_status());
  } catch (error) {
    console.error("Failed to update status", error);
  } finally {
    window.setTimeout(pollStatus, POLL_INTERVAL_MS);
  }
}

document
  .querySelector("#accessibility-button")
  .addEventListener("click", () => window.pywebview.api.open_accessibility_settings());

window.addEventListener("pywebviewready", pollStatus);

if (window.__ZUIKI_TEST_STATUS__) {
  renderStatus(window.__ZUIKI_TEST_STATUS__);
}

window.ZuikiStatusUi = { renderStatus, requestProfileChange, toneForNotch };
