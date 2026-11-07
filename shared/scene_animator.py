"""High-speed scene-graph animator, multi-frame kinematic interference checker, and GIF compiler."""
import os
import math
import subprocess

def clamp(v, min_v, max_v):
    return max(min_v, min(max_v, v))

def smoothstep(edge0, edge1, x):
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def make_yz_transform(y0_mm, z0_mm, dy_mm, dz_mm, ang_rad):
    """
    Constructs an SE(3) Matrix3D for a 2D planar rotation around pivot center (y0_mm, z0_mm)
    by angle ang_rad, followed by linear translation (dy_mm, dz_mm).
    Converts millimeters to centimeters for Autodesk Fusion 360's internal API.
    """
    import adsk.core
    ca = math.cos(ang_rad)
    sa = math.sin(ang_rad)
    ty_mm = (y0_mm + dy_mm) - (y0_mm * ca - z0_mm * sa)
    tz_mm = (z0_mm + dz_mm) - (y0_mm * sa + z0_mm * ca)
    mat = adsk.core.Matrix3D.create()
    mat.setCell(1, 1, ca)
    mat.setCell(1, 2, -sa)
    mat.setCell(1, 3, ty_mm / 10.0)
    mat.setCell(2, 1, sa)
    mat.setCell(2, 2, ca)
    mat.setCell(2, 3, tz_mm / 10.0)
    return mat

def check_stage_interference(design, groups_dict, s_val, min_vol_mm3=3.0):
    """
    Runs native BRep interference analysis across all bodies in groups_dict at normalized step s_val.
    Filters out coincident touching faces and returns a list of substantial collisions (> min_vol_mm3).
    """
    import adsk.core
    stage_bodies = adsk.core.ObjectCollection.create()
    for g_occ in groups_dict.values():
        for b in g_occ.bRepBodies:
            stage_bodies.add(b)

    collisions = []
    if stage_bodies.count < 2:
        return collisions

    inp = design.createInterferenceInput(stage_bodies)
    inp.areCoincidentFacesIncluded = False
    results = design.analyzeInterference(inp)

    for r in results:
        v_mm3 = r.interferenceBody.volume * 1000.0
        if v_mm3 > min_vol_mm3:
            collisions.append({
                "step": s_val,
                "entity_one": r.entityOne.name,
                "entity_two": r.entityTwo.name,
                "volume_mm3": v_mm3,
            })
            print(f"  [s={s_val:.2f}] COLLISION: {r.entityOne.name} <-> {r.entityTwo.name} ({v_mm3:.2f} mm3)")
    return collisions

def compile_ping_pong_gif(frames_dir, output_gif_path, num_frames=28, hold_assembled=25, hold_exploded=18, frame_ms=45, hold_ms=50):
    """
    Loads rendered PNG frames from disk and compiles an optimized ping-pong looping GIF using PIL/Pillow.
    Falls back automatically to PowerShell .NET encoder on Windows if PIL is unavailable.
    """
    try:
        from PIL import Image
    except ImportError:
        print("PIL/Pillow not available. Falling back to PowerShell .NET compiler...")
        return compile_ping_pong_gif_powershell(
            frames_dir=frames_dir,
            output_gif_path=output_gif_path,
            num_frames=num_frames,
            frame_delay_cs=max(1, int(frame_ms / 10)),
            hold_end_cs=max(1, int(hold_ms * hold_assembled / 10)),
        )

    frames = []
    for i in range(num_frames):
        fp = os.path.join(frames_dir, f'frame_{i:03d}.png')
        if not os.path.exists(fp):
            # Also try full_%03d.png
            fp_alt = os.path.join(frames_dir, f'full_{i:03d}.png')
            if os.path.exists(fp_alt):
                fp = fp_alt
            else:
                raise FileNotFoundError(f"Missing animation frame: {fp} (or {fp_alt})")
        frames.append(Image.open(fp).convert('RGB'))

    full_sequence = []
    durations = []

    # 1. Forward motion
    for img in frames:
        full_sequence.append(img)
        durations.append(frame_ms)

    # 2. Hold assembled
    for _ in range(hold_assembled):
        full_sequence.append(frames[-1])
        durations.append(hold_ms)

    # 3. Reverse motion
    for img in reversed(frames[1:-1]):
        full_sequence.append(img)
        durations.append(frame_ms)

    # 4. Hold exploded
    for _ in range(hold_exploded):
        full_sequence.append(frames[0])
        durations.append(hold_ms)

    # Quantize palette for crisp 3D CAD rendering and minimal file size
    p_frames = [f.quantize(colors=128, method=Image.Resampling.LANCZOS, dither=Image.Dither.FLOYDSTEINBERG) for f in full_sequence]

    os.makedirs(os.path.dirname(os.path.abspath(output_gif_path)), exist_ok=True)
    p_frames[0].save(
        output_gif_path,
        save_all=True,
        append_images=p_frames[1:],
        duration=durations,
        loop=0,
        optimize=True
    )
    size_mb = os.path.getsize(output_gif_path) / (1024 * 1024)
    print(f"Compiled ping-pong GIF (PIL): {output_gif_path} ({size_mb:.2f} MB, {len(full_sequence)} frames)")
    return output_gif_path

def compile_ping_pong_gif_powershell(frames_dir, output_gif_path, frame_prefix="full_", num_frames=20, frame_delay_cs=5, hold_end_cs=120):
    """
    Zero-dependency Windows .NET WPF GifBitmapEncoder + binary NETSCAPE2.0 looping and GCE delay patcher.
    Works on Windows without Python PIL/Pillow or ffmpeg.
    """
    frames_dir_esc = os.path.abspath(frames_dir).replace("'", "''")
    output_gif_esc = os.path.abspath(output_gif_path).replace("'", "''")

    ps_script = f"""
    Add-Type -AssemblyName PresentationCore
    Add-Type -AssemblyName WindowsBase

    $encoder = New-Object System.Windows.Media.Imaging.GifBitmapEncoder
    $framesDir = '{frames_dir_esc}'
    $outPath = '{output_gif_esc}'
    $prefix = '{frame_prefix}'

    # 1. Forward Sequence
    for ($i = 0; $i -lt {num_frames}; $i++) {{
        $fn = Join-Path $framesDir ($prefix + (('{{0:d3}}.png') -f $i))
        if (-not (Test-Path $fn)) {{
            $fn = Join-Path $framesDir (('frame_{{0:d3}}.png') -f $i)
        }}
        if (Test-Path $fn) {{
            $frameUri = New-Object System.Uri($fn, [System.UriKind]::Absolute)
            $bitmap = New-Object System.Windows.Media.Imaging.BitmapFrameDecode($frameUri)
            $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
        }}
    }}

    # 2. Reverse Ping-Pong Sequence
    for ($i = {num_frames - 2}; $i -ge 1; $i--) {{
        $fn = Join-Path $framesDir ($prefix + (('{{0:d3}}.png') -f $i))
        if (-not (Test-Path $fn)) {{
            $fn = Join-Path $framesDir (('frame_{{0:d3}}.png') -f $i)
        }}
        if (Test-Path $fn) {{
            $frameUri = New-Object System.Uri($fn, [System.UriKind]::Absolute)
            $bitmap = New-Object System.Windows.Media.Imaging.BitmapFrameDecode($frameUri)
            $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
        }}
    }}

    $ms = New-Object System.IO.MemoryStream
    $encoder.Save($ms)
    $bytes = $ms.ToArray()
    $ms.Close()

    # 3. Splice NETSCAPE2.0 looping block after Logical Screen Descriptor
    $hasGct = ($bytes[10] -band 0x80) -ne 0
    $gctSize = 0
    if ($hasGct) {{
        $gctSize = 3 * [Math]::Pow(2, (($bytes[10] -band 0x07) + 1))
    }}
    $insertPos = 13 + $gctSize

    $netscape = [byte[]]@(0x21, 0xFF, 0x0B, 0x4E, 0x45, 0x54, 0x53, 0x43, 0x41, 0x50, 0x45, 0x32, 0x2E, 0x30, 0x03, 0x01, 0x00, 0x00, 0x00)

    $outList = New-Object System.Collections.Generic.List[byte]
    for ($i = 0; $i -lt $insertPos; $i++) {{ $outList.Add($bytes[$i]) }}
    foreach ($b in $netscape) {{ $outList.Add($b) }}
    for ($i = $insertPos; $i -lt $bytes.Length; $i++) {{ $outList.Add($bytes[$i]) }}
    $patched = $outList.ToArray()

    # 4. Patch Graphic Control Extensions for frame delay (centiseconds)
    $gceCount = 0
    $totalFrames = $encoder.Frames.Count
    for ($i = 0; $i -lt $patched.Length - 8; $i++) {{
        if ($patched[$i] -eq 0x21 -and $patched[$i+1] -eq 0xF9 -and $patched[$i+2] -eq 0x04) {{
            $gceCount++
            $delay = {frame_delay_cs}
            if ($gceCount -eq {num_frames} -or $gceCount -eq $totalFrames) {{
                $delay = {hold_end_cs}
            }}
            $patched[$i+4] = [byte]($delay -band 0xFF)
            $patched[$i+5] = [byte](($delay -shr 8) -band 0xFF)
        }}
    }}

    $parentDir = Split-Path $outPath -Parent
    if (-not (Test-Path $parentDir)) {{ New-Item -ItemType Directory -Path $parentDir -Force | Out-Null }}
    [System.IO.File]::WriteAllBytes($outPath, $patched)
    """
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"PowerShell GIF compilation failed: {res.stderr}")
    print(f"Compiled ping-pong GIF (.NET): {output_gif_path}")
    return output_gif_path
