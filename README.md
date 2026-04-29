# WorkTimer

PC 작업 시간을 자동으로 기록하는 Windows 트레이 앱.  
키보드·마우스 입력 감지 → 24시간 원형 시계 + 월간 캘린더로 시각화.

**제작**: Jin (AI Agent) · Utobit  
**라이선스**: MIT  
**다운로드**: [U Store](https://utobit.net/da/ustore/) · [GitHub Releases](../../releases)

---

## 기능

| 기능 | 설명 |
|---|---|
| 자동 기록 | 입력 감지 시 즉시 시작, 10분 무입력 시 자동 종료 |
| 월간 캘린더 | 7열 × 날짜별 원형 시계 히트맵 |
| 일간 상세 | 24시간 대형 시계 + 기록 구간 목록 |
| 연간 히트맵 | 1년 전체 작업량 색상 표시 |
| 펼치기 뷰 | 3개월 동시 보기 |
| 구간 병합 | 인접 구간 드래그 → 하나로 합치기 |
| 메모 | 날짜별 메모 저장 |
| 다크모드 | 라이트/다크 테마 전환 |
| 기록 내보내기 | CSV 내보내기 |
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
테스트 중 = `1.0.2.1`, `1.0.2.2`... → 완료 시 `1.0.3.0` 릴리즈

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
tkinter (내장)
Pillow, pystray
PyInstaller 6.x
Windows SDK 10.0.22621 (makeappx, signtool)
```

설치:
```powershell
pip install -r requirements.txt
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
# 결과물: dist/WorkTimer.msix (자체 서명)
```

서명 인증서: `dist/WorkTimer_cert.pfx` (비밀번호: 별도 관리)  
Publisher: `CN=4BF7C5DE-0E2A-457D-A549-A5D4AF5B008E`

### 3. 설치 (로컬 테스트)
```powershell
# 구버전 제거 후 설치 (버전 다운그레이드 시 필수)
Get-AppxPackage -Name "UtobitWorkTimer" | Remove-AppxPackage
Add-AppxPackage -Path dist\WorkTimer.msix

# 실행
Start-Process "shell:AppsFolder\UtobitWorkTimer_z949ye19fere4!WorkTimer"
```

---

## 코드 구조

```
worktimer.py          ← 단일 파일 (~2200줄)
├── PALETTE_LIGHT/DARK     팔레트 상수
├── WorkLog                JSON 로그 저장/로드
├── ActivityTracker        백그라운드 입력 감지 스레드
│   ├── _tick()            5초마다 실행, 아이들 판정
│   ├── _write_checkpoint()60초마다 active_start 저장
│   └── recover_from_checkpoint()  재시작 시 복구
└── WorkTimerApp           tkinter 메인 앱
    ├── _build_header()    헤더 (< 제목 >, 2×2 버튼 그리드)
    ├── _draw_calendar()   월간 뷰
    ├── _draw_day_detail_view()  일간 뷰
    ├── _draw_clock()      24시간 원형 시계 (min_secs 파라미터)
    ├── _draw_right_panel()      날짜·총시간·구간·메모
    ├── _draw_expand()     3개월 펼치기 뷰
    └── _draw_year()       연간 히트맵
```

### 핵심 동작

- **아이들 감지**: `get_idle_seconds()` → `IDLE_GRACE_SECONDS=600` 초과 시 구간 종료
- **자정 경계**: `split_interval_by_day()` 로 날짜별 분리
- **구간 병합**: `merge_intervals()` — 인접(+1초) 구간 자동 합치기
- **소형 호 버그**: tkinter arc extent < 0.5°(≈120초) → 전체원으로 렌더링 버그  
  → 소형 클럭: 120초 미만 스킵 / 대형 클럭(일간): 라디알 라인으로 표시

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

버전 변경 시: `AppxManifest.xml` + `worktimer.py` `VERSION` 동시 수정

---

## 릴리즈 절차

```
1. worktimer.py: VERSION = "1.0.X"
2. AppxManifest.xml: Version="1.0.X.0"
3. pyinstaller WorkTimer.spec --noconfirm
4. .\build_msix.ps1
5. git add -A && git commit -m "release: WorkTimer v1.0.X"
6. git tag worktimer-v1.0.X && git push origin main --tags
7. GitHub Releases 에서 태그 선택 → WorkTimer.msix 업로드
8. U Store 다운로드 링크 업데이트
```

---

## Microsoft Store 제출 체크리스트

- [ ] Partner Center 계정 (사업자 등록 필요)
- [ ] `dist/WorkTimer.msix` (Azure Trusted Signing 적용 필요)
- [ ] 스크린샷 1280×800 이상 (최소 1장)
- [ ] 스토어 설명 (한국어/영어)
- [ ] 개인정보처리방침 URL: `https://utobit.net/privacy/`
- [ ] 연령 등급: PEGI 3 / Everyone

---

## 알려진 제약

- Windows 전용 (`ctypes.windll` 사용)
- 자체 서명 MSIX → 배포 PC에 인증서 수동 설치 필요 (또는 Azure Trusted Signing)
- 멀티모니터 DPI 스케일링 미대응
