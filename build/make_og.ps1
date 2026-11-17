# Draws the 1200x630 link-preview image (site/og.png) used when the site is shared.
# Windows only (System.Drawing). The image is committed, so builds elsewhere skip this.
#   powershell -NoProfile -ExecutionPolicy Bypass -File build/make_og.ps1 -Places 2543 -Areas 1033
param([int]$Places = 2500, [int]$Areas = 900)
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root "site\og.png"
$icon = Join-Path $root "site\icons\icon-512.png"

$W = 1200; $H = 630
$bmp = New-Object System.Drawing.Bitmap $W, $H
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = "AntiAlias"; $g.TextRenderingHint = "AntiAliasGridFit"; $g.InterpolationMode = "HighQualityBicubic"

# background: warm map-paper with soft street grid and sea edge
$g.Clear([System.Drawing.Color]::FromArgb(242, 239, 233))
$grid = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 255, 255)), 6
$gridEdge = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(216, 207, 196)), 9
foreach ($i in 0..9) { $x = 620 + $i * 70; $g.DrawLine($gridEdge, $x, 0, $x - 120, $H); $g.DrawLine($grid, $x, 0, $x - 120, $H) }
foreach ($i in 0..8) { $y = 30 + $i * 75; $g.DrawLine($gridEdge, 560, $y, $W, $y + 40); $g.DrawLine($grid, 560, $y, $W, $y + 40) }
$sea = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(170, 211, 223))
$g.FillPolygon($sea, @((New-Object System.Drawing.Point 1200,0), (New-Object System.Drawing.Point 1200,630), (New-Object System.Drawing.Point 1080,630), (New-Object System.Drawing.Point 1130,330), (New-Object System.Drawing.Point 1060,0)))
$road = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(232, 146, 162)), 14
$g.DrawBezier($road, 700, 630, 820, 420, 900, 260, 1050, 0)

# pins
$pinCafe = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(194, 65, 12))
$pinRest = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(15, 139, 125))
$white = New-Object System.Drawing.Pen ([System.Drawing.Color]::White), 5
$pins = @(@(760,140,0),@(860,230,1),@(930,120,0),@(820,350,1),@(980,300,0),@(900,440,0),@(760,500,1),@(1010,470,1),@(700,280,0),@(1040,190,1))
foreach ($p in $pins) {
  $b = if ($p[2] -eq 0) { $pinCafe } else { $pinRest }
  $g.FillEllipse($b, $p[0] - 22, $p[1] - 22, 44, 44); $g.DrawEllipse($white, $p[0] - 22, $p[1] - 22, 44, 44)
}

# left text panel
$panel = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(245, 255, 255, 255))
$g.FillRectangle($panel, 0, 0, 640, $H)
$ink = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(36, 26, 20))
$muted = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(118, 103, 92))
$accent = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(194, 65, 12))
$img = [System.Drawing.Image]::FromFile($icon)
$g.DrawImage($img, 64, 64, 96, 96)
$fTitle = New-Object System.Drawing.Font "Segoe UI", 50, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$fSub = New-Object System.Drawing.Font "Segoe UI", 27, ([System.Drawing.FontStyle]::Regular), ([System.Drawing.GraphicsUnit]::Pixel)
$fStat = New-Object System.Drawing.Font "Segoe UI", 40, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$fSmall = New-Object System.Drawing.Font "Segoe UI", 22, ([System.Drawing.FontStyle]::Regular), ([System.Drawing.GraphicsUnit]::Pixel)
$g.DrawString("Mumbai Cafe &", $fTitle, $ink, 60, 190)
$g.DrawString("Restaurant Finder", $fTitle, $ink, 60, 252)
$rect = New-Object System.Drawing.RectangleF 62, 334, 540, 90
$g.DrawString("Colaba to Thane, Kalyan and Panvel. Veg, Jain, ratings, menus.", $fSub, $muted, $rect)
$g.DrawString(("{0:N0}" -f $Places), $fStat, $accent, 60, 470)
$g.DrawString("places", $fSmall, $muted, 64, 522)
$g.DrawString(("{0:N0}+" -f $Areas), $fStat, $accent, 300, 470)
$g.DrawString("areas & stations", $fSmall, $muted, 304, 522)

$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$img.Dispose(); $g.Dispose(); $bmp.Dispose()
"og.png written: $out"
