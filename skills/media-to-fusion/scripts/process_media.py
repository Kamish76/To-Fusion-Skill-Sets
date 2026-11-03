#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import cv2
    import ezdxf
    import numpy as np
except ImportError as e:
    sys.stderr.write(
        f"Missing required dependency: {e}\n"
        "Ensure Python dependencies are installed:\n"
        "  pip install -r requirements.txt (or run within the project virtual environment)\n"
    )
    sys.exit(1)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def draw_text_halo(img, text, org, scale=0.45, color=(0, 255, 255), thickness=1):
    """Draws text over a subtle dark pill with matching thickness so labels are razor-sharp on any background."""
    (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    x, y = org
    h, w = img.shape[:2]
    x1, y1 = max(0, x - 2), max(0, y - th - 2)
    x2, y2 = min(w, x + tw + 2), min(h, y + baseline + 2)
    if x2 > x1 and y2 > y1:
        sub = img[y1:y2, x1:x2]
        img[y1:y2, x1:x2] = (sub.astype(np.float32) * 0.35).astype(np.uint8)
    cv2.putText(img, text, (x + 1, y + 1), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def draw_measurement_grid(img, step=100):
    """Overlays a calibrated pixel coordinate grid (major=step, minor=step/2) with high-contrast labels."""
    annotated = img.copy()
    h, w = annotated.shape[:2]
    half_step = max(25, step // 2)

    # Minor sub-grid lines (blended 30% opacity)
    overlay = annotated.copy()
    for x in range(half_step, w, step):
        cv2.line(overlay, (x, 0), (x, h), (180, 180, 0), 1, cv2.LINE_AA)
    for y in range(half_step, h, step):
        cv2.line(overlay, (0, y), (w, y), (180, 180, 0), 1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.30, annotated, 0.70, 0, annotated)

    # Major grid lines (blended 55% opacity) + crisp coordinate labels
    overlay_major = annotated.copy()
    for x in range(0, w, step):
        cv2.line(overlay_major, (x, 0), (x, h), (0, 255, 255), 1, cv2.LINE_AA)
    for y in range(0, h, step):
        cv2.line(overlay_major, (0, y), (w, y), (0, 255, 255), 1, cv2.LINE_AA)
    cv2.addWeighted(overlay_major, 0.55, annotated, 0.45, 0, annotated)

    for x in range(0, w, step):
        draw_text_halo(annotated, str(x), (x + 3, 16), scale=0.42, color=(0, 255, 255))
        if h > 300:
            draw_text_halo(annotated, str(x), (x + 3, h - 8), scale=0.42, color=(0, 255, 255))
    for y in range(step, h, step):
        draw_text_halo(annotated, str(y), (4, y - 4), scale=0.42, color=(0, 255, 255))
        if w > 300:
            draw_text_halo(annotated, str(y), (w - 42, y - 4), scale=0.42, color=(0, 255, 255))

    return annotated


def detect_split_viewports(img):
    """Detects if an image is a side-by-side or top-bottom split orthographic sheet."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]

    # Check vertical divider line in middle 20% of width
    x_start, x_end = int(w * 0.42), int(w * 0.58)
    col_grad = np.mean(np.abs(np.diff(gray[:, x_start:x_end].astype(np.float32), axis=1)), axis=0)
    col_var = np.std(gray[:, x_start:x_end].astype(np.float32), axis=0)

    # A clean divider column has very low vertical variance and a sharp step next to it
    min_var_idx = int(np.argmin(col_var))
    if col_var[min_var_idx] < 12.0 and np.max(col_grad) > 15.0:
        split_x = x_start + min_var_idx
        return {
            "is_split": True,
            "split_type": "vertical_side_by_side",
            "split_x_px": split_x,
            "viewports": [
                {"label": "left_view", "bbox_px": [0, 0, split_x, h]},
                {"label": "right_view", "bbox_px": [split_x, 0, w, h]},
            ],
        }
    return {"is_split": False, "viewports": [{"label": "full_frame", "bbox_px": [0, 0, w, h]}]}


def generate_contours_preview(img, out_path):
    """Generates `contours_preview.png` highlighting structural edges, slots/holes, and foreground bounding box."""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    v = np.median(blurred)
    lower = int(max(20, (1.0 - 0.33) * v))
    upper = int(min(220, (1.0 + 0.33) * v))
    edges = cv2.Canny(blurred, lower, upper)

    preview = (img.astype(np.float32) * 0.35).astype(np.uint8)
    preview[edges > 0] = (255, 200, 0)  # Cyan-blue Canny edges

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    slot_centers = []
    major_polygons = 0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        peri = cv2.arcLength(cnt, True)
        if peri < 25:
            continue
        x, y, cw, ch = cv2.boundingRect(cnt)
        aspect = float(max(cw, ch)) / max(1.0, float(min(cw, ch)))

        # Candidate Skadis slot or pivot hole (compact closed loop)
        if 15 <= area <= (w * h * 0.01) and 1.0 <= aspect <= 4.5 and cw < w * 0.08 and ch < h * 0.08:
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                slot_centers.append((cx, cy, cw, ch))
                cv2.circle(preview, (cx, cy), 3, (255, 0, 255), -1)
        elif peri > 120:
            approx = cv2.approxPolyDP(cnt, 0.008 * peri, True)
            cv2.drawContours(preview, [approx], -1, (0, 255, 100), 1, cv2.LINE_AA)
            major_polygons += 1

    # Deduplicate nearby slot/hole centers (within 6 px)
    unique_centers = []
    for cx, cy, cw, ch in slot_centers:
        if not any(abs(cx - ux) < 6 and abs(cy - uy) < 6 for ux, uy, _, _ in unique_centers):
            unique_centers.append((cx, cy, cw, ch))

    # Estimate horizontal/vertical nearest-neighbor pitch if repeating grid (e.g. Skadis pegboard) is present
    estimated_pitch_px = None
    if len(unique_centers) >= 6:
        pts = np.array([[c[0], c[1]] for c in unique_centers], dtype=np.float32)
        diffs_x = []
        for i in range(len(pts)):
            row_neighbors = [abs(pts[j][0] - pts[i][0]) for j in range(len(pts)) if i != j and abs(pts[j][1] - pts[i][1]) < 8]
            if row_neighbors:
                diffs_x.append(min(row_neighbors))
        if len(diffs_x) >= 4:
            estimated_pitch_px = round(float(np.median(diffs_x)), 1)
            draw_text_halo(
                preview,
                f"Detected {len(unique_centers)} slots/holes | Median same-row pitch: ~{estimated_pitch_px} px",
                (12, h - 14),
                scale=0.55,
                color=(0, 255, 128),
            )

    cv2.imwrite(str(out_path), preview)
    return {
        "contours_preview_file": out_path.name,
        "major_contours_count": major_polygons,
        "detected_slots_or_holes_count": len(unique_centers),
        "estimated_same_row_slot_pitch_px": estimated_pitch_px,
    }


def extract_video_kinematic_keyframes(video_path, out_dir, max_frames=6):
    """Extracts the sharpest keyframes representing distinct kinematic states while rejecting fades and blurs."""
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    sampled = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % 3 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape[:2]
            # Evaluate central 70% ROI to avoid edge vignettes or TikTok watermarks skewing metrics
            roi = gray[int(h * 0.15) : int(h * 0.85), int(w * 0.15) : int(w * 0.85)]
            mean_luma = float(np.mean(roi))
            std_luma = float(np.std(roi))
            dark_ratio = float(np.mean(roi < 22))
            bright_ratio = float(np.mean(roi > 240))
            sharpness = float(cv2.Laplacian(roi, cv2.CV_64F).var())

            # Compact 32x32 structural descriptor combining normalized intensity + Canny edge density
            small_gray = cv2.resize(roi, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
            edges = cv2.Canny(roi, 50, 150)
            edge_density = float(np.mean(edges > 0))
            small_edges = cv2.resize(edges, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
            descriptor = np.concatenate([small_gray.flatten(), small_edges.flatten()])

            sampled.append({
                "sample_idx": len(sampled),
                "frame_num": idx,
                "timestamp": idx / fps,
                "mean_luma": mean_luma,
                "std_luma": std_luma,
                "dark_ratio": dark_ratio,
                "bright_ratio": bright_ratio,
                "sharpness": sharpness,
                "edge_density": edge_density,
                "descriptor": descriptor,
                "frame": frame,
            })
        idx += 1
    cap.release()

    if not sampled:
        raise RuntimeError(f"Could not read frames from video: {video_path}")

    # Filter out black/white fade frames and extreme blur/hand-wipe occlusions
    sharp_cutoff = max(15.0, float(np.percentile([s["sharpness"] for s in sampled], 25)) * 0.6)
    valid = [
        s for s in sampled
        if 18.0 <= s["mean_luma"] <= 242.0
        and s["std_luma"] >= 12.0
        and s["dark_ratio"] < 0.65
        and s["bright_ratio"] < 0.75
        and s["sharpness"] >= sharp_cutoff
        and s["edge_density"] >= 0.015
    ]
    if len(valid) < min(3, len(sampled)):
        valid = sampled

    # Greedy furthest-point state sampling anchored at the first valid sharp frame
    chosen = [valid[0]]
    while len(chosen) < min(max_frames, len(valid)):
        best_candidate = None
        best_score = -1.0
        for cand in valid:
            # Avoid picking frames within 0.35s of an already-chosen keyframe unless video is very short
            if any(abs(cand["timestamp"] - c["timestamp"]) < 0.35 for c in chosen):
                continue
            min_dist = min(float(np.linalg.norm(cand["descriptor"] - c["descriptor"])) for c in chosen)
            # Weight structural difference with sharpness bonus
            score = min_dist * (1.0 + 0.15 * np.log1p(cand["sharpness"]))
            if score > best_score:
                best_score = score
                best_candidate = cand
        if best_candidate is None:
            break
        chosen.append(best_candidate)

    # Sort chosen keyframes chronologically and refine each within a +/- 1 sample window for peak sharpness
    chosen.sort(key=lambda s: s["frame_num"])
    base_desc = chosen[0]["descriptor"]

    saved_frames = []
    thumbs = []
    for k_idx, item in enumerate(chosen):
        s_idx = item["sample_idx"]
        w_start = max(0, s_idx - 1)
        w_end = min(len(sampled), s_idx + 2)
        best = max(
            (
                sampled[i]
                for i in range(w_start, w_end)
                if 18.0 <= sampled[i]["mean_luma"] <= 242.0 and sampled[i]["dark_ratio"] < 0.65
            ),
            key=lambda x: x["sharpness"],
            default=item,
        )

        f_num = best["frame_num"]
        timestamp = best["timestamp"]
        sharp = best["sharpness"]
        img = best["frame"]
        state_delta = float(np.linalg.norm(best["descriptor"] - base_desc))

        fname = f"keyframe_{k_idx:02d}_t{timestamp:.2f}s.png"
        cv2.imwrite(str(out_dir / fname), img)

        grid_fname = f"keyframe_{k_idx:02d}_grid.png"
        cv2.imwrite(str(out_dir / grid_fname), draw_measurement_grid(img, step=100))

        # Also save a contours preview for the first and most-transformed keyframes
        saved_frames.append({
            "file": fname,
            "grid_file": grid_fname,
            "frame_number": f_num,
            "timestamp_sec": round(timestamp, 2),
            "sharpness_score": round(sharp, 2),
            "state_delta_from_start": round(state_delta, 3),
        })

        h, w = img.shape[:2]
        scale = 400.0 / w
        thumb = cv2.resize(img, (400, int(h * scale)))
        draw_text_halo(
            thumb,
            f"#{k_idx:02d} t={timestamp:.2f}s (delta={state_delta:.2f})",
            (10, 26),
            scale=0.60,
            color=(0, 255, 100),
            thickness=2,
        )
        thumbs.append(thumb)

    # Generate contours_preview.png on the sharpest keyframe
    sharpest_item = max(chosen, key=lambda x: x["sharpness"])
    generate_contours_preview(sharpest_item["frame"], out_dir / "contours_preview.png")

    if thumbs:
        # Arrange in a clean 3-column grid if >3 frames, else horizontal strip
        cols = min(3, len(thumbs))
        rows = (len(thumbs) + cols - 1) // cols
        th_h, th_w = thumbs[0].shape[:2]
        padded = [cv2.resize(t, (th_w, th_h)) for t in thumbs]
        while len(padded) < rows * cols:
            padded.append(np.zeros((th_h, th_w, 3), dtype=np.uint8))
        row_imgs = [np.hstack(padded[r * cols : (r + 1) * cols]) for r in range(rows)]
        contact = np.vstack(row_imgs)
        cv2.imwrite(str(out_dir / "contact_sheet.png"), contact)

    return saved_frames


def order_points_clockwise(pts):
    """Orders 4 points into [top-left, top-right, bottom-right, bottom-left] to prevent twisted homographies."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def rectify_and_export_dxf(img, corners_str, real_w_mm, real_h_mm, out_dir):
    """Dewarps a 4-point planar region from perspective into true millimeter coordinates and exports DXF + JSON loops."""
    pts = [float(x) for x in corners_str.split(",")]
    if len(pts) != 8:
        raise ValueError("--rectify requires 8 comma-separated numbers: x1,y1,x2,y2,x3,y3,x4,y4")
    src_pts = order_points_clockwise(np.array(pts, dtype=np.float32).reshape((4, 2)))

    px_per_mm = 10.0  # 0.1 mm per pixel resolution
    dst_w = max(10, int(round(real_w_mm * px_per_mm)))
    dst_h = max(10, int(round(real_h_mm * px_per_mm)))
    dst_pts = np.array([[0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]], dtype=np.float32)

    H = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(img, H, (dst_w, dst_h))
    cv2.imwrite(str(out_dir / "rectified_ortho.png"), warped)
    cv2.imwrite(str(out_dir / "rectified_grid.png"), draw_measurement_grid(warped, step=100))

    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    exported_loops = []

    for cnt in contours:
        arc_len = cv2.arcLength(cnt, True)
        if arc_len < 30:
            continue
        epsilon = 0.004 * arc_len
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        pts_mm = [
            [round(float(p[0][0]) / px_per_mm, 3), round(float(dst_h - p[0][1]) / px_per_mm, 3)]
            for p in approx
        ]
        if len(pts_mm) >= 3:
            msp.add_lwpolyline(pts_mm, close=True)
            exported_loops.append({"vertex_count": len(pts_mm), "points_xy_mm": pts_mm})

    dxf_path = out_dir / "rectified_contour.dxf"
    doc.saveas(str(dxf_path))
    return {
        "dxf_file": dxf_path.name,
        "rectified_image": "rectified_ortho.png",
        "real_dimensions_mm": [real_w_mm, real_h_mm],
        "ordered_src_corners_px": src_pts.tolist(),
        "loops_count": len(exported_loops),
        "loops": exported_loops[:25],
    }


def process_single_media(in_path: Path, out_dir: Path, args):
    """Processes a single image or video into `out_dir` and returns its manifest dictionary."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = in_path.suffix.lower()
    media_type = "video" if ext in VIDEO_EXTS else "image"
    summary = {"source": str(in_path), "name": in_path.name, "type": media_type}

    if media_type == "video":
        summary["keyframes"] = extract_video_kinematic_keyframes(in_path, out_dir, max_frames=args.max_frames)
    else:
        img = cv2.imread(str(in_path))
        if img is None:
            raise RuntimeError(f"Could not load image: {in_path}")
        h, w = img.shape[:2]
        summary["resolution_px"] = [w, h]
        summary["aspect_ratio"] = round(w / max(1.0, float(h)), 4)
        summary["viewport_layout"] = detect_split_viewports(img)

        grid_img = draw_measurement_grid(img, step=args.grid_step)
        cv2.imwrite(str(out_dir / "annotated_grid.png"), grid_img)
        summary["annotated_grid_file"] = "annotated_grid.png"
        summary["contour_analysis"] = generate_contours_preview(img, out_dir / "contours_preview.png")

        if args.rectify:
            summary["rectification"] = rectify_and_export_dxf(
                img, args.rectify, args.real_w, args.real_h, out_dir
            )

    with open(out_dir / "media_manifest.json", "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", Path(name).stem).strip("_")[:48]


def main():
    parser = argparse.ArgumentParser(description="Preprocess image, video, or reference folder for Fusion 360 CAD reconstruction.")
    parser.add_argument("input_media", help="Path to input video, image, or folder of reference media")
    parser.add_argument("--out-dir", default="./media_workspace", help="Directory for extracted keyframes, grids, and manifests")
    parser.add_argument("--grid-step", type=int, default=100, help="Pixel spacing for major measurement grid lines (default: 100)")
    parser.add_argument("--max-frames", type=int, default=6, help="Maximum keyframes to extract per video (default: 6)")
    parser.add_argument("--rectify", help="Optional 4 corners 'x1,y1,x2,y2,x3,y3,x4,y4' in pixels for homography dewarp")
    parser.add_argument("--real-w", type=float, default=100.0, help="Real width in mm for rectified plane")
    parser.add_argument("--real-h", type=float, default=100.0, help="Real height in mm for rectified plane")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    in_path = Path(args.input_media)

    if not in_path.exists():
        sys.stderr.write(f"Input path does not exist: {in_path}\n")
        sys.exit(1)

    if in_path.is_dir():
        files = sorted(
            p for p in in_path.iterdir()
            if p.is_file() and p.suffix.lower() in (IMAGE_EXTS | VIDEO_EXTS)
        )
        items = []
        overview_thumbs = []
        for fpath in files:
            sub_dir = out_dir / slugify(fpath.name)
            item_manifest = process_single_media(fpath, sub_dir, args)
            item_manifest["workspace_subdir"] = sub_dir.name
            items.append(item_manifest)

            # Build thumbnail for dataset_overview.png
            preview_src = sub_dir / ("contact_sheet.png" if item_manifest["type"] == "video" else "annotated_grid.png")
            if preview_src.exists():
                im = cv2.imread(str(preview_src))
                if im is not None:
                    th = cv2.resize(im, (360, 270))
                    draw_text_halo(th, f"{fpath.name[:32]}", (8, 22), scale=0.50, color=(0, 255, 255), thickness=1)
                    overview_thumbs.append(th)

        if overview_thumbs:
            cols = min(4, len(overview_thumbs))
            rows = (len(overview_thumbs) + cols - 1) // cols
            while len(overview_thumbs) < rows * cols:
                overview_thumbs.append(np.zeros((270, 360, 3), dtype=np.uint8))
            grid_rows = [np.hstack(overview_thumbs[r * cols : (r + 1) * cols]) for r in range(rows)]
            cv2.imwrite(str(out_dir / "dataset_overview.png"), np.vstack(grid_rows))

        master = {
            "source_directory": str(in_path),
            "total_files": len(items),
            "images_count": sum(1 for x in items if x["type"] == "image"),
            "videos_count": sum(1 for x in items if x["type"] == "video"),
            "dataset_overview_file": "dataset_overview.png" if overview_thumbs else None,
            "items": items,
        }
        with open(out_dir / "media_manifest.json", "w") as f:
            json.dump(master, f, indent=2)
        print(f"Processed directory '{in_path.name}' ({len(items)} media files) -> {out_dir}/media_manifest.json")
    else:
        process_single_media(in_path, out_dir, args)
        print(f"Processed '{in_path.name}' -> {out_dir}/media_manifest.json")


if __name__ == "__main__":
    main()
