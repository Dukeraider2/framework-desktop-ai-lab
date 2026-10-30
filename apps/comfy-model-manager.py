#!/usr/bin/python3

import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

HOME = Path.home()
SERVICE = "comfy-model-watch.service"
SORTER = HOME / "bin" / "comfy-model-sort"
DOWNLOADS = HOME / "Downloads"
MODELS = HOME / "AI" / "ComfyUI" / "app" / "models"


class ComfyModelManager:
    def __init__(self, root):
        self.root = root
        self.root.title("ComfyUI Model Manager")
        self.root.geometry("940x700")
        self.root.minsize(760, 560)

        self.last_logs = ""
        self.service_text = tk.StringVar(value="Checking service...")
        self.autostart_text = tk.StringVar(value="Checking autostart...")

        self.build_ui()
        self.refresh_all()
        self.root.after(5000, self.periodic_refresh)

    def command(self, args, timeout=15):
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            output = (result.stdout + result.stderr).strip()
            return result.returncode, output
        except subprocess.TimeoutExpired:
            return 124, "Command timed out."
        except Exception as exc:
            return 1, str(exc)

    def build_ui(self):
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="ComfyUI Model Manager",
            font=("Sans", 19, "bold")
        ).pack(anchor="w")

        ttk.Label(
            main,
            text="Framework AI - Model download automation",
        ).pack(anchor="w", pady=(2, 14))

        status = ttk.LabelFrame(main, text="Watcher status", padding=12)
        status.pack(fill="x", pady=(0, 12))

        ttk.Label(
            status, textvariable=self.service_text,
            font=("Sans", 11, "bold")
        ).pack(anchor="w")

        ttk.Label(
            status, textvariable=self.autostart_text
        ).pack(anchor="w", pady=(5, 0))

        controls = ttk.LabelFrame(main, text="Service controls", padding=12)
        controls.pack(fill="x", pady=(0, 12))

        buttons = [
            ("Start", lambda: self.service_action("start")),
            ("Stop", lambda: self.service_action("stop")),
            ("Restart", lambda: self.service_action("restart")),
            ("Enable autostart", lambda: self.service_action("enable")),
            ("Disable autostart", lambda: self.service_action("disable")),
            ("Refresh status", self.refresh_all),
        ]

        for index, (label, action) in enumerate(buttons):
            ttk.Button(
                controls, text=label, command=action
            ).grid(row=index // 3, column=index % 3,
                   sticky="ew", padx=5, pady=5)

        for column in range(3):
            controls.columnconfigure(column, weight=1)

        sorter = ttk.LabelFrame(main, text="Model sorting", padding=12)
        sorter.pack(fill="x", pady=(0, 12))

        ttk.Button(
            sorter, text="Preview sorting (dry run)",
            command=lambda: self.run_sort(dry_run=True)
        ).grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        ttk.Button(
            sorter, text="Sort models now",
            command=lambda: self.run_sort(dry_run=False)
        ).grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        for column in range(2):
            sorter.columnconfigure(column, weight=1)

        folders = ttk.LabelFrame(main, text="Open folders", padding=12)
        folders.pack(fill="x", pady=(0, 12))

        folder_buttons = [
            ("Downloads", DOWNLOADS),
            ("All models", MODELS),
            ("Text encoders", MODELS / "text_encoders"),
            ("Diffusion models", MODELS / "diffusion_models"),
            ("VAE models", MODELS / "vae"),
        ]

        for index, (label, path) in enumerate(folder_buttons):
            ttk.Button(
                folders,
                text=label,
                command=lambda p=path: self.open_folder(p)
            ).grid(row=index // 3, column=index % 3,
                   sticky="ew", padx=5, pady=5)

        for column in range(3):
            folders.columnconfigure(column, weight=1)

        log_frame = ttk.LabelFrame(main, text="Service logs", padding=8)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_frame,
            height=12,
            wrap="word",
            font=("Monospace", 9),
            state="disabled"
        )

        scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical",
            command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        footer = ttk.Frame(main)
        footer.pack(fill="x", pady=(8, 0))

        ttk.Label(
            footer,
            text="User-level systemd - No root privileges required"
        ).pack(side="left")

        ttk.Button(
            footer, text="Refresh logs",
            command=self.refresh_logs
        ).pack(side="right")

    def refresh_status(self):
        active_code, active = self.command(
            ["systemctl", "--user", "is-active", SERVICE]
        )
        enabled_code, enabled = self.command(
            ["systemctl", "--user", "is-enabled", SERVICE]
        )

        self.service_text.set(f"Service: {active or 'unknown'}")
        self.autostart_text.set(
            f"Autostart: {enabled or 'unknown'}"
        )

    def refresh_logs(self):
        code, output = self.command([
            "journalctl", "--user", "-u", SERVICE,
            "-n", "70", "--no-pager", "-o", "short-iso"
        ])

        if not output:
            output = "No service log entries available."

        if output != self.last_logs:
            self.last_logs = output
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.insert("end", output)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

    def refresh_all(self):
        self.refresh_status()
        self.refresh_logs()

    def periodic_refresh(self):
        self.refresh_all()
        self.root.after(5000, self.periodic_refresh)

    def service_action(self, action):
        commands = {
            "start": ["systemctl", "--user", "start", SERVICE],
            "stop": ["systemctl", "--user", "stop", SERVICE],
            "restart": ["systemctl", "--user", "restart", SERVICE],
            "enable": ["systemctl", "--user", "enable", SERVICE],
            "disable": ["systemctl", "--user", "disable", SERVICE],
        }

        if action == "stop" and not messagebox.askyesno(
            "Stop watcher",
            "Stop automatic model download monitoring?"
        ):
            return

        code, output = self.command(commands[action])
        self.refresh_all()

        if code == 0:
            messagebox.showinfo(
                "ComfyUI Model Manager",
                f"Command completed: {action}"
                + (f"\n\n{output}" if output else "")
            )
        else:
            messagebox.showerror(
                "Command failed",
                output or f"Exit code: {code}"
            )

    def run_sort(self, dry_run):
        if not SORTER.is_file():
            messagebox.showerror(
                "Sorter missing",
                f"Could not find:\n{SORTER}"
            )
            return

        if not dry_run and not messagebox.askyesno(
            "Confirm model sorting",
            "Move recognized models from Downloads "
            "into their ComfyUI directories?"
        ):
            return

        args = [str(SORTER)]
        if dry_run:
            args.append("--dry-run")

        code, output = self.command(args, timeout=300)
        title = "Sorting preview" if dry_run else "Sorting result"

        if code == 0:
            messagebox.showinfo(
                title, output or "Operation completed."
            )
        else:
            messagebox.showerror(
                title, output or f"Exit code: {code}"
            )

        self.refresh_logs()

    def open_folder(self, path):
        if not path.is_dir():
            messagebox.showwarning(
                "Folder not found",
                f"This folder does not exist yet:\n{path}"
            )
            return

        try:
            subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("Unable to open folder", str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    app = ComfyModelManager(root)
    root.mainloop()
