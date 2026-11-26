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
$torchBase = @{}
foreach ($d in 'build\dist-cpu', 'build\dist') {
    $report = Join-Path $env:TEMP "selftest-$([IO.Path]::GetFileName($d)).json"
    Remove-Item $report -ErrorAction SilentlyContinue
    $p = Start-Process -FilePath (Resolve-Path "$d\Wihok\Wihok.exe").Path -ArgumentList @('--selftest', $report) -PassThru -Wait -WindowStyle Hidden
    if ($p.ExitCode -ne 0) { throw "Self-test failed for $d. See $report" }
    $torchBase[$d] = ((Get-Content $report -Raw | ConvertFrom-Json).torch -replace '\+.*$', '')
    Write-Host "Self-test passed: $d (torch $($torchBase[$d]))"
}
if ($torchBase['build\dist-cpu'] -ne $torchBase['build\dist']) { throw "The two builds use different PyTorch versions: $($torchBase['build\dist-cpu']) and $($torchBase['build\dist'])" }
$torchVersion = $torchBase['build\dist']

# 4. The GPU add-on. Wihok.exe is the same program in both builds, so the add-on holds only the PyTorch
#    files: every file in torch\ and torchaudio\ of the CUDA build that is missing from, or different
#    in, the CPU build. That way an app update never needs a new add-on, only a new PyTorch does.
#    These CUDA libraries are left out because PyTorch runs Demucs without them (measured: loading torch and
#    separating a real song on the GPU both worked, with the same speed and the same audio quality). The rest
#    must stay: without cusparse, cusolver, nvrtc, nvJitLink, cupti or cudnn_ops, torch does not even load, and
#    without the cuDNN engines (precompiled, heuristic, runtime_compiled) the first convolution fails.
#    Check again whenever PyTorch is upgraded.
$leaveOut = 'cusolverMg64_11.dll', 'nvrtc64_120_0.alt.dll', 'nvperf_host.dll', 'nvToolsExt64_1.dll', 'cufftw64_11.dll', 'curand64_10.dll', 'cudnn_adv64_9.dll'
$cpu = (Resolve-Path 'build\dist-cpu\Wihok').Path
$cuda = (Resolve-Path 'build\dist\Wihok').Path
$pack = 'build\cuda-pack'
if (Test-Path $pack) { Remove-Item $pack -Recurse -Force }
New-Item -ItemType Directory -Force $pack | Out-Null
$changed = 0; $bytes = 0; $outside = @()
Get-ChildItem $cuda -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($cuda.Length + 1)
    $other = Join-Path $cpu $rel
    $same = (Test-Path $other) -and ((Get-Item $other).Length -eq $_.Length) -and
            ((Get-FileHash $other -Algorithm SHA256).Hash -eq (Get-FileHash $_.FullName -Algorithm SHA256).Hash)
    if ($same) { return }
    if ($rel -notmatch '^_internal\\(torch|torchaudio)\\') { $outside += $rel; return }
    if ($leaveOut -contains $_.Name) { return }
    $target = Join-Path $pack $rel
    New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
    Copy-Item $_.FullName $target
    $changed++; $bytes += $_.Length
}
# What the add-on deliberately does not carry. These differ between the two builds only because each comes from its
# own virtual environment (the program file, the stdlib archive, package metadata, a compiled markupsafe,
# numba caches); they are the same program. Anything else would mean the builds drifted apart, so stop and look.
$unexpected = @($outside | Where-Object {
    $_ -ne 'Wihok.exe' -and $_ -ne '_internal\base_library.zip' -and $_ -notmatch '\.dist-info\\' -and
    $_ -notmatch '^_internal\\markupsafe\\' -and $_ -notmatch '\.nbc$|\.nbi$' })
if ($unexpected.Count -gt 0) { throw "The builds differ outside torch and torchaudio:$($unexpected -join ', ')" }
Set-Content -Path (Join-Path $pack 'gpu-pack.txt') -Value $torchVersion -Encoding ASCII -NoNewline
$cpuOnly = Get-ChildItem $cpu -Recurse -File | Where-Object { $_.FullName -match '\\_internal\\(torch|torchaudio)\\' -and -not (Test-Path (Join-Path $cuda $_.FullName.Substring($cpu.Length + 1))) }
Write-Host ("GPU add-on: {0} files, {1:N2} GiB before compression; {2} CPU-build library files are replaced by it or removed" -f $changed, ($bytes / 1GB), @($cpuOnly).Count)
if (@($cpuOnly).Count -gt 0) { $cpuOnly | Select-Object -First 10 | ForEach-Object { Write-Host "  CPU-only: $($_.FullName.Substring($cpu.Length + 1))" } }

# 4b. prove the real combination works: the CPU build with the add-on laid over it must see the GPU
if (Test-Path "$env:windir\System32\nvcuda.dll") {
    $trial = 'build\verify-gpu'
    if (Test-Path $trial) { Remove-Item $trial -Recurse -Force }
    Invoke-Native { robocopy $cpu $trial /E /NFL /NDL /NJH /NJS /NP /MT:8 }
    Invoke-Native { robocopy (Resolve-Path $pack).Path (Resolve-Path $trial).Path /E /NFL /NDL /NJH /NJS /NP /MT:8 }
    $report = Join-Path $env:TEMP 'selftest-verify-gpu.json'
    Remove-Item $report -ErrorAction SilentlyContinue
    $p = Start-Process -FilePath (Resolve-Path "$trial\Wihok.exe").Path -ArgumentList @('--selftest', $report) -PassThru -Wait -WindowStyle Hidden
    $r = if (Test-Path $report) { Get-Content $report -Raw | ConvertFrom-Json }
    if ($p.ExitCode -ne 0 -or -not $r -or -not $r.cuda) { throw "The CPU build with the GPU add-on does not see the GPU. See $report" }
    Remove-Item $trial -Recurse -Force
    Write-Host 'Self-test passed: CPU build + GPU add-on (CUDA available)'
} else {
    Write-Host 'No NVIDIA driver on this computer: the CPU build + GPU add-on combination was NOT tested.'
}

# 5. compile the GPU add-on, then the installer that knows its URL and SHA-256
$out = (New-Item -ItemType Directory -Force 'build\installer').FullName
$gen = (Resolve-Path 'packaging\generated').Path
& $iscc /Q "/DAppVersion=$version" "/DPackDir=$((Resolve-Path $pack).Path)" "/DGenerated=$gen" "/DOutDir=$out" packaging\wihok-cuda-pack.iss
if ($LASTEXITCODE -ne 0) { throw 'Compiling the GPU add-on failed.' }
$packExe = Join-Path $out "Wihok-CUDA-Pack-$version.exe"
$sha = (Get-FileHash $packExe -Algorithm SHA256).Hash.ToLower()
Write-Host ("GPU add-on: {0:N2} GiB  sha256 {1}" -f ((Get-Item $packExe).Length / 1GB), $sha)

& $iscc /Q "/DAppVersion=$version" "/DSourceDir=$cpu" "/DGenerated=$gen" "/DOutDir=$out" "/DCudaPackUrl=$PackUrl" "/DCudaPackSha256=$sha" "/DTorchVersion=$torchVersion" packaging\wihok.iss
if ($LASTEXITCODE -ne 0) { throw 'Compiling the installer failed.' }
$setup = Join-Path $out "Wihok-Setup-$version.exe"
Write-Host ("Installer:  {0:N2} GiB  {1}" -f ((Get-Item $setup).Length / 1GB), $setup)
Write-Host ("GitHub release asset limit is 2 GiB per file; the largest file here is {0:N2} GiB." -f ((Get-Item $packExe).Length / 1GB))
