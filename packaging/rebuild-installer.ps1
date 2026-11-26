<#
Recompiles only the main installer (a few minutes) from the folders and GPU add-on that
packaging\build.ps1 already produced. Use it after editing packaging\wihok.iss.

  .\packaging\rebuild-installer.ps1 -PackUrl http://localhost:8099/Wihok-CUDA-Pack-1.0.0.exe
#>
param([Parameter(Mandatory = $true)][string]$PackUrl)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$version = (Select-String -Path core\version.py -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe') |
    Where-Object { Test-Path $_ } | Select-Object -First 1
$out = (Resolve-Path 'build\installer').Path
$packExe = Join-Path $out "Wihok-CUDA-Pack-$version.exe"
if (-not (Test-Path $packExe)) { throw "Missing $packExe; run packaging\build.ps1 first." }
$sha = (Get-FileHash $packExe -Algorithm SHA256).Hash.ToLower()
# the PyTorch version the add-on carries (build.ps1 wrote it next to the add-on's files)
$torchVersion = (Get-Content 'build\cuda-pack\gpu-pack.txt' -Raw).Trim()
$cpu = (Resolve-Path 'build\dist-cpu\Wihok').Path
$gen = (Resolve-Path 'packaging\generated').Path
& $iscc /Q "/DAppVersion=$version" "/DSourceDir=$cpu" "/DGenerated=$gen" "/DOutDir=$out" "/DCudaPackUrl=$PackUrl" "/DCudaPackSha256=$sha" "/DTorchVersion=$torchVersion" packaging\wihok.iss
if ($LASTEXITCODE -ne 0) { throw 'Compiling the installer failed.' }
$setup = Join-Path $out "Wihok-Setup-$version.exe"
Write-Host ("Installer: {0:N3} GiB  {1}" -f ((Get-Item $setup).Length / 1GB), $setup)
