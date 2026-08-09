#Requires -Version 5.1
<#
.SYNOPSIS
    Downloads the recommended model stack for Polar Adventures into a local ComfyUI Desktop install.

.DESCRIPTION
    This script checks for ComfyUI Desktop in the default Electron install location, then
    downloads the SD 1.5 checkpoint, VAE, ControlNet models, and installs the custom nodes
    needed by the polar-adventures asset pipeline.

.PARAMETER ComfyUiPath
    Path to your ComfyUI Desktop folder. Defaults to the ComfyUI Desktop Electron install.

.PARAMETER SkipModels
    Skip downloading model files (useful if you only want to install custom nodes).

.PARAMETER SkipNodes
    Skip installing custom nodes.

.EXAMPLE
    .\setup_windows_comfyui.ps1

.EXAMPLE
    .\setup_windows_comfyui.ps1 -ComfyUiPath "C:\Users\yakov\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"

.NOTE
    CartoonXL is an SDXL 1.0 checkpoint. You need a ComfyUI install that can run SDXL (most modern installs do).
    The Civitai download URL may redirect to a signed B2 link; curl.exe and Invoke-WebRequest both follow redirects.
#>
param(
    [string]$ComfyUiPath = "$env:LOCALAPPDATA\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI",
    [switch]$SkipModels,
    [switch]$SkipNodes
)

$ErrorActionPreference = "Stop"

# -----------------------------------------------------------------------------
# Verify ComfyUI Desktop location
# -----------------------------------------------------------------------------
if (-not (Test-Path $ComfyUiPath)) {
    Write-Host "ERROR: ComfyUI Desktop folder not found at: $ComfyUiPath" -ForegroundColor Red
    Write-Host "Please pass the correct path with -ComfyUiPath"
    exit 1
}

$modelsDir = Join-Path $ComfyUiPath "models"
$customNodesDir = Join-Path $ComfyUiPath "custom_nodes"

foreach ($d in @("checkpoints", "vae", "loras", "controlnet")) {
    $full = Join-Path $modelsDir $d
    if (-not (Test-Path $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
        Write-Host "Created folder: $full" -ForegroundColor DarkGray
    }
}

# -----------------------------------------------------------------------------
# Helper: download a file if it does not already exist
# -----------------------------------------------------------------------------
function Get-ModelFile {
    param(
        [string]$Url,
        [string]$Destination,
        [string]$Name
    )

    if (Test-Path $Destination) {
        Write-Host "  Already exists: $Name" -ForegroundColor Green
        return
    }

    Write-Host "  Downloading $Name..." -ForegroundColor Cyan
    Write-Host "     From: $Url" -ForegroundColor DarkGray
    try {
        $parent = Split-Path $Destination -Parent
        if (-not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
        Write-Host "     Saved to: $Destination" -ForegroundColor Green
    }
    catch {
        Write-Host "     FAILED: $_" -ForegroundColor Red
    }
}

# -----------------------------------------------------------------------------
# Models to download
# -----------------------------------------------------------------------------
$downloads = @(
    @{
        Name = "SD 1.5 base checkpoint"
        Url  = "https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive/resolve/main/v1-5-pruned-emaonly.safetensors?download=true"
        Dest = Join-Path $modelsDir "checkpoints\v1-5-pruned-emaonly.safetensors"
    },
    @{
        Name = "CartoonXL SDXL checkpoint (flat vector game style)"
        Url  = "https://civitai.com/api/download/models/437130"
        Dest = Join-Path $modelsDir "checkpoints\cartoonxl_v10.safetensors"
    },
    @{
        Name = "Improved VAE"
        Url  = "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors?download=true"
        Dest = Join-Path $modelsDir "vae\vae-ft-mse-840000-ema-pruned.safetensors"
    },
    @{
        Name = "ControlNet OpenPose"
        Url  = "https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_openpose.pth?download=true"
        Dest = Join-Path $modelsDir "controlnet\control_v11p_sd15_openpose.pth"
    },
    @{
        Name = "ControlNet Canny"
        Url  = "https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_canny.pth?download=true"
        Dest = Join-Path $modelsDir "controlnet\control_v11p_sd15_canny.pth"
    }
)

if (-not $SkipModels) {
    Write-Host "`nDownloading recommended model stack..." -ForegroundColor Yellow
    foreach ($item in $downloads) {
        Get-ModelFile -Url $item.Url -Destination $item.Dest -Name $item.Name
    }

    Write-Host "`nModel notes:" -ForegroundColor Yellow
    Write-Host "  CartoonXL is an SDXL checkpoint. After install, use it in workflows:" -ForegroundColor Cyan
    Write-Host "    - Prompt keywords: cartoon, cartoon style, flat, cute, kawaii, clipart" -ForegroundColor Cyan
    Write-Host "    - Recommended: 28-40 steps, CFG 7-8, DPM++ 2M Karras, 1024x1024 then downscale" -ForegroundColor Cyan

    Write-Host "`nLoRA note:" -ForegroundColor Yellow
    Write-Host "  You must download LoRAs manually because most sources require login." -ForegroundColor Cyan
    Write-Host "  Put them in: $(Join-Path $modelsDir 'loras')" -ForegroundColor Cyan
    Write-Host "  Recommended for flat-vector characters:" -ForegroundColor Cyan
    Write-Host "    - line-art-flat-colors-sdxl -> https://huggingface.co/Muapi/line-art-flat-colors-sdxl" -ForegroundColor Cyan
    Write-Host "  Recommended for isometric tiles/objects:" -ForegroundColor Cyan
    Write-Host "    - Zavy's Cute Isometric Tiles (SDXL)  -> https://civarchive.com/models/340599?modelVersionId=381373" -ForegroundColor Cyan
    Write-Host "    - Wolfie's Isometric Scenes (SDXL)    -> https://civitai.com/models/593055/wolfies-isometric-scenes-sdxl-concept" -ForegroundColor Cyan
    Write-Host "    - DarkoIsometricStyle (SDXL)          -> https://civitai.com/models/1954920/darkoisometricstyle" -ForegroundColor Cyan
}

# -----------------------------------------------------------------------------
# Custom nodes to install
# -----------------------------------------------------------------------------
$nodes = @(
    @{ Repo = "https://github.com/huchenlei/ComfyUI-layerdiffuse.git"; Name = "ComfyUI-layerdiffuse" },
    @{ Repo = "https://github.com/Jcd1230/rembg-comfyui-node.git"; Name = "rembg-comfyui-node" },
    @{ Repo = "https://github.com/VAST-AI-Research/ComfyUI-Tripo.git"; Name = "ComfyUI-Tripo" }
)

if (-not $SkipNodes) {
    Write-Host "`nInstalling custom nodes..." -ForegroundColor Yellow
    foreach ($node in $nodes) {
        $target = Join-Path $customNodesDir $node.Name
        if (Test-Path $target) {
            Write-Host "  Already installed: $($node.Name)" -ForegroundColor Green
        }
        else {
            Write-Host "  Installing $($node.Name)..." -ForegroundColor Cyan
            try {
                git clone $node.Repo $target
                Write-Host "    Installed: $($node.Name)" -ForegroundColor Green
            }
            catch {
                Write-Host "    FAILED: $_" -ForegroundColor Red
                Write-Host "    Make sure git is on your PATH." -ForegroundColor Red
            }
        }
    }

    Write-Host "`nTripo node note:" -ForegroundColor Yellow
    Write-Host "  ComfyUI-Tripo requires a Tripo API key. Set the TRIPO_API_KEY environment" -ForegroundColor Cyan
    Write-Host "  variable or enter it in the Tripo: Generate model node. Get a key at:" -ForegroundColor Cyan
    Write-Host "    https://developers.tripo3d.ai/" -ForegroundColor Cyan

    Write-Host "`nOptional node note:" -ForegroundColor Yellow
    Write-Host "  ComfyUI-AdvancedTiling is optional. It can fail to install through ComfyUI Manager." -ForegroundColor Cyan
    Write-Host "  If you want it, install from: https://github.com/JosefKuchar/ComfyUI-AdvancedTiling" -ForegroundColor Cyan
    Write-Host "  The postprocess_assets.py script already handles basic tile masking." -ForegroundColor Cyan
}

Write-Host "`nSetup complete. Restart ComfyUI Desktop to load new models and nodes." -ForegroundColor Green
Write-Host "Then import the test workflow:" -ForegroundColor Cyan
Write-Host "  https://raw.githubusercontent.com/yakovkhalinsky/polar-adventure/main/.comfyui-workflows/polar_bear_single_sd15.json" -ForegroundColor Cyan
