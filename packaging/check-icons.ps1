<#
Checks that Wihok shows its icon: the one in the file, and the ones Windows asks the running window for
(those are what the taskbar button and Alt+Tab draw). It starts the program, moves its window off screen at once,
reads the icons, saves them as PNGs and stops the program.

  .\packaging\check-icons.ps1 -Exe C:\path\to\Wihok.exe
  .\packaging\check-icons.ps1 -Exe .\.venv\Scripts\python.exe -Arguments main.py     # the program run from source

Output pictures go to -OutDir (default: build\icon-check).
#>
param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [string]$Arguments = '',
    [string]$OutDir = 'build\icon-check',
    [string]$Title = 'Wihok'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
New-Item -ItemType Directory -Force $OutDir | Out-Null
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System; using System.Runtime.InteropServices; using System.Text; using System.Collections.Generic; using System.Drawing;
public static class IconProbe {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr h, uint cmd);
  [DllImport("user32.dll", EntryPoint="GetWindowLongW")] static extern int GetWindowLong(IntPtr h, int idx);
  [DllImport("user32.dll", EntryPoint="GetClassLongPtrW")] static extern IntPtr GetClassLongPtr(IntPtr h, int idx);
  [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  public static IntPtr FindWindow(uint[] pids, string title) {
    IntPtr found = IntPtr.Zero;
    EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p); if (Array.IndexOf(pids, p) < 0 || !IsWindowVisible(h)) return true; var s = new StringBuilder(256); GetWindowText(h, s, 256); if (s.ToString() == title) { found = h; return false; } return true; }, IntPtr.Zero);
    return found;
  }
  public static void Hide(IntPtr h) { SetWindowPos(h, IntPtr.Zero, -9000, -9000, 0, 0, 0x0001 | 0x0004 | 0x0010); }
  public static void Close(IntPtr h) { PostMessage(h, 0x0010, IntPtr.Zero, IntPtr.Zero); }
  // Would the window get a taskbar button? Visible, not a tool window, and without an owner.
  public static string TaskbarEligibility(IntPtr h) {
    int ex = GetWindowLong(h, -20); bool tool = (ex & 0x80) != 0; bool app = (ex & 0x40000) != 0; bool owned = GetWindow(h, 4) != IntPtr.Zero;
    return "visible=" + IsWindowVisible(h) + " toolWindow=" + tool + " appWindowStyle=" + app + " hasOwner=" + owned + " -> taskbar button: " + (!tool && !owned);
  }
  static IntPtr WmGetIcon(IntPtr h, int kind) { return SendMessage(h, 0x007F, (IntPtr)kind, IntPtr.Zero); }
  // kind: 0 = small, 1 = big, 2 = small2
  public static Bitmap FromWindow(IntPtr h, int kind) {
    IntPtr hi = WmGetIcon(h, kind);
    if (hi == IntPtr.Zero) return null;
    using (var icon = Icon.FromHandle(hi)) { var bmp = new Bitmap(icon.Width, icon.Height); using (var g = Graphics.FromImage(bmp)) { g.Clear(Color.Transparent); g.DrawIcon(icon, 0, 0); } return bmp; }
  }
  public static Bitmap FromClass(IntPtr h, bool small) {
    IntPtr hi = GetClassLongPtr(h, small ? -34 : -14);
    if (hi == IntPtr.Zero) return null;
    using (var icon = Icon.FromHandle(hi)) { var bmp = new Bitmap(icon.Width, icon.Height); using (var g = Graphics.FromImage(bmp)) { g.Clear(Color.Transparent); g.DrawIcon(icon, 0, 0); } return bmp; }
  }
  public static int Opaque(Bitmap b) { int n = 0; for (int x = 0; x < b.Width; x++) for (int y = 0; y < b.Height; y++) if (b.GetPixel(x, y).A > 0) n++; return n; }
}
'@
Add-Type -AssemblyName System.Drawing

function Describe([string]$label, $bmp, [string]$file) {
    if ($null -eq $bmp) { Write-Host ("{0,-38} none" -f $label); return }
    $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png)
    $n = [IconProbe]::Opaque($bmp)
    Write-Host ("{0,-38} {1}x{2}, {3} visible pixels of {4} {5}" -f $label, $bmp.Width, $bmp.Height, $n, ($bmp.Width * $bmp.Height), $(if ($n -gt ($bmp.Width * $bmp.Height * 0.2)) { '(drawn)' } else { '(BLANK or almost)' }))
}

# 1) the icon stored in the program file (what the Start Menu shortcut and the file in Explorer show)
$exePath = (Resolve-Path $Exe).Path
if ($exePath -notmatch 'python') {
    $assoc = [System.Drawing.Icon]::ExtractAssociatedIcon($exePath)
    $bmp = $assoc.ToBitmap()
    Describe 'icon inside the .exe file' $bmp (Join-Path $OutDir 'exe-file.png')
}

# 2) the icons the running window gives Windows
$startedAt = Get-Date
$names = @([IO.Path]::GetFileNameWithoutExtension($exePath), 'python3.12', 'python')
$startArgs = @{ FilePath = $exePath; PassThru = $true; WorkingDirectory = $root }
if ($Arguments) { $startArgs.ArgumentList = $Arguments }   # an empty argument list is an error for Start-Process
$p = Start-Process @startArgs
try {
    $h = [IntPtr]::Zero
    $end = (Get-Date).AddSeconds(40)
    while ($h -eq [IntPtr]::Zero -and (Get-Date) -lt $end) {
        Start-Sleep -Milliseconds 250
        # the venv's python.exe starts the real interpreter as a child and the child owns the window, so look at every
        # process of the right name that started after this script did
        $ids = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $names -contains $_.ProcessName -and $_.StartTime -ge $startedAt.AddSeconds(-2) } | ForEach-Object { [uint32]$_.Id })
        if ($ids.Count -gt 0) { $h = [IconProbe]::FindWindow($ids, $Title) }
    }
    if ($h -eq [IntPtr]::Zero) { Write-Host "window '$Title' did not appear within 40 s"; return }
    [IconProbe]::Hide($h)   # keep it off the user's screen; the taskbar button and its icon still exist
    Start-Sleep -Milliseconds 1500
    Write-Host ("window: " + [IconProbe]::TaskbarEligibility($h))
    Describe 'window icon, big (taskbar, Alt+Tab)' ([IconProbe]::FromWindow($h, 1)) (Join-Path $OutDir 'window-big.png')
    Describe 'window icon, small (title bar)' ([IconProbe]::FromWindow($h, 0)) (Join-Path $OutDir 'window-small.png')
    Describe 'window icon, small2' ([IconProbe]::FromWindow($h, 2)) (Join-Path $OutDir 'window-small2.png')
    Describe 'class icon, big' ([IconProbe]::FromClass($h, $false)) (Join-Path $OutDir 'class-big.png')
    [IconProbe]::Close($h)
    Start-Sleep -Seconds 2
} finally {
    # Stop only what this script started: a process of these names that began after it and runs this program
    # (never anything that mentions PyInstaller, so a build in the background is safe).
    Get-CimInstance Win32_Process | Where-Object {
        $names -contains [IO.Path]::GetFileNameWithoutExtension($_.Name) -and $_.CreationDate -ge $startedAt.AddSeconds(-2) -and
        $_.CommandLine -notmatch 'PyInstaller|--distpath' -and ($_.CommandLine -match 'main\.py' -or $_.ExecutablePath -eq $exePath)
    } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}
