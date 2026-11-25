<#
Tests the installer for real, in silent mode, in throw-away folders under build\install-test.
Run it after packaging\build.ps1. It touches: build\install-test, the current user's Start Menu shortcut
and uninstall entry for Wihok (installed and removed again), and a local web server on port 8099
that stands in for GitHub. It never touches Music\Wihok.

  .\packaging\test-installer.ps1
#>
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$version = (Select-String -Path core\version.py -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
$setup = (Resolve-Path "build\installer\Wihok-Setup-$version.exe").Path
$cudaDist = (Resolve-Path 'build\dist\Wihok').Path
$cpuDist = (Resolve-Path 'build\dist-cpu\Wihok').Path
$work = Join-Path $root 'build\install-test'
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
New-Item -ItemType Directory -Force $work | Out-Null
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{56DDD27F-3F1E-4D2B-B563-96F9AA8ABA04}_is1'
$shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'Wihok.lnk'
$results = @()
function Check([string]$name, [bool]$ok, [string]$detail = '') {
    $script:results += [pscustomobject]@{ Test = $name; Result = $(if ($ok) { 'PASS' } else { 'FAIL' }); Detail = $detail }
    Write-Host ("{0,-4} {1}  {2}" -f $(if ($ok) { 'PASS' } else { 'FAIL' }), $name, $detail)
}
function Run-Setup([string]$dir, [string]$tasks, [string]$log, [string]$lang = '') {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', "/DIR=`"$dir`"", "/TASKS=`"$tasks`"", "/LOG=`"$log`"")
    if ($lang) { $arguments += "/LANG=$lang" }
    $p = Start-Process -FilePath $setup -PassThru -Wait -WindowStyle Hidden -ArgumentList $arguments
    [pscustomobject]@{ Exit = $p.ExitCode; Seconds = [int]$sw.Elapsed.TotalSeconds }
}
function Selftest([string]$exe) {
    $report = Join-Path $work 'selftest.json'
    Remove-Item $report -ErrorAction SilentlyContinue
    $p = Start-Process -FilePath $exe -ArgumentList @('--selftest', $report) -PassThru -Wait -WindowStyle Hidden
    if (Test-Path $report) { Get-Content $report -Raw | ConvertFrom-Json } else { $null }
}
function Start-Server([string]$dir) {
    Start-Process -FilePath (Resolve-Path .\.venv\Scripts\python.exe).Path -ArgumentList @('-m', 'http.server', '8099', '--bind', '127.0.0.1', '--directory', $dir) -PassThru -WindowStyle Hidden
}
function Dir-Stats([string]$dir) {
    $f = Get-ChildItem $dir -Recurse -File -Force -ErrorAction SilentlyContinue
    [pscustomobject]@{ Files = @($f).Count; GB = [math]::Round((($f | Measure-Object Length -Sum).Sum) / 1GB, 2) }
}

Write-Host "== A. a folder not named Wihok: the installer adds \Wihok instead of installing straight into it (also in silent mode)"
$bad = Join-Path $work 'a\NotWihok'
$r = Run-Setup $bad '' (Join-Path $work 'a.log')
$direct = Test-Path (Join-Path $bad 'Wihok.exe')
$nested = Test-Path (Join-Path $bad 'Wihok\Wihok.exe')
Check 'never installs straight into a folder with another name' ($r.Exit -eq 0 -and -not $direct -and $nested) "exit $($r.Exit), files directly in it: $direct, in its Wihok subfolder: $nested"
$strayFiles = @(Get-ChildItem $bad -File -Force -ErrorAction SilentlyContinue)
Check 'nothing else was written next to it' ($strayFiles.Count -eq 0) "$($strayFiles.Count) loose files"
$u = Get-ChildItem (Join-Path $bad 'Wihok') -Filter 'unins*.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($u) { Start-Process -FilePath $u.FullName -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -WindowStyle Hidden; Start-Sleep -Seconds 2 }
Check 'that test install is removed again' (-not (Test-Path $uninstallKey) -and -not (Test-Path $shortcut))

Write-Host "== B. CPU install"
$app = Join-Path $work 'b\Wihok'
$sibling = Join-Path $work 'b\other-app'
New-Item -ItemType Directory -Force $sibling | Out-Null
Set-Content (Join-Path $sibling 'keep.txt') 'belongs to someone else'
$r = Run-Setup $app '' (Join-Path $work 'b.log')
$s = Dir-Stats $app
Check 'CPU install finishes' (($r.Exit -eq 0) -and (Test-Path (Join-Path $app 'Wihok.exe'))) "exit $($r.Exit), $($r.Seconds) s, $($s.Files) files, $($s.GB) GB"
Check 'uninstall entry registered' (Test-Path $uninstallKey)
Check 'Start Menu shortcut created' (Test-Path $shortcut)
$st = Selftest (Join-Path $app 'Wihok.exe')
Check 'installed CPU app passes its self-test (no CUDA)' (($st -ne $null) -and $st.ok -and -not $st.cuda) ($st | ConvertTo-Json -Compress)

Write-Host "== C. a file the user put in the install folder"
Set-Content (Join-Path $app 'my-notes.txt') 'the user wrote this'

Write-Host "== D. run the installer again on the same folder with GPU support (server on :8099 plays GitHub)"
$server = Start-Server (Resolve-Path 'build\installer').Path
Start-Sleep -Seconds 2
$r = Run-Setup $app 'cudapack' (Join-Path $work 'd.log')
$s = Dir-Stats $app
Check 'GPU upgrade finishes' ($r.Exit -eq 0) "exit $($r.Exit), $($r.Seconds) s, $($s.Files) files, $($s.GB) GB"
$entries = @(Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall' | Where-Object { (Get-ItemProperty $_.PSPath).DisplayName -like 'Wihok*' })
Check 'still exactly one uninstall entry' ($entries.Count -eq 1) "$($entries.Count) entries"
$missing = 0; $different = 0
Get-ChildItem $cudaDist -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($cudaDist.Length + 1)
    $target = Join-Path $app $rel
    if (-not (Test-Path $target)) { $missing++ }
    elseif (((Get-Item $target).Length -ne $_.Length) -or ((Get-FileHash $target -Algorithm SHA256).Hash -ne (Get-FileHash $_.FullName -Algorithm SHA256).Hash)) { $different++ }
}
Check 'installed folder matches the CUDA build file for file' (($missing -eq 0) -and ($different -eq 0)) "$missing missing, $different different"
$st = Selftest (Join-Path $app 'Wihok.exe')
Check 'installed GPU app passes its self-test with CUDA' (($st -ne $null) -and $st.ok -and $st.cuda) ($st | ConvertTo-Json -Compress)
Check 'the user file survived the upgrade' (Test-Path (Join-Path $app 'my-notes.txt'))

Write-Host "== E. uninstall"
$settingsBefore = Test-Path 'HKCU:\Software\Wihok'
$unins = Get-ChildItem $app -Filter 'unins*.exe' | Select-Object -First 1
$p = Start-Process -FilePath $unins.FullName -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -PassThru -Wait -WindowStyle Hidden
Start-Sleep -Seconds 2
Check 'uninstaller exits cleanly' ($p.ExitCode -eq 0) "exit $($p.ExitCode)"
Check 'app files are gone (including the GPU add-on)' (-not (Test-Path (Join-Path $app '_internal')) -and -not (Test-Path (Join-Path $app 'Wihok.exe')))
Check 'the user file is still there' (Test-Path (Join-Path $app 'my-notes.txt'))
Check 'a neighbouring folder is untouched' (Test-Path (Join-Path $sibling 'keep.txt'))
Check 'uninstall entry removed' (-not (Test-Path $uninstallKey))
Check 'Start Menu shortcut removed' (-not (Test-Path $shortcut))
Check 'saved settings are kept in a silent uninstall' ((Test-Path 'HKCU:\Software\Wihok') -eq $settingsBefore)
$left = Get-ChildItem $app -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne 'my-notes.txt' }
Check 'nothing else is left in the install folder' (@($left).Count -eq 0) "$(@($left).Count) leftovers: $((@($left) | Select-Object -First 5 | ForEach-Object { $_.Name }) -join ', ')"

Write-Host "== F. a corrupted GPU add-on must be rejected: setup stops and installs nothing"
Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
$junk = Join-Path $work 'junk-server'
New-Item -ItemType Directory -Force $junk | Out-Null
[IO.File]::WriteAllBytes((Join-Path $junk "Wihok-CUDA-Pack-$version.exe"), (New-Object byte[] 2MB))
$server = Start-Server $junk
Start-Sleep -Seconds 2
$app2 = Join-Path $work 'f\Wihok'
$r = Run-Setup $app2 'cudapack' (Join-Path $work 'f.log')
Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
Check 'setup stops with an error exit code' ($r.Exit -ne 0) "exit $($r.Exit), $($r.Seconds) s"
Check 'nothing was installed' (-not (Test-Path (Join-Path $app2 'Wihok.exe')) -and -not (Test-Path $uninstallKey) -and -not (Test-Path $shortcut))
Check 'the log says the hash was wrong' ((Select-String -Path (Join-Path $work 'f.log') -Pattern 'File hash is incorrect' -Quiet))
Check 'the user is told in plain English that the checksum did not match' ((Select-String -Path (Join-Path $work 'f.log') -Pattern 'did not match its checksum' -Quiet))

Write-Host "== G. no download server at all: a plain message, in English and in Thai, and nothing installed"
foreach ($case in @(@('en', 'Could not connect to the download server', 'g-en'), @('th', 'เชื่อมต่อเซิร์ฟเวอร์ดาวน์โหลดไม่ได้', 'g-th'))) {
    $lang, $phrase, $tag = $case
    $dirG = Join-Path $work "$tag\Wihok"
    $r = Run-Setup $dirG 'cudapack' (Join-Path $work "$tag.log") $lang
    $logText = Get-Content (Join-Path $work "$tag.log") -Raw -Encoding UTF8
    Check "[$lang] setup stops with an error exit code" ($r.Exit -ne 0) "exit $($r.Exit)"
    Check "[$lang] the message names the problem in plain words" ($logText.Contains($phrase))
    Check "[$lang] the technical text is hidden from the user but kept in the log" ((-not ($logText -match 'Defaulting to OK[^\r\n]*\r?\n[^\r\n]*Worker thread')) -and $logText.Contains('GPU add-on download error:') -and $logText.Contains('12029'))
    Check "[$lang] nothing was installed" (-not (Test-Path (Join-Path $dirG 'Wihok.exe')) -and -not (Test-Path $uninstallKey))
}

Write-Host "== H. the GPU add-on must not install on its own (NVIDIA's license: only inside the application)"
$packExe = (Resolve-Path "build\installer\Wihok-CUDA-Pack-$version.exe").Path
$lonely = Join-Path $work 'h\Wihok'
$p = Start-Process -FilePath $packExe -PassThru -Wait -WindowStyle Hidden -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', "/DIR=`"$lonely`"", "/LOG=`"$(Join-Path $work 'h.log')`"")
$any = @(Get-ChildItem $lonely -Recurse -File -ErrorAction SilentlyContinue).Count
Check 'the add-on refuses to install where there is no Wihok' (($p.ExitCode -ne 0) -and ($any -eq 0)) "exit $($p.ExitCode), $any files written"

Write-Host "== I. the license files reach the installed folder"
$appL = Join-Path $work 'i\Wihok'
$r = Run-Setup $appL '' (Join-Path $work 'i.log')
Check 'LICENSE and THIRD-PARTY-NOTICES.txt are installed' ((Test-Path (Join-Path $appL 'LICENSE')) -and (Test-Path (Join-Path $appL 'THIRD-PARTY-NOTICES.txt'))) "exit $($r.Exit)"
$ul = Get-ChildItem $appL -Filter 'unins*.exe' | Select-Object -First 1
if ($ul) { Start-Process -FilePath $ul.FullName -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -WindowStyle Hidden; Start-Sleep -Seconds 2 }
Check 'and they are removed again on uninstall' (-not (Test-Path (Join-Path $appL 'LICENSE')) -and -not (Test-Path (Join-Path $appL 'THIRD-PARTY-NOTICES.txt')))

Write-Host "`n== Summary"
$results | Group-Object Result | ForEach-Object { Write-Host ("{0}: {1}" -f $_.Name, $_.Count) }
$results | Where-Object Result -eq 'FAIL' | Format-Table -AutoSize -Wrap
