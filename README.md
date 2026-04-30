# WorkTimer

PC 작업 시간을 자동으로 기록하는 Windows 트레이 앱.  
키보드·마우스 입력 감지 → 24시간 원형 시계 + 월간 캘린더로 시각화.

**제작**: Jin (AI Agent) · Utobit  
**버전**: 1.0.1  
**라이선스**: MIT  
**Microsoft Store**: [PC_WorkTimer](https://apps.microsoft.com/detail/9N6RFQF96ZTD)

---

## 기능

| 기능 | 설명 |
|---|---|
| 자동 기록 | 입력 감지 시 즉시 시작, 10분 무입력 시 자동 종료 |
| 월간 캘린더 | 7열 × 날짜별 원형 시계 히트맵 |
| 일간 상세 | 24시간 대형 시계 + 기록 구간 목록 |
| 연간 히트맵 | 1년 전체 작업량 색상 표시 (펼치기 시 3개년) |
| 3개월 뷰 | 펼치기/접기로 전환 |
| 구간 병합 | 인접 구간 클릭 → 하나로 합치기 |
| 메모 | 날짜별 메모 저장 |
| 다크/라이트 모드 | 테마 전환 |
| 기록 내보내기 | 텍스트 파일 내보내기 (Notion 등 바로 붙여넣기) |
| 커스텀 아이콘 | 트레이·시계 아이콘 교체 |
| 시계 배경 이미지 | 커스텀 이미지 설정 |
| 체크포인트 | 강제 종료 시 60초 단위 자동 복구 |

---

## 버전 규칙

```
X.Y.Z.W
│ │ │ └─ 테스트 버전 (1,2,3... → 0으로 확정)
│ │ └─── 배포 버전업 (기능 수정/버그픽스)
│ └───── 탭·기능 추가 수준
└─────── 메이저
```

배포 버전 마지막 자리 = 0 (예: `1.0.2.0`)

---

## 데이터 저장 위치

```
%LOCALAPPDATA%\LinaAI\WorkTimer\
  work_log.json      ← 전체 기록 (MSIX 재설치해도 유지됨)
  checkpoint.json    ← 강제종료 복구용 (재시작 시 자동 삭제)
  settings.json      ← 설정
  backups/           ← 자동 백업
```

---

## 개발 환경

```
Python 3.12
PyQt6
PyInstaller 6.x
Windows SDK 10.0.22621 (makeappx, signtool)
```

설치:
```powershell
pip install PyQt6
python worktimer.py
```

---

## 빌드 절차

### 1. EXE 빌드 (PyInstaller)
```powershell
pyinstaller WorkTimer.spec --noconfirm
# 결과물: dist/WorkTimer/
```

### 2. MSIX 패키징 + 서명
```powershell
.\build_msix.ps1
# 결과물: dist/WorkTimer.msix
# Microsoft Store 제출용: MSStore/WorkTimer.msix
```

### 3. 로컬 테스트 설치
```powershell
Get-AppxPackage -Name "utobit.PCWorkTimer" | Remove-AppxPackage
Add-AppxPackage -Path dist\WorkTimer.msix

# 실행
Start-Process "shell:AppsFolder\utobit.PCWorkTimer_z949ye19fere4!WorkTimer"
```

> 재실행 시 반드시 기존 프로세스 먼저 종료 (mutex 때문):
> ```powershell
> taskkill /F /IM pythonw.exe; taskkill /F /IM WorkTimer.exe
> ```

---

## 코드 구조

```
worktimer.py          ← 단일 파일 (~1900줄)
├── PALETTE_LIGHT/DARK     팔레트 상수
├── LANG_KO / LANG_EN      다국어 문자열
├── WorkLog                JSON 로그 저장/로드
├── ActivityTracker        백그라운드 입력 감지 스레드
└── WorkTimerApp           PyQt6 메인 앱
    ├── CalendarWidget     월간/다중월 캘린더
    ├── ClockWidget        24시간 원형 시계
    ├── RightPanel         기록 구간·메모·총시간
    ├── YearWidget         연간 히트맵
    └── SettingsDialog     설정창 (아이콘·색상·배경)
```

---

## MSIX 구조

```
msix/
  AppxManifest.xml   ← 버전·Publisher·아이콘 경로
  Assets/
    Square44x44Logo.png
    Square150x150Logo.png
    Wide310x150Logo.png
    StoreLogo.png
```

**Package Identity:**
- Name: `utobit.PCWorkTimer`
- Publisher: `CN=4BF7C5DE-0E2A-457D-A549-A5D4AF5B008E`
- Family: `utobit.PCWorkTimer_z949ye19fere4`

버전 변경 시: `AppxManifest.xml` Version + `worktimer.py` VERSION 동시 수정

---

## 릴리즈 절차

```
1. worktimer.py: VERSION = "1.0.X"
2. AppxManifest.xml: Version="1.0.X.0"
3. pyinstaller WorkTimer.spec --noconfirm
4. .\build_msix.ps1
5. Copy-Item dist\WorkTimer.msix MSStore\WorkTimer.msix -Force
6. git add -A && git commit -m "release: WorkTimer v1.0.X"
7. git push
8. Microsoft Store Partner Center에 MSStore\WorkTimer.msix 업로드
```

---

## 알려진 제약

- Windows 전용 (`ctypes.windll` 사용)
- 멀티모니터 DPI 스케일링 미대응
