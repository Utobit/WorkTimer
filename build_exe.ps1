$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

python -m pip install -r .\requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$iconArg = @()
if (Test-Path -LiteralPath ".\icon.png") {
    python -c "from PIL import Image; Image.open('icon.png').save('icon.ico', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $iconArg = @("--icon", ".\icon.ico", "--add-data", "icon.png;.")
}

$iconsArg = @()
if (Test-Path -LiteralPath ".\icons") {
    $iconsArg = @("--add-data", "icons;icons")
}

python -m PyInstaller --noconfirm --windowed --name WorkTimer @iconArg @iconsArg .\worktimer.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Built: $PSScriptRoot\dist\WorkTimer\WorkTimer.exe"
