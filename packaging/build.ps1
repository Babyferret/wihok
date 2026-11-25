<#
Builds the Wihok installer.

  .\packaging\build.ps1 -PackUrl https://github.com/<owner>/<repo>/releases/download/v1.0.0/Wihok-CUDA-Pack-1.0.0.exe

Needs two virtual environments, both Python 3.12:
  .venv       CUDA build of PyTorch   (requirements.txt)
  .venv-cpu   CPU build of PyTorch    (requirements-cpu.txt)
and Inno Setup 6.  Output goes to build\installer:
  Wihok-Setup-<version>.exe       small installer (the CPU build); this is what users download
  Wihok-CUDA-Pack-<version>.exe   GPU add-on; upload it to the same release. The installer downloads it
                                  for NVIDIA users and checks its SHA-256 first.

Use -Rebuild to rebuild the two PyInstaller folders even if they already exist.
#>
param(
    [Parameter(Mandatory = $true)][string]$PackUrl,
    [switch]$Rebuild
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$version = (Select-String -Path core\version.py -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe') |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw 'Inno Setup 6 is not installed (winget install JRSoftware.InnoSetup).' }
Write-Host "Version $version"

# Native tools (PyInstaller, Qt) write progress to stderr; Windows PowerShell 5.1 treats that as an error
# under 'Stop', so run them with errors relaxed and judge by the exit code instead.
function Invoke-Native([scriptblock]$Command) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Command | Out-Null } finally { $ErrorActionPreference = $previous }
}

# 1. icon and installer images
$env:QT_QPA_PLATFORM = 'offscreen'
Invoke-Native { & .\.venv\Scripts\python.exe packaging\make_assets.py }
Remove-Item Env:QT_QPA_PLATFORM
if (-not (Test-Path packaging\generated\wihok.ico)) { throw 'Generating the icon failed.' }

# 2. the two PyInstaller folders
function Build-Dist($venv, $dist, $work, $spec) {
    if ((Test-Path "$dist\Wihok\Wihok.exe") -and -not $Rebuild) { Write-Host "Using existing $dist"; return }
    Write-Host "Building $dist ..."
    $icon = (Resolve-Path packaging\generated\wihok.ico).Path
    $assets = (Resolve-Path assets).Path
    Invoke-Native {
        & "$venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --name Wihok --windowed --onedir `
            --icon $icon --distpath $dist --workpath $work --specpath $spec `
            --add-data "$assets;assets" `
            --collect-data demucs --collect-submodules demucs --collect-data librosa main.py *> "$work.log"
    }
    if (-not (Test-Path "$dist\Wihok\Wihok.exe")) { throw "PyInstaller failed for $dist, see $work.log" }
}
Build-Dist '.venv-cpu' 'build\dist-cpu' 'build\work-cpu' 'build\spec-cpu'
Build-Dist '.venv' 'build\dist' 'build\work' 'build\spec'

# 3. every packaged build must pass its own self-test before it is shipped
foreach ($d in 'build\dist-cpu', 'build\dist') {
    $report = Join-Path $env:TEMP "selftest-$([IO.Path]::GetFileName($d)).json"
    Remove-Item $report -ErrorAction SilentlyContinue
    $p = Start-Process -FilePath (Resolve-Path "$d\Wihok\Wihok.exe").Path -ArgumentList @('--selftest', $report) -PassThru -Wait -WindowStyle Hidden
    if ($p.ExitCode -ne 0) { throw "Self-test failed for $d. See $report" }
    Write-Host "Self-test passed: $d"
}

# 4. the GPU add-on = every file of the CUDA build that is missing from, or different in, the CPU build
$cpu = (Resolve-Path 'build\dist-cpu\Wihok').Path
$cuda = (Resolve-Path 'build\dist\Wihok').Path
$pack = 'build\cuda-pack'
if (Test-Path $pack) { Remove-Item $pack -Recurse -Force }
New-Item -ItemType Directory -Force $pack | Out-Null
$changed = 0; $bytes = 0
Get-ChildItem $cuda -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($cuda.Length + 1)
    $other = Join-Path $cpu $rel
    $same = (Test-Path $other) -and ((Get-Item $other).Length -eq $_.Length) -and
            ((Get-FileHash $other -Algorithm SHA256).Hash -eq (Get-FileHash $_.FullName -Algorithm SHA256).Hash)
    if (-not $same) {
        $target = Join-Path $pack $rel
        New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
        Copy-Item $_.FullName $target
        $changed++; $bytes += $_.Length
    }
}
$cpuOnly = Get-ChildItem $cpu -Recurse -File | Where-Object { -not (Test-Path (Join-Path $cuda $_.FullName.Substring($cpu.Length + 1))) }
Write-Host ("GPU add-on: {0} files, {1:N2} GiB before compression; {2} files exist only in the CPU build" -f $changed, ($bytes / 1GB), @($cpuOnly).Count)
if (@($cpuOnly).Count -gt 0) { $cpuOnly | Select-Object -First 10 | ForEach-Object { Write-Host "  CPU-only: $($_.FullName.Substring($cpu.Length + 1))" } }

# 5. compile the GPU add-on, then the installer that knows its URL and SHA-256
$out = (New-Item -ItemType Directory -Force 'build\installer').FullName
$gen = (Resolve-Path 'packaging\generated').Path
& $iscc /Q "/DAppVersion=$version" "/DPackDir=$((Resolve-Path $pack).Path)" "/DGenerated=$gen" "/DOutDir=$out" packaging\wihok-cuda-pack.iss
if ($LASTEXITCODE -ne 0) { throw 'Compiling the GPU add-on failed.' }
$packExe = Join-Path $out "Wihok-CUDA-Pack-$version.exe"
$sha = (Get-FileHash $packExe -Algorithm SHA256).Hash.ToLower()
Write-Host ("GPU add-on: {0:N2} GiB  sha256 {1}" -f ((Get-Item $packExe).Length / 1GB), $sha)

& $iscc /Q "/DAppVersion=$version" "/DSourceDir=$cpu" "/DGenerated=$gen" "/DOutDir=$out" "/DCudaPackUrl=$PackUrl" "/DCudaPackSha256=$sha" packaging\wihok.iss
if ($LASTEXITCODE -ne 0) { throw 'Compiling the installer failed.' }
$setup = Join-Path $out "Wihok-Setup-$version.exe"
Write-Host ("Installer:  {0:N2} GiB  {1}" -f ((Get-Item $setup).Length / 1GB), $setup)
Write-Host ("GitHub release asset limit is 2 GiB per file; the largest file here is {0:N2} GiB." -f ((Get-Item $packExe).Length / 1GB))
