#Requires -Version 7.2
<#
.SYNOPSIS
    Patch ComfyUI-layerdiffuse for newer ComfyUI Desktop versions.

.DESCRIPTION
    The official huchenlei/ComfyUI-layerdiffuse repository calls
    JoinImageWithAlpha().join_image_with_alpha(), which was removed in
    recent ComfyUI versions (refactored to .execute()).

    This script rewrites that single line in layered_diffusion.py so it
    tries the new API first and falls back to the old one, making
    LayeredDiffusionDecodeRGBA work on current ComfyUI Desktop installs.

.PARAMETER LayerDiffusePath
    Path to the ComfyUI-layerdiffuse custom node folder. Defaults to the
    standard ComfyUI Desktop location.

.EXAMPLE
    .\.comfyui-workflows\patch_layerdiffuse_comfyui.ps1

.EXAMPLE
    .\.comfyui-workflows\patch_layerdiffuse_comfyui.ps1 -LayerDiffusePath "C:\ComfyUI\custom_nodes\ComfyUI-layerdiffuse"
#>
param(
    [string]$LayerDiffusePath = "$env:LOCALAPPDATA\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\custom_nodes\ComfyUI-layerdiffuse"
)

$ErrorActionPreference = "Stop"

$layeredDiffusionPy = Join-Path $LayerDiffusePath "layered_diffusion.py"

if (-not (Test-Path $layeredDiffusionPy)) {
    Write-Error "Could not find $layeredDiffusionPy"
    Write-Host "Install ComfyUI-layerdiffuse first, or pass -LayerDiffusePath with the correct folder." -ForegroundColor Yellow
    exit 1
}

$content = Get-Content $layeredDiffusionPy -Raw
$oldLine = "return JoinImageWithAlpha().join_image_with_alpha(image, alpha)"

if ($content -notlike "*JoinImageWithAlpha*") {
    Write-Host "Patch already applied or JoinImageWithAlpha not present; nothing to do." -ForegroundColor Green
    exit 0
}

if ($content -like "*try:*execute*except AttributeError*join_image_with_alpha*") {
    Write-Host "Patch already applied." -ForegroundColor Green
    exit 0
}

if ($content -like "*$oldLine*") {
    Write-Host "Patching $layeredDiffusionPy for newer ComfyUI versions..." -ForegroundColor Cyan

    $newBlock = @'
try:
    return JoinImageWithAlpha().execute(image, alpha)
except AttributeError:
    return JoinImageWithAlpha().join_image_with_alpha(image, alpha)
'@

    $content = $content.Replace($oldLine, $newBlock.Trim())
    Set-Content $layeredDiffusionPy $content -NoNewline
    Write-Host "Done. Restart ComfyUI Desktop completely for the change to take effect." -ForegroundColor Green
}
else {
    Write-Warning "Could not locate the expected JoinImageWithAlpha call."
    Write-Warning "Manual inspection may be needed: $layeredDiffusionPy"
    exit 1
}
