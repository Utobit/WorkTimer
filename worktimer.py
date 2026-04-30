from __future__ import annotations

import calendar
import ctypes
import json
import math
import os
import sys
import time
import winreg
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QTextEdit, QDialog,
    QSystemTrayIcon, QMenu, QFileDialog, QMessageBox,
    QComboBox, QCheckBox, QSpinBox, QScrollArea, QSizePolicy,
    QColorDialog, QGridLayout, QButtonGroup, QRadioButton,
    QInputDialog
)
from PyQt6.QtCore import (
    Qt, QTimer, QPointF, QRectF, QSize, pyqtSignal
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QPixmap, QIcon, QCursor, QPainterPath
)

# ── 상수 ────────────────────────────────────────────────
APP_NAME      = "WorkTimer"
VERSION       = "1.0.1"
IDLE_GRACE_SECONDS = 10 * 60
POLL_SECONDS  = 5
APP_DIR       = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_DIR  = Path(getattr(sys, "_MEIPASS", APP_DIR))
LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", APP_DIR))
DATA_DIR      = LOCAL_APPDATA / "LinaAI" / APP_NAME
DATA_FILE     = DATA_DIR / "work_log.json"
CHECKPOINT_FILE = DATA_DIR / "checkpoint.json"
BACKUP_DIR    = DATA_DIR / "backups"
LEGACY_DATA_FILE = APP_DIR / "data" / "work_log.json"
ICON_FILE     = RESOURCE_DIR / "icon.png"
SETTINGS_FILE = DATA_DIR / "settings.json"
REG_RUN_KEY   = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME  = "UtobitWorkTimer"
MUTEX_NAME    = "UtobitWorkTimer_SingleInstance"

PALETTE_LIGHT = {
    "bg": "#f8fafc",        "panel": "#ffffff",      "line": "#e2e8f0",
    "text": "#1e293b",      "muted": "#64748b",       "clock": "#eff6ff",
    "clock_line": "#93c5fd","active": "#1d4ed8",      "active_dark": "#1e40af",
    "center": "#2563eb",    "today_border": "#f59e0b",
    "btn_bg": "#f1f5f9",    "btn_hover": "#e2e8f0",   "btn_fg": "#334155",
    "btn_border": "#cbd5e1","btn_dark": "#3b82f6",    "btn_dark_fg": "#ffffff",
    "btn_dark_hover": "#2563eb", "merged_bg": "#dbeafe",
    "range_bg": "#fef3c7",  "range_border": "#f59e0b",
}
PALETTE_DARK = {
    "bg": "#0f172a",        "panel": "#1e293b",       "line": "#334155",
    "text": "#f1f5f9",      "muted": "#94a3b8",       "clock": "#172554",
    "clock_line": "#1d4ed8","active": "#3b82f6",       "active_dark": "#2563eb",
    "center": "#60a5fa",    "today_border": "#f59e0b",
    "btn_bg": "#1e293b",    "btn_hover": "#334155",    "btn_fg": "#cbd5e1",
    "btn_border": "#475569","btn_dark": "#3b82f6",     "btn_dark_fg": "#ffffff",
    "btn_dark_hover": "#2563eb", "merged_bg": "#1e3a5f",
    "range_bg": "#3b2f0a",  "range_border": "#f59e0b",
}
P = dict(PALETTE_LIGHT)

def pc(key: str) -> QColor:
    return QColor(P[key])

# ── 아이콘 ──────────────────────────────────────────────
ICON_FILES = ["icon_1.png", "icon_2.png", "icon_3.png", "icon_4.ico", "icon_5.png"]
ICON_NAMES = ["그린", "블루", "핑크", "클래식", "캐릭터"]

_icon_search = [
    RESOURCE_DIR / "icons",
    Path(__file__).resolve().parent / "icons",
]
ICONS_DIR: Path | None = next((p for p in _icon_search if p.exists()), None)

def load_icon(idx: int) -> QIcon:
    if ICONS_DIR:
        f = ICONS_DIR / ICON_FILES[idx % len(ICON_FILES)]
        if f.exists():
            return QIcon(str(f))
    colors = ["#16a34a", "#2563eb", "#db2777", "#334155", "#94a3b8"]
    c = colors[idx % len(colors)]
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(c))
    p.drawEllipse(2, 2, 60, 60)
    p.end()
    return QIcon(pix)

def load_icon_any(idx: int, custom_icons: "list[str]") -> QIcon:
    n = len(ICON_FILES)
    if idx >= n and custom_icons:
        ci = idx - n
        if ci < len(custom_icons):
            p = Path(custom_icons[ci])
            if p.exists():
                return QIcon(str(p))
    return load_icon(min(idx, n - 1))

def generate_icon(color_idx: int, size: int = 64) -> QIcon:
    return load_icon(color_idx)

def clip_icon_circle(icon: QIcon, size: int = 44) -> QIcon:
    """아이콘 → 짧은 쪽 기준 정사각형 센터크롭 → 원형 클리핑."""
    # 자연 비율 유지를 위해 큰 크기로 요청 (Qt가 aspect ratio 보존)
    raw = icon.pixmap(QSize(512, 512))
    if raw.isNull():
        raw = icon.pixmap(QSize(size, size))
    sw, sh = raw.width(), raw.height()
    # 짧은 쪽 기준 정사각형 센터크롭
    dim = min(sw, sh)
    ox, oy = (sw - dim) // 2, (sh - dim) // 2
    if ox or oy:
        raw = raw.copy(ox, oy, dim, dim)
    scaled = raw.scaled(size, size,
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    p = QPainter(result)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(QRectF(0, 0, size, size))
    p.setClipPath(path)
    p.drawPixmap(0, 0, scaled)
    p.end()
    return QIcon(result)

# ── 다국어 ──────────────────────────────────────────────
LANG_KO = {
    "prev": "‹", "today": "오늘", "next": "›",
    "export": "기록 내보내기", "settings": "설정",
    "year_view": "연간 보기", "month_view": "월간",
    "total_month": "이번 달 총 작업시간",
    "total": "총 작업시간",
    "intervals": "기록 구간",
    "no_record": "아직 기록이 없습니다.",
    "memo": "메모", "memo_save": "저장",
    "export_title": "기록 내보내기", "export_format": "형식 선택",
    "fmt_simple": "간단 (날짜·시간)",
    "fmt_table": "표 형식 (Notion/Docs)",
    "fmt_detail": "상세 (구간 포함)",
    "export_done": "내보내기 완료", "export_saved": "저장 완료:\n{}",
    "export_err": "오류", "reset_title": "데이터 초기화",
    "reset_confirm": "모든 작업 기록이 삭제됩니다.\n정말 초기화하시겠습니까?",
    "reset_done": "초기화 완료", "settings_title": "설정",
    "lang_label": "언어", "idle_label": "유휴 감지 시간 (분)",
    "data_path": "데이터 폴더 열기", "reset_btn": "데이터 초기화",
    "weekdays": ["일", "월", "화", "수", "목", "금", "토"],
    "made_by": "Made by Jin (AI Agent) · Utobit",
    "year": "년", "month_unit": "월", "day_unit": "일",
    "weekday_names": ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"],
    "export_header": "WorkTimer 작업 기록", "export_time": "내보내기:",
    "no_data": "기록 없음",
    "table_date": "날짜", "table_wd": "요일", "table_time": "작업시간", "table_note": "메모",
    "autostart": "시작 시 자동 실행",
    "theme_label": "테마", "theme_light": "라이트", "theme_dark": "다크",
    "expand_btn": "펼치기", "collapse_btn": "접기",
    "color_active": "활동 색상", "color_clock_bg": "시계 배경", "color_center": "중앙점",
    "color_reset": "기본값으로 초기화",
    "export_range": "기간",
    "icon_label": "아이콘",
    "range_label_prompt": "날짜 묶음 이름 (빈칸이면 취소):",
    "total_label": "총 작업시간",
    "recording_now": "지금 기록중",
    "clock_bg_label": "시계 배경 이미지",
    "clock_bg_pick": "선택",
    "clock_bg_clear": "지우기",
    "clock_bg_none": "없음",
    "icon_add": "+ 추가",
    "month_names": None,
}
LANG_EN = {
    "prev": "‹", "today": "Today", "next": "›",
    "export": "Export", "settings": "Settings",
    "year_view": "Year View", "month_view": "Month",
    "total_month": "Monthly total", "total": "Total",
    "intervals": "Sessions", "no_record": "No records yet.",
    "memo": "Memo", "memo_save": "Save",
    "export_title": "Export Records", "export_format": "Select format",
    "fmt_simple": "Simple (date·time)", "fmt_table": "Table (Notion/Docs)",
    "fmt_detail": "Detail (with sessions)",
    "export_done": "Export Done", "export_saved": "Saved:\n{}",
    "export_err": "Error", "reset_title": "Reset Data",
    "reset_confirm": "All work records will be deleted.\nAre you sure?",
    "reset_done": "Reset complete", "settings_title": "Settings",
    "lang_label": "Language", "idle_label": "Idle threshold (min)",
    "data_path": "Open data folder", "reset_btn": "Reset all data",
    "weekdays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    "made_by": "Made by Jin (AI Agent) · Utobit",
    "year": "", "month_unit": "", "day_unit": "",
    "weekday_names": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "export_header": "WorkTimer Records", "export_time": "Exported:",
    "no_data": "No records",
    "table_date": "Date", "table_wd": "Day", "table_time": "Hours", "table_note": "Memo",
    "autostart": "Run at startup",
    "theme_label": "Theme", "theme_light": "Light", "theme_dark": "Dark",
    "expand_btn": "Expand", "collapse_btn": "Collapse",
    "color_active": "Active", "color_clock_bg": "Clock BG", "color_center": "Center",
    "color_reset": "Reset to defaults",
    "export_range": "Period",
    "icon_label": "Icon",
    "range_label_prompt": "Range name (empty to cancel):",
    "total_label": "Total",
    "recording_now": "Recording...",
    "clock_bg_label": "Clock Background Image",
    "clock_bg_pick": "Pick",
    "clock_bg_clear": "Clear",
    "clock_bg_none": "None",
    "icon_add": "+ Add",
    "month_names": ["January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"],
}
LANGUAGES = {"한국어": LANG_KO, "English": LANG_EN}

# ── 유틸 ────────────────────────────────────────────────
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

_user32   = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

def now_local() -> datetime:
    return datetime.now().replace(microsecond=0)

def get_idle_seconds() -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not _user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    return max(0.0, (_kernel32.GetTickCount64() - info.dwTime) / 1000.0)

def date_key(d: date) -> str:
    return d.isoformat()

def seconds_from_midnight(dt: datetime) -> int:
    return dt.hour * 3600 + dt.minute * 60 + dt.second

def seconds_to_hhmm(s: int) -> str:
    s = max(0, int(s))
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"

def split_interval_by_day(start: datetime, end: datetime) -> list[tuple[str, int, int]]:
    if end <= start:
        return []
    pieces: list[tuple[str, int, int]] = []
    cursor = start
    while cursor.date() < end.date():
        midnight = datetime.combine(cursor.date() + timedelta(days=1), dt_time.min)
        pieces.append((date_key(cursor.date()), seconds_from_midnight(cursor), 86400))
        cursor = midnight
    pieces.append((date_key(cursor.date()), seconds_from_midnight(cursor), seconds_from_midnight(end)))
    return [(d, s, e) for d, s, e in pieces if e > s]

def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    clean = sorted((max(0, int(s)), min(86400, int(e))) for s, e in intervals if e > s)
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

# ── 설정 ────────────────────────────────────────────────
def load_settings() -> dict:
    try:
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def save_settings(s: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")

def set_autostart(enable: bool) -> None:
    if not getattr(sys, "frozen", False):
        return
    exe = f'"{sys.executable}"'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, exe)
        else:
            try: winreg.DeleteValue(key, APP_REG_NAME)
            except FileNotFoundError: pass
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

# ── 데이터 ──────────────────────────────────────────────
def prepare_data_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists() and LEGACY_DATA_FILE.exists():
        try:
            DATA_FILE.write_text(LEGACY_DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
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
    merges: dict[str, list[list[int]]]
    ranges: list[dict]

    @classmethod
    def load(cls) -> "WorkLog":
        prepare_data_storage()
        if not DATA_FILE.exists():
            return cls(days={}, notes={}, merges={}, ranges=[])
        try:
            payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            days = payload.get("days", {})
            parsed: dict[str, list[list[int]]] = {}
            for key, value in days.items():
                if isinstance(value, list):
                    parsed[key] = merge_intervals(value)
            notes = payload.get("notes", {})
            if not isinstance(notes, dict): notes = {}
            merges_raw = payload.get("merges", {})
            merges = {k: v for k, v in merges_raw.items() if isinstance(v, list)} if isinstance(merges_raw, dict) else {}
            ranges = payload.get("ranges", [])
            return cls(days=parsed, notes={str(k): str(v) for k, v in notes.items()},
                       merges=merges, ranges=ranges if isinstance(ranges, list) else [])
        except Exception:
            backup = DATA_FILE.with_suffix(f".broken-{int(time.time())}.json")
            DATA_FILE.replace(backup)
            return cls(days={}, notes={}, merges={}, ranges=[])

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            backup_data_file("before-save")
        payload = {
            "schema": 1, "updated_at": now_local().isoformat(),
            "days": self.days, "notes": self.notes,
            "merges": self.merges, "ranges": self.ranges,
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
        if note: self.notes[key] = note
        else: self.notes.pop(key, None)
        self.save()

    def reset(self) -> None:
        backup_data_file("before-reset")
        self.days.clear(); self.notes.clear()
        self.merges.clear(); self.ranges.clear()
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
        self.merges[key] = [g for g in self.merges.get(key, []) if g != [gap_start, gap_end]]
        if not self.merges.get(key): self.merges.pop(key, None)
        self.save()

    def ranges_for_month(self, year: int, month: int) -> list[dict]:
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        result = []
        for r in self.ranges:
            try:
                rs = date.fromisoformat(r["start"]); re = date.fromisoformat(r["end"])
                if rs <= last and re >= first:
                    result.append({**r, "start_date": rs, "end_date": re})
            except Exception: pass
        return result

    def add_range(self, start: date, end: date, label: str) -> None:
        self.ranges.append({"start": start.isoformat(), "end": end.isoformat(), "label": label})
        self.save()

    def remove_range_containing(self, d: date) -> bool:
        before = len(self.ranges)
        self.ranges = [
            r for r in self.ranges
            if not (date.fromisoformat(r["start"]) <= d <= date.fromisoformat(r["end"]))
        ]
        if len(self.ranges) < before:
            self.save(); return True
        return False

# ── 트래커 ──────────────────────────────────────────────
class ActivityTracker:
    def __init__(self, log: WorkLog, on_change, recovered_start: "datetime | None" = None) -> None:
        self.log = log
        self.on_change = on_change
        self._active_start: datetime | None = recovered_start
        self._last_activity_at: datetime | None = recovered_start
        self._last_checkpoint_write: datetime | None = None

    def _write_checkpoint(self) -> None:
        if self._active_start is None: return
        try:
            CHECKPOINT_FILE.write_text(
                json.dumps({"active_start": self._active_start.isoformat()}), encoding="utf-8")
        except Exception: pass

    def _clear_checkpoint(self) -> None:
        try: CHECKPOINT_FILE.unlink(missing_ok=True)
        except Exception: pass

    @staticmethod
    def recover_from_checkpoint(log: WorkLog) -> "datetime | None":
        if not CHECKPOINT_FILE.exists(): return None
        try:
            data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
            active_start = datetime.fromisoformat(data.get("active_start", ""))
            today = now_local().date()
            if active_start.date() < today:
                log.add_interval(active_start, datetime.combine(today, dt_time.min))
                return None
            return active_start
        except Exception: return None
        finally:
            try: CHECKPOINT_FILE.unlink(missing_ok=True)
            except Exception: pass

    def stop(self) -> None:
        if self._active_start is not None:
            self.log.add_interval(self._active_start, now_local())
        self._clear_checkpoint()

    @property
    def current_interval(self) -> tuple[datetime, datetime] | None:
        if self._active_start is None: return None
        return (self._active_start, now_local())

    def _tick(self) -> None:
        current = now_local()
        idle = get_idle_seconds()
        is_working = idle <= IDLE_GRACE_SECONDS

        if is_working:
            last_input = current - timedelta(seconds=idle)
            if self._active_start is None:
                self._active_start = last_input
            elif self._active_start.date() < current.date():
                midnight = datetime.combine(current.date(), dt_time.min)
                self.log.add_interval(self._active_start, midnight)
                self._active_start = current
                self._clear_checkpoint()
            if (self._last_checkpoint_write is None or
                    (current - self._last_checkpoint_write).total_seconds() >= 60):
                self._write_checkpoint()
                self._last_checkpoint_write = current
            self._last_activity_at = last_input
            self.on_change()
            return

        if self._active_start is not None:
            if self._active_start.date() < current.date():
                midnight = datetime.combine(current.date(), dt_time.min)
                self.log.add_interval(self._active_start, midnight)
                self._active_start = None; self._last_activity_at = None
                self._clear_checkpoint(); self.on_change(); return
            if self._last_activity_at is not None:
                grace_end = self._last_activity_at + timedelta(seconds=IDLE_GRACE_SECONDS)
                if current >= grace_end:
                    self.log.add_interval(self._active_start, self._last_activity_at)
                    self._active_start = None; self._last_activity_at = None
                    self._clear_checkpoint(); self.on_change()

# ── 우측 패널 (일간 뷰) ─────────────────────────────────
class RightPanel(QScrollArea):
    unmerge_requested = pyqtSignal(date, int, int)
    save_memo_requested = pyqtSignal(date, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._content.setObjectName("right_panel_content")
        self.setWidget(self._content)
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(14, 10, 14, 16)
        self._layout.setSpacing(0)
        self._memo_edit: QTextEdit | None = None
        self._current_day: date | None = None
        self._apply_style()

    def _apply_style(self) -> None:
        bg = P["bg"]; panel = P["panel"]; text = P["text"]; line = P["line"]
        self.setStyleSheet(f"""
            QScrollArea, QWidget#right_panel_content {{ background: {bg}; border: none; }}
            QLabel {{ background: transparent; }}
            QTextEdit {{
                background: {panel}; color: {text};
                border: 1px solid {line}; border-radius: 6px;
                padding: 6px; font-size: 13px;
            }}
            QTextEdit:focus {{ border-color: #93c5fd; }}
            QPushButton {{
                background: {P["btn_bg"]}; color: {P["btn_fg"]};
                border: 1px solid {line}; border-radius: 6px;
                padding: 4px 14px; font-size: 12px;
            }}
            QPushButton:hover {{ background: {P["btn_hover"]}; }}
        """)

    def populate(self, day: date, intervals: list[list[int]], merges: list[list[int]],
                 total_s: int, live: bool, day_header: str, note: str, L: dict) -> None:
        self._current_day = day

        # clear
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        def lbl(text_str, bold=False, color=None, size=13, top=0, bottom=0):
            l = QLabel(text_str)
            l.setWordWrap(True)
            f = QFont(); f.setPointSize(size); f.setBold(bold)
            l.setFont(f)
            style = f"color: {color or P['text']};"
            if top or bottom:
                style += f" margin-top: {top}px; margin-bottom: {bottom}px;"
            l.setStyleSheet(style)
            return l

        def sep(top=6, bottom=4):
            container = QWidget()
            vl = QVBoxLayout(container)
            vl.setContentsMargins(0, top, 0, bottom)
            vl.setSpacing(0)
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet(f"background: {P['line']}; border: none;")
            line.setFixedHeight(1)
            vl.addWidget(line)
            return container

        # 날짜 헤더
        if day_header:
            self._layout.addWidget(lbl(day_header, bold=True, size=13, bottom=1))

        # 총 작업시간 — 1칸 들여쓰기
        total_row = QWidget()
        total_lay = QHBoxLayout(total_row)
        total_lay.setContentsMargins(4, 0, 0, 6)
        total_lbl = QLabel(f"{L['total_label']}   {seconds_to_hhmm(total_s)}")
        f_t = QFont(); f_t.setPointSize(12); f_t.setBold(True)
        total_lbl.setFont(f_t)
        total_lbl.setStyleSheet("color: #60a5fa;")
        total_lay.addWidget(total_lbl)
        total_lay.addStretch()
        self._layout.addWidget(total_row)

        self._layout.addWidget(sep(top=2, bottom=6))

        # 기록 구간 헤더
        self._layout.addWidget(lbl(L["intervals"], bold=True, size=15, top=10, bottom=6))

        groups = self._group_intervals(day, intervals, merges)
        if not groups:
            self._layout.addWidget(lbl(f"  {L['no_record']}", color=P["muted"], size=12))
        else:
            last_idx = len(groups) - 1
            for gi, g in enumerate(groups):
                is_last = (gi == last_idx)
                if g["merged"]:
                    s = g["intervals"][0][0]; e = g["intervals"][-1][1]
                    row = QFrame()
                    row.setStyleSheet(f"background: {P['merged_bg']}; border-radius: 5px; border: none;")
                    rlay = QHBoxLayout(row)
                    rlay.setContentsMargins(10, 5, 6, 5)
                    tl = QLabel(f"  {seconds_to_hhmm(s)} – {seconds_to_hhmm(e)}")
                    tl.setStyleSheet(f"color: {P['text']}; font-size: 13px; background: transparent;")
                    rlay.addWidget(tl)
                    if live and is_last:
                        ll = QLabel(L["recording_now"])
                        ll.setStyleSheet("color: #60a5fa; font-size: 11px; background: transparent;")
                        rlay.addWidget(ll)
                    rlay.addStretch()
                    gaps = list(g["gaps"])
                    xb = QPushButton("✕")
                    xb.setFixedSize(20, 20)
                    xb.setStyleSheet("background: transparent; border: none; color: #94a3b8; font-size: 10px; padding: 0;")
                    xb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    def mk_unmerge(d=day, gs=gaps):
                        def fn():
                            for gap_s, gap_e in gs:
                                self.unmerge_requested.emit(d, gap_s, gap_e)
                        return fn
                    xb.clicked.connect(mk_unmerge())
                    rlay.addWidget(xb)
                    wrapper = QWidget()
                    wl = QVBoxLayout(wrapper)
                    wl.setContentsMargins(0, 2, 0, 2)
                    wl.addWidget(row)
                    self._layout.addWidget(wrapper)
                else:
                    s, e = g["intervals"][0]
                    row = QWidget()
                    rl = QHBoxLayout(row)
                    rl.setContentsMargins(4, 2, 0, 2)
                    tl = QLabel(f"  {seconds_to_hhmm(s)} – {seconds_to_hhmm(e)}")
                    tl.setStyleSheet(f"color: {P['text']}; font-size: 13px;")
                    rl.addWidget(tl)
                    if live and is_last:
                        ll = QLabel(L["recording_now"])
                        ll.setStyleSheet("color: #60a5fa; font-size: 11px;")
                        rl.addWidget(ll)
                    rl.addStretch()
                    self._layout.addWidget(row)

        self._layout.addWidget(sep(top=16, bottom=8))

        # 메모
        self._layout.addWidget(lbl(L["memo"], bold=True, size=15, bottom=4))
        self._memo_edit = QTextEdit()
        self._memo_edit.setPlainText(note)
        self._memo_edit.setFixedHeight(90)
        self._memo_edit.setAcceptRichText(False)
        self._layout.addWidget(self._memo_edit)

        save_btn = QPushButton(L["memo_save"])
        save_btn.setFixedWidth(60)
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.clicked.connect(lambda checked=False, d=day: self._save_memo(d))
        btn_row = QWidget()
        bl = QHBoxLayout(btn_row)
        bl.setContentsMargins(0, 4, 0, 0)
        bl.addStretch()
        bl.addWidget(save_btn)
        self._layout.addWidget(btn_row)
        self._layout.addStretch()

    def _save_memo(self, d: date) -> None:
        if self._memo_edit is None:
            return
        try:
            self.save_memo_requested.emit(d, self._memo_edit.toPlainText())
        except RuntimeError:
            pass

    def _group_intervals(self, day: date, intervals: list[list[int]],
                         merges: list[list[int]]) -> list[dict]:
        if not intervals: return []
        groups: list[dict] = []
        used: set[int] = set()

        for merge_gap in merges:
            gap_s, gap_e = merge_gap
            # Find intervals immediately before and after the gap
            before = [i for i, iv in enumerate(intervals) if i not in used and iv[1] <= gap_s]
            after  = [i for i, iv in enumerate(intervals) if i not in used and iv[0] >= gap_e]
            if before and after and before[-1] < after[0]:
                idxs = list(range(before[-1], after[0] + 1))
                if all(j not in used for j in idxs):
                    used.update(idxs)
                    groups.append({
                        "merged": True,
                        "intervals": [intervals[j] for j in idxs],
                        "gaps": [merge_gap],
                    })

        for i, iv in enumerate(intervals):
            if i not in used:
                groups.append({"merged": False, "intervals": [iv], "gaps": []})
        groups.sort(key=lambda g: g["intervals"][0][0])
        return groups

# ── 메인 드로잉 위젯 ─────────────────────────────────────
class DrawingWidget(QWidget):
    day_clicked = pyqtSignal(date)

    def __init__(self, app_ref: "WorkTimerApp", parent=None):
        super().__init__(parent)
        self._app = app_ref
        self.setMouseTracking(True)

        # 일간 뷰 상태
        self._day_cx = 0.0; self._day_cy = 0.0; self._day_r = 0.0
        self._day_intervals: list[list[int]] = []
        self._press_x = 0; self._press_y = 0
        self._merge_drag_active = False
        self._drag_interval_idx = -1
        self._drag_current_sec = -1  # 드래그 중 현재 위치 (시각 피드백용)

        # 월간 뷰 상태
        self._day_hitboxes: list[tuple[float, float, float, float, date]] = []
        self._cal_press_day: date | None = None

        # 날짜 범위 선택 (Ctrl+드래그)
        self._range_start: date | None = None
        self._range_end: date | None = None
        self._range_dragging = False

        # 연간 뷰
        self._year_month_hitboxes: list[tuple[float, float, float, float, int, int]] = []

        # 우측 패널
        self._right_panel = RightPanel(self)
        self._right_panel.hide()
        self._right_panel.unmerge_requested.connect(self._on_unmerge)
        self._right_panel.save_memo_requested.connect(self._on_save_memo)

    def _on_unmerge(self, d: date, gs: int, ge: int) -> None:
        self._app.log.remove_merge(d, gs, ge)
        self._app.redraw()

    def _on_save_memo(self, d: date, text: str) -> None:
        self._app.log.set_note_for(d, text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._app.schedule_redraw()

    def refresh_day_panel(self, d: date, intervals: list[list[int]], merges: list[list[int]],
                          total_s: int, live: bool, day_header: str, note: str) -> None:
        # 메모 편집 중이면 재구성 건너뜀
        if (self._right_panel._current_day == d and
                self._right_panel._memo_edit is not None and
                self._right_panel._memo_edit.hasFocus()):
            return
        self._right_panel._apply_style()
        self._right_panel.populate(d, intervals, merges, total_s, live, day_header, note,
                                   self._app.L)

    # ── 페인트 진입점 ──────────────────────────────────
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), pc("bg"))

        view = self._app.view
        if view == "month":
            self._right_panel.hide()
            self._draw_month(painter)
        elif view == "multi_month":
            self._right_panel.hide()
            self._draw_multi_month(painter)
        elif view == "day":
            self._draw_day_clock(painter)
        elif view == "year":
            self._right_panel.hide()
            self._draw_year(painter)
        elif view == "multi_year":
            self._right_panel.hide()
            self._draw_multi_year(painter)

    # ── 월간 뷰 ───────────────────────────────────────
    def _draw_month_grid(self, painter: QPainter, year: int, month: int,
                         area_x: float, area_y: float, area_w: float, area_h: float,
                         collect_hitboxes: bool = True) -> None:
        """단일 월 달력을 (area_x, area_y, area_w, area_h) 안에 그린다."""
        app = self._app; L = app.L
        today = date.today()

        cal = calendar.monthcalendar(year, month)
        rows = len(cal)
        wdays = L["weekdays"]

        pad = 4
        header_h = 24
        grid_top = area_y + header_h + pad
        grid_h = area_y + area_h - grid_top - pad
        cell_w = area_w / 7
        cell_h = grid_h / rows

        # 요일 헤더
        font_wd = QFont(); font_wd.setPointSize(9); font_wd.setBold(True)
        painter.setFont(font_wd)
        for col, wd in enumerate(wdays):
            x = area_x + col * cell_w
            color = "#ef4444" if col == 0 else "#3b82f6" if col == 6 else P["muted"]
            painter.setPen(QColor(color))
            painter.drawText(QRectF(x, area_y, cell_w, header_h),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, wd)

        ranges = app.log.ranges_for_month(year, month)

        for row_i, week in enumerate(cal):
            for col_i, day_num in enumerate(week):
                if day_num == 0:
                    continue
                d = date(year, month, day_num)
                cx = area_x + col_i * cell_w
                cy = grid_top + row_i * cell_h
                cell_rect = QRectF(cx + 1, cy + 1, cell_w - 2, cell_h - 2)

                # 범위 선택 중 하이라이트
                in_drag_range = False
                if self._range_dragging and self._range_start and self._range_end:
                    lo = min(self._range_start, self._range_end)
                    hi = max(self._range_start, self._range_end)
                    in_drag_range = lo <= d <= hi

                # 날짜 묶음 범위
                in_range = any(r["start_date"] <= d <= r["end_date"] for r in ranges)
                range_label = next((r["label"] for r in ranges if r["start_date"] <= d <= r["end_date"]), "")

                is_today = (d == today)

                # 셀 배경
                if in_drag_range:
                    painter.setPen(QPen(QColor(P["range_border"]), 1.5))
                    painter.setBrush(QColor(P["range_bg"]))
                elif is_today:
                    painter.setPen(QPen(QColor(P["today_border"]), 2.0))
                    painter.setBrush(QColor(P["panel"]))
                else:
                    painter.setPen(QPen(QColor(P["line"]), 0.8))
                    painter.setBrush(QColor(P["panel"]))
                painter.drawRoundedRect(cell_rect, 5, 5)

                # 범위 band (상단 줄)
                if in_range:
                    band = QRectF(cx + 2, cy + 2, cell_w - 4, 4)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(P["range_border"]))
                    painter.drawRoundedRect(band, 2, 2)

                if collect_hitboxes:
                    self._day_hitboxes.append((cx + 1, cy + 1, cx + cell_w - 1, cy + cell_h - 1, d))

                # 미니 클럭
                intervals = app.log.intervals_for(d)
                live = (d == today and app.tracker.current_interval is not None)
                if live:
                    ci = app.tracker.current_interval
                    display_ivs = merge_intervals(intervals + [[seconds_from_midnight(ci[0]), seconds_from_midnight(ci[1])]])
                else:
                    display_ivs = intervals
                total_s = sum(e - s for s, e in display_ivs)

                clock_r = min(cell_w * 0.28, cell_h * 0.28)
                clock_cx = cx + cell_w * 0.5
                clock_cy = cy + cell_h * 0.5 + 4
                self._draw_clock(painter, clock_cx, clock_cy, clock_r, display_ivs,
                                 P["clock"], mini=True, live=live)

                # 날짜 숫자
                font_day = QFont(); font_day.setPointSize(9); font_day.setBold(is_today)
                painter.setFont(font_day)
                painter.setPen(QColor(P["today_border"] if is_today else P["text"]))
                painter.drawText(QRectF(cx + 4, cy + 3, cell_w - 8, 16),
                                 Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, str(day_num))

                # 작업 시간
                if total_s > 0:
                    font_t = QFont(); font_t.setPointSize(8)
                    painter.setFont(font_t)
                    painter.setPen(QColor(P["active_dark"] if is_today else P["muted"]))
                    painter.drawText(QRectF(cx + 2, cy + cell_h - 14, cell_w - 4, 12),
                                     Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                                     seconds_to_hhmm(total_s))

    def _draw_month(self, painter: QPainter) -> None:
        self._day_hitboxes = []
        w = self.width(); h = self.height()
        pad = 12
        self._draw_month_grid(painter, self._app.year, self._app.month,
                              pad, pad, w - pad * 2, h - pad * 2,
                              collect_hitboxes=True)

    def _draw_multi_month(self, painter: QPainter) -> None:
        """이전·이번·다음 달 3개를 가로로 나란히 표시."""
        self._day_hitboxes = []
        app = self._app
        w = self.width(); h = self.height()
        pad = 8
        col_w = (w - pad * 4) / 3

        months = []
        for delta in (-1, 0, 1):
            yr, mo = app.year, app.month
            mo += delta
            if mo < 1:   yr -= 1; mo += 12
            if mo > 12:  yr += 1; mo -= 12
            months.append((yr, mo))

        for i, (yr, mo) in enumerate(months):
            ax = pad + i * (col_w + pad)
            ay = pad

            # 월 제목
            font_mo = QFont(); font_mo.setPointSize(11); font_mo.setBold(True)
            painter.setFont(font_mo)
            center_color = P["active"] if (yr == app.year and mo == app.month) else P["text"]
            painter.setPen(QColor(center_color))
            mo_names = app.L.get("month_names")
            mo_label = f"{mo_names[mo - 1]} {yr}" if mo_names else f"{yr}년 {mo}월"
            painter.drawText(QRectF(ax, ay, col_w, 22),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                             mo_label)

            # 구분선 (현재 달 제외)
            if i != 1:
                painter.setPen(QPen(QColor(P["line"]), 1))
                if i == 0:
                    painter.drawLine(QPointF(ax + col_w + pad / 2, ay),
                                     QPointF(ax + col_w + pad / 2, ay + h - pad * 2))

            self._draw_month_grid(painter, yr, mo,
                                  ax, ay + 26, col_w, h - ay - 26 - pad,
                                  collect_hitboxes=True)

    # ── 일간 뷰 (시계만 그림, 패널 populate는 redraw()에서) ──
    def _draw_day_clock(self, painter: QPainter) -> None:
        app = self._app
        d = app.detail_day
        if d is None: return
        w = self.width(); h = self.height()
        today = date.today()

        right_panel_w = min(260, int(w * 0.35))
        pad = 20
        clock_area_w = w - right_panel_w - pad * 2
        cx = pad + clock_area_w / 2
        cy = h / 2
        radius = min(clock_area_w / 2, (h - 80) / 2) * 0.85

        intervals = app.log.intervals_for(d)
        live = (d == today and app.tracker.current_interval is not None)
        if live:
            ci = app.tracker.current_interval
            display_ivs = merge_intervals(intervals + [[seconds_from_midnight(ci[0]), seconds_from_midnight(ci[1])]])
        else:
            display_ivs = list(intervals)

        self._day_cx = cx; self._day_cy = cy; self._day_r = radius
        self._day_intervals = list(display_ivs)

        self._draw_clock(painter, cx, cy, radius, display_ivs, P["clock"], mini=False, live=live)
        self._draw_hour_labels(painter, cx, cy, radius)

        # 드래그 중 선 피드백
        if self._merge_drag_active and self._drag_interval_idx >= 0 and self._drag_current_sec >= 0:
            sec = self._drag_current_sec
            angle = math.radians(90 - (sec / 86400) * 360)
            x2 = cx + math.cos(angle) * radius * 0.96
            y2 = cy - math.sin(angle) * radius * 0.96
            painter.setPen(QPen(QColor("#f59e0b"), 2, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(cx, cy), QPointF(x2, y2))

        # 우측 패널 위치
        panel_x = int(w - right_panel_w - pad)
        panel_y = pad
        panel_h = h - pad * 2
        self._right_panel.setGeometry(panel_x, panel_y, right_panel_w, panel_h)
        if not self._right_panel.isVisible():
            self._right_panel.show()

    # ── 연간 뷰 ───────────────────────────────────────
    def _draw_year(self, painter: QPainter) -> None:
        """단일 연도 — 4열×3행으로 12개월 히트맵."""
        self._draw_year_impl(painter, [self._app.year_year])

    def _draw_multi_year(self, painter: QPainter) -> None:
        """3개년 — 이전·현재·다음 나란히."""
        yr = self._app.year_year
        self._draw_year_impl(painter, [yr - 1, yr, yr + 1])

    def _draw_year_impl(self, painter: QPainter, years: list[int]) -> None:
        app = self._app; L = app.L
        center_yr = app.year_year
        w = self.width(); h = self.height()
        self._year_month_hitboxes = []
        today = date.today()
        n_cols = len(years)
        col_pad = 10
        yr_pad_top = 8

        if n_cols == 1:
            # 단일 연도: 4열×3행
            yr = years[0]
            mo_cols = 4; mo_rows = 3
            mo_top = yr_pad_top + 28
            mo_w = (w - col_pad * 2) / mo_cols
            mo_h = (h - mo_top - col_pad) / mo_rows
            mo_names = L.get("month_names")

            font_yr = QFont(); font_yr.setPointSize(14); font_yr.setBold(True)
            painter.setFont(font_yr)
            painter.setPen(QColor(P["text"]))
            painter.drawText(QRectF(0, yr_pad_top, w, 24),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, str(yr))

            for mo in range(1, 13):
                mc = (mo - 1) % mo_cols
                mr = (mo - 1) // mo_cols
                mx = col_pad + mc * mo_w
                my = mo_top + mr * mo_h
                self._draw_year_month(painter, yr, mo, mx, my, mo_w, mo_h, today, mo_names)
        else:
            # 다중 연도: 연도별 열
            col_w = (w - col_pad * (n_cols + 1)) / n_cols
            mo_cols = 3; mo_rows = 4
            mo_names = L.get("month_names")

            for yi, yr in enumerate(years):
                col_x = col_pad + yi * (col_w + col_pad)
                font_yr = QFont(); font_yr.setPointSize(12); font_yr.setBold(True)
                painter.setFont(font_yr)
                yr_color = P["active"] if yr == center_yr else P["text"]
                painter.setPen(QColor(yr_color))
                painter.drawText(QRectF(col_x, yr_pad_top, col_w, 22),
                                 Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, str(yr))
                if yi > 0:
                    painter.setPen(QPen(QColor(P["line"]), 1))
                    painter.drawLine(QPointF(col_x - col_pad / 2, yr_pad_top),
                                     QPointF(col_x - col_pad / 2, h - col_pad))
                mo_top = yr_pad_top + 26
                mo_w = col_w / mo_cols
                mo_h = (h - mo_top - col_pad) / mo_rows
                for mo in range(1, 13):
                    mc = (mo - 1) % mo_cols
                    mr = (mo - 1) // mo_cols
                    mx = col_x + mc * mo_w
                    my = mo_top + mr * mo_h
                    self._draw_year_month(painter, yr, mo, mx, my, mo_w, mo_h, today, mo_names)

    def _draw_year_month(self, painter: QPainter, yr: int, mo: int,
                         mx: float, my: float, mo_w: float, mo_h: float,
                         today: date, mo_names) -> None:
        app = self._app
        mo_lbl = mo_names[mo - 1][:3] if mo_names else f"{mo}월"
        font_mo = QFont(); font_mo.setPointSize(7)
        painter.setFont(font_mo)
        painter.setPen(QColor(P["muted"]))
        painter.drawText(QRectF(mx, my, mo_w, 13),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, mo_lbl)
        cal = calendar.monthcalendar(yr, mo)
        n_weeks = len(cal)
        avail_h = mo_h - 13
        avail_w = mo_w - 2
        day_sz = min(avail_w / 7, avail_h / n_weeks)
        grid_x = mx + (avail_w - day_sz * 7) / 2 + 1
        grid_y = my + 13
        max_s = max((app.log.total_seconds_for(date(yr, mo, d))
                     for week in cal for d in week if d != 0), default=1) or 1
        self._year_month_hitboxes.append((mx, my, mx + mo_w, my + mo_h, yr, mo))
        for r_i, week in enumerate(cal):
            for c_i, day_num in enumerate(week):
                if day_num == 0: continue
                d = date(yr, mo, day_num)
                total = app.log.total_seconds_for(d)
                dx = grid_x + c_i * day_sz
                dy = grid_y + r_i * day_sz
                ratio = total / max_s if max_s > 0 else 0
                sz = max(day_sz - 1, 1)
                if total > 0:
                    base = QColor(P["active"]); base.setAlphaF(0.2 + 0.8 * ratio)
                    painter.fillRect(QRectF(dx + 0.5, dy + 0.5, sz, sz), base)
                else:
                    painter.fillRect(QRectF(dx + 0.5, dy + 0.5, sz, sz), QColor(P["line"]))
                if d == today:
                    painter.setPen(QPen(QColor(P["today_border"]), 1))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(QRectF(dx + 0.5, dy + 0.5, sz, sz))

    # ── 시계 그리기 ───────────────────────────────────
    def _draw_clock(self, painter: QPainter, cx: float, cy: float, radius: float,
                    intervals: list[list[int]], fill: str,
                    mini: bool = False, live: bool = False) -> None:
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(fill))
        painter.drawEllipse(rect)

        bg_pix = getattr(self._app, "_clock_bg_pixmap", None)
        if bg_pix:
            painter.save()
            clip = QPainterPath()
            clip.addEllipse(rect)
            painter.setClipPath(clip)
            painter.setOpacity(0.65 if mini else 0.82)
            painter.drawPixmap(rect.toRect(), bg_pix)
            painter.setOpacity(1.0)
            painter.restore()
        has_bg = bool(bg_pix)

        for i, (s, e) in enumerate(intervals):
            dur = e - s
            if dur <= 0: continue
            is_live_seg = live and (i == len(intervals) - 1)
            color = QColor(P["active"])
            if is_live_seg:
                color = QColor(P["active"]); color.setAlphaF(0.65)
            if has_bg:
                color.setAlphaF(color.alphaF() * 0.80)

            if dur < 120 and not mini:
                mid = (s + e) / 2
                angle = math.radians(90 - (mid / 86400) * 360)
                x1 = cx + math.cos(angle) * radius * 0.1
                y1 = cy - math.sin(angle) * radius * 0.1
                x2 = cx + math.cos(angle) * radius * 0.97
                y2 = cy - math.sin(angle) * radius * 0.97
                painter.setPen(QPen(color, 2))
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                continue
            if mini and dur < 120:
                continue

            start_angle = int((90 - s / 86400 * 360) * 16)
            span_angle  = int(-(e - s) / 86400 * 360 * 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawPie(rect, start_angle, span_angle)

        painter.setPen(QPen(QColor(P["clock_line"]), 1.5 if not mini else 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)

        if not mini:
            for hour in range(0, 24, 3):
                angle = math.radians(90 - (hour / 24) * 360)
                major = hour % 6 == 0
                inner = 0.82 if major else 0.90
                x1 = cx + math.cos(angle) * radius * inner
                y1 = cy - math.sin(angle) * radius * inner
                x2 = cx + math.cos(angle) * radius * 0.96
                y2 = cy - math.sin(angle) * radius * 0.96
                painter.setPen(QPen(QColor(P["clock_line"]), 1.2))
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        else:
            for hour in (0, 6, 12, 18):
                angle = math.radians(90 - (hour / 24) * 360)
                x1 = cx + math.cos(angle) * radius * 0.80
                y1 = cy - math.sin(angle) * radius * 0.80
                x2 = cx + math.cos(angle) * radius * 0.96
                y2 = cy - math.sin(angle) * radius * 0.96
                painter.setPen(QPen(QColor(P["clock_line"]), 0.8))
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        if not mini:
            cr = 4
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(P["center"]))
            painter.drawEllipse(QRectF(cx - cr, cy - cr, cr * 2, cr * 2))

    def _draw_hour_labels(self, painter: QPainter, cx: float, cy: float, radius: float) -> None:
        font = QFont(); font.setPointSize(9); font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#334155" if self._app._theme == "light" else "#94a3b8"))
        for hour in range(0, 24, 3):
            angle = math.radians(90 - (hour / 24) * 360)
            tx = cx + math.cos(angle) * radius * 1.14
            ty = cy - math.sin(angle) * radius * 1.14
            painter.drawText(QRectF(tx - 16, ty - 10, 32, 20),
                             Qt.AlignmentFlag.AlignCenter, f"{hour:02d}")

    # ── 마우스 이벤트 ──────────────────────────────────
    def _hit_day(self, x, y) -> date | None:
        for x1, y1, x2, y2, d in self._day_hitboxes:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return d
        return None

    def mousePressEvent(self, event) -> None:
        self._press_x = event.pos().x()
        self._press_y = event.pos().y()
        self._merge_drag_active = False
        self._drag_interval_idx = -1
        self._drag_current_sec = -1

        app = self._app
        x, y = event.pos().x(), event.pos().y()
        ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier

        if app.view == "day":
            if event.button() == Qt.MouseButton.LeftButton and self._is_on_clock(x, y):
                sec = self._clock_pos_to_sec(x, y)
                idx = self._sec_to_interval_idx(sec)
                if idx >= 0:
                    self._drag_interval_idx = idx
                    self._merge_drag_active = True
            return

        if app.view in ("year", "multi_year"):
            for x1, y1, x2, y2, yr, mo in self._year_month_hitboxes:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    app.year = yr; app.month = mo
                    app.view = "month"; app.detail_day = None
                    app.redraw(); return
            return

        # month / multi_month
        d = self._hit_day(x, y)
        if d:
            if ctrl:
                # Ctrl+클릭 → 범위 선택 시작
                self._range_start = d
                self._range_end = d
                self._range_dragging = True
            else:
                self._cal_press_day = d
                self._range_dragging = False
        else:
            self._cal_press_day = None

    def mouseMoveEvent(self, event) -> None:
        app = self._app
        x, y = event.pos().x(), event.pos().y()

        if app.view == "day" and self._merge_drag_active:
            sec = self._clock_pos_to_sec(x, y)
            self._drag_current_sec = sec
            self.update()
            return

        if self._range_dragging and app.view in ("month", "multi_month"):
            d = self._hit_day(x, y)
            if d:
                self._range_end = d
                self.update()

    def mouseReleaseEvent(self, event) -> None:
        app = self._app
        x, y = event.pos().x(), event.pos().y()

        if app.view == "day" and self._merge_drag_active:
            sec = self._clock_pos_to_sec(x, y)
            idx = self._sec_to_interval_idx(sec)
            if idx >= 0 and idx != self._drag_interval_idx:
                lo = min(self._drag_interval_idx, idx)
                hi = max(self._drag_interval_idx, idx)
                ivs = self._day_intervals
                if lo + 1 <= hi < len(ivs):
                    gap_s = ivs[lo][1]; gap_e = ivs[hi][0]
                    app.log.add_merge(app.detail_day, gap_s, gap_e)
                    app.redraw()
            self._merge_drag_active = False
            self._drag_current_sec = -1
            self.update()
            return

        if self._range_dragging:
            self._range_dragging = False
            if self._range_start and self._range_end:
                lo = min(self._range_start, self._range_end)
                hi = max(self._range_start, self._range_end)
                # 라벨 입력 다이얼로그
                label, ok = QInputDialog.getText(self, "날짜 묶음", app.L["range_label_prompt"])
                if ok and label.strip():
                    app.log.add_range(lo, hi, label.strip())
                    app.redraw()
            self._range_start = None; self._range_end = None
            self.update()
            return

        if app.view in ("month", "multi_month") and self._cal_press_day:
            dx = abs(x - self._press_x); dy = abs(y - self._press_y)
            if dx < 6 and dy < 6:
                if event.button() == Qt.MouseButton.RightButton:
                    # 우클릭 → 범위 삭제
                    if app.log.remove_range_containing(self._cal_press_day):
                        app.redraw()
                else:
                    app.open_day(self._cal_press_day)
            self._cal_press_day = None

    def contextMenuEvent(self, event) -> None:
        # 우클릭 메뉴 (범위 삭제)
        app = self._app
        if app.view in ("month", "multi_month"):
            d = self._hit_day(event.pos().x(), event.pos().y())
            if d and any(r["start_date"] <= d <= r["end_date"]
                         for r in app.log.ranges_for_month(app.year, app.month)):
                from PyQt6.QtWidgets import QMenu as _QMenu
                menu = _QMenu(self)
                menu.addAction("날짜 묶음 삭제", lambda: (app.log.remove_range_containing(d), app.redraw()))
                menu.exec(event.globalPos())

    def _is_on_clock(self, x: float, y: float) -> bool:
        if self._day_r <= 0: return False
        return (x - self._day_cx) ** 2 + (y - self._day_cy) ** 2 <= self._day_r ** 2

    def _clock_pos_to_sec(self, x: float, y: float) -> int:
        angle_deg = math.degrees(math.atan2(self._day_cy - y, x - self._day_cx))
        frac = (90 - angle_deg) % 360 / 360
        return int(frac * 86400)

    def _sec_to_interval_idx(self, sec: int) -> int:
        for i, (s, e) in enumerate(self._day_intervals):
            if s <= sec <= e: return i
        return -1

# ── 설정 다이얼로그 ──────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, app_ref: "WorkTimerApp", parent=None):
        super().__init__(parent)
        self._app = app_ref
        L = app_ref.L
        self.setWindowTitle(L["settings_title"])
        self.setFixedWidth(380)
        self.setModal(True)
        self._icon_idx = app_ref._icon_idx
        self._build()
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{ background: {P['bg']}; }}
            QLabel {{ color: {P['text']}; background: transparent; }}
            QComboBox, QSpinBox {{
                background: {P['panel']}; color: {P['text']};
                border: 1px solid {P['line']}; border-radius: 5px; padding: 4px 8px;
            }}
            QComboBox QAbstractItemView {{
                background: {P['panel']}; color: {P['text']};
                selection-background-color: {P['active']};
                selection-color: #ffffff;
                border: 1px solid {P['line']};
                outline: none;
            }}
            QCheckBox {{ color: {P['text']}; }}
            QPushButton {{
                background: {P['btn_bg']}; color: {P['btn_fg']};
                border: 1px solid {P['line']}; border-radius: 6px; padding: 6px 14px;
            }}
            QPushButton:hover {{ background: {P['btn_hover']}; }}
        """)

    def _build(self) -> None:
        app = self._app; L = app.L
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        def row(label_text, widget):
            r = QWidget(); lay = QHBoxLayout(r)
            lay.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label_text); lbl.setFixedWidth(120)
            lay.addWidget(lbl); lay.addWidget(widget)
            return r

        # 언어
        lang_cb = QComboBox()
        for k in LANGUAGES: lang_cb.addItem(k)
        lang_cb.setCurrentText(app._lang_name)
        layout.addWidget(row(L["lang_label"], lang_cb))

        # 테마
        theme_cb = QComboBox()
        theme_cb.addItems([L["theme_light"], L["theme_dark"]])
        theme_cb.setCurrentIndex(0 if app._theme == "light" else 1)
        layout.addWidget(row(L["theme_label"], theme_cb))

        # 유휴 감지 시간
        idle_spin = QSpinBox()
        idle_spin.setRange(1, 120)
        idle_spin.setValue(IDLE_GRACE_SECONDS // 60)
        layout.addWidget(row(L["idle_label"], idle_spin))

        # 자동 시작
        autostart_cb = QCheckBox(L["autostart"])
        autostart_cb.setChecked(get_autostart())
        layout.addWidget(autostart_cb)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {P['line']}; border: none;"); sep.setFixedHeight(1)
        layout.addWidget(sep)

        # 아이콘 선택
        icon_lbl = QLabel(L["icon_label"])
        icon_lbl.setStyleSheet(f"color: {P['muted']}; font-size: 11px;")
        layout.addWidget(icon_lbl)

        icon_row = QWidget(); ilay = QHBoxLayout(icon_row); ilay.setContentsMargins(0, 0, 0, 0); ilay.setSpacing(6)
        self._icon_btns: list[QPushButton] = []

        def _refresh_icon_selection(selected_idx: int) -> None:
            self._icon_idx = selected_idx
            border_sel = P["active"]
            for j, b in enumerate(self._icon_btns):
                sel = (j == selected_idx)
                b.setStyleSheet(f"border: 3px solid {border_sel if sel else 'transparent'}; border-radius: 8px; padding: 0;")

        ICON_SZ = QSize(44, 44)  # 원형 클리핑 아이콘 크기
        # 아이콘별 클립 크기: 투명 여백이 많은 아이콘은 크게 클립해서 콘텐츠가 같은 크기로 보임
        ICON_CLIP_SIZES = [44, 44, 52, 44, 44]  # icon_3(54% 투명)만 크게 클립

        for i, name in enumerate(ICON_NAMES):
            clip_sz = ICON_CLIP_SIZES[i] if i < len(ICON_CLIP_SIZES) else 44
            btn = QPushButton()
            btn.setFixedSize(48, 48)
            btn.setIcon(clip_icon_circle(load_icon(i), clip_sz))
            btn.setIconSize(ICON_SZ)
            btn.setToolTip(name)
            selected = (i == self._icon_idx)
            btn.setStyleSheet(
                f"border: 3px solid {P['active'] if selected else 'transparent'}; border-radius: 8px; padding: 0;"
            )
            btn.clicked.connect(lambda _=False, ii=i: _refresh_icon_selection(ii))
            self._icon_btns.append(btn)
            ilay.addWidget(btn)

        # 커스텀 아이콘 추가 버튼
        add_icon_btn = QPushButton(L["icon_add"])
        add_icon_btn.setFixedSize(56, 48)
        add_icon_btn.setStyleSheet(f"border: 2px dashed {P['line']}; border-radius: 8px; color: {P['muted']}; font-size: 11px;")
        def _add_custom_icon():
            path, _ = QFileDialog.getOpenFileName(
                self, "아이콘 이미지 선택", "",
                "이미지 파일 (*.png *.ico *.jpg *.jpeg *.bmp *.webp)")
            if path and path not in app._custom_icons:
                app._custom_icons.append(path)
                new_idx = len(ICON_FILES) + len(app._custom_icons) - 1
                ci_btn = QPushButton()
                ci_btn.setFixedSize(48, 48)
                ci_btn.setIcon(clip_icon_circle(QIcon(path), 44))
                ci_btn.setIconSize(ICON_SZ)
                ci_btn.setToolTip(Path(path).name)
                ci_btn.setStyleSheet("border: 3px solid transparent; border-radius: 8px; padding: 0;")
                ci_btn.clicked.connect(lambda _=False, ii=new_idx: _refresh_icon_selection(ii))
                self._icon_btns.append(ci_btn)
                # add_icon_btn은 ilay에서 마지막 항목(stretch 제외)이므로 그 앞에 삽입
                insert_pos = ilay.count() - 2  # before add_icon_btn
                ilay.insertWidget(insert_pos, ci_btn)
                _refresh_icon_selection(new_idx)
                icon_row.adjustSize()
        add_icon_btn.clicked.connect(_add_custom_icon)
        ilay.addWidget(add_icon_btn)
        ilay.addStretch()

        # 아이콘 행 수평 스크롤로 감싸기 (넘칠 경우 대비)
        icon_scroll = QScrollArea()
        icon_scroll.setWidget(icon_row)
        icon_scroll.setWidgetResizable(False)
        icon_scroll.setFixedHeight(60)
        icon_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        icon_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        icon_scroll.setFrameShape(QFrame.Shape.NoFrame)
        icon_scroll.setStyleSheet(f"background: {P['bg']}; border: none;")
        layout.addWidget(icon_scroll)

        # 시계 배경 이미지
        bg_lbl = QLabel(L["clock_bg_label"])
        bg_lbl.setStyleSheet(f"color: {P['muted']}; font-size: 11px;")
        layout.addWidget(bg_lbl)

        bg_row = QWidget(); blay = QHBoxLayout(bg_row); blay.setContentsMargins(0, 0, 0, 0); blay.setSpacing(6)
        self._bg_name_lbl = QLabel(Path(app._clock_bg_path).name if app._clock_bg_path else L["clock_bg_none"])
        self._bg_name_lbl.setStyleSheet(f"color: {P['text']}; font-size: 11px;")
        self._bg_name_lbl.setMaximumWidth(160)
        bg_pick_btn = QPushButton(L["clock_bg_pick"])
        bg_pick_btn.setFixedHeight(28)
        bg_clear_btn = QPushButton(L["clock_bg_clear"])
        bg_clear_btn.setFixedHeight(28)
        def _pick_bg():
            path, _ = QFileDialog.getOpenFileName(
                self, "시계 배경 이미지 선택", "",
                "이미지 파일 (*.png *.jpg *.jpeg *.bmp *.webp)")
            if path:
                app._clock_bg_path = path
                app._clock_bg_pixmap = QPixmap(path)
                self._bg_name_lbl.setText(Path(path).name)
        def _clear_bg():
            app._clock_bg_path = ""
            app._clock_bg_pixmap = None
            self._bg_name_lbl.setText(L["clock_bg_none"])
        bg_pick_btn.clicked.connect(_pick_bg)
        bg_clear_btn.clicked.connect(_clear_bg)
        blay.addWidget(self._bg_name_lbl)
        blay.addWidget(bg_pick_btn)
        blay.addWidget(bg_clear_btn)
        blay.addStretch()
        layout.addWidget(bg_row)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"background: {P['line']}; border: none;"); sep2.setFixedHeight(1)
        layout.addWidget(sep2)

        # 색상 설정
        color_lbl = QLabel("색상 설정")
        color_lbl.setStyleSheet(f"color: {P['muted']}; font-size: 11px;")
        layout.addWidget(color_lbl)

        def color_btn(key, label):
            btn = QPushButton(label)
            # 배경은 해당 색, 텍스트는 대비 색
            bg = P[key]
            # 어두운 색이면 흰 텍스트, 밝은 색이면 검은 텍스트
            r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            fg = "#ffffff" if luma < 140 else "#1e293b"
            btn.setStyleSheet(f"background: {bg}; color: {fg}; border: 2px solid {P['line']}; border-radius: 5px; padding: 5px 8px; font-size: 11px;")
            def pick():
                c = QColorDialog.getColor(QColor(P[key]), self)
                if c.isValid():
                    P[key] = c.name()
                    r2, g2, b2 = int(c.name()[1:3], 16), int(c.name()[3:5], 16), int(c.name()[5:7], 16)
                    luma2 = 0.299 * r2 + 0.587 * g2 + 0.114 * b2
                    fg2 = "#ffffff" if luma2 < 140 else "#1e293b"
                    btn.setStyleSheet(f"background: {P[key]}; color: {fg2}; border: 2px solid {P['line']}; border-radius: 5px; padding: 5px 8px; font-size: 11px;")
            btn.clicked.connect(pick)
            return btn

        color_row = QWidget(); clay = QHBoxLayout(color_row); clay.setContentsMargins(0, 0, 0, 0); clay.setSpacing(6)
        clay.addWidget(color_btn("active", L["color_active"]))
        clay.addWidget(color_btn("clock", L["color_clock_bg"]))
        clay.addWidget(color_btn("center", L["color_center"]))
        layout.addWidget(color_row)

        reset_btn = QPushButton(L["color_reset"])
        reset_btn.clicked.connect(self._reset_colors)
        layout.addWidget(reset_btn)

        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet(f"background: {P['line']}; border: none;"); sep3.setFixedHeight(1)
        layout.addWidget(sep3)

        # 데이터
        data_btn = QPushButton(L["data_path"])
        data_btn.clicked.connect(lambda: os.startfile(str(DATA_DIR)))
        layout.addWidget(data_btn)

        reset_data_btn = QPushButton(L["reset_btn"])
        reset_data_btn.setStyleSheet("background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5; border-radius: 6px; padding: 6px 14px;")
        reset_data_btn.clicked.connect(self._reset_data)
        layout.addWidget(reset_data_btn)

        ok_btn = QPushButton("확인")
        ok_btn.setStyleSheet(f"background: {P['btn_dark']}; color: #fff; border: none; border-radius: 6px; padding: 8px;")
        ok_btn.clicked.connect(lambda: self._save(lang_cb, theme_cb, idle_spin, autostart_cb))
        layout.addWidget(ok_btn)

    def _save(self, lang_cb, theme_cb, idle_spin, autostart_cb) -> None:
        global IDLE_GRACE_SECONDS
        app = self._app
        app._lang_name = lang_cb.currentText()
        app.L = LANGUAGES.get(app._lang_name, LANG_KO)
        new_theme = "light" if theme_cb.currentIndex() == 0 else "dark"
        IDLE_GRACE_SECONDS = idle_spin.value() * 60
        set_autostart(autostart_cb.isChecked())
        app._icon_idx = self._icon_idx

        if new_theme != app._theme:
            app._theme = new_theme
            P.update(PALETTE_DARK if new_theme == "dark" else PALETTE_LIGHT)
            app.main_window.apply_palette()

        # 아이콘 업데이트
        icon = load_icon_any(app._icon_idx, app._custom_icons)
        app.main_window.setWindowIcon(icon)
        if app._tray:
            app._tray.setIcon(icon)

        settings = load_settings()
        settings.update({
            "lang": app._lang_name, "theme": app._theme,
            "idle_grace_minutes": idle_spin.value(),
            "color_active": P["active"], "color_clock_bg": P["clock"],
            "color_center": P["center"], "icon_idx": app._icon_idx,
            "clock_bg_path": app._clock_bg_path,
            "custom_icons": app._custom_icons,
        })
        save_settings(settings)
        app.redraw()
        self.accept()

    def _reset_colors(self) -> None:
        base = PALETTE_DARK if self._app._theme == "dark" else PALETTE_LIGHT
        for key in ("active", "clock", "center"):
            P[key] = base[key]
        self._app.redraw()
        self.accept()
        SettingsDialog(self._app, self.parent()).exec()

    def _reset_data(self) -> None:
        L = self._app.L
        if QMessageBox.question(self, L["reset_title"], L["reset_confirm"]) == QMessageBox.StandardButton.Yes:
            self._app.log.reset()
            self._app.redraw()
            self.accept()

# ── 내보내기 다이얼로그 ──────────────────────────────────
class ExportDialog(QDialog):
    def __init__(self, app_ref: "WorkTimerApp", parent=None):
        super().__init__(parent)
        self._app = app_ref
        L = app_ref.L
        self.setWindowTitle(L["export_title"])
        self.setFixedWidth(340)
        self.setModal(True)
        self._build()
        self.setStyleSheet(f"""
            QDialog {{ background: {P['bg']}; }}
            QLabel {{ color: {P['text']}; background: transparent; }}
            QRadioButton {{
                color: {P['text']}; spacing: 10px; font-size: 13px;
            }}
            QRadioButton::indicator {{
                width: 18px; height: 18px; border-radius: 9px;
                border: 2px solid {P['active']};
                background: {P['panel']};
            }}
            QRadioButton::indicator:checked {{
                background: {P['active']};
                border-color: {P['active']};
                image: none;
            }}
            QPushButton {{
                background: {P['btn_dark']}; color: #fff;
                border: none; border-radius: 6px; padding: 10px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {P['btn_dark_hover']}; }}
        """)

    def _build(self) -> None:
        L = self._app.L
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel(L["export_format"]))

        self._fmt_group = QButtonGroup(self)
        for i, (key, label) in enumerate([
            ("simple", L["fmt_simple"]),
            ("table",  L["fmt_table"]),
            ("detail", L["fmt_detail"]),
        ]):
            rb = QRadioButton(label)
            if i == 0: rb.setChecked(True)
            rb.setProperty("fmt", key)
            self._fmt_group.addButton(rb, i)
            layout.addWidget(rb)

        export_btn = QPushButton(L["export"])
        export_btn.clicked.connect(self._do_export)
        layout.addWidget(export_btn)

    def _do_export(self) -> None:
        app = self._app; L = app.L
        btn = self._fmt_group.checkedButton()
        fmt = btn.property("fmt") if btn else "simple"
        lines = self._build_text(fmt)
        ts = now_local().strftime("%Y-%m-%d_%H-%M")
        path, _ = QFileDialog.getSaveFileName(self, L["export_title"],
                                               str(DATA_DIR / f"work_export_{ts}.txt"),
                                               "Text Files (*.txt)")
        if path:
            Path(path).write_text("\n".join(lines), encoding="utf-8")
            QMessageBox.information(self, L["export_done"], L["export_saved"].format(path))
        self.accept()

    def _build_text(self, fmt: str) -> list[str]:
        app = self._app; L = app.L
        lines = [L["export_header"], f"{L['export_time']} {now_local().strftime('%Y-%m-%d %H:%M')}", ""]
        for dk in sorted(app.log.days.keys()):
            d = date.fromisoformat(dk)
            ivs = app.log.intervals_for(d)
            if not ivs: continue
            total = seconds_to_hhmm(sum(e - s for s, e in ivs))
            note = app.log.note_for(d)
            wd = L["weekday_names"][d.weekday()]
            if fmt == "simple":
                lines.append(f"{dk} ({wd})  {total}" + (f"  [{note}]" if note else ""))
            elif fmt == "table":
                lines.append(f"| {dk} | {wd} | {total} | {note} |")
            elif fmt == "detail":
                lines.append(f"{dk} ({wd})  {total}")
                for s, e in ivs:
                    lines.append(f"  {seconds_to_hhmm(s)} – {seconds_to_hhmm(e)}")
                if note: lines.append(f"  [{note}]")
        return lines

# ── 메인 윈도우 ──────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, app_ref: "WorkTimerApp"):
        super().__init__()
        self._app = app_ref
        self.setWindowTitle(APP_NAME)
        self.resize(1180, 760)
        self.setMinimumSize(940, 620)
        self._build()
        self.apply_palette()

    def _build(self) -> None:
        app = self._app; L = app.L

        central = QWidget()
        self.setCentralWidget(central)
        main_lay = QVBoxLayout(central)
        main_lay.setContentsMargins(18, 14, 18, 5)
        main_lay.setSpacing(6)

        # ── 헤더
        header = QWidget(); header.setFixedHeight(66)
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(0, 0, 0, 0)

        left_spacer = QWidget(); left_spacer.setMinimumWidth(200)
        header_lay.addWidget(left_spacer)

        center_w = QWidget()
        center_lay = QVBoxLayout(center_w)
        center_lay.setContentsMargins(0, 0, 0, 0); center_lay.setSpacing(2)

        nav_row = QWidget()
        nav_lay = QHBoxLayout(nav_row); nav_lay.setContentsMargins(0, 0, 0, 0); nav_lay.setSpacing(8)

        self.btn_prev = self._nav_btn(L["prev"], app.prev_month)
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.title_label.mousePressEvent = lambda _: app.title_click()
        self.btn_next = self._nav_btn(L["next"], app.next_month)

        nav_lay.addWidget(self.btn_prev)
        nav_lay.addWidget(self.title_label)
        nav_lay.addWidget(self.btn_next)
        center_lay.addWidget(nav_row)

        self.subtitle_label = QLabel()
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_lay.addWidget(self.subtitle_label)
        header_lay.addWidget(center_w)

        right_w = QWidget(); right_w.setMinimumWidth(200)
        right_lay = QGridLayout(right_w)
        right_lay.setContentsMargins(0, 0, 0, 0); right_lay.setSpacing(4)
        right_lay.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.btn_year     = self._tool_btn(L["year_view"],   app.toggle_year)
        self.btn_settings = self._tool_btn(L["settings"],    app.open_settings)
        self.btn_expand   = self._tool_btn(L["expand_btn"],  app.toggle_expand)
        self.btn_export   = self._tool_btn(L["export"],      app.open_export)

        right_lay.addWidget(self.btn_year,     0, 0)
        right_lay.addWidget(self.btn_settings, 0, 1)
        right_lay.addWidget(self.btn_expand,   1, 0)
        right_lay.addWidget(self.btn_export,   1, 1)
        header_lay.addWidget(right_w)

        main_lay.addWidget(header)

        self.canvas = DrawingWidget(app)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_lay.addWidget(self.canvas)

        self.footer_lbl = QLabel(L["made_by"])
        self.footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_lay.addWidget(self.footer_lbl)

    def _nav_btn(self, text, fn) -> QPushButton:
        btn = QPushButton(text); btn.setFixedSize(32, 30)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.clicked.connect(fn); return btn

    def _tool_btn(self, text, fn) -> QPushButton:
        btn = QPushButton(text); btn.setFixedHeight(26)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.clicked.connect(fn); return btn

    def apply_palette(self) -> None:
        bg = P["bg"]; text = P["text"]; muted = P["muted"]
        btn_bg = P["btn_bg"]; btn_fg = P["btn_fg"]
        btn_hover = P["btn_hover"]; btn_border = P["btn_border"]
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {bg}; }}
            QLabel {{ color: {text}; background: transparent; }}
            QPushButton {{
                background: {btn_bg}; color: {btn_fg};
                border: 1px solid {btn_border}; border-radius: 6px;
                padding: 3px 10px; font-size: 12px;
            }}
            QPushButton:hover {{ background: {btn_hover}; }}
        """)
        font_title = QFont(); font_title.setPointSize(16); font_title.setBold(True)
        self.title_label.setFont(font_title)
        self.title_label.setStyleSheet(f"color: {text};")

        font_sub = QFont(); font_sub.setPointSize(10)
        self.subtitle_label.setFont(font_sub)
        self.subtitle_label.setStyleSheet(f"color: {muted};")

        font_footer = QFont(); font_footer.setPointSize(7)
        self.footer_lbl.setFont(font_footer)
        self.footer_lbl.setStyleSheet(f"color: {muted};")

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()

# ── 앱 컨트롤러 ─────────────────────────────────────────
class WorkTimerApp:
    def __init__(self, start_minimized: bool = False) -> None:
        self.log = WorkLog.load()
        _recovered = ActivityTracker.recover_from_checkpoint(self.log)
        self._settings = load_settings()
        self._lang_name = self._settings.get("lang", "한국어")
        self.L = LANGUAGES.get(self._lang_name, LANG_KO)
        self._theme = self._settings.get("theme", "light")
        self._icon_idx: int = int(self._settings.get("icon_idx", 0))
        self._custom_icons: list[str] = self._settings.get("custom_icons", [])
        self._clock_bg_path: str = self._settings.get("clock_bg_path", "")
        self._clock_bg_pixmap: QPixmap | None = None
        if self._clock_bg_path and Path(self._clock_bg_path).exists():
            self._clock_bg_pixmap = QPixmap(self._clock_bg_path)
        if self._theme == "dark":
            P.update(PALETTE_DARK)

        for skey, pkey in [("color_active", "active"), ("color_clock_bg", "clock"), ("color_center", "center")]:
            val = self._settings.get(skey, "")
            if val and val.startswith("#") and len(val) == 7:
                P[pkey] = val

        today = date.today()
        self.year = today.year
        self.month = today.month
        self.view = "month"
        self.year_year = today.year
        self.detail_day: date | None = None
        self._redraw_pending = False

        self.tracker = ActivityTracker(self.log, self.schedule_redraw, recovered_start=_recovered)

        self.main_window = MainWindow(self)
        icon = load_icon_any(self._icon_idx, self._custom_icons)
        self.main_window.setWindowIcon(icon)
        QApplication.instance().setWindowIcon(icon)

        self._tray = self._build_tray(icon)
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self.tracker._tick)
        self._poll_timer.start(POLL_SECONDS * 1000)

        self.redraw()
        if not start_minimized:
            self.main_window.show()

    def _build_tray(self, icon: QIcon) -> "QSystemTrayIcon | None":
        from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None
        tray = QSystemTrayIcon()
        tray.setIcon(icon)
        tray.setToolTip(APP_NAME)
        menu = QMenu()
        menu.addAction("열기", self.show_window)
        menu.addSeparator()
        menu.addAction("종료", self.quit)
        tray.setContextMenu(menu)
        tray.activated.connect(lambda reason:
            self.show_window() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        tray.show()
        return tray

    def show_window(self) -> None:
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def quit(self) -> None:
        self.tracker.stop()
        if self._tray: self._tray.hide()
        QApplication.quit()

    # ── 뷰 전환 ─────────────────────────────────────
    def open_day(self, d: date) -> None:
        self.detail_day = d
        self.view = "day"
        self.redraw()

    def close_day(self) -> None:
        self.view = "month"
        self.detail_day = None
        self.redraw()

    def title_click(self) -> None:
        if self.view == "day":
            self.close_day()
        else:
            today = date.today()
            self.year = today.year; self.month = today.month
            self.redraw()

    def toggle_year(self) -> None:
        if self.view in ("year", "multi_year"):
            self.view = "month"
        else:
            self.year_year = self.year
            self.view = "year"
        self.redraw()

    def toggle_expand(self) -> None:
        if self.view == "multi_month":
            self.view = "month"
        elif self.view == "month":
            self.view = "multi_month"
        elif self.view == "year":
            self.view = "multi_year"
        elif self.view == "multi_year":
            self.view = "year"
        self.redraw()

    def prev_month(self) -> None:
        if self.view in ("year", "multi_year"):
            self.year_year -= 1
        elif self.view == "day":
            if self.detail_day:
                self.detail_day -= timedelta(days=1)
        else:
            if self.month == 1: self.year -= 1; self.month = 12
            else: self.month -= 1
        self.redraw()

    def next_month(self) -> None:
        if self.view in ("year", "multi_year"):
            self.year_year += 1
        elif self.view == "day":
            if self.detail_day:
                self.detail_day += timedelta(days=1)
        else:
            if self.month == 12: self.year += 1; self.month = 1
            else: self.month += 1
        self.redraw()

    def open_settings(self) -> None:
        SettingsDialog(self, self.main_window).exec()

    def open_export(self) -> None:
        ExportDialog(self, self.main_window).exec()

    # ── 리드로우 ─────────────────────────────────────
    def schedule_redraw(self) -> None:
        if self._redraw_pending: return
        self._redraw_pending = True
        QTimer.singleShot(300, self._do_redraw)

    def _do_redraw(self) -> None:
        self._redraw_pending = False
        self.redraw()

    def redraw(self) -> None:
        L = self.L
        mw = self.main_window

        def _month_title(yr: int, mo: int) -> str:
            mo_names = L.get("month_names")
            if mo_names:
                return f"{mo_names[mo - 1]} {yr}"
            return f"{yr}{L['year']} {mo}{L['month_unit']}"

        if self.view in ("month", "multi_month"):
            mw.title_label.setText(_month_title(self.year, self.month))
            month_total = sum(
                self.log.total_seconds_for(date(self.year, self.month, d))
                for d in range(1, calendar.monthrange(self.year, self.month)[1] + 1)
            )
            mw.subtitle_label.setText(f"{L['total_month']}  {seconds_to_hhmm(month_total)}")
            mw.btn_expand.setText(L["collapse_btn"] if self.view == "multi_month" else L["expand_btn"])

        elif self.view == "day" and self.detail_day:
            d = self.detail_day
            mo_names = L.get("month_names")
            if mo_names:
                day_title = f"{mo_names[d.month - 1]} {d.day}, {d.year}"
            else:
                day_title = f"{d.year}{L['year']} {d.month}{L['month_unit']} {d.day}{L['day_unit']}"
            mw.title_label.setText(day_title)
            mw.subtitle_label.setText("")
            mw.btn_expand.setText(L["expand_btn"])

            # 우측 패널 업데이트 (paintEvent 외부에서 호출)
            today = date.today()
            intervals = self.log.intervals_for(d)
            live = (d == today and self.tracker.current_interval is not None)
            if live:
                ci = self.tracker.current_interval
                display_ivs = merge_intervals(intervals + [[seconds_from_midnight(ci[0]), seconds_from_midnight(ci[1])]])
            else:
                display_ivs = list(intervals)
            total_s = sum(e - s for s, e in display_ivs)
            merges = self.log.merges_for(d)
            wd = L["weekday_names"][d.weekday()]
            day_header = f"{d.year}-{d.month:02d}-{d.day:02d}  {wd}"
            note = self.log.note_for(d)
            mw.canvas.refresh_day_panel(d, intervals, merges, total_s, live, day_header, note)

        elif self.view == "year":
            mw.title_label.setText(str(self.year_year))
            mw.subtitle_label.setText("")
            mw.btn_expand.setText(L["expand_btn"])

        elif self.view == "multi_year":
            yr = self.year_year
            mw.title_label.setText(f"{yr - 1} – {yr + 1}")
            mw.subtitle_label.setText("")
            mw.btn_expand.setText(L["collapse_btn"])

        # 헤더 버튼 텍스트 언어 동기화
        mw.btn_year.setText(L["year_view"])
        mw.btn_settings.setText(L["settings"])
        mw.btn_export.setText(L["export"])

        mw.canvas.update()

# ── 진입점 ──────────────────────────────────────────────
def main() -> None:
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Utobit.WorkTimer")
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    font = QFont("Malgun Gothic", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    start_minimized = "--minimized" in sys.argv
    wt = WorkTimerApp(start_minimized=start_minimized)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
