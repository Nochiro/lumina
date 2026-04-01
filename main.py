from typing import Any, Dict

from groq import Groq

from agents.profile_extractor import extract_profiles, update_or_create_profile
from agents.cultural_agent import grade_cultural_output, run_cultural_adaptor
from agents.continuity_agent import (
    grade_continuity_output,
    run_continuity_director,
)
from agents.translation_agent import (
    detect_language,
    grade_translation_output,
    translate_literal_metadata,
    translate_page,
    run_translation_agent,
)
from agents.typesetting_agent import (
    grade_typesetting_output,
    run_typesetting_editor,
)
from memory import vector_store
from memory.vector_store import (
    add_approved_line,
    query_character_profile_dict,
)
from utils.groq_client import load_environment
from utils.project_manager import mark_chapter_complete

# TODO: Import CrewAI orchestration primitives when implementing multi-agent Crew.
# from crewai import Crew


def test_groq_connection() -> None:
    """
    Perform a basic test call to the Groq API to confirm connectivity.

    This function sends a simple message to the llama3-70b-8192 model and
    prints the response. Errors (e.g., invalid API key) are handled with
    clear messages instead of crashing the application.
    """
    try:
        client = load_environment()
    except RuntimeError as exc:
        # Clear message if the API key is missing.
        print(f"[Groq Test] Configuration error: {exc}")
        return
    except Exception as exc:  # Defensive: unexpected errors during initialization.
        print(f"[Groq Test] Unexpected error while initializing Groq client: {exc}")
        return

    try:
        completion = client.chat.completions.create(
            # Updated to a currently supported Groq Llama 3 70B model.
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": "Hello, respond in one sentence.",
                }
            ],
        )
        message = completion.choices[0].message.content
        print("[Groq Test] Connection successful. Model response:")
        print(message)
    except Exception as exc:
        # Catch errors such as invalid API keys or network failures.
        print("[Groq Test] Error while communicating with Groq API:")
        print(str(exc))


def build_crew():
    """
    Placeholder for future CrewAI-based orchestration.
    """
    raise NotImplementedError("Crew construction is not implemented yet.")


def _run_with_retries(
    step_name: str,
    run_fn,
    grade_fn,
    *,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Run an agent step with grading and up to `max_retries` attempts.

    The caller is responsible for providing small lambdas for `run_fn` and
    `grade_fn` that capture the appropriate arguments.
    """
    attempt = 0
    last_output: Any = None
    last_scores: Dict[str, Any] = {}

    while attempt < max_retries:
        attempt += 1
        print(f"[Pipeline] Running {step_name} (attempt {attempt}/{max_retries})...")

        candidate = run_fn()
        scores = grade_fn(candidate)

        last_output = candidate
        last_scores = scores

        if scores.get("pass"):
            print(f"[Pipeline] {step_name} PASS.")
            break

        if attempt < max_retries:
            print(f"[Pipeline] {step_name} FAIL — retry {attempt}/{max_retries}")
        else:
            print(
                f"[Pipeline] {step_name} FAIL after {max_retries} attempts — "
                "continuing with last output."
            )

    return {"output": last_output, "scores": last_scores}


def run_pipeline(
    raw_text: str,
    character_name: str,
    bubble_type: str,
    client: Groq,
    *,
    bubble_char_limit: int | None = None,
    character_profile: Dict[str, Any] | None = None,
    skip_continuity: bool = False,
) -> Dict[str, Any]:
    """
    Run the full Lumina Pipeline on a single line of script.

    Pipeline stages:
    - Step 0: Translation (Japanese → rough English)
    - Agent 1: Cultural Adaptation
    - Agent 2: Continuity Director
    - Agent 3: Typesetting Editor
    """
    print("[Pipeline] Starting full pipeline run.")

    # STEP 0 — Translation (New Agent)
    detected_language = detect_language(raw_text)
    print(f"[Pipeline] Detected language: {detected_language}")

    if detected_language in ("korean", "japanese"):
        translation_result = _run_with_retries(
            "Step 0 (Translation Agent)",
            run_fn=lambda: run_translation_agent(
                raw_text,
                client,
                character_name=character_name,
            ),
            grade_fn=lambda translated: grade_translation_output(
                original=raw_text,
                translated=translated,
                client=client,
            ),
        )
        translated_output = translation_result["output"]
        translation_scores = translation_result["scores"]
    else:
        print(
            "[Pipeline] Input appears to be English — skipping translation."
        )
        translated_output = raw_text
        translation_scores = {
            "contextual_accuracy": None,
            "tone_preservation": None,
            "naturalness": None,
            "pass": True,
        }

    # Resolve character profile once for continuity.
    if character_profile is None:
        character_profile = query_character_profile_dict(
            character_name,
            manga_id="default",
        ) or {
            "name": character_name,
            "role": "character",
            "speech_style": "",
            "forbidden_phrases": [],
            "speech_rules": [],
            "manga_id": "default",
        }

    # STEP A — Cultural Adaptation (Agent 1)
    cultural_result = _run_with_retries(
        "Agent 1 (Cultural Adaptor)",
        run_fn=lambda: run_cultural_adaptor(translated_output, client),
        grade_fn=lambda adapted: grade_cultural_output(
            translated_output,
            adapted,
            client,
        ),
    )
    cultural_output = cultural_result["output"]
    cultural_scores = cultural_result["scores"]

    # STEP B — Continuity Check (Agent 2)
    if skip_continuity:
        # These are not tracked characters; grading against a voice profile is meaningless.
        continuity_output = cultural_output
        continuity_scores = {
            "voice_consistency": 10,
            "forbidden_phrase_compliance": 10,
            "meaning_preservation": 10,
            "pass": True,
            "skipped": True,
        }
    else:
        continuity_result = _run_with_retries(
            "Agent 2 (Continuity Director)",
            run_fn=lambda: run_continuity_director(
                cultural_output,
                character_profile,
                client,
            ),
            grade_fn=lambda continuity_text: grade_continuity_output(
                adapted_text=cultural_output,
                continuity_text=continuity_text,
                character_name=character_name,
                client=client,
            ),
        )
        continuity_output = continuity_result["output"]
        continuity_scores = continuity_result["scores"]

    # STEP C — Typesetting (Agent 3)
    typesetting_result = _run_with_retries(
        "Agent 3 (Typesetting Editor)",
        run_fn=lambda: run_typesetting_editor(
            continuity_output,
            bubble_type,
            client,
            bubble_char_limit=bubble_char_limit,
        ),
        grade_fn=lambda final_text: grade_typesetting_output(
            original=continuity_output,
            final=final_text,
            bubble_type=bubble_type,
            client=client,
            bubble_char_limit=bubble_char_limit,
        ),
    )
    final_output = typesetting_result["output"]
    typesetting_scores = typesetting_result["scores"]

    print("[Pipeline] Pipeline run complete.")

    return {
        "original": raw_text,
        "detected_language": detected_language,
        "translated_output": translated_output,
        "cultural_output": cultural_output,
        "continuity_output": continuity_output,
        "final_output": final_output,
        "translation_scores": translation_scores,
        "cultural_scores": cultural_scores,
        "continuity_scores": continuity_scores,
        "typesetting_scores": typesetting_scores,
        "status": "complete",
    }


def _flagged_from_scores(scores: Dict[str, Any]) -> bool:
    """
    Flag True if any numeric score across nested score dicts is < 7.
    Ignores boolean `pass` fields.
    """

    def walk(v: Any) -> bool:
        if isinstance(v, bool):
            return False
        if isinstance(v, (int, float)):
            return v < 7
        if isinstance(v, dict):
            return any(walk(x) for x in v.values())
        if isinstance(v, list):
            return any(walk(x) for x in v)
        return False

    return walk(scores)


def process_chapter(chapter_data: Dict[str, Any], client: Groq) -> list[Dict[str, Any]]:
    """
    Process an uploaded chapter JSON through the 4-step pipeline per panel.

    Returns a list of panel results:
      - panel_id
      - original
      - final_output
      - scores
      - flagged
    """
    manga_id = str(chapter_data.get("manga_id") or "unknown").strip() or "unknown"
    chapter = int(chapter_data.get("chapter") or 0)

    panels = chapter_data.get("panels") or []

    # Collect panel jobs first so we can run Step 0 translation across ALL panels
    # before extracting/updating character profiles.
    panel_jobs: list[Dict[str, Any]] = []
    for panel in panels:
        if not isinstance(panel, dict):
            continue

        panel_id = panel.get("panel_id") or panel.get("id") or panel.get("index")
        panel_id = str(panel_id) if panel_id is not None else ""

        character_name = str(panel.get("character") or "").strip()
        original_japanese = str(panel.get("text") or "")
        if not character_name or not original_japanese:
            continue

        skip_continuity = character_name in (
            "NARRATION",
            "TEACHER",
            "STUDENT",
            "TITLE_CARD",
            "SFX",
            "NARRATOR",
            "CAPTION",
            "SOUND_EFFECT",
        )

        bubble_char_limit = panel.get("bubble_char_limit")
        bubble_char_limit = (
            int(bubble_char_limit) if bubble_char_limit is not None else None
        )

        bubble_type = str(panel.get("bubble_type") or "medium").strip()

        panel_jobs.append(
            {
                "panel_id": panel_id,
                "character_name": character_name,
                "original_japanese": original_japanese,
                "skip_continuity": skip_continuity,
                "bubble_type": bubble_type,
                "bubble_char_limit": bubble_char_limit,
            }
        )

    # STEP 0 — Translate one page at a time.
    translated_outputs: list[str] = []
    translation_scores_by_panel: list[Dict[str, Any]] = []
    translated_lines_by_character: Dict[str, list[str]] = {}

    # Group panel jobs by page number from panel_id prefix (e.g., "1-2" -> page "1").
    page_groups: Dict[str, list[Dict[str, Any]]] = {}
    page_order: list[str] = []
    for job in panel_jobs:
        panel_id = str(job["panel_id"])
        page_key = panel_id.split("-", 1)[0] if "-" in panel_id else "0"
        job["page_key"] = page_key
        if page_key not in page_groups:
            page_groups[page_key] = []
            page_order.append(page_key)
        page_groups[page_key].append(job)

    translated_by_panel_id: Dict[str, str] = {}
    score_by_panel_id: Dict[str, Dict[str, Any]] = {}
    page_translation_score_by_page: Dict[str, Dict[str, Any]] = {}

    for page_key in page_order:
        page_jobs = page_groups[page_key]

        # TITLE_CARD panels are translated separately with literal metadata behavior.
        normal_page_panels: list[Dict[str, Any]] = []
        for job in page_jobs:
            panel_id = job["panel_id"]
            character_name = job["character_name"]
            original_japanese = job["original_japanese"]

            if character_name == "TITLE_CARD":
                try:
                    translated = translate_literal_metadata(original_japanese, client)
                    if not translated:
                        translated = original_japanese
                    score = grade_translation_output(
                        original=original_japanese,
                        translated=translated,
                        client=client,
                    )
                except Exception as exc:
                    print(
                        f"[ProcessChapter] TITLE_CARD literal translation failed for panel_id='{panel_id}': {exc}"
                    )
                    translated = original_japanese
                    score = {
                        "contextual_accuracy": 0,
                        "tone_preservation": 0,
                        "naturalness": 0,
                        "pass": False,
                    }

                translated_by_panel_id[panel_id] = translated
                score_by_panel_id[panel_id] = score
            else:
                normal_page_panels.append(
                    {
                        "panel_id": panel_id,
                        "character": character_name,
                        "text": original_japanese,
                    }
                )

        if normal_page_panels:
            try:
                page_translation_map = translate_page(normal_page_panels, client)
            except Exception as exc:
                print(f"[ProcessChapter] Page translation failed for page='{page_key}': {exc}")
                page_translation_map = {}

            for panel in normal_page_panels:
                panel_id = str(panel["panel_id"])
                original_japanese = str(panel["text"])
                translated = page_translation_map.get(panel_id) or original_japanese
                try:
                    score = grade_translation_output(
                        original=original_japanese,
                        translated=translated,
                        client=client,
                    )
                except Exception:
                    score = {
                        "contextual_accuracy": 0,
                        "tone_preservation": 0,
                        "naturalness": 0,
                        "pass": False,
                    }
                translated_by_panel_id[panel_id] = translated
                score_by_panel_id[panel_id] = score

        # Real page-level translation quality signal:
        # grade the first non-NARRATION panel on this page.
        sample_job = next(
            (
                pj
                for pj in page_jobs
                if str(pj["character_name"]).strip() != "NARRATION"
            ),
            None,
        )
        if sample_job is not None:
            sample_panel_id = sample_job["panel_id"]
            sample_original = sample_job["original_japanese"]
            sample_translated = translated_by_panel_id.get(sample_panel_id) or sample_original
            try:
                page_translation_score_by_page[page_key] = grade_translation_output(
                    original=sample_original,
                    translated=sample_translated,
                    client=client,
                )
            except Exception:
                page_translation_score_by_page[page_key] = {
                    "contextual_accuracy": 0,
                    "tone_preservation": 0,
                    "naturalness": 0,
                    "pass": False,
                }
        else:
            page_translation_score_by_page[page_key] = {
                "contextual_accuracy": 0,
                "tone_preservation": 0,
                "naturalness": 0,
                "pass": False,
            }

    for job in panel_jobs:
        panel_id = job["panel_id"]
        character_name = job["character_name"]
        original_japanese = job["original_japanese"]
        translated_output = translated_by_panel_id.get(panel_id) or original_japanese
        translation_scores = score_by_panel_id.get(panel_id) or {
            "contextual_accuracy": 0,
            "tone_preservation": 0,
            "naturalness": 0,
            "pass": False,
        }
        translated_outputs.append(translated_output)
        translation_scores_by_panel.append(translation_scores)
        translated_lines_by_character.setdefault(character_name, []).append(
            translated_output
        )

    # Extract character profiles from translated English dialogue.
    chapter_for_profiles = {"panels": []}
    for character_name, lines in translated_lines_by_character.items():
        for line in lines:
            chapter_for_profiles["panels"].append(
                {"character": character_name, "text": line}
            )

    try:
        inferred_profiles = extract_profiles(chapter_for_profiles, client)
        for profile in inferred_profiles:
            inferred_character_name = str(profile.get("name") or "").strip()
            if not inferred_character_name:
                continue
            update_or_create_profile(
                character_name=inferred_character_name,
                new_profile=profile,
                vector_store=vector_store,
                manga_id=manga_id,
            )

            # Seed continuity memory from profile sample dialogue on chapter 1 cold start.
            sample_dialogue = profile.get("sample_dialogue") or []
            if isinstance(sample_dialogue, list):
                for sample_line in sample_dialogue:
                    sample_line_str = str(sample_line).strip()
                    if not sample_line_str:
                        continue
                    add_approved_line(
                        panel_id="profile_seed",
                        character_name=inferred_character_name,
                        manga_id=manga_id,
                        original_japanese="",
                        final_output=sample_line_str,
                        scores={"profile_seed": True, "pass": True},
                        chapter=0,
                    )
    except Exception as exc:
        print(f"[ProcessChapter] Profile extraction failed (continuing anyway): {exc}")

    # Run Steps A/B/C per panel using the already-translated English.
    results: list[Dict[str, Any]] = []
    for i, job in enumerate(panel_jobs):
        panel_id = job["panel_id"]
        character_name = job["character_name"]
        original_japanese = job["original_japanese"]
        skip_continuity = job["skip_continuity"]
        bubble_type = job["bubble_type"]
        bubble_char_limit = job["bubble_char_limit"]

        translated_output = translated_outputs[i]
        translation_scores = translation_scores_by_panel[i]

        character_profile = query_character_profile_dict(
            character_name,
            manga_id=manga_id,
        ) or {
            "name": character_name,
            "role": "character",
            "speech_style": "",
            "forbidden_phrases": [],
            "speech_rules": [],
        }
        character_profile["manga_id"] = manga_id

        pipeline_result = run_pipeline(
            raw_text=translated_output,
            character_name=character_name,
            bubble_type=bubble_type,
            client=client,
            bubble_char_limit=bubble_char_limit,
            character_profile=character_profile,
            skip_continuity=skip_continuity,
        )

        final_output = pipeline_result.get("final_output", "")
        scores = {
            "translation": translation_scores,
            "cultural": pipeline_result.get("cultural_scores"),
            "continuity": pipeline_result.get("continuity_scores"),
            "typesetting": pipeline_result.get("typesetting_scores"),
        }
        flagged = _flagged_from_scores(scores)

        add_approved_line(
            panel_id=panel_id,
            character_name=character_name,
            manga_id=manga_id,
            original_japanese=original_japanese,
            final_output=final_output,
            scores=scores,
            chapter=chapter,
        )

        results.append(
            {
                "panel_id": panel_id,
                "original": original_japanese,
                "final_output": final_output,
                "scores": scores,
                "page_translation_score": page_translation_score_by_page.get(
                    str(job.get("page_key", "0"))
                ),
                "flagged": flagged,
            }
        )

    mark_chapter_complete(manga_id, chapter)
    return results


def test_full_pipeline() -> None:
    """
    Manual end-to-end test of the Lumina Pipeline with all three agents.
    """
    try:
        client = load_environment()
    except Exception as exc:
        print(f"[Pipeline Test] Failed to initialize Groq client: {exc}")
        return

    raw_text = "たとえ天が崩れ落ちようとも、私は一歩も退かない。"
    character_name = "Kira"
    bubble_type = "medium"

    print("[Pipeline Test] Raw text:")
    print(raw_text)
    print("[Pipeline Test] Character:", character_name)
    print("[Pipeline Test] Bubble type:", bubble_type)

    result = run_pipeline(
        raw_text=raw_text,
        character_name=character_name,
        bubble_type=bubble_type,
        client=client,
    )

    print("\n[Pipeline Test] Cultural output:")
    print(result["cultural_output"])

    print("\n[Pipeline Test] Continuity output:")
    print(result["continuity_output"])

    print("\n[Pipeline Test] Final typeset output:")
    print(result["final_output"])

    print("\n[Pipeline Test] Cultural scores:")
    print(result["cultural_scores"])

    print("\n[Pipeline Test] Continuity scores:")
    print(result["continuity_scores"])

    print("\n[Pipeline Test] Typesetting scores:")
    print(result["typesetting_scores"])


def main() -> None:
    """
    CLI-style entrypoint for running the pipeline.

    For now, this runs a simple end-to-end test of the full pipeline.
    """
    test_full_pipeline()


if __name__ == "__main__":
    main()

