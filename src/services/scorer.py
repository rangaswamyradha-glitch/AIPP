# src/services/scorer.py
"""
AI Vision scoring using Claude.
Only called for photos that passed local pre-filtering.
Scores eyes, body, subject separation, moment quality.
"""
import anthropic
import base64
import os
import json
import re
from PIL import Image
from io import BytesIO
from src.database import get_session, Photo

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CATEGORIES = [
    "close_up_portrait",
    "habitat_environmental",
    "action_flight",
    "behaviour_interaction",
    "high_key",
    "low_key_dramatic",
    "abstract_detail",
    "vertical_portrait",
]

CATEGORY_LABELS = {
    "close_up_portrait":      "Close-up Portrait",
    "habitat_environmental":  "Habitat / Environmental",
    "action_flight":          "Action / Flight",
    "behaviour_interaction":  "Behaviour / Interaction",
    "high_key":               "High Key",
    "low_key_dramatic":       "Low Key / Dramatic",
    "abstract_detail":        "Abstract / Detail",
    "vertical_portrait":      "Vertical Portrait",
}

CATEGORY_WEIGHTS = {
    "close_up_portrait": {
        "eyes_sharp": 0.30, "body_complete": 0.20,
        "subject_separation": 0.20, "exposure": 0.15,
        "moment_quality": 0.15,
    },
    "action_flight": {
        "eyes_sharp": 0.15, "body_complete": 0.25,
        "subject_separation": 0.15, "exposure": 0.20,
        "moment_quality": 0.25,
    },
    "habitat_environmental": {
        "eyes_sharp": 0.10, "body_complete": 0.15,
        "subject_separation": 0.10, "exposure": 0.30,
        "moment_quality": 0.35,
    },
    "behaviour_interaction": {
        "eyes_sharp": 0.15, "body_complete": 0.20,
        "subject_separation": 0.15, "exposure": 0.15,
        "moment_quality": 0.35,
    },
}

DEFAULT_WEIGHTS = {
    "eyes_sharp": 0.20, "body_complete": 0.20,
    "subject_separation": 0.20, "exposure": 0.20,
    "moment_quality": 0.20,
}


def image_to_base64(thumbnail_path: str,
                    max_size: int = 1024) -> str:
    """Convert thumbnail to base64 for Claude."""
    img = Image.open(thumbnail_path).convert("RGB")
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode()


def score_photo(photo: Photo) -> dict:
    """
    Send photo to Claude for vision scoring.
    Returns scores dict with explanation.
    """
    if not photo.thumbnail_path or \
       not os.path.exists(photo.thumbnail_path):
        return {}

    img_b64 = image_to_base64(photo.thumbnail_path)

    exif_info = (
        f"Camera: {photo.exif_camera or 'Unknown'} | "
        f"ISO: {photo.exif_iso or '?'} | "
        f"Aperture: f/{photo.exif_aperture or '?'} | "
        f"Shutter: {photo.exif_shutter or '?'} | "
        f"Focal length: {photo.exif_focal_len or '?'}mm"
    )

    prompt = f"""You are an expert wildlife photography judge.
Analyse this wildlife photograph and provide structured scores.

EXIF: {exif_info}
Blur score (pre-computed, 0-100, higher=sharper): {photo.blur_score:.1f}
Exposure score (pre-computed, 0-100): {photo.exposure_score:.1f}

Score each dimension 1-10. Be honest and critical.
Respond ONLY in JSON, no other text:
{{
  "category": "one of: close_up_portrait | habitat_environmental | action_flight | behaviour_interaction | high_key | low_key_dramatic | abstract_detail | vertical_portrait",
  "category_confidence": 0.0,
  "eyes_sharp": 0,
  "body_complete": 0,
  "subject_separation": 0,
  "moment_quality": 0,
  "exposure_quality": 0,
  "species": "identified species or Unknown",
  "explanation": "2-3 sentence plain English explanation of the scores. Be specific about what you see.",
  "edit_suggestions": {{
    "lightroom": "Specific slider values e.g. Exposure +0.5, Highlights -30, Clarity +15, Vibrance +10",
    "topaz": "Specific tool recommendation e.g. DeNoise AI (Low Light preset) — ISO {photo.exif_iso or 800} detected",
    "crop": "Crop recommendation or None needed"
  }},
  "strengths": ["list", "of", "2-3", "specific", "strengths"],
  "improvements": ["list", "of", "1-2", "specific", "improvements"]
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            temperature=0.0,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )

        raw = response.content[0].text
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        result = json.loads(raw)
        return result

    except Exception as e:
        print(f"  AI scoring error: {e}")
        return {}


def compute_composite(scores: dict,
                      blur: float,
                      exposure: float,
                      category: str) -> tuple[float, dict]:
    """
    Compute composite score from AI + local scores.
    Returns (composite_score, breakdown_dict).
    """
    weights = CATEGORY_WEIGHTS.get(category, DEFAULT_WEIGHTS)

    # Normalise AI scores to 0-100
    eyes      = scores.get("eyes_sharp", 5) * 10
    body      = scores.get("body_complete", 5) * 10
    sep       = scores.get("subject_separation", 5) * 10
    moment    = scores.get("moment_quality", 5) * 10
    exp_ai    = scores.get("exposure_quality", 5) * 10

    # Blend AI exposure with local histogram score
    exposure_blend = (exp_ai * 0.6) + (exposure * 0.4)

    breakdown = {
        "Eyes / Focus":        round(eyes * weights["eyes_sharp"], 1),
        "Body Complete":       round(body * weights["body_complete"], 1),
        "Subject Separation":  round(sep * weights["subject_separation"], 1),
        "Moment / Story":      round(moment * weights["moment_quality"], 1),
        "Exposure":            round(exposure_blend * weights["exposure"], 1),
        "Sharpness (local)":   round(min(blur, 100) * 0.05, 1),
    }

    composite = sum(breakdown.values())
    composite = min(100.0, max(0.0, composite))
    return round(composite, 1), breakdown


def assign_tier(score: float,
                needs_review: bool) -> str:
    """Assign Great/Good/Review/Delete tier."""
    if needs_review:
        return "review"
    if score >= 72:
        return "great"
    if score >= 50:
        return "good"
    if score >= 30:
        return "review"
    return "delete"


def batch_score(trip_id: str,
                progress_callback=None) -> dict:
    """
    Score all pending photos for a trip.
    Skips auto-deleted photos.
    """
    session = get_session()
    photos  = session.query(Photo).filter(
        Photo.trip_id == trip_id,
        Photo.tier    == "pending",
        Photo.auto_deleted == False,
    ).all()

    total     = len(photos)
    scored    = 0
    errors    = 0

    for i, photo in enumerate(photos):
        try:
            ai = score_photo(photo)
            if not ai:
                errors += 1
                photo.tier = "review"
                photo.needs_review = True
                session.commit()
                continue

            category = ai.get("category", "close_up_portrait")
            composite, breakdown = compute_composite(
                ai, photo.blur_score,
                photo.exposure_score, category
            )
            confidence = float(ai.get("category_confidence", 0.7))

            # Flag for review if confidence low or borderline score
            borderline = 45 <= composite <= 55
            needs_rev  = confidence < 0.65 or borderline

            photo.category          = category
            photo.ai_confidence     = confidence
            photo.ai_score          = composite
            photo.composite_score   = composite
            photo.score_breakdown   = breakdown
            photo.ai_explanation    = ai.get("explanation", "")
            photo.edit_suggestions  = ai.get("edit_suggestions", {})
            photo.tier              = assign_tier(composite, needs_rev)
            photo.needs_review      = needs_rev

            session.commit()
            scored += 1

        except Exception as e:
            print(f"  Scoring error {photo.filename}: {e}")
            errors += 1

        if progress_callback:
            progress_callback(i + 1, total)

    session.close()
    return {"total": total, "scored": scored, "errors": errors}