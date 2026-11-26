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
# The Start menu learns about a new app a few seconds after the installer ends (10 s on this PC), so wait for it.
$startApp = $null
for ($i = 0; $i -lt 45 -and -not $startApp; $i++) { $startApp = Get-StartApps | Where-Object { $_.Name -eq 'Wihok' } | Select-Object -First 1; if (-not $startApp) { Start-Sleep -Seconds 1 } }
Check 'the Start menu knows the app, under the same ID the app uses for its taskbar button' (($null -ne $startApp) -and ($startApp.AppID -eq 'Wihok.Wihok')) "AppID: $($startApp.AppID), found after about $i s"
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
$packDir = (Resolve-Path 'build\cuda-pack').Path
function Count-Mismatches([string]$expectedDir, [string]$target, [string]$skipDir = '') {
    $missing = 0; $different = 0
    Get-ChildItem $expectedDir -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($expectedDir.Length + 1)
        if ($skipDir -and (Test-Path (Join-Path $skipDir $rel))) { return }   # replaced by the add-on: checked on its own
        $t = Join-Path $target $rel
        if (-not (Test-Path $t)) { $script:missing++ }
        elseif (((Get-Item $t).Length -ne $_.Length) -or ((Get-FileHash $t -Algorithm SHA256).Hash -ne (Get-FileHash $_.FullName -Algorithm SHA256).Hash)) { $script:different++ }
    }
}
$missing = 0; $different = 0
Count-Mismatches $packDir $app
$packMissing = $missing; $packDifferent = $different
$missing = 0; $different = 0
Count-Mismatches $cpuDist $app $packDir
Check 'installed folder = the CPU build with the GPU add-on laid over it, file for file' (($packMissing -eq 0) -and ($packDifferent -eq 0) -and ($missing -eq 0) -and ($different -eq 0)) "add-on files: $packMissing missing, $packDifferent different; CPU-build files: $missing missing, $different different"
Check 'the add-on left its PyTorch version marker' ((Test-Path (Join-Path $app 'gpu-pack.txt')) -and ((Get-Content (Join-Path $app 'gpu-pack.txt') -Raw).Trim() -eq (Get-Content (Join-Path $packDir 'gpu-pack.txt') -Raw).Trim()))
$st = Selftest (Join-Path $app 'Wihok.exe')
Check 'installed GPU app passes its self-test with CUDA' (($st -ne $null) -and $st.ok -and $st.cuda) ($st | ConvertTo-Json -Compress)
Check 'the user file survived the upgrade' (Test-Path (Join-Path $app 'my-notes.txt'))

Write-Host "== D2. updating an install that has GPU support must keep the GPU (what an in-app update does: run the installer, no add-on task)"
$torchCuda = Join-Path $app '_internal\torch\lib\torch_cuda.dll'
$hashBefore = (Get-FileHash $torchCuda -Algorithm SHA256).Hash
$r = Run-Setup $app '' (Join-Path $work 'd2.log')
$st = Selftest (Join-Path $app 'Wihok.exe')
Check 'updating over GPU support finishes' ($r.Exit -eq 0) "exit $($r.Exit), $($r.Seconds) s"
Check 'GPU support is still there afterwards (same PyTorch files, CUDA still works)' (((Get-FileHash (Join-Path $app '_internal\torch\lib\torch_cuda.dll') -Algorithm SHA256).Hash -eq $hashBefore) -and ($st -ne $null) -and $st.ok -and $st.cuda) ($st | ConvertTo-Json -Compress)
Check 'the update did not rewrite the PyTorch files' ($r.Seconds -lt 120) "$($r.Seconds) s (a full CPU install takes about 20 s, the GPU add-on about 160 s)"

Write-Host "== D3. GPU support made for another PyTorch version cannot be kept as it is"
$marker = Join-Path $app 'gpu-pack.txt'
$currentVersion = (Get-Content $marker -Raw).Trim()
# D3a. no download server: the installer must stop before touching anything (the old GPU install keeps working)
Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Set-Content $marker '1.0.0' -Encoding ASCII -NoNewline
$hashBefore = (Get-FileHash $torchCuda -Algorithm SHA256).Hash
$r = Run-Setup $app '' (Join-Path $work 'd3a.log')
Check 'offline: setup stops with an error instead of leaving a mix of old and new PyTorch files' (($r.Exit -ne 0) -and ((Get-FileHash $torchCuda -Algorithm SHA256).Hash -eq $hashBefore) -and ((Get-Content $marker -Raw).Trim() -eq '1.0.0')) "exit $($r.Exit)"
# D3b. with the server: the matching add-on is chosen and installed on its own (the person is not left on the CPU)
$server = Start-Server (Resolve-Path 'build\installer').Path
Start-Sleep -Seconds 2
$r = Run-Setup $app '' (Join-Path $work 'd3b.log')
$st = Selftest (Join-Path $app 'Wihok.exe')
Check 'online: the matching GPU support is installed again and the marker is current' (($r.Exit -eq 0) -and ((Get-Content $marker -Raw).Trim() -eq $currentVersion)) "exit $($r.Exit), $($r.Seconds) s, marker '$((Get-Content $marker -Raw).Trim())'"
Check 'and the app uses the GPU' (($st -ne $null) -and $st.ok -and $st.cuda) ($st | ConvertTo-Json -Compress)

Write-Host "== D4. an update started from inside the program: exactly its command line (no /TASKS), server OFF to prove nothing is downloaded"
Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
$torchBefore = (Get-FileHash $torchCuda -Algorithm SHA256).Hash
$appExe = Join-Path $app 'Wihok.exe'
$inApp = @('/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', "/DIR=$app", '/LANG=th', '/RELAUNCH=1', "/LOG=`"$(Join-Path $work 'd4.log')`"")
$sw4 = [Diagnostics.Stopwatch]::StartNew()
# No -Wait here: it would also wait for the program the installer reopens, which stays open (a hang).
$p4 = Start-Process -FilePath $setup -ArgumentList $inApp -PassThru
if (-not $p4.WaitForExit(240000)) { Stop-Process -Id $p4.Id -Force -ErrorAction SilentlyContinue }
$relaunched = $null
for ($i = 0; $i -lt 20 -and -not $relaunched; $i++) { $relaunched = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $appExe } | Select-Object -First 1; if (-not $relaunched) { Start-Sleep -Milliseconds 500 } }
Check 'the in-app update finishes without any download' (($p4.ExitCode -eq 0) -and ($sw4.Elapsed.TotalSeconds -lt 120)) "exit $($p4.ExitCode), $([int]$sw4.Elapsed.TotalSeconds) s"
Check 'it kept the GPU add-on untouched' (((Get-FileHash $torchCuda -Algorithm SHA256).Hash -eq $torchBefore) -and (Test-Path $marker))
Check 'it opened the program again' ($null -ne $relaunched) $(if ($relaunched) { "pid $($relaunched.ProcessId)" } else { 'no Wihok.exe started from the install folder' })
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $appExe } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

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

Write-Host "== D5. an in-app update of a CPU-only install must not start downloading GPU support (no server is running)"
$appC = Join-Path $work 'd5\Wihok'
$r = Run-Setup $appC '' (Join-Path $work 'd5a.log')
$inAppC = @('/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', "/DIR=$appC", '/LANG=en', '/RELAUNCH=1', "/LOG=`"$(Join-Path $work 'd5b.log')`"")
$p5 = Start-Process -FilePath $setup -ArgumentList $inAppC -PassThru
if (-not $p5.WaitForExit(240000)) { Stop-Process -Id $p5.Id -Force -ErrorAction SilentlyContinue }
Check 'the update finishes and downloads nothing' (($r.Exit -eq 0) -and ($p5.ExitCode -eq 0) -and -not (Select-String -Path (Join-Path $work 'd5b.log') -Pattern 'Downloading temporary file' -Quiet)) "install exit $($r.Exit), update exit $($p5.ExitCode)"
Check 'the install is still CPU only' ((-not (Test-Path (Join-Path $appC 'gpu-pack.txt'))) -and (-not (Test-Path (Join-Path $appC '_internal\torch\lib\torch_cuda.dll'))))
Start-Sleep -Seconds 3
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq (Join-Path $appC 'Wihok.exe') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2
$u5 = Get-ChildItem $appC -Filter 'unins*.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($u5) { Start-Process -FilePath $u5.FullName -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -WindowStyle Hidden; Start-Sleep -Seconds 2 }
Check 'that test install is removed again' (-not (Test-Path $uninstallKey) -and -not (Test-Path $shortcut))

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

Write-Host "== J. the language chosen in the installer becomes the app's language (the app reads HKCU\Software\Wihok\Wihok)"
$langKey = 'HKCU:\Software\Wihok\Wihok'
$hadKey = Test-Path $langKey
$langBefore = if ($hadKey) { (Get-ItemProperty $langKey -ErrorAction SilentlyContinue).language } else { $null }
function Get-AppLanguage { if (Test-Path $langKey) { (Get-ItemProperty $langKey -ErrorAction SilentlyContinue).language } else { $null } }
function Uninstall-Quietly([string]$dir) {
    $u = Get-ChildItem $dir -Filter 'unins*.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($u) { Start-Process -FilePath $u.FullName -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -WindowStyle Hidden; Start-Sleep -Seconds 2 }
}
try {
    foreach ($lang in 'th', 'en') {
        if (Test-Path $langKey) { Remove-ItemProperty -Path $langKey -Name language -ErrorAction SilentlyContinue }   # a computer that has not run Wihok yet
        $dirJ = Join-Path $work "j-$lang\Wihok"
        $r = Run-Setup $dirJ '' (Join-Path $work "j-$lang.log") $lang
        Check "installer language '$lang' is handed to the app" (($r.Exit -eq 0) -and ((Get-AppLanguage) -eq $lang)) "exit $($r.Exit), app language is now '$(Get-AppLanguage)'"
        Uninstall-Quietly $dirJ
    }
    # somebody who already picked a language inside the app keeps it
    if (-not (Test-Path $langKey)) { New-Item -Path $langKey -Force | Out-Null }
    Set-ItemProperty -Path $langKey -Name language -Value 'en'
    $dirK = Join-Path $work 'j-keep\Wihok'
    $r = Run-Setup $dirK '' (Join-Path $work 'j-keep.log') 'th'
    Check 'a language already chosen in the app is not overwritten by the installer' (($r.Exit -eq 0) -and ((Get-AppLanguage) -eq 'en')) "installer in Thai, app language stays '$(Get-AppLanguage)'"
    Uninstall-Quietly $dirK
    Check 'the language setting survives an uninstall (the settings prompt is the only thing that removes it)' ((Get-AppLanguage) -eq 'en')
} finally {
    # put the real setting back exactly as it was
    if ($hadKey) {
        if ($null -ne $langBefore) { Set-ItemProperty -Path $langKey -Name language -Value $langBefore } elseif (Test-Path $langKey) { Remove-ItemProperty -Path $langKey -Name language -ErrorAction SilentlyContinue }
    } elseif (Test-Path $langKey) { Remove-Item -Path $langKey -Recurse -Force }
}

Write-Host "`n== Summary"
$results | Group-Object Result | ForEach-Object { Write-Host ("{0}: {1}" -f $_.Name, $_.Count) }
$results | Where-Object Result -eq 'FAIL' | Format-Table -AutoSize -Wrap
