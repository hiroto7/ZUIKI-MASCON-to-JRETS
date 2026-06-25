import sys
import tkinter as tk

import pygame

from accessibility_permission import (
    is_accessibility_permission_granted,
    is_macos,
    open_accessibility_settings,
)
from mascon_controller import (
    PROFILE_LABELS,
    PYGAME_POLL_INTERVAL_MS,
    MasconController,
    Notch,
    TrainProfile,
    effective_notch_order,
)
from version_info import BUILD_LABEL

ACCESSIBILITY_PERMISSION_POLL_INTERVAL_MS = 1000


def color_for_notch(current_notch: Notch) -> str:
    if current_notch == Notch.EB:
        return "#b42318"
    if current_notch >= Notch.P1:
        return "#0969da"
    if current_notch == Notch.N:
        return "#57606a"
    return "#cf222e"


def accessibility_permission_status(granted: bool) -> tuple[str, str]:
    if granted:
        return ("アクセシビリティ権限: 許可済み", "#57606a")

    return ("アクセシビリティ権限: 未許可", "#b42318")


def should_show_accessibility_permission_status() -> bool:
    return is_macos()


class StatusWindow:
    def __init__(self, root: tk.Tk, controller: MasconController) -> None:
        self.root = root
        self.controller = controller
        self.show_accessibility_permission_status = (
            should_show_accessibility_permission_status()
        )
        self.root.title("ZUIKI MASCON to JRETS")
        self.root.geometry(
            "640x360" if self.show_accessibility_permission_status else "640x320"
        )
        self.root.resizable(False, False)
        self.root.configure(bg="#f6f8fa")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.title_label = tk.Label(
            root,
            text="ZUIKI MASCON to JRETS",
            font=("Helvetica", 16, "bold"),
            bg="#f6f8fa",
            fg="#24292f",
        )
        self.title_label.pack(pady=(16, 8))

        self.main_frame = tk.Frame(root, bg="#f6f8fa")
        self.main_frame.pack(fill="x", padx=24)

        self.notch_label = tk.Label(
            self.main_frame,
            text=Notch.N.name,
            width=4,
            font=("Helvetica", 48, "bold"),
            bg="#f6f8fa",
            fg=color_for_notch(Notch.N),
        )
        self.notch_label.pack(side="left", padx=(0, 20))

        self.info_frame = tk.Frame(self.main_frame, bg="#f6f8fa")
        self.info_frame.pack(side="left", fill="x", expand=True)

        self.profile_frame = tk.Frame(self.info_frame, bg="#f6f8fa")
        self.profile_frame.pack(fill="x", pady=2)

        self.profile_title = tk.Label(
            self.profile_frame,
            text="車種:",
            font=("Helvetica", 12),
            bg="#f6f8fa",
            fg="#57606a",
        )
        self.profile_title.pack(side="left")

        self.profile_buttons: dict[TrainProfile, tk.Label] = {}
        for train_profile, label in PROFILE_LABELS.items():
            button = tk.Label(
                self.profile_frame,
                text=label,
                width=5,
                font=("Helvetica", 11),
                relief="flat",
                padx=8,
                pady=4,
                cursor="hand2",
            )
            button.bind(
                "<Button-1>",
                lambda _event, selected=train_profile: self.change_profile(selected),
            )
            button.pack(side="left", padx=(6, 0))
            self.profile_buttons[train_profile] = button

        self.profile_limit_label = tk.Label(
            self.profile_frame,
            anchor="w",
            font=("Helvetica", 12),
            bg="#f6f8fa",
            fg="#57606a",
        )
        self.profile_limit_label.pack(side="left", padx=(10, 0))

        self.raw_label = self.create_info_label()
        self.controller_label = self.create_info_label()

        self.accessibility_frame = tk.Frame(self.info_frame, bg="#f6f8fa")
        if self.show_accessibility_permission_status:
            self.accessibility_frame.pack(fill="x", pady=2)
        self.accessibility_label = tk.Label(
            self.accessibility_frame,
            anchor="w",
            font=("Helvetica", 12),
            bg="#f6f8fa",
            fg="#57606a",
        )
        if self.show_accessibility_permission_status:
            self.accessibility_label.pack(side="left")
        self.accessibility_settings_button = tk.Button(
            self.accessibility_frame,
            text="システム設定で許可する",
            font=("Helvetica", 10),
            bg="#ffffff",
            fg="#24292f",
            activebackground="#f6f8fa",
            activeforeground="#24292f",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=open_accessibility_settings,
        )

        self.notch_bar = tk.Frame(root, bg="#f6f8fa")
        self.notch_bar.pack(pady=(14, 14))

        self.notch_labels: dict[Notch, tk.Label] = {}
        self.rebuild_notch_bar()

        self.buttons_title = tk.Label(
            root,
            text="押下中のボタン",
            font=("Helvetica", 11),
            bg="#f6f8fa",
            fg="#57606a",
        )
        self.buttons_title.pack()

        self.buttons_frame = tk.Frame(root, bg="#f6f8fa", height=28)
        self.buttons_frame.pack(pady=(4, 0))

        self.version_label = tk.Label(
            root,
            text=BUILD_LABEL,
            font=("Helvetica", 10),
            bg="#f6f8fa",
            fg="#57606a",
        )
        self.version_label.pack(side="bottom", pady=(0, 8))

        self.button_labels: dict[str, tk.Label] = {}
        if self.show_accessibility_permission_status:
            self.update_accessibility_status()
        self.update_status()

    def create_info_label(self, font_size: int = 12) -> tk.Label:
        label = tk.Label(
            self.info_frame,
            anchor="w",
            font=("Helvetica", font_size),
            bg="#f6f8fa",
            fg="#57606a",
        )
        label.pack(fill="x", pady=2)
        return label

    def render_status(self) -> None:
        self.notch_label.config(
            text=self.controller.notch.name,
            fg=color_for_notch(self.controller.notch),
        )
        self.profile_limit_label.config(
            text=(
                "max "
                f"{self.controller.profile_limit.max_power.name}/"
                f"{self.controller.profile_limit.max_brake.name}"
            )
        )
        self.raw_label.config(text=f"raw input: {self.controller.raw_notch.name}")
        if self.controller.joysticks:
            self.controller_label.config(
                text=f"コントローラー認識数: {len(self.controller.joysticks)}",
                fg="#57606a",
            )
        else:
            self.controller_label.config(
                text="コントローラーが認識されていません",
                fg="#b42318",
            )

        for train_profile, button in self.profile_buttons.items():
            if train_profile == self.controller.profile:
                button.config(bg="#24292f", fg="#ffffff")
            else:
                button.config(bg="#ffffff", fg="#24292f")

        for item, label in self.notch_labels.items():
            if item == self.controller.notch:
                label.config(bg=color_for_notch(item), fg="#ffffff")
            else:
                label.config(bg="#ffffff", fg="#57606a")

        current_buttons = {button.name for button in self.controller.pressed_buttons}

        for button_name in sorted(current_buttons):
            if button_name not in self.button_labels:
                label = tk.Label(
                    self.buttons_frame,
                    text=button_name,
                    font=("Helvetica", 10, "bold"),
                    bg="#24292f",
                    fg="#ffffff",
                    padx=8,
                    pady=3,
                )
                label.pack(side="left", padx=3)
                self.button_labels[button_name] = label

        for button_name in list(self.button_labels):
            if button_name not in current_buttons:
                self.button_labels[button_name].destroy()
                del self.button_labels[button_name]

    def update_status(self) -> None:
        self.render_status()
        self.root.after(PYGAME_POLL_INTERVAL_MS, self.update_status)

    def update_accessibility_status(self) -> None:
        is_accessibility_granted = is_accessibility_permission_granted()
        accessibility_text, accessibility_color = accessibility_permission_status(
            is_accessibility_granted
        )
        self.accessibility_label.config(
            text=accessibility_text,
            fg=accessibility_color,
        )
        if is_accessibility_granted:
            self.accessibility_settings_button.pack_forget()
        else:
            if not self.accessibility_settings_button.winfo_manager():
                self.accessibility_settings_button.pack(side="left", padx=(8, 0))
        self.root.after(
            ACCESSIBILITY_PERMISSION_POLL_INTERVAL_MS,
            self.update_accessibility_status,
        )

    def rebuild_notch_bar(self) -> None:
        for label in self.notch_labels.values():
            label.destroy()
        self.notch_labels.clear()

        for item in effective_notch_order(self.controller.profile_limit):
            label = tk.Label(
                self.notch_bar,
                text=item.name,
                width=3,
                font=("Helvetica", 10, "bold"),
                bg="#ffffff",
                fg="#57606a",
                relief="flat",
                padx=4,
                pady=4,
            )
            label.pack(side="left", padx=2)
            self.notch_labels[item] = label

    def change_profile(self, profile: TrainProfile) -> None:
        self.controller.change_profile(profile)
        self.rebuild_notch_bar()
        self.render_status()

    def close(self) -> None:
        self.controller.release_all_inputs()
        pygame.quit()
        self.root.destroy()
        sys.exit()
