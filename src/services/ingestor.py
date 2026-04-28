# src/services/ingestor.py
"""
Ingests a folder of photos.
Handles RAW (NEF, ARW, CR3, CR2) and JPEG.
Extracts EXIF, creates thumbnails, runs blur + exposure analysis.
"""
import os
import uuid
import rawpy
import imageio
import numpy as np
import cv2
import exifread
import imagehash
from PIL import Image
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.database import get_session, Photo, Trip

RAW_EXTENSIONS = {
    ".nef",   # Nikon
    ".arw",   # Sony
    ".cr3",   # Canon (new)
    ".cr2",   # Canon (old)
    ".orf",   # Olympus
    ".rw2",   # Panasonic
    ".dng",   # Adobe DNG
}
JPEG_EXTENSIONS = {".jpg", ".jpeg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi"}
THUMBNAIL_SIZE  = (400, 267)
THUMB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "thumbnails"
)
os.makedirs(THUMB_DIR, exist_ok=True)


def discover_files(folder: str) -> list[str]:
    """Find all supported image files in folder (recursive)."""
    found = []
    for root, _, files in os.walk(folder):
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in RAW_EXTENSIONS | JPEG_EXTENSIONS:
                found.append(os.path.join(root, f))
    return sorted(found)


def load_image_pil(filepath: str) -> Image.Image | None:
    """Load any supported format as a PIL Image."""
    ext = Path(filepath).suffix.lower()
    try:
        if ext in RAW_EXTENSIONS:
            with rawpy.imread(filepath) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    half_size=True,
                    no_auto_bright=False,
                    output_bps=8,
                )
            return Image.fromarray(rgb)
        else:
            return Image.open(filepath).convert("RGB")
    except Exception as e:
        print(f"  Load error {os.path.basename(filepath)}: {e}")
        return None


def create_thumbnail(img: Image.Image, photo_id: str) -> str:
    """Create and save a thumbnail. Returns path."""
    thumb_path = os.path.join(THUMB_DIR, f"{photo_id}.jpg")
    if not os.path.exists(thumb_path):
        thumb = img.copy()
        thumb.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
        thumb.save(thumb_path, "JPEG", quality=85)
    return thumb_path


def extract_exif(filepath: str) -> dict:
    """Extract EXIF metadata from file."""
    data = {}
    try:
        with open(filepath, "rb") as f:
            tags = exifread.process_file(f, stop_tag="UNDEF",
                                         details=False)

        def get(key, default=None):
            v = tags.get(key)
            return str(v) if v else default

        data["camera"]    = get("Image Model", "Unknown")
        data["lens"]      = get("EXIF LensModel", "Unknown")
        data["iso"]       = int(str(tags.get(
            "EXIF ISOSpeedRatings", 0)))
        data["shutter"]   = get("EXIF ExposureTime", "?")
        data["date"]      = get("EXIF DateTimeOriginal", "")

        aperture = tags.get("EXIF FNumber")
        if aperture:
            parts = str(aperture).split("/")
            data["aperture"] = (float(parts[0]) / float(parts[1])
                                if len(parts) == 2
                                else float(parts[0]))
        else:
            data["aperture"] = 0.0

        focal = tags.get("EXIF FocalLength")
        if focal:
            parts = str(focal).split("/")
            data["focal_length"] = (float(parts[0]) / float(parts[1])
                                    if len(parts) == 2
                                    else float(parts[0]))
        else:
            data["focal_length"] = 0.0

    except Exception as e:
        print(f"  EXIF error: {e}")
    return data


def compute_blur_score(img: Image.Image) -> float:
    """
    Laplacian variance — higher = sharper.
    Returns 0–100 score.
    """
    try:
        gray = np.array(img.convert("L"))
        lap  = cv2.Laplacian(gray, cv2.CV_64F)
        var  = lap.var()
        # Normalise: 0 = very blurry, 100 = very sharp
        # Typical sharp wildlife: var > 500
        score = min(100.0, (var / 10.0))
        return round(score, 1)
    except Exception:
        return 0.0


def compute_exposure_score(img: Image.Image) -> float:
    """
    Histogram-based exposure quality.
    Penalises blown highlights and crushed shadows.
    Returns 0–100.
    """
    try:
        arr  = np.array(img)
        flat = arr.flatten()
        n    = len(flat)

        # % pixels clipped to pure white (overexposed)
        highlight_clip = np.sum(flat >= 252) / n
        # % pixels clipped to pure black (underexposed)
        shadow_clip    = np.sum(flat <= 3) / n

        # Penalise clipping
        penalty = (highlight_clip * 200) + (shadow_clip * 100)
        score   = max(0.0, 100.0 - (penalty * 100))
        return round(score, 1)
    except Exception:
        return 50.0


def is_duplicate(img: Image.Image,
                 seen_hashes: set) -> tuple[bool, str]:
    """Perceptual hash duplicate detection."""
    try:
        h = str(imagehash.phash(img))
        if h in seen_hashes:
            return True, h
        seen_hashes.add(h)
        return False, h
    except Exception:
        return False, ""


def process_single(filepath: str, trip_id: str,
                   seen_hashes: set) -> Photo | None:
    """Process one photo — load, analyse, thumbnail."""
    photo_id = str(uuid.uuid4())
    filename = os.path.basename(filepath)

    img = load_image_pil(filepath)
    if img is None:
        return None

    # Duplicate check
    dupl, _ = is_duplicate(img, seen_hashes)
    if dupl:
        photo = Photo(
            id=photo_id, trip_id=trip_id,
            filename=filename, filepath=filepath,
            tier="delete", auto_deleted=True,
            skip_reason="Duplicate detected",
            composite_score=0.0,
        )
        return photo

    # Fast local scores
    blur     = compute_blur_score(img)
    exposure = compute_exposure_score(img)

    # Auto-delete very blurry images
    if blur < 15:
        photo = Photo(
            id=photo_id, trip_id=trip_id,
            filename=filename, filepath=filepath,
            blur_score=blur, exposure_score=exposure,
            tier="delete", auto_deleted=True,
            skip_reason="Too blurry for AI analysis",
            composite_score=max(0.0, blur),
        )
        return photo

    # Create thumbnail
    thumb_path = create_thumbnail(img, photo_id)
    w, h = img.size

    # EXIF
    exif = extract_exif(filepath)

    # Build photo record (AI scoring happens later in batch)
    photo = Photo(
        id=photo_id, trip_id=trip_id,
        filename=filename, filepath=filepath,
        thumbnail_path=thumb_path,
        blur_score=blur,
        exposure_score=exposure,
        image_width=w, image_height=h,
        exif_camera=exif.get("camera"),
        exif_lens=exif.get("lens"),
        exif_iso=exif.get("iso"),
        exif_aperture=exif.get("aperture"),
        exif_shutter=exif.get("shutter"),
        exif_focal_len=exif.get("focal_length"),
        exif_date=exif.get("date"),
        tier="pending",
    )
    return photo


def ingest_folder(trip_id: str, folder: str,
                  progress_callback=None) -> dict:
    """
    Ingest all photos from folder.
    Returns summary dict.
    """
    files = discover_files(folder)
    total = len(files)
    if total == 0:
        return {"total": 0, "ingested": 0, "skipped": 0}

    session      = get_session()
    seen_hashes  = set()
    ingested     = 0
    skipped      = 0

    for i, filepath in enumerate(files):
        try:
            photo = process_single(filepath, trip_id, seen_hashes)
            if photo:
                session.add(photo)
                if photo.auto_deleted:
                    skipped += 1
                else:
                    ingested += 1
            # Commit every 50 photos
            if i % 50 == 0:
                session.commit()
        except Exception as e:
            print(f"  Error processing {os.path.basename(filepath)}: {e}")
        if progress_callback:
            progress_callback(i + 1, total)

    session.commit()
    session.close()
    return {"total": total, "ingested": ingested, "skipped": skipped}
def ingest_single_file(trip_id: str, filepath: str) -> dict:
    """
    Ingest a single uploaded photo file (JPG/JPEG/PNG).
    Robust version for file uploader.
    """
    photo_id = str(uuid.uuid4())
    filename = os.path.basename(filepath)
    
    print(f"[INGEST] Starting: {filename}")

    session = get_session()

    try:
        # Step 1: Load image
        img = Image.open(filepath).convert("RGB")
        w, h = img.size
        print(f"[INGEST] Loaded: {w}x{h}")

        # Step 2: Create thumbnail
        os.makedirs(THUMB_DIR, exist_ok=True)
        thumb_path = os.path.join(THUMB_DIR, f"{photo_id}.jpg")
        thumb = img.copy()
        thumb.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
        thumb.save(thumb_path, "JPEG", quality=85)
        print(f"[INGEST] Thumbnail saved: {thumb_path}")

        # Step 3: RESIZE image before computing scores
        # Blur and exposure algorithms need ~1000px images, not 8000px
        score_img = img.copy()
        score_img.thumbnail((1200, 1200), Image.LANCZOS)
        print(f"[INGEST] Score image resized to: {score_img.size}")

        # Step 4: Compute blur score on RESIZED image
        try:
            blur = compute_blur_score(score_img)
        except Exception as e:
            print(f"[INGEST] Blur score failed: {e}")
            blur = 50.0
        print(f"[INGEST] Blur score: {blur}")

        # Step 5: Compute exposure score on RESIZED image
        try:
            exposure = compute_exposure_score(score_img)
        except Exception as e:
            print(f"[INGEST] Exposure score failed: {e}")
            exposure = 50.0
        print(f"[INGEST] Exposure score: {exposure}")

        # Step 6: Extract EXIF
        exif = {}
        try:
            exif = extract_exif(filepath)
        except Exception:
            pass
        print(f"[INGEST] EXIF: ISO={exif.get('iso')}, f/{exif.get('aperture')}")

        # Step 7: Create Photo record — ALWAYS set tier to "pending"
        # Let the AI scorer decide what to keep or delete
        # No auto-delete for uploaded files
        photo = Photo(
            id=photo_id,
            trip_id=trip_id,
            filename=filename,
            filepath=filepath,
            thumbnail_path=thumb_path,
            blur_score=blur,
            exposure_score=exposure,
            image_width=w,
            image_height=h,
            exif_camera=exif.get("camera"),
            exif_lens=exif.get("lens"),
            exif_iso=exif.get("iso"),
            exif_aperture=exif.get("aperture"),
            exif_shutter=exif.get("shutter"),
            exif_focal_len=exif.get("focal_length"),
            exif_date=exif.get("date"),
            tier="pending",
        )

        session.add(photo)
        session.commit()
        print(f"[INGEST] ✓ SUCCESS: {filename} → tier=pending, blur={blur}, exposure={exposure}")

        return {
            "success": True,
            "photo_id": photo_id,
            "skipped": False,
            "reason": None,
        }

    except Exception as e:
        session.rollback()
        print(f"[INGEST] ✗ ERROR for {filename}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "photo_id": None,
            "skipped": True,
            "reason": f"{type(e).__name__}: {str(e)}",
        }
    finally:
        session.close()