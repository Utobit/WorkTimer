from __future__ import annotations

import calendar
import ctypes
import json
import math
import os
import sys
import threading
import time
import winreg
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from tkinter import (
    BOTH, END, LEFT, RIGHT, TOP, BOTTOM, X, Y,
    Canvas, Frame, Label, PhotoImage, Text, Tk, TclError,
    colorchooser, filedialog, messagebox, StringVar, OptionMenu
)
from tkinter import font as tkfont
import tkinter as tk
import tkinter.ttk as ttk

try:
    import pystray
    from PIL import Image, ImageDraw, ImageTk
except Exception:
    pystray = None
    Image = None
    ImageDraw = None
    ImageTk = None


APP_NAME = "WorkTimer"
VERSION = "1.0.2"
IDLE_GRACE_SECONDS = 10 * 60
POLL_SECONDS = 5
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", APP_DIR))
DATA_DIR = LOCAL_APPDATA / "LinaAI" / APP_NAME
DATA_FILE = DATA_DIR / "work_log.json"
CHECKPOINT_FILE = DATA_DIR / "checkpoint.json"
BACKUP_DIR = DATA_DIR / "backups"
LEGACY_DATA_FILE = APP_DIR / "data" / "work_log.json"
ICON_FILE = RESOURCE_DIR / "icon.png"
ICONS_DIR = RESOURCE_DIR / "icons"
SETTINGS_FILE = DATA_DIR / "settings.json"
REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "UtobitWorkTimer"

PALETTE_LIGHT: dict[str, str] = {
    "bg": "#f8fafc",       "panel": "#ffffff",    "line": "#e2e8f0",
    "text": "#1e293b",     "muted": "#64748b",    "clock": "#eff6ff",
    "clock_line": "#bfdbfe", "active": "#1d4ed8", "active_dark": "#1e40af",
    "center": "#2563eb",   "today": "#fefce8",    "btn_bg": "#f1f5f9",
    "btn_bg_hover": "#e2e8f0", "btn_fg": "#334155", "btn_border": "#cbd5e1",
    "btn_dark_bg": "#3b82f6", "btn_dark_fg": "#ffffff", "btn_dark_hover": "#2563eb",
}
PALETTE_DARK: dict[str, str] = {
    "bg": "#0f172a",       "panel": "#1e293b",    "line": "#334155",
    "text": "#f1f5f9",     "muted": "#94a3b8",    "clock": "#172554",
    "clock_line": "#1d4ed8", "active": "#3b82f6", "active_dark": "#2563eb",
    "center": "#60a5fa",   "today": "#1c1917",    "btn_bg": "#1e293b",
    "btn_bg_hover": "#334155", "btn_fg": "#cbd5e1", "btn_border": "#475569",
    "btn_dark_bg": "#3b82f6", "btn_dark_fg": "#ffffff", "btn_dark_hover": "#2563eb",
}
PALETTE: dict[str, str] = dict(PALETTE_LIGHT)

# ── 다국어 ──────────────────────────────────────────────
ICON_NAMES_KO = {"icon_1": "아이콘 1", "icon_2": "아이콘 2", "icon_3": "아이콘 3", "icon_4": "아이콘 4", "icon_5": "아이콘 5"}
ICON_NAMES_EN = {"icon_1": "Icon 1", "icon_2": "Icon 2", "icon_3": "Icon 3", "icon_4": "Icon 4", "icon_5": "Icon 5"}

LANG_KO = {
    "prev": "‹", "today": "오늘", "next": "›",
    "export": "기록 내보내기", "settings": "설정",
    "year_view": "연간 보기", "month_view": "월간",
    "back": "← 월간",
    "total_month": "이번 달 총 작업시간",
    "total_day": "전체 작업시간",
    "total": "총 작업시간",
    "intervals": "기록 구간",
    "no_record": "아직 기록이 없습니다.",
    "memo": "메모",
    "memo_save": "저장",
    "export_title": "기록 내보내기",
    "export_format": "형식 선택",
    "fmt_simple": "간단 (날짜·시간)",
    "fmt_table": "표 형식 (Notion/Docs)",
    "fmt_detail": "상세 (구간 포함)",
    "export_done": "내보내기 완료",
    "export_saved": "저장 완료:\n{}",
    "export_err": "오류",
    "reset_title": "데이터 초기화",
    "reset_confirm": "모든 작업 기록이 삭제됩니다.\n정말 초기화하시겠습니까?",
    "reset_done": "초기화 완료",
    "settings_title": "설정",
    "lang_label": "언어",
    "idle_label": "유휴 감지 시간 (분)",
    "data_path": "데이터 폴더 열기",
    "reset_btn": "데이터 초기화",
    "weekdays": ["일", "월", "화", "수", "목", "금", "토"],
    "made_by": "Made by Jin (AI Agent) · Utobit",
    "year": "년", "month_unit": "월", "day_unit": "일",
    "weekday_names": ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"],
    "export_header": "WorkTimer 작업 기록",
    "export_time": "내보내기:",
    "no_data": "기록 없음",
    "table_date": "날짜", "table_wd": "요일", "table_time": "작업시간", "table_note": "메모",
    "autostart": "시작 시 자동 실행",
    "icon_label": "앱 아이콘",
    "icon_pick_btn": "아이콘 변경",
    "icon_picker_title": "앱 아이콘 선택",
    "icon_picker_desc": "앱의 아이콘 색상을 선택하세요.",
    "icon_names": ICON_NAMES_KO,
    "color_section": "색상 설정",
    "color_active": "활동 구간 색상",
    "color_clock_bg": "시계 배경 색상",
    "color_center": "중앙점 색상",
    "color_reset": "기본값으로 초기화",
    "export_range": "기간",
    "theme_label": "테마",
    "theme_light": "라이트",
    "theme_dark": "다크",
    "expand_btn": "펼치기",
    "collapse_btn": "접기",
}

LANG_EN = {
    "prev": "‹", "today": "Today", "next": "›",
    "export": "Export", "settings": "Settings",
    "year_view": "Year View", "month_view": "Month",
    "back": "← Month",
    "total_month": "Monthly total",
    "total_day": "Work time",
    "total": "Total",
    "intervals": "Sessions",
    "no_record": "No records yet.",
    "memo": "Memo",
    "memo_save": "Save",
    "export_title": "Export Records",
    "export_format": "Select format",
    "fmt_simple": "Simple (date·time)",
    "fmt_table": "Table (Notion/Docs)",
    "fmt_detail": "Detail (with sessions)",
    "export_done": "Export Done",
    "export_saved": "Saved:\n{}",
    "export_err": "Error",
    "reset_title": "Reset Data",
    "reset_confirm": "All work records will be deleted.\nAre you sure?",
    "reset_done": "Reset complete",
    "settings_title": "Settings",
    "lang_label": "Language",
    "idle_label": "Idle threshold (min)",
    "data_path": "Open data folder",
    "reset_btn": "Reset all data",
    "weekdays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    "made_by": "Made by Jin (AI Agent) · Utobit",
    "year": "", "month_unit": "", "day_unit": "",
    "weekday_names": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "export_header": "WorkTimer Records",
    "export_time": "Exported:",
    "no_data": "No records",
    "table_date": "Date", "table_wd": "Day", "table_time": "Hours", "table_note": "Memo",
    "autostart": "Run at startup",
    "icon_label": "App icon",
    "icon_pick_btn": "Change icon",
    "icon_picker_title": "Choose App Icon",
    "icon_picker_desc": "Select the icon color for the app.",
    "icon_names": ICON_NAMES_EN,
    "color_section": "Color Settings",
    "color_active": "Active interval color",
    "color_clock_bg": "Clock background",
    "color_center": "Center dot color",
    "color_reset": "Reset to defaults",
    "export_range": "Period",
    "theme_label": "Theme",
    "theme_light": "Light",
    "theme_dark": "Dark",
    "expand_btn": "Expand",
    "collapse_btn": "Collapse",
}

LANGUAGES = {"한국어": LANG_KO, "English": LANG_EN}

ICON_STYLES: dict[str, dict[str, tuple]] = {
    "blue":   {"bg": (224,242,254,255), "outline": (2,132,199,255),   "active": (253,186,116,255), "hand": (31,41,55,255)},
    "dark":   {"bg": (30, 64,175,255),  "outline": (147,197,253,255), "active": (251,191, 36,255), "hand": (255,255,255,255)},
    "green":  {"bg": (209,250,229,255), "outline": (5,150,105,255),   "active": (52,211,153,255),  "hand": (31,41,55,255)},
    "purple": {"bg": (237,233,254,255), "outline": (124,58,237,255),  "active": (196,181,253,255), "hand": (31,41,55,255)},
    "warm":   {"bg": (255,237,213,255), "outline": (234,88, 12,255),  "active": (253,186,116,255), "hand": (31,41,55,255)},
}


# ── 설정 파일 ───────────────────────────────────────────
def load_settings() -> dict:
    try:
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_settings(settings: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def set_autostart(enable: bool) -> None:
    if not getattr(sys, "frozen", False):
        return
    exe = f'"{sys.executable}"'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, exe)
        else:
            try:
                winreg.DeleteValue(key, APP_REG_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def get_autostart() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_REG_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


def _rgba_to_hex(rgba: tuple) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgba[:3])


def get_icon_files() -> list[Path]:
    if not ICONS_DIR.exists():
        return []
    files = list(ICONS_DIR.glob("*.png")) + list(ICONS_DIR.glob("*.ico"))
    return sorted(files, key=lambda p: p.name)


# ── 유틸 ────────────────────────────────────────────────
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32


def now_local() -> datetime:
    return datetime.now().replace(microsecond=0)


def get_idle_seconds() -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not _user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    return max(0.0, (_kernel32.GetTickCount64() - info.dwTime) / 1000.0)


def date_key(value: date) -> str:
    return value.isoformat()


def seconds_from_midnight(value: datetime) -> int:
    return value.hour * 3600 + value.minute * 60 + value.second


def seconds_to_hhmm(seconds: int) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"


def split_interval_by_day(start: datetime, end: datetime) -> list[tuple[str, int, int]]:
    if end <= start:
        return []
    pieces: list[tuple[str, int, int]] = []
    cursor = start
    while cursor.date() < end.date():
        midnight = datetime.combine(cursor.date() + timedelta(days=1), dt_time.min)
        pieces.append((date_key(cursor.date()), seconds_from_midnight(cursor), 24 * 3600))
        cursor = midnight
    pieces.append((date_key(cursor.date()), seconds_from_midnight(cursor), seconds_from_midnight(end)))
    return [(d, s, e) for d, s, e in pieces if e > s]


def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    clean = sorted((max(0, int(s)), min(24 * 3600, int(e))) for s, e in intervals if e > s)
    if not clean:
        return []
    merged: list[list[int]] = [[clean[0][0], clean[0][1]]]
    for start, end in clean[1:]:
        last = merged[-1]
        if start <= last[1] + 1:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return merged


# ── 커스텀 버튼 ─────────────────────────────────────────
class RoundedButton(Canvas):
    def __init__(self, parent, text, command=None, width=100, height=30,
                 radius=14, dark=False, ghost=False, font_size=9, **kwargs):
        bg = parent.cget("bg") if hasattr(parent, "cget") else PALETTE["bg"]
        super().__init__(parent, width=width, height=height,
                         bg=bg, highlightthickness=0, cursor="hand2")
        self._text = text
        self._command = command
        self._r = min(radius, height // 2, width // 2)
        self._width = width
        self._height = height
        self._dark = dark
        self._ghost = ghost
        self._font_size = font_size
        self._hover = False
        self._parent_bg = bg
        self._draw()
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))

    def _set_hover(self, val: bool) -> None:
        self._hover = val
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w, h, r = self._width, self._height, self._r

        if self._dark:
            fill = PALETTE["btn_dark_hover"] if self._hover else PALETTE["btn_dark_bg"]
            fg = PALETTE["btn_dark_fg"]
            border_w = 0
            border_c = fill
        elif self._ghost:
            fill = PALETTE["btn_bg_hover"] if self._hover else self._parent_bg
            fg = PALETTE["btn_fg"]
            border_w = 1
            border_c = PALETTE["btn_border"]
        else:
            fill = PALETTE["btn_bg_hover"] if self._hover else PALETTE["btn_bg"]
            fg = PALETTE["btn_fg"]
            border_w = 1
            border_c = PALETTE["btn_border"]

        # smooth=True polygon → 진짜 둥근 사각형
        pts = [
            r, 0,   w - r, 0,
            w, 0,   w, r,
            w, h - r, w, h,
            w - r, h, r, h,
            0, h,   0, h - r,
            0, r,   0, 0,
            r, 0,
        ]
        self.create_polygon(pts, smooth=True,
                            fill=fill, outline=border_c, width=border_w)
        self.create_text(w // 2, h // 2, text=self._text, fill=fg,
                         font=("Segoe UI", self._font_size))

    def configure(self, **kwargs):
        if "text" in kwargs:
            self._text = kwargs.pop("text")
            self._draw()
        super().configure(**kwargs)

    def _click(self, _event) -> None:
        if self._command:
            self._command()


# ── 데이터 ──────────────────────────────────────────────
def prepare_data_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists() and LEGACY_DATA_FILE.exists():
        try:
            DATA_FILE.write_text(LEGACY_DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            (BACKUP_DIR / f"migrated-{stamp}.json").write_text(
                DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass


def backup_data_file(reason: str = "auto") -> None:
    if not DATA_FILE.exists():
        return
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d")
        target = BACKUP_DIR / f"work_log-{reason}-{stamp}.json"
        if not target.exists():
            target.write_text(DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass


@dataclass
class WorkLog:
    days: dict[str, list[list[int]]]
    notes: dict[str, str]
    merges: dict[str, list[list[int]]]  # date_key → [[gap_start, gap_end], ...]
    ranges: list[dict]                  # [{"start":"YYYY-MM-DD","end":"YYYY-MM-DD","label":"..."}]

    @classmethod
    def load(cls) -> "WorkLog":
        prepare_data_storage()
        if not DATA_FILE.exists():
            return cls(days={}, notes={}, merges={}, ranges=[])
        try:
            payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            days = payload.get("days", {})
            if not isinstance(days, dict):
                return cls(days={}, notes={}, merges={}, ranges=[])
            parsed: dict[str, list[list[int]]] = {}
            for key, value in days.items():
                if isinstance(value, list):
                    parsed[key] = merge_intervals(value)
            notes = payload.get("notes", {})
            if not isinstance(notes, dict):
                notes = {}
            merges_raw = payload.get("merges", {})
            merges: dict[str, list[list[int]]] = (
                {k: v for k, v in merges_raw.items() if isinstance(v, list)}
                if isinstance(merges_raw, dict) else {}
            )
            ranges_raw = payload.get("ranges", [])
            ranges = ranges_raw if isinstance(ranges_raw, list) else []
            return cls(days=parsed, notes={str(k): str(v) for k, v in notes.items()},
                       merges=merges, ranges=ranges)
        except Exception:
            backup = DATA_FILE.with_suffix(f".broken-{int(time.time())}.json")
            DATA_FILE.replace(backup)
            return cls(days={}, notes={}, merges={}, ranges=[])

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            backup_data_file("before-save")
        payload = {
            "schema": 1,
            "updated_at": now_local().isoformat(),
            "idle_grace_seconds": IDLE_GRACE_SECONDS,
            "days": self.days,
            "notes": self.notes,
            "merges": self.merges,
            "ranges": self.ranges,
        }
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(DATA_FILE)

    def add_interval(self, start: datetime, end: datetime) -> None:
        changed = False
        for day, s, e in split_interval_by_day(start, end):
            current = self.days.setdefault(day, [])
            before = list(current)
            current.append([s, e])
            self.days[day] = merge_intervals(current)
            changed = changed or before != self.days[day]
        if changed:
            self.save()

    def intervals_for(self, day: date) -> list[list[int]]:
        return self.days.get(date_key(day), [])

    def total_seconds_for(self, day: date) -> int:
        return sum(max(0, e - s) for s, e in self.intervals_for(day))

    def note_for(self, day: date) -> str:
        return self.notes.get(date_key(day), "")

    def set_note_for(self, day: date, note: str) -> None:
        key = date_key(day)
        note = note.strip()
        if note:
            self.notes[key] = note
        else:
            self.notes.pop(key, None)
        self.save()

    def reset(self) -> None:
        backup_data_file("before-reset")
        self.days.clear()
        self.notes.clear()
        self.merges.clear()
        self.ranges.clear()
        self.save()

    def merges_for(self, day: date) -> list[list[int]]:
        return self.merges.get(date_key(day), [])

    def add_merge(self, day: date, gap_start: int, gap_end: int) -> None:
        key = date_key(day)
        gaps = self.merges.setdefault(key, [])
        pair = [gap_start, gap_end]
        if pair not in gaps:
            gaps.append(pair)
        self.save()

    def remove_merge(self, day: date, gap_start: int, gap_end: int) -> None:
        key = date_key(day)
        self.merges[key] = [g for g in self.merges.get(key, [])
                             if g != [gap_start, gap_end]]
        if not self.merges.get(key):
            self.merges.pop(key, None)
        self.save()

    def ranges_for_month(self, year: int, month: int) -> list[dict]:
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        result = []
        for r in self.ranges:
            try:
                rs = date.fromisoformat(r["start"])
                re = date.fromisoformat(r["end"])
                if rs <= last and re >= first:
                    result.append({**r, "start_date": rs, "end_date": re})
            except Exception:
                pass
        return result

    def add_range(self, start: date, end: date, label: str) -> None:
        self.ranges.append({"start": start.isoformat(), "end": end.isoformat(),
                             "label": label})
        self.save()

    def remove_range(self, start: date, end: date) -> None:
        self.ranges = [r for r in self.ranges
                       if not (r.get("start") == start.isoformat()
                               and r.get("end") == end.isoformat())]
        self.save()


# ── 트래커 ──────────────────────────────────────────────
class ActivityTracker:
    def __init__(self, log: WorkLog, on_change,
                 recovered_start: "datetime | None" = None) -> None:
        self.log = log
        self.on_change = on_change
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._active_start: datetime | None = recovered_start
        self._recorded_until: datetime | None = None
        self._last_activity_at: datetime | None = recovered_start
        self._last_checkpoint_write: datetime | None = None

    def _write_checkpoint(self) -> None:
        if self._active_start is None:
            return
        try:
            CHECKPOINT_FILE.write_text(
                json.dumps({"active_start": self._active_start.isoformat()},
                           ensure_ascii=False),
                encoding="utf-8")
        except Exception:
            pass

    def _clear_checkpoint(self) -> None:
        try:
            CHECKPOINT_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    @staticmethod
    def recover_from_checkpoint(log: WorkLog) -> "datetime | None":
        """체크포인트에서 active_start를 복구해 반환. 자정 경계를 넘은 경우 어제분만 커밋."""
        if not CHECKPOINT_FILE.exists():
            return None
        try:
            data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
            start_str = data.get("active_start")
            if not start_str:
                return None
            active_start = datetime.fromisoformat(start_str)
            today = now_local().date()
            if active_start.date() < today:
                # 자정을 넘긴 경우 — 어제분만 커밋, 오늘은 트래커가 새로 시작
                midnight = datetime.combine(today, dt_time.min)
                log.add_interval(active_start, midnight)
                return None
            return active_start  # 오늘 세션 → 트래커에서 이어서 기록
        except Exception:
            return None
        finally:
            try:
                CHECKPOINT_FILE.unlink(missing_ok=True)
            except Exception:
                pass

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="worktimer-activity", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._active_start is not None:
            self.log.add_interval(self._active_start, now_local())
            self.on_change()
        self._clear_checkpoint()

    @property
    def current_interval(self) -> tuple[datetime, datetime] | None:
        if self._active_start is None:
            return None
        return (self._active_start, now_local())

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._tick()
            self._stop.wait(POLL_SECONDS)

    def _tick(self) -> None:
        current = now_local()
        idle = get_idle_seconds()
        is_working = idle <= IDLE_GRACE_SECONDS

        if is_working:
            last_input = current - timedelta(seconds=idle)
            if self._active_start is None:
                self._active_start = last_input
                self._recorded_until = None
            elif self._active_start.date() < current.date():
                # 자정 경계: 어제까지 저장, 오늘은 current(오늘 날짜 확정)로 재시작
                midnight = datetime.combine(current.date(), dt_time.min)
                self.log.add_interval(self._active_start, midnight)
                self._active_start = current
                self._recorded_until = None
                self._clear_checkpoint()
            # 60초마다 현재 구간을 체크포인트로 저장 (강제 종료 시 복구용)
            if (self._last_checkpoint_write is None or
                    (current - self._last_checkpoint_write).total_seconds() >= 60):
                self._write_checkpoint()
                self._last_checkpoint_write = current
            self._last_activity_at = last_input
            self.on_change()
            return

        if self._active_start is not None:
            # Always resolve midnight crossing, even while idle
            if self._active_start.date() < current.date():
                midnight = datetime.combine(current.date(), dt_time.min)
                self.log.add_interval(self._active_start, midnight)
                self._active_start = None
                self._recorded_until = None
                self._last_activity_at = None
                self._clear_checkpoint()
                self.on_change()
                return
            if self._last_activity_at is not None:
                grace_end = self._last_activity_at + timedelta(seconds=IDLE_GRACE_SECONDS)
                if current >= grace_end:
                    self.log.add_interval(self._active_start, self._last_activity_at)
                    self.on_change()
                    self._active_start = None
                    self._recorded_until = None
                    self._last_activity_at = None
                    self._clear_checkpoint()


# ── 메인 앱 ─────────────────────────────────────────────
class WorkTimerApp:
    def __init__(self, start_minimized: bool = False) -> None:
        self.log = WorkLog.load()
        _recovered_start = ActivityTracker.recover_from_checkpoint(self.log)
        self._settings = load_settings()
        self._lang_name = self._settings.get("lang", "한국어")
        self._L = LANGUAGES.get(self._lang_name, LANG_KO)
        self._icon_style = self._settings.get("icon_style", "")
        self._start_minimized = start_minimized
        self._first_launch = not self._settings.get("icon_style")

        # Apply custom palette colors from settings
        for skey, pkey in [("color_active", "active"), ("color_clock_bg", "clock"),
                            ("color_center", "center")]:
            val = self._settings.get(skey, "")
            if val and len(val) == 7 and val.startswith("#"):
                PALETTE[pkey] = val

        # Drag/merge state for day-view clock
        self._merge_drag_active: bool = False
        self._drag_interval_idx: int = -1
        self._drag_target_idx: int = -1
        self._press_x: int = 0
        self._press_y: int = 0
        self._day_clock_cx: float = 0.0
        self._day_clock_cy: float = 0.0
        self._day_clock_r: float = 0.0
        self._day_intervals: list[list[int]] = []

        # Calendar range selection state
        self._cal_press_day: date | None = None
        self._cal_drag_end: date | None = None
        self._cal_drag_mode: bool = False
        self._range_entry_winid: int | None = None
        self._range_sel_start: date | None = None
        self._range_sel_end: date | None = None

        # Theme + expand state
        self._theme = self._settings.get("theme", "light")
        if self._theme == "dark":
            PALETTE.update(PALETTE_DARK)
        self._expanded: bool = False

        self.root = Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1180x760")
        self.root.minsize(940, 620)
        self.root.configure(bg=PALETTE["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self._tk_icon = None
        self._pil_icon = None
        self._set_window_icon()

        today = date.today()
        self.year = today.year
        self.month = today.month
        self.view = "month"  # month | day | year
        self.year_year = today.year
        self.detail_day: date | None = None
        self._day_hitboxes: list[tuple[float, float, float, float, date]] = []
        self._year_month_hitboxes: list[tuple[float, float, float, float, int, int]] = []
        self._detail_back_hitbox: tuple[float, float, float, float] | None = None
        self._embedded_widgets: list[tk.Widget] = []
        self._redraw_pending = False
        self._tray_icon = None

        self.tracker = ActivityTracker(self.log, self.schedule_redraw,
                                       recovered_start=_recovered_start)
        self._build_ui()
        if self._icon_style:
            self._apply_icon(self._icon_style, save=False)
        if self._first_launch:
            self.root.after(600, self.open_icon_picker)

    # ── UI 구성 ────────────────────────────────────────
    def _build_ui(self) -> None:
        self._header_frame: Frame | None = None
        self._footer_label: Label | None = None
        self.canvas = None  # 파괴된 위젯 참조를 먼저 초기화 (_build_header before= 오류 방지)
        self._build_header()

        # 캔버스
        self.canvas = Canvas(self.root, bg=PALETTE["bg"], highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=True, padx=18, pady=(0, 4))
        self.canvas.bind("<Configure>", lambda _: self.schedule_redraw())
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # 푸터
        self._footer_label = Label(self.root, text=self._L["made_by"],
                                    bg=PALETTE["bg"], fg=PALETTE["muted"],
                                    font=("Malgun Gothic", 7))
        self._footer_label.pack(pady=(0, 5))

    def _build_header(self) -> None:
        if self._header_frame is not None:
            self._header_frame.destroy()
        header = Frame(self.root, bg=PALETTE["bg"], height=66)
        header.pack_propagate(False)  # 높이 고정 → place 자식 사용 가능
        if hasattr(self, "canvas") and self.canvas is not None:
            header.pack(fill=X, padx=18, pady=(14, 6), before=self.canvas)
        else:
            header.pack(fill=X, padx=18, pady=(14, 6))
        self._header_frame = header

        # ── 중앙 (place relx=0.5 → 완전 수평 중앙) ────
        center_f = Frame(header, bg=PALETTE["bg"])
        center_f.place(relx=0.5, y=0, anchor="n")

        nav_row = Frame(center_f, bg=PALETTE["bg"])
        nav_row.pack()

        self._btn_prev = RoundedButton(nav_row, self._L["prev"], self.prev_month,
                                       width=32, height=30, radius=15, ghost=True, font_size=15)
        self._btn_prev.pack(side=LEFT, padx=(0, 10))

        self.title_label = Label(nav_row, bg=PALETTE["bg"], fg=PALETTE["text"],
                                  font=("Malgun Gothic", 16, "bold"), cursor="hand2")
        self.title_label.pack(side=LEFT)
        self.title_label.bind("<Button-1>", lambda _: self._title_click())

        self._btn_next = RoundedButton(nav_row, self._L["next"], self.next_month,
                                       width=32, height=30, radius=15, ghost=True, font_size=15)
        self._btn_next.pack(side=LEFT, padx=(10, 0))

        self.summary_label = Label(center_f, bg=PALETTE["bg"], fg=PALETTE["muted"],
                                    font=("Malgun Gothic", 9))
        self.summary_label.pack(pady=(3, 0))

        # ── 우상단 (place relx=1.0 → 완전 우측) 2×2 ──
        # 연간보기 | 설정
        # 펼치기   | 기록내보내기
        right_f = Frame(header, bg=PALETTE["bg"])
        right_f.place(relx=1.0, y=0, anchor="ne")

        bw, bh, gap = 80, 26, 3

        self._btn_year = RoundedButton(right_f, self._L["year_view"], self.toggle_year_view,
                                       width=bw, height=bh, radius=12)
        self._btn_year.grid(row=0, column=0, padx=(0, gap), pady=(0, gap))

        self._btn_settings = RoundedButton(right_f, self._L["settings"], self.open_settings,
                                           width=bw, height=bh, radius=12, ghost=True)
        self._btn_settings.grid(row=0, column=1, pady=(0, gap))

        self._btn_expand = RoundedButton(right_f,
                                          self._L.get("collapse_btn", "접기") if self._expanded
                                          else self._L.get("expand_btn", "펼치기"),
                                          self.toggle_expand,
                                          width=bw, height=bh, radius=12)
        self._btn_expand.grid(row=1, column=0, padx=(0, gap))

        self._btn_export = RoundedButton(right_f, self._L["export"], self.open_export,
                                         width=bw, height=bh, radius=12)
        self._btn_export.grid(row=1, column=1)

    def _apply_theme(self) -> None:
        """Tear down and rebuild entire UI with new PALETTE."""
        for w in self.root.winfo_children():
            w.destroy()
        self._embedded_widgets = []
        self._header_frame = None
        self._footer_label = None
        self.root.configure(bg=PALETTE["bg"])
        self._build_ui()
        self.redraw()
        self._set_window_icon()

    def _title_click(self) -> None:
        if self.view == "day":
            self.close_day_detail()
        else:
            self.go_today()

    # ── 언어 갱신 ──────────────────────────────────────
    def _apply_lang(self) -> None:
        self._L = LANGUAGES[self._lang_name]
        self._build_header()
        self.redraw()

    # ── 네비게이션 ────────────────────────────────────
    def prev_month(self) -> None:
        if self.view == "year":
            self.year_year -= 1
        elif self.view == "day" and self.detail_day is not None:
            self.open_day_detail(self.detail_day - timedelta(days=1))
            return
        else:
            self.detail_day = None
            if self.view not in ("expand",):
                self.view = "month"
            if self.month == 1:
                self.year -= 1; self.month = 12
            else:
                self.month -= 1
        self.redraw()

    def next_month(self) -> None:
        if self.view == "year":
            self.year_year += 1
        elif self.view == "day" and self.detail_day is not None:
            self.open_day_detail(self.detail_day + timedelta(days=1))
            return
        else:
            self.detail_day = None
            if self.view not in ("expand",):
                self.view = "month"
            if self.month == 12:
                self.year += 1; self.month = 1
            else:
                self.month += 1
        self.redraw()

    def go_today(self) -> None:
        today = date.today()
        self.year = today.year
        self.month = today.month
        self.year_year = today.year
        self.detail_day = None
        self.view = "month"
        self.redraw()

    def toggle_year_view(self) -> None:
        if self.view == "year":
            self.view = "month"
        else:
            self.view = "year"
            self.year_year = self.year
        self.detail_day = None
        self.redraw()

    def toggle_expand(self) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            sw = self.root.winfo_screenwidth()
            self.root.geometry(f"{min(sw - 60, 2600)}x760")
            self.root.minsize(1800, 620)
            self.view = "expand"
        else:
            self.root.geometry("1180x760")
            self.root.minsize(940, 620)
            self.view = "month"
        self._build_header()
        self.detail_day = None
        self.redraw()

    def open_day_detail(self, day: date) -> None:
        self.detail_day = day
        self.year = day.year
        self.month = day.month
        self.view = "day"
        self.redraw()

    def close_day_detail(self) -> None:
        self.detail_day = None
        self.view = "month"
        self.redraw()

    # ── 클릭/드래그 핸들러 ────────────────────────────
    def _on_canvas_press(self, event) -> None:
        self._press_x = event.x
        self._press_y = event.y
        self._merge_drag_active = False
        self._drag_interval_idx = -1
        self._drag_target_idx = -1

        if self.view == "day":
            # Back button
            if self._detail_back_hitbox:
                x1, y1, x2, y2 = self._detail_back_hitbox
                if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                    self.close_day_detail()
                    return
            # Drag-to-merge on clock
            if self._is_on_clock(event.x, event.y):
                sec = self._clock_pos_to_sec(event.x, event.y)
                idx = self._sec_to_interval_idx(sec)
                if idx >= 0:
                    self._drag_interval_idx = idx
                    self._merge_drag_active = True
            return

        if self.view == "year":
            for x1, y1, x2, y2, yr, mo in self._year_month_hitboxes:
                if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                    self.year = yr; self.month = mo
                    self.view = "month"
                    self.detail_day = None
                    self.redraw()
                    return
            return

        # Month view: record press day (detail opens on release if no drag)
        self._cal_press_day = None
        self._cal_drag_end = None
        self._cal_drag_mode = False
        for x1, y1, x2, y2, day in self._day_hitboxes:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self._cal_press_day = day
                return

    def _on_canvas_drag(self, event) -> None:
        # Day view: clock merge drag
        if self._merge_drag_active and self.view == "day":
            dx = event.x - self._press_x
            dy = event.y - self._press_y
            if dx * dx + dy * dy < 64:
                return
            sec = self._clock_pos_to_sec(event.x, event.y)
            new_tgt = self._sec_to_interval_idx(sec)
            if new_tgt != self._drag_interval_idx and new_tgt >= 0:
                if new_tgt != self._drag_target_idx:
                    self._drag_target_idx = new_tgt
                    self._draw_day_detail_view()
            elif new_tgt == self._drag_interval_idx and self._drag_target_idx >= 0:
                self._drag_target_idx = -1
                self._draw_day_detail_view()
            return

        # Month view: calendar range selection drag
        if self.view == "month" and self._cal_press_day is not None:
            dx = event.x - self._press_x
            dy = event.y - self._press_y
            if dx * dx + dy * dy < 64:
                return
            self._cal_drag_mode = True
            for x1, y1, x2, y2, day in self._day_hitboxes:
                if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                    if day != self._cal_drag_end:
                        self._cal_drag_end = day
                        self._draw_calendar()
                    break

    def _on_canvas_release(self, event) -> None:
        # Day view: clock merge
        if self._merge_drag_active:
            dx = event.x - self._press_x
            dy = event.y - self._press_y
            if (dx * dx + dy * dy) >= 64 and self._drag_interval_idx >= 0 and self._drag_target_idx >= 0:
                self._do_merge(self._drag_interval_idx, self._drag_target_idx)
            self._merge_drag_active = False
            self._drag_interval_idx = -1
            self._drag_target_idx = -1
            self.redraw()
            return

        # Month view
        if self.view == "month":
            if self._cal_drag_mode and self._cal_press_day and self._cal_drag_end and \
                    self._cal_drag_end != self._cal_press_day:
                # Range drag complete → show label input
                lo = min(self._cal_press_day, self._cal_drag_end)
                hi = max(self._cal_press_day, self._cal_drag_end)
                self._range_sel_start = lo
                self._range_sel_end = hi
                self._show_range_input(lo, hi)
            else:
                # Plain click → open day detail
                if self._cal_press_day:
                    self.open_day_detail(self._cal_press_day)
            self._cal_press_day = None
            self._cal_drag_end = None
            self._cal_drag_mode = False

    def _is_on_clock(self, x: float, y: float) -> bool:
        if self._day_clock_r <= 0:
            return False
        return (x - self._day_clock_cx) ** 2 + (y - self._day_clock_cy) ** 2 <= self._day_clock_r ** 2

    def _clock_pos_to_sec(self, x: float, y: float) -> int:
        angle_deg = math.degrees(math.atan2(self._day_clock_cy - y, x - self._day_clock_cx))
        return int(((90 - angle_deg) % 360) / 360 * 86400)

    def _sec_to_interval_idx(self, sec: int) -> int:
        for i, (s, e) in enumerate(self._day_intervals):
            if s <= sec <= e:
                return i
        return -1

    def _do_merge(self, idx1: int, idx2: int) -> None:
        if self.detail_day is None or not self._day_intervals:
            return
        a, b = sorted([idx1, idx2])
        if b >= len(self._day_intervals) or b != a + 1:
            return
        e1 = self._day_intervals[a][1]
        s2 = self._day_intervals[b][0]
        if e1 < s2:
            self.log.add_merge(self.detail_day, e1, s2)

    def _group_intervals_with_merges(self, day: date,
                                      intervals: list[list[int]]) -> list[dict]:
        gap_set = {(g[0], g[1]) for g in self.log.merges_for(day)}
        groups: list[dict] = []
        i = 0
        while i < len(intervals):
            group_ivs = [intervals[i]]
            group_gaps: list[tuple[int, int]] = []
            while i + 1 < len(intervals):
                e1 = intervals[i][1]
                s2 = intervals[i + 1][0]
                if (e1, s2) in gap_set:
                    group_gaps.append((e1, s2))
                    i += 1
                    group_ivs.append(intervals[i])
                else:
                    break
            groups.append({"intervals": group_ivs,
                           "merged": len(group_ivs) > 1,
                           "gaps": group_gaps})
            i += 1
        return groups

    def _show_range_input(self, start: date, end: date) -> None:
        """Inline borderless text entry overlaid on the calendar after range drag."""
        # Find the first row of the selected range to place the entry
        cells = [(x1, y1, x2, y2, d) for x1, y1, x2, y2, d in self._day_hitboxes
                 if start <= d <= end]
        if not cells:
            return
        cells.sort(key=lambda c: (c[1], c[0]))
        first_row_y = cells[0][1]
        row0 = [c for c in cells if c[1] == first_row_y]
        row0.sort(key=lambda c: c[0])
        ex1, ey1, ex2, ey2 = row0[0][0], row0[0][1], row0[-1][2], row0[-1][3]
        mid_x = (ex1 + ex2) / 2
        mid_y = (ey1 + ey2) / 2

        entry_var = StringVar()
        entry = tk.Entry(self.canvas, textvariable=entry_var,
                         font=("Malgun Gothic", 9, "bold"),
                         relief="flat", bd=0, bg="#bfdbfe", fg="#1e3a8a",
                         highlightthickness=0, justify="center",
                         insertbackground="#1e3a8a")
        self._embedded_widgets.append(entry)

        win_id = self.canvas.create_window(mid_x, mid_y, window=entry,
                                            width=ex2 - ex1 - 12, height=22)
        self._range_entry_winid = win_id
        entry.focus_set()

        def _save(evt=None):
            label = entry_var.get().strip()
            if label:
                self.log.add_range(start, end, label)
            self._range_sel_start = None
            self._range_sel_end = None
            self._range_entry_winid = None
            self.redraw()

        def _cancel(evt=None):
            self._range_sel_start = None
            self._range_sel_end = None
            self._range_entry_winid = None
            self.redraw()

        entry.bind("<Return>", _save)
        entry.bind("<Escape>", _cancel)
        # No FocusOut — it causes spurious saves during Korean IME composition

    def _draw_range_overlay(self) -> None:
        """Draw stored range labels + current drag selection onto the calendar canvas."""
        # Draw stored ranges for this month
        for r in self.log.ranges_for_month(self.year, self.month):
            self._draw_range_band(r["start_date"], r["end_date"], r["label"],
                                   "#bfdbfe", "#2563eb")

        # Draw in-progress drag selection
        if self._cal_drag_mode and self._cal_press_day and self._cal_drag_end:
            lo = min(self._cal_press_day, self._cal_drag_end)
            hi = max(self._cal_press_day, self._cal_drag_end)
            self._draw_range_band(lo, hi, "", "#e0f2fe", "#0284c7", preview=True)

        # Draw confirmed selection (while showing input)
        if self._range_sel_start and self._range_sel_end:
            self._draw_range_band(self._range_sel_start, self._range_sel_end,
                                   "", "#bfdbfe", "#2563eb", preview=True)

    def _draw_range_band(self, start: date, end: date, label: str,
                          fill: str, color: str, preview: bool = False) -> None:
        cells = [(x1, y1, x2, y2, d) for x1, y1, x2, y2, d in self._day_hitboxes
                 if start <= d <= end]
        if not cells:
            return
        rows: dict[float, list] = {}
        for c in cells:
            rows.setdefault(c[1], []).append(c)
        first_row_y = min(rows.keys())
        inset = 3
        for ry, rcells in sorted(rows.items()):
            rcells.sort(key=lambda c: c[0])
            x1r = rcells[0][0] + inset
            y1r = rcells[0][1] + inset
            x2r = rcells[-1][2] - inset
            y2r = rcells[-1][3] - inset
            # Transparent fill: only the border is drawn so cell content remains visible
            self.canvas.create_rectangle(x1r, y1r, x2r, y2r,
                                          fill="", outline=color,
                                          width=3 if not preview else 2)
            # Draw label text in the first row only
            if label and ry == first_row_y:
                mid_x = (x1r + x2r) / 2
                mid_y = (y1r + y2r) / 2
                self.canvas.create_text(mid_x, mid_y, text=label, fill=color,
                                         font=("Malgun Gothic", 8, "bold"))
                # Remove (✕) handle — small label at top-right of band
                def _rm(evt=None, s=start, e=end):
                    self.log.remove_range(s, e)
                    self.redraw()
                tag = f"range_{start}_{end}"
                self.canvas.create_text(x2r - 6, y1r + 8, text="✕", fill=color,
                                         font=("Malgun Gothic", 7), tags=(tag,))
                self.canvas.tag_bind(tag, "<Button-1>", _rm)

    # ── 리드로우 ──────────────────────────────────────
    def schedule_redraw(self) -> None:
        if self._redraw_pending:
            return
        self._redraw_pending = True
        self.root.after(300, self._scheduled_redraw)

    def _scheduled_redraw(self) -> None:
        self._redraw_pending = False
        self.redraw()

    def redraw(self) -> None:
        try:
            if self.view == "year":
                self._draw_year()
            elif self.view == "day":
                self._draw_day_detail_view()
            elif self.view == "expand":
                self._draw_expand()
            else:
                self._draw_calendar()
        except TclError:
            pass

    # ── 표시 인터벌 (실시간 포함) ──────────────────────
    def _get_display_intervals(self, day: date) -> list[list[int]]:
        intervals = list(self.log.intervals_for(day))
        if day == date.today():
            ci = self.tracker.current_interval
            if ci and ci[1] > ci[0]:
                for d_key, s, e in split_interval_by_day(ci[0], ci[1]):
                    if d_key == date_key(day) and e > s:
                        intervals = merge_intervals(intervals + [[s, e]])
        # Defensive clamp: never allow arcs beyond [0, 86400]
        return [[max(0, s), min(86400, e)] for s, e in intervals if e > s]

    def _get_display_total(self, day: date) -> int:
        return sum(max(0, e - s) for s, e in self._get_display_intervals(day))

    # ── 월간 뷰 ───────────────────────────────────────
    def _draw_calendar(self) -> None:
        self._clear_embedded_widgets()
        self.canvas.delete("all")
        self._day_hitboxes = []
        self._detail_back_hitbox = None
        width = max(900, self.canvas.winfo_width())
        height = max(560, self.canvas.winfo_height())
        L = self._L

        month_name = f"{self.year}{L['year']} {self.month}{L['month_unit']}"
        self.title_label.configure(text=month_name)

        month_days = calendar.monthrange(self.year, self.month)[1]
        total = sum(self._get_display_total(date(self.year, self.month, d))
                    for d in range(1, month_days + 1))
        self.summary_label.configure(text=f"{L['total_month']}  {seconds_to_hhmm(total)}")

        col_count = 7
        header_h = 34
        gap = 6
        cell_w = (width - gap * (col_count - 1)) / col_count
        weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(self.year, self.month)
        row_count = len(weeks)
        cell_h = (height - header_h - gap * (row_count - 1)) / row_count

        bold = tkfont.Font(family="Malgun Gothic", size=10, weight="bold")
        small = tkfont.Font(family="Malgun Gothic", size=8)
        today = date.today()

        for col, label in enumerate(L["weekdays"]):
            x = col * (cell_w + gap)
            self.canvas.create_text(x + cell_w / 2, 15, text=label,
                                     fill=PALETTE["muted"], font=bold)

        for row, week in enumerate(weeks):
            for col, day in enumerate(week):
                x = col * (cell_w + gap)
                y = header_h + row * (cell_h + gap)
                self._day_hitboxes.append((x, y, x + cell_w, y + cell_h, day))
                is_cur = day.month == self.month
                fill = PALETTE["panel"] if is_cur else (PALETTE["bg"])
                outline = PALETTE["today"] if day == today else PALETTE["line"]
                self.canvas.create_rectangle(x, y, x + cell_w, y + cell_h,
                                              fill=fill, outline=outline,
                                              width=2 if day == today else 1)
                self.canvas.create_text(x + 8, y + 8, text=str(day.day), anchor="nw",
                                         fill=PALETTE["text"] if is_cur else PALETTE["muted"],
                                         font=bold)
                intervals = self._get_display_intervals(day)
                total_s = sum(max(0, e - s) for s, e in intervals)  # 동일 스냅샷 재사용
                radius = max(24, min(cell_w * 0.32, cell_h * 0.28))
                cx, cy = x + cell_w / 2, y + cell_h / 2 - 4
                alpha = PALETTE["clock"] if is_cur else "#e5e7eb"
                self._draw_clock(cx, cy, radius, intervals, alpha)
                self.canvas.create_text(x + cell_w / 2, y + cell_h - 14,
                                         text=seconds_to_hhmm(total_s),
                                         fill=PALETTE["active_dark"] if total_s else PALETTE["muted"],
                                         font=small)

        # Range labels overlay (drawn last so they appear on top)
        self._draw_range_overlay()

    # ── 펼치기 뷰 (3개월) ────────────────────────────
    def _draw_expand(self) -> None:
        self._clear_embedded_widgets()
        self.canvas.delete("all")
        self._day_hitboxes = []
        self._year_month_hitboxes = []
        self._detail_back_hitbox = None

        width = max(1800, self.canvas.winfo_width())
        height = max(560, self.canvas.winfo_height())
        L = self._L

        # 3개월: 이전/현재/다음
        months = []
        for delta in (-1, 0, 1):
            m = self.month + delta
            y = self.year
            if m < 1:
                m += 12; y -= 1
            elif m > 12:
                m -= 12; y += 1
            months.append((y, m))

        col_w = width / 3
        gap = 8
        bold = tkfont.Font(family="Malgun Gothic", size=9, weight="bold")
        small = tkfont.Font(family="Malgun Gothic", size=7)
        today = date.today()
        is_center = [False, True, False]

        for col_i, (yr, mo) in enumerate(months):
            x_off = col_i * col_w
            mo_name = f"{yr}{L['year']} {mo}{L['month_unit']}"

            # 월 헤더
            self.canvas.create_text(x_off + col_w / 2, 14, text=mo_name,
                                     fill=PALETTE["text"] if is_center[col_i] else PALETTE["muted"],
                                     font=bold)
            # 구분선
            if col_i > 0:
                self.canvas.create_line(x_off, 0, x_off, height,
                                         fill=PALETTE["line"], width=1)

            # 요일 헤더
            header_h = 32
            n_cols = 7
            cw = (col_w - gap) / n_cols
            for c, wd in enumerate(L["weekdays"]):
                self.canvas.create_text(x_off + c * cw + cw / 2, 24,
                                         text=wd, fill=PALETTE["muted"], font=small)

            # 날짜 셀
            weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(yr, mo)
            row_count = len(weeks)
            ch = (height - header_h - gap * (row_count - 1)) / row_count
            radius = max(16, min(cw * 0.30, ch * 0.26))

            for row, week in enumerate(weeks):
                for c, day in enumerate(week):
                    cx2 = x_off + c * cw
                    cy2 = header_h + row * (ch + gap)
                    self._day_hitboxes.append((cx2, cy2, cx2 + cw, cy2 + ch, day))
                    is_cur = day.month == mo
                    fill = PALETTE["panel"] if is_cur else "#f3f4f6" if self._theme == "light" else "#0f172a"
                    outline = PALETTE["today"] if day == today else PALETTE["line"]
                    self.canvas.create_rectangle(cx2, cy2, cx2 + cw, cy2 + ch,
                                                  fill=fill, outline=outline,
                                                  width=2 if day == today else 1)
                    self.canvas.create_text(cx2 + 4, cy2 + 4, text=str(day.day), anchor="nw",
                                             fill=PALETTE["text"] if is_cur else PALETTE["muted"],
                                             font=small)
                    intervals = self._get_display_intervals(day)
                    total_s = sum(max(0, e - s) for s, e in intervals)  # 동일 스냅샷 재사용
                    self._draw_clock(cx2 + cw / 2, cy2 + ch / 2 - 2, radius, intervals,
                                      PALETTE["clock"] if is_cur else (
                                          "#e5e7eb" if self._theme == "light" else "#1e293b"))
                    self.canvas.create_text(cx2 + cw / 2, cy2 + ch - 10,
                                             text=seconds_to_hhmm(total_s),
                                             fill=PALETTE["active_dark"] if total_s else PALETTE["muted"],
                                             font=small)

        # Title bar update
        self.title_label.configure(
            text=f"{months[1][0]}{L['year']} {months[1][1]}{L['month_unit']}")
        total3 = sum(
            self._get_display_total(date(yr, mo, d))
            for yr, mo in months
            for d in range(1, calendar.monthrange(yr, mo)[1] + 1)
        )
        self.summary_label.configure(text=f"3개월 총  {seconds_to_hhmm(total3)}")

    # ── 일간 뷰 ───────────────────────────────────────
    def _draw_day_detail_view(self) -> None:
        self._clear_embedded_widgets()
        self.canvas.delete("all")
        self._detail_back_hitbox = None
        self._day_hitboxes = []

        if self.detail_day is None:
            return

        day = self.detail_day
        L = self._L
        width = max(900, self.canvas.winfo_width())
        height = max(560, self.canvas.winfo_height())

        wd = L["weekday_names"][day.weekday()]
        self.title_label.configure(
            text=f"{day.year}{L['year']} {day.month}{L['month_unit']} {day.day}{L['day_unit']}")
        total_s = self._get_display_total(day)
        self.summary_label.configure(
            text=f"{L['total_day']}  {seconds_to_hhmm(total_s)}")

        # 날짜 헤더 (뒤로가기는 헤더 제목 클릭으로 대체)
        self._detail_back_hitbox = None
        pad = 24

        # 시계 (좌측 중앙)
        right_panel_w = 260
        clock_area_w = width - right_panel_w - pad * 2
        radius = min(clock_area_w / 2, (height - 120) / 2) * 0.82
        cx = pad + clock_area_w / 2
        cy = height / 2
        intervals = self._get_display_intervals(day)
        self._day_clock_cx = cx
        self._day_clock_cy = cy
        self._day_clock_r = radius
        self._day_intervals = list(intervals)
        merge_gaps = [(g[0], g[1]) for g in self.log.merges_for(day)]
        hi = ([self._drag_interval_idx, self._drag_target_idx]
              if self._merge_drag_active else [])
        self._draw_clock(cx, cy, radius, intervals, PALETTE["clock"],
                          merge_gaps=merge_gaps, highlight_idxs=hi, min_secs=0)
        self._draw_hour_labels(cx, cy, radius)

        # 우측 패널 (기록 구간 + 메모)
        panel_x = width - right_panel_w - pad
        live = (day == date.today())
        day_header = f"{day.year}-{day.month:02d}-{day.day:02d}  {wd}"
        self._draw_right_panel(panel_x, pad + 10, right_panel_w, height - pad - 10,
                                intervals, day, total_s=total_s, live=live,
                                day_header=day_header)

    def _draw_right_panel(self, x: float, y: float, w: float, h: float,
                           intervals: list[list[int]], day: date,
                           total_s: int = 0, live: bool = False,
                           day_header: str = "") -> None:
        L = self._L

        panel = Frame(self.canvas, bg=PALETTE["bg"])
        self._embedded_widgets.append(panel)
        self.canvas.create_window(x, y, window=panel, anchor="nw", width=w)

        bold = ("Malgun Gothic", 10, "bold")
        small = ("Malgun Gothic", 9)
        tiny = ("Malgun Gothic", 8)

        # ── 날짜 헤더 ──────────────────────────────────
        if day_header:
            Label(panel, text=day_header, bg=PALETTE["bg"], fg=PALETTE["text"],
                  font=("Malgun Gothic", 9)).pack(anchor="w", pady=(0, 4))

        # ── 총 작업시간 ────────────────────────────────
        Label(panel, text=f"{L['total']}  {seconds_to_hhmm(total_s)}",
              bg=PALETTE["bg"], fg=PALETTE["muted"],
              font=("Malgun Gothic", 10)).pack(anchor="w")
        Frame(panel, bg=PALETTE["line"], height=1).pack(fill=X, pady=(6, 8))

        # ── 기록 구간 ─────────────────────────────────
        Label(panel, text=L["intervals"], bg=PALETTE["bg"], fg=PALETTE["text"],
              font=bold).pack(anchor="w", pady=(0, 4))

        if not intervals:
            Label(panel, text=L["no_record"], bg=PALETTE["bg"], fg=PALETTE["muted"],
                  font=small).pack(anchor="w")
        else:
            groups = self._group_intervals_with_merges(day, intervals)
            total_groups = len(groups)
            count = 0
            for g_idx, group in enumerate(groups):
                if count >= 10:
                    Label(panel, text=f"외 {len(intervals) - 10}개",
                          bg=PALETTE["bg"], fg=PALETTE["muted"], font=small).pack(anchor="w")
                    break
                is_last = (g_idx == total_groups - 1)
                if group["merged"]:
                    s = group["intervals"][0][0]
                    e = group["intervals"][-1][1]
                    blk = Frame(panel, bg="#dbeafe")
                    blk.pack(fill=X, pady=2, padx=2)
                    Label(blk, text=f"{seconds_to_hhmm(s)} – {seconds_to_hhmm(e)}",
                          bg="#dbeafe", fg=PALETTE["text"],
                          font=small).pack(side=LEFT, padx=(6, 0), pady=3)
                    if live and is_last:
                        Label(blk, text="지금 기록중", bg="#dbeafe",
                              fg="#60a5fa", font=tiny).pack(side=LEFT, padx=(6, 0), pady=3)
                    gaps_copy = list(group["gaps"])
                    def make_unmerge(d=day, gaps=gaps_copy):
                        def _fn():
                            for gs, ge in gaps:
                                self.log.remove_merge(d, gs, ge)
                            self.redraw()
                        return _fn
                    lbl_x = Label(blk, text="✕", bg="#dbeafe", fg=PALETTE["muted"],
                                  font=("Malgun Gothic", 8), cursor="hand2", padx=4)
                    lbl_x.pack(side=RIGHT, pady=3)
                    lbl_x.bind("<Button-1>", lambda _e, fn=make_unmerge(): fn())
                else:
                    s, e = group["intervals"][0]
                    row_f = Frame(panel, bg=PALETTE["bg"])
                    row_f.pack(fill=X, pady=1)
                    Label(row_f, text=f"{seconds_to_hhmm(s)} – {seconds_to_hhmm(e)}",
                          bg=PALETTE["bg"], fg=PALETTE["muted"],
                          font=small).pack(side=LEFT)
                    if live and is_last:
                        Label(row_f, text="지금 기록중", bg=PALETTE["bg"],
                              fg="#60a5fa", font=tiny).pack(side=LEFT, padx=(6, 0))
                count += 1

        # ── 구분선 ─────────────────────────────────────
        Frame(panel, bg=PALETTE["line"], height=1).pack(fill=X, pady=(10, 6))

        # ── 메모 ──────────────────────────────────────
        Label(panel, text=L["memo"], bg=PALETTE["bg"], fg=PALETTE["text"],
              font=bold).pack(anchor="w", pady=(0, 4))

        txt = Text(panel, width=28, height=5, bg=PALETTE["panel"], fg=PALETTE["text"],
                   relief="flat", bd=0, font=small, wrap="word",
                   highlightthickness=1, highlightbackground="#d1d9e0",
                   highlightcolor="#93c5fd", undo=False, padx=6, pady=6)
        txt.insert("1.0", self.log.note_for(day))
        txt.pack(fill=X)

        def save_note() -> None:
            self.log.set_note_for(day, txt.get("1.0", END))

        btn_f = Frame(panel, bg=PALETTE["bg"])
        btn_f.pack(anchor="e", pady=(6, 0))
        RoundedButton(btn_f, L["memo_save"], save_note, width=60, height=26).pack()

    # ── 연간 뷰 (히트맵) ──────────────────────────────
    def _draw_year(self) -> None:
        self._clear_embedded_widgets()
        self.canvas.delete("all")
        self._year_month_hitboxes = []
        self._day_hitboxes = []
        self._detail_back_hitbox = None

        L = self._L
        yr = self.year_year
        self.title_label.configure(text=f"{yr}{L['year']}")

        annual = sum(self.log.total_seconds_for(date(yr, m, d))
                     for m in range(1, 13)
                     for d in range(1, calendar.monthrange(yr, m)[1] + 1))
        self.summary_label.configure(text=f"{seconds_to_hhmm(annual)}")

        width = max(900, self.canvas.winfo_width())
        height = max(560, self.canvas.winfo_height())

        cols, rows_mo = 4, 3
        gap = 10
        cell_w = (width - gap * (cols + 1)) / cols
        cell_h = (height - gap * (rows_mo + 1)) / rows_mo

        bold = tkfont.Font(family="Malgun Gothic", size=9, weight="bold")
        small = tkfont.Font(family="Malgun Gothic", size=7)
        today = date.today()

        # 히트맵 색상 (작업량 0→낮음→중→높음)
        HEAT = ["#f1f5f9", "#bfdbfe", "#60a5fa", "#2563eb", "#1e3a8a"]

        def heat_color(sec: int) -> str:
            if sec == 0:     return HEAT[0]
            if sec < 3600:   return HEAT[1]
            if sec < 14400:  return HEAT[2]
            if sec < 28800:  return HEAT[3]
            return HEAT[4]

        for i, mo in enumerate(range(1, 13)):
            col = i % cols
            row = i // cols
            x = gap + col * (cell_w + gap)
            y = gap + row * (cell_h + gap)

            self._year_month_hitboxes.append((x, y, x + cell_w, y + cell_h, yr, mo))

            is_cur = (yr == today.year and mo == today.month)
            self.canvas.create_rectangle(x, y, x + cell_w, y + cell_h,
                                          fill=PALETTE["panel"],
                                          outline="#fde68a" if is_cur else PALETTE["line"],
                                          width=2 if is_cur else 1)

            mo_total = sum(self.log.total_seconds_for(date(yr, mo, d))
                           for d in range(1, calendar.monthrange(yr, mo)[1] + 1))
            self.canvas.create_text(x + 10, y + 13,
                                     text=f"{mo}{L['month_unit']}",
                                     anchor="w", fill=PALETTE["text"], font=bold)
            self.canvas.create_text(x + cell_w - 8, y + 13,
                                     text=seconds_to_hhmm(mo_total),
                                     anchor="e",
                                     fill=PALETTE["active_dark"] if mo_total else PALETTE["muted"],
                                     font=small)

            # 히트맵 점 그리기
            weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(yr, mo)
            n_weeks = len(weeks)
            pad_x, pad_y = 8, 30
            avail_w = cell_w - pad_x * 2
            avail_h = cell_h - pad_y - 6
            dot_w = avail_w / 7
            dot_h = avail_h / n_weeks
            dot_r = min(dot_w, dot_h) * 0.38

            for r_i, week in enumerate(weeks):
                for c_i, day in enumerate(week):
                    if day.month != mo:
                        continue
                    sec = self.log.total_seconds_for(day)
                    if day == today and self.tracker.current_interval:
                        sec += self._get_display_total(day) - self.log.total_seconds_for(day)
                    color = heat_color(sec)
                    dx = x + pad_x + c_i * dot_w + dot_w / 2
                    dy = y + pad_y + r_i * dot_h + dot_h / 2
                    self.canvas.create_oval(dx - dot_r, dy - dot_r,
                                             dx + dot_r, dy + dot_r,
                                             fill=color, outline="")

    # ── 시계 그리기 ───────────────────────────────────
    def _draw_clock(self, cx, cy, radius, intervals, fill,
                    merge_gaps=None, highlight_idxs=None, min_secs=120) -> None:
        l, t, r, b = cx-radius, cy-radius, cx+radius, cy+radius
        self.canvas.create_oval(l, t, r, b, fill=fill, outline=PALETTE["clock_line"])

        hi_set = set(highlight_idxs) if highlight_idxs else set()

        # Regular (non-highlighted) intervals
        for i, (s, e) in enumerate(intervals):
            if i in hi_set:
                continue
            dur = e - s
            if dur < 120:
                if min_secs > 0:
                    continue  # 소형 클럭에서는 생략
                # 대형 클럭(일간): 라인으로 표시
                mid = (s + e) / 2
                angle = math.radians(90 - (mid / 86400) * 360)
                self.canvas.create_line(
                    cx + math.cos(angle) * radius * 0.1,
                    cy - math.sin(angle) * radius * 0.1,
                    cx + math.cos(angle) * radius * 0.97,
                    cy - math.sin(angle) * radius * 0.97,
                    fill=PALETTE["active"], width=2)
                continue
            sd = 90 - (s / 86400) * 360
            ex = -((e - s) / 86400) * 360
            self.canvas.create_arc(l, t, r, b, start=sd, extent=ex,
                                    style="pieslice", fill=PALETTE["active"],
                                    outline=PALETTE["active"])

        # Merged gap bridges (same color → seamless)
        if merge_gaps:
            for gs, ge in merge_gaps:
                sd = 90 - (gs / 86400) * 360
                ex = -((ge - gs) / 86400) * 360
                self.canvas.create_arc(l, t, r, b, start=sd, extent=ex,
                                        style="pieslice", fill=PALETTE["active"],
                                        outline=PALETTE["active"])

        # Highlighted intervals (drag preview)
        for i in hi_set:
            if i < len(intervals):
                s, e = intervals[i]
                sd = 90 - (s / 86400) * 360
                ex = -((e - s) / 86400) * 360
                self.canvas.create_arc(l, t, r, b, start=sd, extent=ex,
                                        style="pieslice", fill="#818cf8",
                                        outline="#818cf8")

        # Preview bridge between the two highlighted intervals
        if len(hi_set) == 2 and intervals:
            a_idx, b_idx = sorted(hi_set)
            if b_idx < len(intervals) and b_idx == a_idx + 1:
                e1 = intervals[a_idx][1]
                s2 = intervals[b_idx][0]
                if e1 < s2:
                    sd = 90 - (e1 / 86400) * 360
                    ex = -((s2 - e1) / 86400) * 360
                    self.canvas.create_arc(l, t, r, b, start=sd, extent=ex,
                                            style="pieslice", fill="#c7d2fe",
                                            outline="#818cf8")

        self.canvas.create_oval(l, t, r, b, outline=PALETTE["clock_line"])
        for hour in (0, 6, 12, 18):
            angle = math.radians(90 - (hour / 24) * 360)
            x1 = cx + math.cos(angle) * radius * 0.82
            y1 = cy - math.sin(angle) * radius * 0.82
            x2 = cx + math.cos(angle) * radius * 0.96
            y2 = cy - math.sin(angle) * radius * 0.96
            self.canvas.create_line(x1, y1, x2, y2, fill="#7dd3fc")
        self.canvas.create_oval(cx-3, cy-3, cx+3, cy+3, fill=PALETTE["center"], outline="")

    def _draw_hour_labels(self, cx, cy, radius) -> None:
        for hour in range(0, 24, 3):
            angle = math.radians(90 - (hour / 24) * 360)
            tx = cx + math.cos(angle) * radius * 1.14
            ty = cy - math.sin(angle) * radius * 1.14
            self.canvas.create_text(tx, ty, text=f"{hour:02d}",
                                     fill=PALETTE["muted"],
                                     font=("Malgun Gothic", 9, "bold"))

    def _clear_embedded_widgets(self) -> None:
        for w in self._embedded_widgets:
            try:
                w.destroy()
            except TclError:
                pass
        self._embedded_widgets = []

    # ── 내보내기 ──────────────────────────────────────
    def open_export(self) -> None:
        L = self._L
        win = tk.Toplevel(self.root)
        win.title(L["export_title"])
        win.configure(bg=PALETTE["bg"])
        win.resizable(False, False)
        win.grab_set()

        pad = 20
        Label(win, text=L["export_format"], bg=PALETTE["bg"], fg=PALETTE["text"],
              font=("Malgun Gothic", 10, "bold")).pack(padx=pad, pady=(pad, 8), anchor="w")

        fmt_var = StringVar(value=L["fmt_simple"])
        for fmt in [L["fmt_simple"], L["fmt_table"], L["fmt_detail"]]:
            tk.Radiobutton(win, text=fmt, variable=fmt_var, value=fmt,
                           bg=PALETTE["bg"], fg=PALETTE["text"],
                           activebackground=PALETTE["bg"],
                           font=("Malgun Gothic", 9)).pack(padx=pad+8, anchor="w")

        # ── 날짜 범위 필터 ─────────────────────────────
        Frame(win, bg=PALETTE["line"], height=1).pack(fill=X, padx=pad, pady=(12, 6))
        rf = Frame(win, bg=PALETTE["bg"])
        rf.pack(padx=pad, anchor="w", pady=(0, 4))
        Label(rf, text=L.get("export_range", "기간"), bg=PALETTE["bg"],
              fg=PALETTE["text"], font=("Malgun Gothic", 9, "bold")).pack(side=LEFT, padx=(0, 8))
        all_days = sorted(self.log.days.keys())
        first_day = all_days[0] if all_days else date.today().isoformat()
        last_day  = all_days[-1] if all_days else date.today().isoformat()
        from_var = StringVar(value=first_day)
        to_var   = StringVar(value=last_day)
        Label(rf, text="from", bg=PALETTE["bg"], fg=PALETTE["muted"],
              font=("Malgun Gothic", 8)).pack(side=LEFT)
        tk.Entry(rf, textvariable=from_var, width=11, font=("Malgun Gothic", 9),
                 relief="flat", highlightthickness=1,
                 highlightbackground=PALETTE["btn_border"]).pack(side=LEFT, padx=(2, 4))
        Label(rf, text="→", bg=PALETTE["bg"], fg=PALETTE["muted"],
              font=("Malgun Gothic", 8)).pack(side=LEFT)
        tk.Entry(rf, textvariable=to_var, width=11, font=("Malgun Gothic", 9),
                 relief="flat", highlightthickness=1,
                 highlightbackground=PALETTE["btn_border"]).pack(side=LEFT, padx=(2, 0))

        bf = Frame(win, bg=PALETTE["bg"])
        bf.pack(padx=pad, pady=pad)
        RoundedButton(bf, L["export"],
                      lambda: self._do_export(fmt_var.get(), win, from_var.get(), to_var.get()),
                      width=100, height=30, dark=True).pack(side=LEFT, padx=4)
        RoundedButton(bf, "✕", win.destroy, width=40, height=30).pack(side=LEFT)

    def _do_export(self, fmt_label: str, win: tk.Toplevel,
                   from_str: str = "", to_str: str = "") -> None:
        L = self._L
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("텍스트 파일", "*.txt")],
            initialfile=f"WorkTimer_{date.today().isoformat()}.txt",
            title=L["export_title"],
            parent=win,
        )
        if not path:
            return

        try:
            from_date = date.fromisoformat(from_str) if from_str else None
            to_date   = date.fromisoformat(to_str)   if to_str   else None
        except ValueError:
            from_date = to_date = None

        all_days_raw = sorted(self.log.days.keys())
        all_days = [k for k in all_days_raw if
                    (from_date is None or date.fromisoformat(k) >= from_date) and
                    (to_date   is None or date.fromisoformat(k) <= to_date)]
        lines: list[str] = [
            L["export_header"],
            f"{L['export_time']} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            L["made_by"], "",
        ]

        if fmt_label == L["fmt_table"]:
            hd = L
            lines.append(f"| {hd['table_date']} | {hd['table_wd']} | {hd['table_time']} | {hd['table_note']} |")
            lines.append("|------|------|----------|------|")
            for key in all_days:
                d = date.fromisoformat(key)
                wd = L["weekdays"][d.weekday()]
                t = seconds_to_hhmm(self.log.total_seconds_for(d))
                note = self.log.note_for(d) or "-"
                lines.append(f"| {key} | {wd} | {t} | {note} |")

        elif fmt_label == L["fmt_detail"]:
            for key in all_days:
                d = date.fromisoformat(key)
                wd = L["weekdays"][d.weekday()]
                t = seconds_to_hhmm(self.log.total_seconds_for(d))
                lines.append(f"## {key} ({wd})  {t}")
                for s, e in self.log.intervals_for(d):
                    lines.append(f"  {seconds_to_hhmm(s)} – {seconds_to_hhmm(e)}")
                note = self.log.note_for(d)
                if note:
                    lines.append(f"  📝 {note}")
                lines.append("")

        else:
            if not all_days:
                lines.append(L["no_data"])
            for key in all_days:
                d = date.fromisoformat(key)
                wd = L["weekdays"][d.weekday()]
                t = seconds_to_hhmm(self.log.total_seconds_for(d))
                note = self.log.note_for(d)
                line = f"{key} ({wd})  {t}"
                if note:
                    line += f"  | {note}"
                lines.append(line)

        # Append range labels that overlap the exported period
        relevant_ranges = [
            r for r in self.log.ranges
            if (from_date is None or date.fromisoformat(r.get("end", "9999")) >= from_date) and
               (to_date   is None or date.fromisoformat(r.get("start", "0000")) <= to_date)
        ]
        if relevant_ranges:
            lines += ["", "── 구간 메모 ──"]
            for r in sorted(relevant_ranges, key=lambda x: x.get("start", "")):
                lines.append(f"  {r['start']} ~ {r['end']}  {r.get('label', '')}")

        try:
            Path(path).write_text("\n".join(lines), encoding="utf-8")
            win.destroy()
            messagebox.showinfo(L["export_done"], L["export_saved"].format(path))
        except Exception as exc:
            messagebox.showerror(L["export_err"], str(exc))

    # ── 설정 ──────────────────────────────────────────
    def open_settings(self) -> None:
        L = self._L
        win = tk.Toplevel(self.root)
        win.title(L["settings_title"])
        win.configure(bg=PALETTE["bg"])
        win.resizable(False, False)
        win.grab_set()

        pad = 20
        row = 0

        Label(win, text=L["lang_label"], bg=PALETTE["bg"], fg=PALETTE["text"],
              font=("Malgun Gothic", 10, "bold")).grid(row=row, column=0, padx=pad, pady=(pad, 4), sticky="w")
        lang_var = StringVar(value=self._lang_name)
        ttk.Combobox(win, textvariable=lang_var, values=list(LANGUAGES.keys()),
                     state="readonly", width=12).grid(row=row, column=1, padx=pad, pady=(pad, 4), sticky="w")
        row += 1

        Label(win, text=L["autostart"], bg=PALETTE["bg"], fg=PALETTE["text"],
              font=("Malgun Gothic", 9)).grid(row=row, column=0, padx=pad, pady=4, sticky="w")
        autostart_var = tk.BooleanVar(value=get_autostart())
        tk.Checkbutton(win, variable=autostart_var, bg=PALETTE["bg"],
                       activebackground=PALETTE["bg"]).grid(row=row, column=1, padx=pad, pady=4, sticky="w")
        row += 1

        Label(win, text=L["icon_label"], bg=PALETTE["bg"], fg=PALETTE["text"],
              font=("Malgun Gothic", 9)).grid(row=row, column=0, padx=pad, pady=4, sticky="w")
        RoundedButton(win, L["icon_pick_btn"], lambda: (win.destroy(), self.open_icon_picker()),
                      width=80, height=26).grid(row=row, column=1, padx=pad, pady=4, sticky="w")
        row += 1

        Label(win, text=L["data_path"], bg=PALETTE["bg"], fg=PALETTE["text"],
              font=("Malgun Gothic", 9)).grid(row=row, column=0, padx=pad, pady=4, sticky="w")
        RoundedButton(win, "📁", lambda: os.startfile(DATA_DIR), width=36, height=26
                      ).grid(row=row, column=1, padx=pad, pady=4, sticky="w")
        row += 1

        Label(win, text=L["reset_btn"], bg=PALETTE["bg"], fg=PALETTE["text"],
              font=("Malgun Gothic", 9)).grid(row=row, column=0, padx=pad, pady=4, sticky="w")
        RoundedButton(win, "🗑", self._reset_data, width=36, height=26
                      ).grid(row=row, column=1, padx=pad, pady=4, sticky="w")
        row += 1

        # ── 색상 설정 ─────────────────────────────────
        Frame(win, bg=PALETTE["line"], height=1).grid(
            row=row, column=0, columnspan=2, padx=pad, pady=(8, 4), sticky="ew")
        row += 1
        Label(win, text=L.get("color_section", "색상 설정"), bg=PALETTE["bg"],
              fg=PALETTE["text"], font=("Malgun Gothic", 10, "bold")).grid(
            row=row, column=0, columnspan=2, padx=pad, pady=(0, 4), sticky="w")
        row += 1

        color_entries: dict[str, tuple[StringVar, Canvas]] = {}
        color_defs = [
            ("color_active", "active",    L.get("color_active",   "활동 구간 색상")),
            ("color_clock_bg", "clock",   L.get("color_clock_bg", "시계 배경 색상")),
            ("color_center",  "center",   L.get("color_center",   "중앙점 색상")),
        ]
        for skey, pkey, clabel in color_defs:
            Label(win, text=clabel, bg=PALETTE["bg"], fg=PALETTE["text"],
                  font=("Malgun Gothic", 9)).grid(row=row, column=0, padx=pad, pady=2, sticky="w")
            cf = Frame(win, bg=PALETTE["bg"])
            cf.grid(row=row, column=1, padx=pad, pady=2, sticky="w")
            cur = self._settings.get(skey, PALETTE[pkey])
            cv = StringVar(value=cur)
            swatch = Canvas(cf, width=18, height=18, highlightthickness=1,
                            highlightbackground=PALETTE["btn_border"],
                            bg=cur, cursor="hand2")
            swatch.pack(side=LEFT, padx=(0, 4))
            ent = tk.Entry(cf, textvariable=cv, width=9, font=("Malgun Gothic", 9),
                           relief="flat", highlightthickness=1,
                           highlightbackground=PALETTE["btn_border"])
            ent.pack(side=LEFT)
            color_entries[skey] = (cv, swatch)

            def _pick(sv=cv, sw=swatch):
                res = colorchooser.askcolor(color=sv.get(), title="색상 선택", parent=win)
                if res and res[1]:
                    sv.set(res[1])
                    try:
                        sw.configure(bg=res[1])
                    except Exception:
                        pass

            def _trace(_, __, ___, sv=cv, sw=swatch):
                v = sv.get()
                if len(v) == 7 and v.startswith("#"):
                    try:
                        sw.configure(bg=v)
                    except Exception:
                        pass

            swatch.bind("<Button-1>", lambda _e, fn=_pick: fn())
            cv.trace_add("write", _trace)
            row += 1

        # 색상 초기화 버튼
        def _reset_colors():
            base = PALETTE_DARK if self._theme == "dark" else PALETTE_LIGHT
            for skey, pkey, _ in color_defs:
                color_entries[skey][0].set(base[pkey])
                color_entries[skey][1].configure(bg=base[pkey])
                if skey in self._settings:
                    del self._settings[skey]

        RoundedButton(win, L.get("color_reset", "기본값 초기화"), _reset_colors,
                      width=120, height=24).grid(row=row, column=0, columnspan=2,
                                                  padx=pad, pady=(0, 4), sticky="w")
        row += 1

        # ── 테마 ──────────────────────────────────────
        Frame(win, bg=PALETTE["line"], height=1).grid(
            row=row, column=0, columnspan=2, padx=pad, pady=(8, 4), sticky="ew")
        row += 1
        Label(win, text=L.get("theme_label", "테마"), bg=PALETTE["bg"], fg=PALETTE["text"],
              font=("Malgun Gothic", 9, "bold")).grid(row=row, column=0, padx=pad, pady=4, sticky="w")
        theme_var = StringVar(value=self._theme)
        tf = Frame(win, bg=PALETTE["bg"])
        tf.grid(row=row, column=1, padx=pad, pady=4, sticky="w")
        for tv, tl in [("light", L.get("theme_light", "라이트")),
                        ("dark",  L.get("theme_dark",  "다크"))]:
            tk.Radiobutton(tf, text=tl, variable=theme_var, value=tv,
                           bg=PALETTE["bg"], fg=PALETTE["text"],
                           activebackground=PALETTE["bg"],
                           font=("Malgun Gothic", 9)).pack(side=LEFT, padx=(0, 8))
        row += 1

        def apply() -> None:
            set_autostart(autostart_var.get())
            self._settings["lang"] = lang_var.get()
            self._settings["icon_style"] = self._icon_style
            # Colors
            for skey, pkey, _ in color_defs:
                val = color_entries[skey][0].get().strip()
                if len(val) == 7 and val.startswith("#"):
                    self._settings[skey] = val
                    PALETTE[pkey] = val
            # Theme
            new_theme = theme_var.get()
            theme_changed = new_theme != self._theme
            self._theme = new_theme
            self._settings["theme"] = new_theme
            base = PALETTE_DARK if new_theme == "dark" else PALETTE_LIGHT
            PALETTE.update(base)
            # Re-apply saved color overrides on top of theme
            for skey, pkey, _ in color_defs:
                val = self._settings.get(skey, "")
                if len(val) == 7 and val.startswith("#"):
                    PALETTE[pkey] = val
            save_settings(self._settings)
            self._lang_name = lang_var.get()
            win.destroy()
            if theme_changed:
                self._apply_theme()
            else:
                self._apply_lang()
                self.redraw()

        Frame(win, bg=PALETTE["bg"]).grid(row=row, column=0, columnspan=2, pady=8)
        row += 1
        RoundedButton(win, "✓ 적용" if self._lang_name == "한국어" else "✓ Apply",
                      apply, width=80, height=28, dark=True
                      ).grid(row=row, column=0, columnspan=2, pady=(0, pad))

    def _reset_data(self) -> None:
        L = self._L
        if messagebox.askyesno(L["reset_title"], L["reset_confirm"]):
            self.log.reset()
            self.redraw()
            messagebox.showinfo(L["reset_title"], L["reset_done"])

    # ── 트레이 ────────────────────────────────────────
    def run(self) -> None:
        self.tracker.start()
        self._start_tray()
        if self._start_minimized:
            self.root.withdraw()
        self.redraw()
        self.root.mainloop()

    def quit(self) -> None:
        self.tracker.stop()
        if self._tray_icon:
            self._tray_icon.stop()
        self.root.destroy()

    def hide_window(self) -> None:
        self.root.withdraw()

    def show_window(self) -> None:
        self.root.after(0, self._show_window)

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.redraw()

    def _set_window_icon(self) -> None:
        def _do():
            if self._icon_style:
                img = self._load_icon_pil(self._icon_style, 32)
                if img and ImageTk is not None:
                    try:
                        self._tk_icon = ImageTk.PhotoImage(img)
                        self.root.iconphoto(True, self._tk_icon)
                        return
                    except Exception:
                        pass
            if ICON_FILE.exists():
                try:
                    self._tk_icon = PhotoImage(file=str(ICON_FILE))
                    self.root.iconphoto(True, self._tk_icon)
                except Exception:
                    self._tk_icon = None
        _do()
        self.root.after(400, _do)  # 윈도우가 완전히 뜬 뒤 한 번 더 보장

    def _load_icon_pil(self, icon_name: str, size: int = 64):
        if Image is None:
            return None
        path = ICONS_DIR / icon_name
        if not path.exists():
            return None
        try:
            return Image.open(path).convert("RGBA").resize((size, size))
        except Exception:
            return None

    def _apply_icon(self, icon_name: str, save: bool = True) -> None:
        self._icon_style = icon_name
        if save:
            self._settings["icon_style"] = icon_name
            self._settings["lang"] = self._lang_name
            save_settings(self._settings)

        img = self._load_icon_pil(icon_name, 64)
        if img is None:
            return
        self._pil_icon = img

        if ImageTk is not None:
            try:
                self._tk_icon = ImageTk.PhotoImage(img.resize((32, 32)))
                self.root.iconphoto(True, self._tk_icon)
            except Exception:
                pass

        if self._tray_icon is not None:
            try:
                self._tray_icon.icon = img
            except Exception:
                pass

    def open_icon_picker(self) -> None:
        L = self._L
        icon_files = get_icon_files()

        win = tk.Toplevel(self.root)
        win.title(L["icon_picker_title"])
        win.configure(bg=PALETTE["bg"])
        win.resizable(False, False)
        win.grab_set()

        Label(win, text=L["icon_picker_title"], bg=PALETTE["bg"], fg=PALETTE["text"],
              font=("Malgun Gothic", 12, "bold")).pack(pady=(18, 4))
        Label(win, text=L["icon_picker_desc"], bg=PALETTE["bg"], fg=PALETTE["muted"],
              font=("Malgun Gothic", 9)).pack(pady=(0, 14))

        preview_frame = Frame(win, bg=PALETTE["bg"])
        preview_frame.pack(padx=20, pady=(0, 10))

        sel_var = StringVar(value=self._icon_style if self._icon_style else "")
        # 미리보기 이미지 참조 보관 (GC 방지)
        self._picker_refs: list = []

        THUMB = 64
        if not icon_files:
            Label(preview_frame, text="icons/ 폴더에 PNG 파일이 없습니다.",
                  bg=PALETTE["bg"], fg=PALETTE["muted"],
                  font=("Malgun Gothic", 9)).pack()
        else:
            for i, path in enumerate(icon_files):
                col_frame = Frame(preview_frame, bg=PALETTE["bg"])
                col_frame.grid(row=0, column=i, padx=8)

                # PIL 썸네일
                tk_img = None
                if Image is not None and ImageTk is not None:
                    try:
                        pil_img = Image.open(path).convert("RGBA").resize((THUMB, THUMB))
                        tk_img = ImageTk.PhotoImage(pil_img)
                        self._picker_refs.append(tk_img)
                    except Exception:
                        pass

                if tk_img:
                    lbl = Label(col_frame, image=tk_img, bg=PALETTE["bg"],
                                cursor="hand2", relief="flat")
                    lbl.pack()
                    lbl.bind("<Button-1>", lambda _e, n=path.name: sel_var.set(n))
                else:
                    # PIL 없을 때 tkinter PhotoImage 폴백
                    try:
                        tk_img2 = PhotoImage(file=str(path))
                        self._picker_refs.append(tk_img2)
                        Label(col_frame, image=tk_img2, bg=PALETTE["bg"]).pack()
                    except Exception:
                        Label(col_frame, text="[?]", bg=PALETTE["bg"],
                              width=6, height=3).pack()

                tk.Radiobutton(col_frame, text=path.stem, variable=sel_var,
                               value=path.name, bg=PALETTE["bg"], fg=PALETTE["text"],
                               activebackground=PALETTE["bg"],
                               font=("Malgun Gothic", 8)).pack()

        def confirm() -> None:
            chosen = sel_var.get()
            if chosen:
                self._apply_icon(chosen, save=True)
            win.destroy()

        Frame(win, bg=PALETTE["bg"]).pack(pady=6)
        RoundedButton(win, "✓ 선택" if self._lang_name == "한국어" else "✓ Select",
                      confirm, width=90, height=30, dark=True).pack(pady=(0, 18))

    def _start_tray(self) -> None:
        if pystray is None or Image is None:
            return
        image = self._make_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem("열기", lambda _i, _it: self.show_window(), default=True),
            pystray.MenuItem("숨기기", lambda _i, _it: self.root.after(0, self.hide_window)),
            pystray.MenuItem("종료", lambda _i, _it: self.root.after(0, self.quit)),
        )
        self._tray_icon = pystray.Icon(APP_NAME, image, APP_NAME, menu)
        threading.Thread(target=self._tray_icon.run, name="worktimer-tray", daemon=True).start()

    def _make_tray_image(self):
        if Image is None:
            return None
        if self._icon_style:
            img = self._load_icon_pil(self._icon_style, 64)
            if img:
                return img
        if ICON_FILE.exists():
            try:
                return Image.open(ICON_FILE).convert("RGBA").resize((64, 64))
            except Exception:
                pass
        # 폴백: 생성 아이콘
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((4, 4, 60, 60), fill=(224,242,254,255), outline=(2,132,199,255), width=3)
        draw.pieslice((4, 4, 60, 60), start=270, end=20, fill=(253,186,116,255))
        draw.line((32, 32, 32, 14), fill=(31,41,55,255), width=3)
        draw.line((32, 32, 46, 38), fill=(31,41,55,255), width=3)
        draw.ellipse((29, 29, 35, 35), fill=(31,41,55,255))
        return img


_SINGLE_INSTANCE_MUTEX = None

def main() -> int:
    if os.name != "nt":
        print("WorkTimer currently supports Windows only.")
        return 1
    # 중복 실행 방지 — Named Mutex
    global _SINGLE_INSTANCE_MUTEX
    _SINGLE_INSTANCE_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, True, "UtobitWorkTimer_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return 0
    start_minimized = "--minimized" in sys.argv or "--tray" in sys.argv
    app = WorkTimerApp(start_minimized=start_minimized)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
