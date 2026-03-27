"""
Profile extractor for Lumina Pipeline.

Uses an LLM to infer character profile fields from chapter dialogue.
"""

from __future__ import annotations

from typing import Any, Dict, List

from groq import Groq
from utils.groq_client import QUALITY_MODEL


def extract_profiles(chapter_data: dict, client: Groq) -> list:
    """
    Infer character profiles from a chapter JSON containing pre-translated
    English dialogue lines (grouped by character).

    Expected input shape:
      chapter_data["panels"] is a list of panel objects.
      Each panel should include:
        - "character": character name
        - "text": pre-translated English dialogue line text
        - (other optional fields are ignored here)
    """
    panels = chapter_data.get("panels") or []

    grouped: Dict[str, List[str]] = {}
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        character = str(panel.get("character") or "").strip()
        text = str(panel.get("text") or "").strip()
        if not character or not text:
            continue
        grouped.setdefault(character, []).append(text)

    system_prompt = (
        "You are an expert manga/webtoon character profiling assistant.\n"
        "You will be given multiple English dialogue lines for ONE character.\n\n"
        "Infer the character's:\n"
        "- personality (short description of demeanor)\n"
        "- speech_style (how they generally speak)\n"
        "- speech_rules (a list of concrete rules/constraints about their speech)\n\n"
        "Output rules (IMPORTANT):\n"
        "- Output ONLY a single valid JSON object.\n"
        "- No markdown. No explanations.\n"
        "- Use EXACT keys: personality, speech_style, speech_rules\n"
        '- speech_rules must be an array of strings.\n'
    )

    profiles: List[Dict[str, Any]] = []
    for character_name, lines in grouped.items():
        joined_lines = "\n".join(lines)
        user_content = (
            f"CHARACTER NAME: {character_name}\n\n"
            "DIALOGUE LINES:\n"
            f"{joined_lines}\n"
        )

        completion = client.chat.completions.create(
            model=QUALITY_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )

        raw = (completion.choices[0].message.content or "").strip()
        try:
            import json

            data = json.loads(raw)
        except Exception:
            # Fallback: keep minimally useful fields.
            data = {
                "personality": "",
                "speech_style": "",
                "speech_rules": [],
            }

        # Always stamp the character name into the profile.
        data["name"] = character_name
        profiles.append(data)

    return profiles


def _merge_list_field(existing: list, incoming: list) -> list:
    merged: list = []
    seen = set()
    for item in existing + incoming:
        key = str(item).strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _merge_profile_dicts(existing: dict, incoming: dict) -> dict:
    """
    Merge inferred profile observations into the stored profile.
    """
    merged = dict(existing or {})

    for key, incoming_val in (incoming or {}).items():
        if incoming_val is None:
            continue

        existing_val = merged.get(key)
        if isinstance(existing_val, list) and isinstance(incoming_val, list):
            merged[key] = _merge_list_field(existing_val, incoming_val)
        elif isinstance(existing_val, str) and isinstance(incoming_val, str):
            existing_val_str = existing_val.strip()
            incoming_val_str = incoming_val.strip()
            if not existing_val_str:
                merged[key] = incoming_val_str
            elif not incoming_val_str:
                merged[key] = existing_val_str
            elif existing_val_str.lower() == incoming_val_str.lower():
                merged[key] = existing_val_str
            else:
                merged[key] = f"{existing_val_str} / {incoming_val_str}"
        else:
            # Prefer existing if it's non-empty; otherwise take incoming.
            if existing_val is None or existing_val == "" or existing_val == []:
                merged[key] = incoming_val

    return merged


def update_or_create_profile(
    character_name: str,
    new_profile: dict,
    vector_store,
    manga_id: str,
) -> None:
    """
    Update an existing character profile in ChromaDB, or create it if missing.

    `vector_store` is expected to expose:
      - query_character_profile_dict(character_name, manga_id=...) -> Optional[dict]
      - add_character_profile(character_name, profile_data, manga_id=...) -> None
    """
    existing = vector_store.query_character_profile_dict(
        character_name,
        manga_id=manga_id,
    )

    if existing is None:
        profile_to_store = dict(new_profile or {})
        profile_to_store["name"] = character_name
        vector_store.add_character_profile(
            character_name,
            profile_to_store,
            manga_id=manga_id,
        )
        return

    merged = _merge_profile_dicts(existing, new_profile or {})
    merged["name"] = character_name
    vector_store.add_character_profile(
        character_name,
        merged,
        manga_id=manga_id,
    )

