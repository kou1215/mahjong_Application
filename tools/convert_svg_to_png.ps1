# Convert all SVG tiles to PNG using ImageMagick (Windows PowerShell)
# Requires: ImageMagick `magick` available on PATH

$tilesDir = Join-Path $PSScriptRoot "..\static\tiles"
Get-ChildItem -Path $tilesDir -Filter "*.svg" | ForEach-Object {
    $svg = $_.FullName
    $png = [System.IO.Path]::ChangeExtension($svg, '.png')
    Write-Host "Converting $($_.Name) -> $(Split-Path $png -Leaf)"
    magick convert "$svg" -background none -resize 288x420 "$png"
}
Write-Host "Done. PNGs are in $tilesDir"
