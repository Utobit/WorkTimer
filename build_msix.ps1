# WorkTimer MSIX Build Script
# 실행: powershell -ExecutionPolicy Bypass -File build_msix.ps1

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$DIST = "$ROOT\dist\WorkTimer"
$MSIX_STAGING = "$ROOT\msix_staging_$(Get-Date -Format 'HHmmss')"
$MSIX_OUT = "$ROOT\dist\WorkTimer.msix"
$PUBLISHER = "CN=4BF7C5DE-0E2A-457D-A549-A5D4AF5B008E"
$CERT_PATH = "$ROOT\dist\WorkTimer_cert.pfx"
$CERT_PASS = "utobit2026"

# Windows SDK 경로 탐색
$SDK_PATHS = @(
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64",
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64",
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.18362.0\x64"
)
$SDK = $null
foreach ($p in $SDK_PATHS) {
    if (Test-Path "$p\makeappx.exe") { $SDK = $p; break }
}
if (-not $SDK) {
    # 와일드카드로 추가 탐색
    $found = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" -Filter "makeappx.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $SDK = $found.DirectoryName }
}
if (-not $SDK) {
    Write-Error "Windows SDK를 찾을 수 없습니다. https://developer.microsoft.com/windows/downloads/windows-sdk/ 에서 설치하세요."
    exit 1
}
Write-Host "SDK: $SDK"

# 1. 스테이징 폴더 구성 (타임스탬프 폴더라 기존 잠금 없음)
New-Item -ItemType Directory -Path $MSIX_STAGING | Out-Null

# dist 파일 복사
Copy-Item "$DIST\*" $MSIX_STAGING -Recurse

# 매니페스트 + 에셋 복사
Copy-Item "$ROOT\msix\AppxManifest.xml" $MSIX_STAGING
Copy-Item "$ROOT\msix\Assets" $MSIX_STAGING -Recurse

Write-Host "스테이징 완료"

# 2. MSIX 패키징
if (Test-Path $MSIX_OUT) { Remove-Item $MSIX_OUT -Force -Confirm:$false }
& "$SDK\makeappx.exe" pack /d $MSIX_STAGING /p $MSIX_OUT /nv
Write-Host "MSIX 생성: $MSIX_OUT"

# 3. 자체 서명 인증서 생성 (없을 때만)
if (-not (Test-Path $CERT_PATH)) {
    Write-Host "자체 서명 인증서 생성 중..."
    $cert = New-SelfSignedCertificate `
        -Subject $PUBLISHER `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -Type CodeSigningCert `
        -KeyUsage DigitalSignature `
        -NotAfter (Get-Date).AddYears(5)
    $secPass = ConvertTo-SecureString $CERT_PASS -AsPlainText -Force
    Export-PfxCertificate -Cert $cert -FilePath $CERT_PATH -Password $secPass | Out-Null
    Write-Host "인증서 저장: $CERT_PATH"
}

# 4. 서명
& "$SDK\signtool.exe" sign /fd SHA256 /p7 . /p7co 1.2.840.113549.1.7.1 /p7ce DetachedSignedData /f $CERT_PATH /p $CERT_PASS $MSIX_OUT
Write-Host "서명 완료"

# 구 스테이징 폴더 정리
Get-ChildItem -Path $ROOT -Filter "msix_staging_*" -Directory | Where-Object { $_.FullName -ne $MSIX_STAGING } | ForEach-Object { cmd /c "rd /s /q `"$($_.FullName)`"" }
cmd /c "rd /s /q `"$MSIX_STAGING`"" 2>$null

Write-Host ""
Write-Host "=== 빌드 완료 ==="
Write-Host "출력: $MSIX_OUT"
Write-Host ""
Write-Host "[UStore 배포 시]"
Write-Host "사용자 PC에 인증서 신뢰 추가 필요 (최초 1회):"
Write-Host "  $CERT_PATH 더블클릭 → '로컬 컴퓨터' → '신뢰할 수 있는 루트 인증 기관'"
Write-Host "이후 WorkTimer.msix 더블클릭으로 설치"
