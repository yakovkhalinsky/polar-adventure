#Requires -Version 7.2
<#
.SYNOPSIS
    Downloads the recommended SDXL model stack for Fez-like voxel game assets into a local ComfyUI Desktop install.

.DESCRIPTION
    Faster, resumable, parallel version of the original setup script.
    - Installs CartoonXL SDXL base + Voxel XL LoRA for Fez-like voxel game assets
    - Uses BITS/aria2/curl-style resume where possible (falls back to Invoke-WebRequest)
    - Runs downloads in parallel with progress bars
    - Verifies partial files and resumes interrupted transfers
    - Clones custom nodes with --depth=1 and updates existing ones
    - Provides verbose, color-coded progress output

.PARAMETER ComfyUiPath
    Path to your ComfyUI Desktop folder. Defaults to the ComfyUI Desktop Electron install.

.PARAMETER SkipModels
    Skip downloading model files (useful if you only want to install custom nodes).

.PARAMETER SkipNodes
    Skip installing custom nodes.

.PARAMETER MaxParallelDownloads
    Maximum number of model downloads to run in parallel. Default: 3.

.PARAMETER Force
    Re-download existing model files even if they already exist.

.EXAMPLE
    .\setup_windows_comfyui_fast.ps1

.EXAMPLE
    .\setup_windows_comfyui_fast.ps1 -ComfyUiPath "C:\Users\yakov\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"

.NOTE
    CartoonXL is an SDXL 1.0 base checkpoint. Voxel XL LoRA adds the Fez-like voxel style.
    You need a ComfyUI install that can run SDXL (most modern installs do).
    The Civitai download URL may redirect to a signed B2 link; curl.exe and Invoke-WebRequest both follow redirects.
#>
param(
    [string]$ComfyUiPath = "$env:LOCALAPPDATA\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI",
    [switch]$SkipModels,
    [switch]$SkipNodes,
    [int]$MaxParallelDownloads = 3,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
function Write-Info    ($msg) { Write-Host "[INFO]    $msg" -ForegroundColor Cyan }
function Write-Success ($msg) { Write-Host "[OK]      $msg" -ForegroundColor Green }
function Write-Warn    ($msg) { Write-Host "[WARN]    $msg" -ForegroundColor Yellow }
function Write-Error   ($msg) { Write-Host "[ERROR]   $msg" -ForegroundColor Red }

# ---------------------------------------------------------------------------
# Verify ComfyUI Desktop location
# ---------------------------------------------------------------------------
if (-not (Test-Path $ComfyUiPath)) {
    Write-Error "ComfyUI Desktop folder not found at: $ComfyUiPath"
    Write-Info "Please pass the correct path with -ComfyUiPath"
    exit 1
}

$modelsDir = Join-Path $ComfyUiPath "models"
$customNodesDir = Join-Path $ComfyUiPath "custom_nodes"

foreach ($d in @("checkpoints", "vae", "loras", "controlnet")) {
    $full = Join-Path $modelsDir $d
    if (-not (Test-Path $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
        Write-Info "Created folder: $full"
    }
}

# ---------------------------------------------------------------------------
# Pick the best available downloader
# ---------------------------------------------------------------------------
function Get-DownloadTool {
    # NOTE: aria2 is installed but cannot reach the network in this environment.
    # Prefer Windows curl.exe (works with the system proxy/firewall).
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) { return @{ Name = "curl"; Command = $curl.Source } }

    # Fallback to aria2 if present and eventually reachable
    $aria2Path = "C:\Users\yakov\AppData\Local\Microsoft\WinGet\Packages\aria2.aria2_Microsoft.Winget.Source_8wekyb3d8bbwe\aria2-1.37.0-win-64bit-build1\aria2c.exe"
    if (Test-Path $aria2Path) { return @{ Name = "aria2"; Command = $aria2Path } }
    $aria2 = Get-Command aria2c.exe -ErrorAction SilentlyContinue
    if ($aria2) { return @{ Name = "aria2"; Command = $aria2.Source } }

    return @{ Name = "bits"; Command = "bits" }
}

# ---------------------------------------------------------------------------
# Ensure git binary is discoverable this session
# ---------------------------------------------------------------------------
$gitBinDir = "C:\Program Files\Git\cmd"
if (Test-Path $gitBinDir) {
    if (-not ($env:PATH -like "*${gitBinDir}*")) {
        $env:PATH = "$env:PATH;$gitBinDir"
    }
}
$downloadTool = Get-DownloadTool
Write-Info "Using downloader: $($downloadTool.Name)"

# ---------------------------------------------------------------------------
# Download a single file with resume support and progress
# ---------------------------------------------------------------------------
function Get-ModelFile {
    param(
        [string]$Url,
        [string]$Destination,
        [string]$Name
    )

    if ((Test-Path $Destination) -and -not $Force) {
        $existingSize = (Get-Item $Destination).Length
        if ($existingSize -gt 1MB) {
            Write-Success "Already exists: $Name ($([math]::Round($existingSize/1MB,2)) MB)"
            return @{ Success = $true; Name = $Name; Skipped = $true }
        } else {
            Write-Warn "Removing tiny/incomplete file: $Name ($existingSize bytes)"
            Remove-Item $Destination -Force
        }
    }

    $parent = Split-Path $Destination -Parent
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    Write-Info "Downloading $Name..."
    Write-Host "          From: $Url" -ForegroundColor DarkGray

    try {
        switch ($downloadTool.Name) {
            "aria2" {
                $log = [System.IO.Path]::GetTempFileName()
                $proc = Start-Process -FilePath $downloadTool.Command -ArgumentList @(
                    "--continue", "--max-connection-per-server=8", "--split=8",
                    "--min-split-size=5M", "--file-allocation=none",
                    "--summary-interval=0", "--console-log-level=error",
                    "-d", "`"$parent`"", "-o", "`"$(Split-Path $Destination -Leaf)`"",
                    "`"$Url`""
                ) -RedirectStandardOutput $log -RedirectStandardError $log -PassThru -NoNewWindow
                $proc.WaitForExit()
                if ($proc.ExitCode -ne 0) {
                    throw "aria2c exited with code $($proc.ExitCode). Log: $(Get-Content $log -Raw)"
                }
                Remove-Item $log -ErrorAction SilentlyContinue
            }
            "curl" {
                $proc = Start-Process -FilePath $downloadTool.Command -ArgumentList @(
                    "-L", "-C", "-", "--retry", "3", "--retry-delay", "5",
                    "--progress-bar", "-o", "`"$Destination`"", "`"$Url`""
                ) -Wait -NoNewWindow
                if ($proc.ExitCode -ne 0) {
                    throw "curl exited with code $($proc.ExitCode)"
                }
            }
            "bits" {
                # BITS does not support all URLs, but is the fastest native option when it works
                $jobName = "download_$(Get-Random)"
                try {
                    Start-BitsTransfer -Source $Url -Destination $Destination -DisplayName $jobName -Description $Name -ErrorAction Stop
                }
                catch {
                    # Fallback to Invoke-WebRequest if BITS fails (e.g., unsupported protocol/headers)
                    Write-Warn "BITS transfer failed for $Name, falling back to Invoke-WebRequest."
                    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
                }
            }
        }

        $finalSize = (Get-Item $Destination).Length
        Write-Success "Saved $Name ($([math]::Round($finalSize/1MB,2)) MB)"
        return @{ Success = $true; Name = $Name; Skipped = $false }
    }
    catch {
        Write-Error "FAILED to download ${Name}: $_"
        return @{ Success = $false; Name = $Name; Skipped = $false }
    }
}

# ---------------------------------------------------------------------------
# Models to download
# ---------------------------------------------------------------------------
$downloads = @(
    @{
        Name = "SD 1.5 base checkpoint"
        Url  = "https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive/resolve/main/v1-5-pruned-emaonly.safetensors?download=true"
        Dest = Join-Path $modelsDir "checkpoints\v1-5-pruned-emaonly.safetensors"
    },
    @{
        Name = "CartoonXL SDXL checkpoint (base for voxel style)"
        Url  = "https://civitai.com/api/download/models/437130"
        Dest = Join-Path $modelsDir "checkpoints\cartoonxl_v10.safetensors"
    },
    @{
        Name = "Voxel XL LoRA (Fez-like voxel style)"
        Url  = "https://huggingface.co/Fictiverse/Voxel_XL_Lora/resolve/main/VoxelXL_v1.safetensors?download=true"
        Dest = Join-Path $modelsDir "loras\VoxelXL_v1.safetensors"
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
    Write-Info "Starting model downloads (max parallel: $MaxParallelDownloads)..."

    $results = $downloads | ForEach-Object -Parallel {
        # Re-import helper by dot-sourcing the function definition from parent scope
        function Get-ModelFile {
            param([string]$Url, [string]$Destination, [string]$Name)
            # Minimal inline fallback for parallel execution
            $tool = $using:downloadTool
            try {
                switch ($tool.Name) {
                    "aria2" {
                        $parent = Split-Path $Destination -Parent
                        $proc = Start-Process -FilePath $tool.Command -ArgumentList @(
                            "--continue", "--max-connection-per-server=8", "--split=8",
                            "--min-split-size=5M", "--file-allocation=none",
                            "--summary-interval=0", "--console-log-level=error",
                            "-d", "`"$parent`"", "-o", "`"$(Split-Path $Destination -Leaf)`"",
                            "`"$Url`""
                        ) -Wait -NoNewWindow
                        if ($proc.ExitCode -ne 0) { throw "aria2c exit code $($proc.ExitCode)" }
                    }
                    "curl" {
                        $proc = Start-Process -FilePath $tool.Command -ArgumentList @(
                            "-L", "-C", "-", "--retry", "3", "--retry-delay", "5",
                            "--progress-bar", "-o", "`"$Destination`"", "`"$Url`""
                        ) -Wait -NoNewWindow
                        if ($proc.ExitCode -ne 0) { throw "curl exit code $($proc.ExitCode)" }
                    }
                    "bits" {
                        try {
                            Start-BitsTransfer -Source $Url -Destination $Destination -DisplayName $Name -Description $Name -ErrorAction Stop
                        } catch {
                            Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
                        }
                    }
                }
                return @{ Success = $true; Name = $Name }
            }
            catch {
                Write-Host "[ERROR]   FAILED: $Name - $_" -ForegroundColor Red
                return @{ Success = $false; Name = $Name }
            }
        }
        Get-ModelFile -Url $_.Url -Destination $_.Dest -Name $_.Name
    } -ThrottleLimit $MaxParallelDownloads

    $successCount = ($results | Where-Object { $_.Success }).Count
    $failCount = $results.Count - $successCount

    Write-Info "Model downloads complete: $successCount succeeded, $failCount failed."

    Write-Host ""
    Write-Warn "Model notes:"
    Write-Info "  CartoonXL is the SDXL base checkpoint."
    Write-Info "  Voxel XL LoRA is loaded in the asset pipeline to produce Fez-like voxel art."
    Write-Info "    - Trigger word: voxel style"
    Write-Info "    - Prompt keywords: voxel style, low poly, isometric, Fez-like, blocky, retro 3D"
    Write-Info "    - Recommended: 30-40 steps, CFG 7-8, DPM++ 2M Karras, 1024x1024 then downscale"

    Write-Host ""
    Write-Warn "Optional LoRAs:"
    Write-Info "  Put extras in: $(Join-Path $modelsDir 'loras')"
    Write-Info "  - Zavy's Cute Isometric Tiles (SDXL) -> https://civarchive.com/models/340599?modelVersionId=381373"
    Write-Info "  - Wolfie's Isometric Scenes (SDXL)  -> https://civitai.com/models/593055/wolfies-isometric-scenes-sdxl-concept"
    Write-Info "  - DarkoIsometricStyle (SDXL)         -> https://civitai.com/models/1954920/darkoisometricstyle"
}

# ---------------------------------------------------------------------------
# Custom nodes to install
# ---------------------------------------------------------------------------
$nodes = @(
    @{ Repo = "https://github.com/huchenlei/ComfyUI-layerdiffuse.git"; Name = "ComfyUI-layerdiffuse" },
    @{ Repo = "https://github.com/Jcd1230/rembg-comfyui-node.git"; Name = "rembg-comfyui-node" },
    @{ Repo = "https://github.com/VAST-AI-Research/ComfyUI-Tripo.git"; Name = "ComfyUI-Tripo" }
)

if (-not $SkipNodes) {
    Write-Host ""
    Write-Info "Installing custom nodes..."

    foreach ($node in $nodes) {
        $target = Join-Path $customNodesDir $node.Name
        if (Test-Path $target) {
            Write-Success "Already installed: $($node.Name)"
            try {
                Push-Location $target
                git pull --ff-only --depth=1 2>&1 | Out-Null
                Pop-Location
            }
            catch {
                Write-Warn "Could not update $($node.Name): $_"
            }
        }
        else {
            Write-Info "Installing $($node.Name)..."
            try {
                git clone --depth=1 $node.Repo $target
                Write-Success "Installed: $($node.Name)"

                # Install node-specific Python dependencies if a requirements file exists.
                if ($node.Name -eq "ComfyUI-Tripo") {
                    $reqFile = Join-Path $target "requirements.txt"
                    if (Test-Path $reqFile) {
                        Write-Info "  Installing Python requirements for $($node.Name)..."
                        try {
                            & python -m pip install -r $reqFile
                            Write-Success "  Requirements installed for $($node.Name)"
                        }
                        catch {
                            Write-Warn "  Could not install requirements for $($node.Name): $_"
                            Write-Warn "  You may need to run: python -m pip install -r $reqFile"
                        }
                    }
                }
            }
            catch {
                Write-Error "FAILED: $_"
                Write-Error "Make sure git is on your PATH."
            }
        }
    }

    Write-Host ""
    Write-Warn "Tripo node note:"
    Write-Info "  ComfyUI-Tripo requires a Tripo API key. Set the TRIPO_API_KEY environment"
    Write-Info "  variable or enter it in the Tripo: Generate model node. Get a key at:"
    Write-Info "    https://developers.tripo3d.ai/"

    Write-Host ""
    Write-Warn "Optional node note:"
    Write-Info "  ComfyUI-AdvancedTiling is optional. It can fail to install through ComfyUI Manager."
    Write-Info "  If you want it, install from: https://github.com/JosefKuchar/ComfyUI-AdvancedTiling"
    Write-Info "  The postprocess_assets.py script already handles basic tile masking."
}

Write-Host ""
Write-Success "Setup complete. Restart ComfyUI Desktop to load new models and nodes."
Write-Info "Then import the test workflow:"
Write-Info "  https://raw.githubusercontent.com/yakovkhalinsky/polar-adventure/main/.comfyui-workflows/polar_bear_single_sd15.json"
