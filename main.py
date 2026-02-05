import os
import platform
import random
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Resolve sound file paths — handles both normal and PyInstaller bundled mode
if getattr(sys, 'frozen', False):
    _BASE_DIR = sys._MEIPASS  # PyInstaller extracts to temp folder
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COPY_SOUND = os.path.join(_BASE_DIR, "sounds", "copy_sound.mp3")
DONE_SOUND = os.path.join(_BASE_DIR, "sounds", "done_sound.mp3")


def play_sound(sound_path: str = COPY_SOUND):
    """Play a sound in a background thread (cross-platform)."""
    def _play():
        try:
            system = platform.system()
            if system == "Darwin":
                subprocess.Popen(
                    ["afplay", sound_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            elif system == "Windows":
                subprocess.Popen(
                    [
                        "powershell", "-c",
                        f'(New-Object Media.SoundPlayer "{sound_path}").PlaySync()',
                    ],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                for player in ["mpv", "ffplay", "aplay", "paplay"]:
                    try:
                        args = [player]
                        if player == "mpv":
                            args += ["--no-terminal", "--no-video"]
                        elif player == "ffplay":
                            args += ["-nodisp", "-autoexit"]
                        args.append(sound_path)
                        subprocess.Popen(
                            args,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        )
                        break
                    except FileNotFoundError:
                        continue
        except Exception:
            pass

    threading.Thread(target=_play, daemon=True).start()


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

HEADERS = {
    "User-Agent": random.choice(USER_AGENTS),
}


def fetch_page(url: str) -> BeautifulSoup:
    for _ in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                return BeautifulSoup(response.content, "html.parser")
        except Exception:
            pass
    raise Exception(f"Failed to fetch {url} after 3 attempts")


def get_episode_tt(url: str) -> dict[int, str]:
    start: int = 1
    soup = fetch_page(url)

    articles = soup.select("article.episode-item-wrapper")
    links = [
        link.get("href", "")
        for article in articles
        for link in article.find_all("a", class_="ipc-title-link-wrapper")
    ]

    links = filter(lambda href: re.search(r"(tt\d+)\D", href), links)
    tt_list = [re.search(r"(tt\d+)\D", href).group(1) for href in links]

    if soup.find(
            "div", class_="ipc-title__text", string=lambda text: text and "E0" in text
    ):
        start = 0

    return {idx: tt_id for idx, tt_id in enumerate(tt_list, start=start)}


def find_season_amount(url: str) -> int:
    for _ in range(3):
        soup = fetch_page(url)
        tablist = soup.select('ul[role="tablist"]')
        if len(tablist) >= 2:
            links_without_unknown = (
                [a for a in tablist[1].find_all("a") if a.text.isdigit()]
                if tablist[1]
                else []
            )
            return len(links_without_unknown)
    raise Exception("Failed to find season amount after 3 attempts")


def extract_id(str_contain_id: str) -> str:
    match = re.search(r"tt\d+", str_contain_id)
    if not match:
        return ""
    tt_id = match.group(0)

    soup = fetch_page("https://imdb.com/title/" + tt_id)
    h3_tags = soup.find_all("h3")

    for tag in h3_tags:
        if "Episodes" in tag.text:
            return tt_id
        else:
            a_tag = soup.find("a", {"aria-label": "View all episodes"})
            if a_tag:
                root_match = re.search(r"tt\d+", a_tag.get("href", ""))
                if root_match:
                    return root_match.group(0)

    return tt_id


def is_dark_mode() -> bool:
    """Detect if the system is using a dark color scheme."""
    system = platform.system()

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=2,
            )
            return result.stdout.strip().lower() == "dark"
        except Exception:
            return False

    elif system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0
        except Exception:
            return False

    else:  # Linux — check multiple sources
        # 1. Check GTK theme name
        for env_var in ("GTK_THEME", "GTK2_RC_FILES"):
            val = os.environ.get(env_var, "").lower()
            if "dark" in val:
                return True

        # 2. Check freedesktop color-scheme via dbus (KDE, GNOME 42+)
        try:
            result = subprocess.run(
                [
                    "dbus-send", "--session", "--print-reply=literal",
                    "--dest=org.freedesktop.portal.Desktop",
                    "/org/freedesktop/portal/desktop",
                    "org.freedesktop.portal.Settings.Read",
                    "string:org.freedesktop.appearance",
                    "string:color-scheme",
                ],
                capture_output=True, text=True, timeout=2,
            )
            # color-scheme: 0=default, 1=dark, 2=light
            if "uint32 1" in result.stdout:
                return True
        except Exception:
            pass

        # 3. Check gsettings (GNOME)
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=2,
            )
            if "dark" in result.stdout.lower():
                return True
        except Exception:
            pass

        # 4. Fallback: sample the tkinter default background color
        try:
            temp = tk.Tk()
            temp.withdraw()
            bg = temp.cget("background")
            temp.destroy()
            # Parse the color — dark backgrounds have low brightness
            r, g, b = temp.winfo_rgb(bg) if hasattr(temp, 'winfo_rgb') else (0xFFFF, 0xFFFF, 0xFFFF)
            brightness = (r + g + b) / 3 / 256
            return brightness < 128
        except Exception:
            pass

        return False


class IMDbLookupApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("IMDb ID Lookup")
        self.root.minsize(700, 500)

        # Detect dark/light mode for adaptive colors
        self.dark_mode = is_dark_mode()
        self.status_color = "yellow" if self.dark_mode else "blue"

        # Store episode data — keyed by season
        self.episodes_by_season: dict[int, list[dict]] = {}
        self.episode_rows: list[dict] = []  # flat list currently displayed
        self.season_amount: int = 0

        # Auto-copy state
        self.auto_copy_active = False
        self.auto_copy_index = 0
        self.auto_copy_after_id: Optional[str] = None
        self.auto_copy_season_rows: list[dict] = []

        self._build_ui()
        self._bind_shortcuts()

    def _bind_shortcuts(self):
        """Explicitly bind Cmd/Ctrl shortcuts so they work with non-English input methods on macOS."""
        for widget in (self.root, self.search_entry):
            widget.bind("<Command-a>", self._select_all)
            widget.bind("<Command-A>", self._select_all)
            widget.bind("<Command-c>", self._cmd_copy)
            widget.bind("<Command-C>", self._cmd_copy)
            widget.bind("<Command-v>", self._cmd_paste)
            widget.bind("<Command-V>", self._cmd_paste)
            widget.bind("<Command-x>", self._cmd_cut)
            widget.bind("<Command-X>", self._cmd_cut)
            # Also bind Control- variants for non-macOS or edge cases
            widget.bind("<Control-a>", self._select_all)
            widget.bind("<Control-A>", self._select_all)
            widget.bind("<Control-c>", self._cmd_copy)
            widget.bind("<Control-C>", self._cmd_copy)
            widget.bind("<Control-v>", self._cmd_paste)
            widget.bind("<Control-V>", self._cmd_paste)
            widget.bind("<Control-x>", self._cmd_cut)
            widget.bind("<Control-X>", self._cmd_cut)

    def _select_all(self, event):
        widget = event.widget
        if isinstance(widget, (tk.Entry, ttk.Entry)):
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
            return "break"
        elif isinstance(widget, tk.Text):
            widget.tag_add(tk.SEL, "1.0", tk.END)
            return "break"

    def _cmd_copy(self, event):
        widget = event.widget
        try:
            if isinstance(widget, (tk.Entry, ttk.Entry)):
                if widget.selection_present():
                    self.root.clipboard_clear()
                    self.root.clipboard_append(widget.selection_get())
            elif isinstance(widget, tk.Text):
                sel = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                if sel:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(sel)
        except tk.TclError:
            pass
        return "break"

    def _cmd_paste(self, event):
        widget = event.widget
        try:
            text = self.root.clipboard_get()
            if isinstance(widget, (tk.Entry, ttk.Entry)):
                if widget.selection_present():
                    widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                widget.insert(tk.INSERT, text)
            elif isinstance(widget, tk.Text):
                try:
                    widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass
                widget.insert(tk.INSERT, text)
        except tk.TclError:
            pass
        return "break"

    def _cmd_cut(self, event):
        self._cmd_copy(event)
        widget = event.widget
        try:
            if isinstance(widget, (tk.Entry, ttk.Entry)):
                if widget.selection_present():
                    widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
            elif isinstance(widget, tk.Text):
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass
        return "break"

    def _build_ui(self):
        # --- Search frame ---
        search_frame = ttk.LabelFrame(self.root, text="Search", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        top_label_row = ttk.Frame(search_frame)
        top_label_row.pack(fill=tk.X)

        ttk.Label(top_label_row, text="Paste an IMDb URL or tt ID:").pack(
            side=tk.LEFT, anchor=tk.W
        )

        self.imdb_btn = ttk.Button(
            top_label_row,
            text="🌐 Open IMDb",
            command=lambda: webbrowser.open("https://www.imdb.com"),
        )
        self.imdb_btn.pack(side=tk.RIGHT)

        input_row = ttk.Frame(search_frame)
        input_row.pack(fill=tk.X, pady=(5, 0))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(input_row, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.search_entry.bind("<Return>", lambda e: self._on_search())

        self.search_btn = ttk.Button(input_row, text="Fetch", command=self._on_search)
        self.search_btn.pack(side=tk.RIGHT)

        # --- Status ---
        self.status_var = tk.StringVar(value="Ready. Open IMDb, find your title, paste the URL here.")
        ttk.Label(self.root, textvariable=self.status_var, foreground="gray").pack(
            anchor=tk.W, padx=10, pady=(2, 2)
        )

        # --- Pack bottom frames FIRST (bottom-up) so they always stay visible ---
        # --- Bottom buttons ---
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

        self.copy_all_btn = ttk.Button(
            btn_frame, text="📋 Copy All", command=self._copy_all, state=tk.DISABLED
        )
        self.copy_all_btn.pack(side=tk.RIGHT)

        # --- Auto-copy frame ---
        auto_frame = ttk.LabelFrame(self.root, text="Auto Copy (sequential)", padding=5)
        auto_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))

        auto_row1 = ttk.Frame(auto_frame)
        auto_row1.pack(fill=tk.X)

        ttk.Label(auto_row1, text="Season:").pack(side=tk.LEFT)
        self.season_var = tk.StringVar(value="1")
        self.season_spinbox = ttk.Spinbox(
            auto_row1, from_=1, to=1, increment=1,
            textvariable=self.season_var, width=4, state=tk.DISABLED
        )
        self.season_spinbox.pack(side=tk.LEFT, padx=(5, 10))

        ttk.Label(auto_row1, text="Interval (sec):").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value="2")
        self.interval_entry = ttk.Spinbox(
            auto_row1, from_=0.5, to=30, increment=0.5,
            textvariable=self.interval_var, width=5
        )
        self.interval_entry.pack(side=tk.LEFT, padx=(5, 10))

        self.reverse_var = tk.BooleanVar(value=False)
        self.reverse_check = ttk.Checkbutton(
            auto_row1, text="◀ Reverse", variable=self.reverse_var
        )
        self.reverse_check.pack(side=tk.LEFT, padx=(0, 10))

        self.sound_enabled = tk.BooleanVar(value=False)
        self.sound_check = ttk.Checkbutton(
            auto_row1, text="🔊 Sound", variable=self.sound_enabled
        )
        self.sound_check.pack(side=tk.LEFT, padx=(0, 10))

        auto_row2 = ttk.Frame(auto_frame)
        auto_row2.pack(fill=tk.X, pady=(4, 0))

        self.auto_copy_btn = ttk.Button(
            auto_row2, text="▶ Start Auto Copy", command=self._toggle_auto_copy, state=tk.DISABLED
        )
        self.auto_copy_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.auto_copy_status = tk.StringVar(value="")
        ttk.Label(auto_row2, textvariable=self.auto_copy_status, foreground=self.status_color).pack(
            side=tk.LEFT
        )

        # --- Episode list frame (scrollable) — packed LAST so it fills remaining space ---
        output_frame = ttk.LabelFrame(self.root, text="Episode IDs", padding=5)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 5))

        self.canvas = tk.Canvas(output_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            output_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.inner_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor=tk.NW
        )

        self.inner_frame.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"),
        )
        self.canvas.bind_all(
            "<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units")
        )
        self.canvas.bind_all(
            "<Button-5>", lambda e: self.canvas.yview_scroll(1, "units")
        )

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _set_status(self, msg: str):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def _set_busy(self, busy: bool):
        state = tk.DISABLED if busy else tk.NORMAL
        self.search_btn.configure(state=state)
        self.search_entry.configure(state=state)

    def _on_search(self):
        query = self.search_var.get().strip()
        if not query:
            return

        if self.auto_copy_active:
            self._stop_auto_copy()

        tt_match = re.search(r"tt\d+", query)
        if not tt_match:
            self._set_status("Could not find a tt ID in your input. Paste an IMDb URL or tt ID.")
            return

        root_id = tt_match.group(0)
        self._set_busy(True)
        self._set_status(f"Fetching {root_id}...")
        threading.Thread(
            target=self._fetch_and_display, args=(root_id,), daemon=True
        ).start()

    def _fetch_and_display(self, root_id: str):
        try:
            self.root.after(0, self._set_status, f"Resolving {root_id}...")
            resolved_id = extract_id(root_id)
            if resolved_id != root_id:
                self.root.after(
                    0, self._set_status, f"Resolved to series {resolved_id}..."
                )
                root_id = resolved_id

            self.root.after(
                0, self._set_status, f"Fetching seasons for {root_id}..."
            )
            season_amount = find_season_amount(
                f"https://imdb.com/title/{root_id}/episodes/"
            )

            episodes_by_season: dict[int, list[tuple]] = {}
            for season in range(1, season_amount + 1):
                self.root.after(
                    0,
                    self._set_status,
                    f"Fetching season {season}/{season_amount}...",
                )
                episode_ids = get_episode_tt(
                    f"https://imdb.com/title/{root_id}/episodes?season={season}"
                )
                episodes_by_season[season] = [
                    (ep_num, ep_tt) for ep_num, ep_tt in episode_ids.items()
                ]

            self.root.after(
                0, self._display_episodes, root_id, episodes_by_season, season_amount
            )

        except Exception as e:
            self.root.after(0, self._set_status, f"Error: {e}")
            self.root.after(0, self._set_busy, False)

    def _display_episodes(
            self, root_id: str, episodes_by_season: dict[int, list[tuple]], season_amount: int
    ):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        self.episodes_by_season = {}
        self.episode_rows = []
        self.season_amount = season_amount

        # --- Root title ID row ---
        root_row = ttk.Frame(self.inner_frame)
        root_row.pack(fill=tk.X, padx=5, pady=(5, 8))

        root_text = f"[imdbid-{root_id}]"
        root_label = ttk.Label(
            root_row, text=f"Title: {root_text}", font=("Consolas", 12, "bold"), anchor=tk.W
        )
        root_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        root_copy_btn = ttk.Button(
            root_row,
            text="📋",
            width=3,
            command=lambda: self._copy_single(root_text),
        )
        root_copy_btn.pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Separator(self.inner_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=(0, 5))

        total_episodes = 0
        for season, eps in episodes_by_season.items():
            season_rows = []

            if season_amount > 1:
                header = ttk.Label(
                    self.inner_frame,
                    text=f"── Season {season} ──",
                    font=("Consolas", 11, "bold"),
                )
                header.pack(fill=tk.X, padx=5, pady=(8, 2))

            for ep_num, ep_tt in eps:
                ep_text = f"{str(ep_num).zfill(2)} [imdbid-{ep_tt}]"
                row_data = {"ep_num": ep_num, "ep_tt": ep_tt, "text": ep_text, "season": season}
                season_rows.append(row_data)
                self.episode_rows.append(row_data)

                row = ttk.Frame(self.inner_frame)
                row.pack(fill=tk.X, padx=5, pady=1)

                label = ttk.Label(
                    row, text=ep_text, font=("Consolas", 11), anchor=tk.W
                )
                label.pack(side=tk.LEFT, fill=tk.X, expand=True)

                copy_btn = ttk.Button(
                    row,
                    text="📋",
                    width=3,
                    command=lambda t=ep_text: self._copy_single(t),
                )
                copy_btn.pack(side=tk.RIGHT, padx=(5, 0))

            self.episodes_by_season[season] = season_rows
            total_episodes += len(season_rows)

        # Update season spinbox
        self.season_var.set("1")
        self.season_spinbox.configure(from_=1, to=max(1, season_amount))
        if season_amount > 1:
            self.season_spinbox.configure(state=tk.NORMAL)
        else:
            self.season_spinbox.configure(state=tk.DISABLED)

        self.copy_all_btn.configure(state=tk.NORMAL)
        self.auto_copy_btn.configure(state=tk.NORMAL)
        self.auto_copy_status.set("")
        self._set_status(
            f"Done — {root_id} • {total_episodes} episodes across {season_amount} season{'s' if season_amount != 1 else ''}"
        )
        self._set_busy(False)

        self.canvas.yview_moveto(0)

    def _copy_single(self, text: str):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._set_status(f"Copied: {text}")

    def _copy_all(self):
        self.root.clipboard_clear()
        all_text = "\n".join(row["text"] for row in self.episode_rows)
        self.root.clipboard_append(all_text)
        self._set_status("Copied all episode IDs to clipboard!")

    # --- Auto Copy (one season at a time) ---

    def _toggle_auto_copy(self):
        if self.auto_copy_active:
            self._stop_auto_copy()
        else:
            self._start_auto_copy()

    def _start_auto_copy(self):
        try:
            selected_season = int(self.season_var.get())
        except ValueError:
            self._set_status("Invalid season number.")
            return

        if selected_season not in self.episodes_by_season:
            self._set_status(f"Season {selected_season} not found.")
            return

        season_rows = self.episodes_by_season[selected_season]
        if not season_rows:
            self._set_status(f"Season {selected_season} has no episodes.")
            return

        # Reverse order if checkbox is checked
        if self.reverse_var.get():
            self.auto_copy_season_rows = list(reversed(season_rows))
        else:
            self.auto_copy_season_rows = list(season_rows)

        self.auto_copy_active = True
        self.auto_copy_index = 0
        self.auto_copy_btn.configure(text="⏹ Stop")
        self.interval_entry.configure(state=tk.DISABLED)
        self.season_spinbox.configure(state=tk.DISABLED)
        self.reverse_check.configure(state=tk.DISABLED)
        self._auto_copy_next()

    def _stop_auto_copy(self):
        self.auto_copy_active = False
        if self.auto_copy_after_id:
            self.root.after_cancel(self.auto_copy_after_id)
            self.auto_copy_after_id = None
        self.auto_copy_btn.configure(text="▶ Start Auto Copy")
        self.interval_entry.configure(state=tk.NORMAL)
        self.reverse_check.configure(state=tk.NORMAL)
        if self.season_amount > 1:
            self.season_spinbox.configure(state=tk.NORMAL)
        self.auto_copy_status.set("Stopped.")

    def _auto_copy_next(self):
        if not self.auto_copy_active:
            return

        total = len(self.auto_copy_season_rows)

        if self.auto_copy_index >= total:
            selected_season = int(self.season_var.get())
            direction = " (reversed)" if self.reverse_var.get() else ""
            self.auto_copy_status.set(f"✅ Done — Season {selected_season}{direction} complete!")
            self.auto_copy_active = False
            self.auto_copy_btn.configure(text="▶ Start Auto Copy")
            self.interval_entry.configure(state=tk.NORMAL)
            self.reverse_check.configure(state=tk.NORMAL)
            if self.season_amount > 1:
                self.season_spinbox.configure(state=tk.NORMAL)
            if self.sound_enabled.get():
                play_sound(DONE_SOUND)
            return

        row = self.auto_copy_season_rows[self.auto_copy_index]
        self.root.clipboard_clear()
        self.root.clipboard_append(row["text"])

        self.auto_copy_status.set(
            f"[{self.auto_copy_index + 1}/{total}] {row['text']}"
        )
        if self.sound_enabled.get():
            play_sound(COPY_SOUND)
        self._set_status(f"Auto-copied: {row['text']}")

        # Scroll to the row in the list
        try:
            flat_idx = self.episode_rows.index(row)
            self._highlight_row(flat_idx)
        except ValueError:
            pass

        self.auto_copy_index += 1

        try:
            interval_ms = int(float(self.interval_var.get()) * 1000)
        except ValueError:
            interval_ms = 2000

        self.auto_copy_after_id = self.root.after(interval_ms, self._auto_copy_next)

    def _highlight_row(self, index: int):
        """Scroll the canvas so the given episode row index is visible."""
        if not self.episode_rows:
            return
        total = len(self.episode_rows)
        fraction = max(0, (index - 2)) / total
        self.canvas.yview_moveto(fraction)


if __name__ == "__main__":
    root = tk.Tk()
    app = IMDbLookupApp(root)
    root.mainloop()
