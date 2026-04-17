"""
Streamlit frontend for the Lumina Pipeline.

Provides an interactive UI to run the full localization pipeline:
Step 0 Translation → Agent 1 Cultural Adaptation → Agent 2 Continuity →
Agent 3 Typesetting.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

# Ensure project root is importable when running `streamlit run ui/app.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from main import process_chapter  # type: ignore
from memory.vector_store import (  # type: ignore
    delete_chapter_data,
    delete_manga_data,
    load_characters_from_json,
)
from utils.project_manager import (  # type: ignore
    create_project,
    delete_project,
    load_projects,
    remove_chapter,
)


@st.cache_resource
def get_client():
    from utils.groq_client import load_environment

    return load_environment()


def _load_bubble_config() -> Dict[str, Any]:
    config_path = PROJECT_ROOT / "data" / "bubble_config.json"
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _bubble_limit(bubble_type: str, config: Dict[str, Any]) -> int:
    default_max = int(config.get("default_max_chars", 80))
    bubbles = config.get("bubbles", {}) or {}
    val = bubbles.get(bubble_type)
    return int(val) if val is not None else default_max


def _metric_int(label: str, value: Any) -> None:
    """
    Render a metric that may be None/unknown.
    """
    if value is None:
        st.metric(label, "—")
    else:
        st.metric(label, int(value))


def _init_page() -> None:
    st.set_page_config(layout="wide")
    st.title("🎌 Lumina Pipeline")
    st.caption("Autonomous Japanese Manga Localization Engine")


def _sidebar() -> Dict[str, str]:
    with st.sidebar:
        st.header("Settings")

        character_name = st.selectbox(
            "Select Character",
            options=["Kira", "Unknown"],
            index=0,
        )

        bubble_type = st.selectbox(
            "Bubble Type",
            options=["small", "medium", "large", "thought"],
            index=1,
        )

        st.divider()
        st.subheader("Agents")
        st.write("🌐 Agent 0: Detects Japanese and translates contextually")
        st.write("🎭 Agent 1: Adapts cultural idioms to natural English")
        st.write("🧠 Agent 2: Matches character voice from memory")
        st.write("📐 Agent 3: Fits text into speech bubble limits")

    return {"character_name": character_name, "bubble_type": bubble_type}


def _load_characters_on_startup() -> None:
    """
    Load all character profiles into ChromaDB.
    """
    characters_folder = PROJECT_ROOT / "data" / "characters"
    load_characters_from_json(characters_folder, manga_id="default")


@st.cache_resource
def _load_characters_for_manga(manga_id: str) -> None:
    """
    Load character profiles into ChromaDB for a specific manga/project.
    Cached to avoid re-loading on every rerun.
    """
    characters_folder = PROJECT_ROOT / "data" / "characters"
    load_characters_from_json(characters_folder, manga_id=manga_id)


def _results_tabs(raw_text: str, result: Dict[str, Any]) -> None:
    tabs = st.tabs(
        [
            "🌐 Translation",
            "🎭 Cultural Adaptation",
            "🧠 Continuity Check",
            "📐 Final Typeset Output",
        ]
    )

    translation_scores = result.get("translation_scores", {}) or {}
    cultural_scores = result.get("cultural_scores", {}) or {}
    continuity_scores = result.get("continuity_scores", {}) or {}
    typesetting_scores = result.get("typesetting_scores", {}) or {}

    detected_language = result.get("detected_language", "unknown")

    with tabs[0]:
        st.info(f"Detected language: {detected_language}")
        left, right = st.columns(2)
        with left:
            st.subheader("Original Input")
            st.text_area(
                "Original",
                value=raw_text,
                height=150,
                key="orig_view",
                disabled=True,
            )
        with right:
            st.subheader("Translated English")
            st.text_area(
                "Translated",
                value=result.get("translated_output", ""),
                height=150,
                key="translated_view",
                disabled=True,
            )

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            _metric_int("Contextual accuracy", translation_scores.get("contextual_accuracy"))
        with m2:
            _metric_int("Tone preservation", translation_scores.get("tone_preservation"))
        with m3:
            _metric_int("Naturalness", translation_scores.get("naturalness"))
        with m4:
            st.metric("Pass", "✅" if translation_scores.get("pass") else "❌")

    with tabs[1]:
        left, right = st.columns(2)
        with left:
            st.subheader("Translation input")
            st.text_area(
                "Input to cultural adaptor",
                value=result.get("translated_output", ""),
                height=150,
                key="cultural_in_view",
                disabled=True,
            )
        with right:
            st.subheader("Cultural output")
            st.text_area(
                "Cultural output",
                value=result.get("cultural_output", ""),
                height=150,
                key="cultural_out_view",
                disabled=True,
            )

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            _metric_int("Cultural accuracy", cultural_scores.get("cultural_accuracy"))
        with m2:
            _metric_int("Tone preservation", cultural_scores.get("tone_preservation"))
        with m3:
            _metric_int("Naturalness", cultural_scores.get("naturalness"))
        with m4:
            st.metric("Pass", "✅" if cultural_scores.get("pass") else "❌")

    with tabs[2]:
        left, right = st.columns(2)
        with left:
            st.subheader("Cultural input")
            st.text_area(
                "Input to continuity director",
                value=result.get("cultural_output", ""),
                height=150,
                key="cont_in_view",
                disabled=True,
            )
        with right:
            st.subheader("Continuity output")
            st.text_area(
                "Continuity output",
                value=result.get("continuity_output", ""),
                height=150,
                key="cont_out_view",
                disabled=True,
            )

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            _metric_int("Voice consistency", continuity_scores.get("voice_consistency"))
        with m2:
            _metric_int(
                "Forbidden phrase compliance",
                continuity_scores.get("forbidden_phrase_compliance"),
            )
        with m3:
            _metric_int("Meaning preservation", continuity_scores.get("meaning_preservation"))
        with m4:
            st.metric("Pass", "✅" if continuity_scores.get("pass") else "❌")

    with tabs[3]:
        final_output = result.get("final_output", "")
        st.success(final_output)

        bubble_cfg = _load_bubble_config()
        max_chars = _bubble_limit(st.session_state.get("bubble_type", "medium"), bubble_cfg)
        st.write(f"**Character count**: {len(final_output)} / {max_chars}")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            _metric_int("Fits constraint", typesetting_scores.get("fits_constraint"))
        with m2:
            _metric_int("Meaning preserved", typesetting_scores.get("meaning_preserved"))
        with m3:
            _metric_int("Voice maintained", typesetting_scores.get("voice_maintained"))
        with m4:
            st.metric("Pass", "✅" if typesetting_scores.get("pass") else "❌")

        st.divider()

        download_payload = {
            "original_japanese": raw_text,
            "detected_language": result.get("detected_language"),
            "translated_output": result.get("translated_output"),
            "cultural_output": result.get("cultural_output"),
            "continuity_output": result.get("continuity_output"),
            "final_output": result.get("final_output"),
            "all_scores": {
                "translation": result.get("translation_scores"),
                "cultural": result.get("cultural_scores"),
                "continuity": result.get("continuity_scores"),
                "typesetting": result.get("typesetting_scores"),
            },
        }

        st.download_button(
            label="Download JSON output",
            data=json.dumps(download_payload, ensure_ascii=False, indent=2),
            file_name="lumina_pipeline_output.json",
            mime="application/json",
        )


def main() -> None:
    _init_page()
    st.divider()
    st.sidebar.header("📚 Lumina Projects")

    if "selected_project_manga_id" not in st.session_state:
        st.session_state["selected_project_manga_id"] = None

    projects = load_projects()

    # Render project selection list (click to select).
    if projects:
        st.sidebar.caption("Click a project to select it.")
        for proj in projects:
            manga_id = str(proj.get("manga_id") or "").strip()
            display_name = str(proj.get("display_name") or "")
            language = str(proj.get("language") or "")
            chapters_completed = proj.get("chapters_completed") or []
            try:
                chapters_count = len(chapters_completed)
            except Exception:
                chapters_count = 0

            label = (
                f"{display_name} ({language}) — {chapters_count} chapters completed"
            )
            proj_col, del_col = st.sidebar.columns([0.85, 0.15], gap="small")
            with proj_col:
                if st.button(label, key=f"proj_btn_{manga_id}"):
                    st.session_state["selected_project_manga_id"] = manga_id
            with del_col:
                if st.button("🗑️", key=f"proj_delete_btn_{manga_id}", help="Delete project"):
                    st.session_state["pending_delete_manga_id"] = manga_id
                    st.session_state["pending_delete_name"] = display_name

    new_project_clicked = st.sidebar.button("New Project")
    if new_project_clicked:
        st.session_state["show_new_project_form"] = True

    if st.session_state.get("show_new_project_form"):
        with st.sidebar.form("new_project_form", clear_on_submit=True):
            display_name = st.text_input("Display Name")
            language = st.selectbox("Language", options=["Japanese", "Korean"])
            submitted = st.form_submit_button("Create Project")

            if submitted:
                manga_id = (
                    str(display_name).lower().replace(" ", "_").strip()
                    or ""
                )
                try:
                    create_project(
                        manga_id=manga_id,
                        display_name=str(display_name).strip(),
                        language=language,
                    )
                except Exception as exc:
                    st.sidebar.error(f"Failed to create project: {exc}")
                else:
                    st.session_state["selected_project_manga_id"] = manga_id
                    st.session_state["show_new_project_form"] = False
                    st.rerun()

    selected_manga_id = st.session_state.get("selected_project_manga_id")

    pending_delete_manga_id = st.session_state.get("pending_delete_manga_id")
    if pending_delete_manga_id:
        pending_delete_name = st.session_state.get("pending_delete_name", "")
        st.warning(
            "⚠️ Delete "
            f"'{pending_delete_name}'? This will permanently wipe ALL character profiles, approved lines, and localization memory for this manga from ChromaDB. This cannot be undone."
        )
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("Yes, delete everything", type="primary", key="confirm_delete_project"):
                delete_manga_data(str(pending_delete_manga_id))
                delete_project(str(pending_delete_manga_id))
                st.session_state.pop("pending_delete_manga_id", None)
                st.session_state.pop("pending_delete_name", None)
                if st.session_state.get("selected_project_manga_id") == pending_delete_manga_id:
                    st.session_state.pop("selected_project_manga_id", None)
                st.rerun()
        with cancel_col:
            if st.button("Cancel", key="cancel_delete_project"):
                st.session_state.pop("pending_delete_manga_id", None)
                st.session_state.pop("pending_delete_name", None)
                st.rerun()

    if not selected_manga_id:
        st.info("Select a project from the sidebar to run the pipeline.")
        return

    selected_project = next(
        (
            proj
            for proj in projects
            if str(proj.get("manga_id") or "").strip() == str(selected_manga_id)
        ),
        None,
    )
    chapters_completed = selected_project.get("chapters_completed") if selected_project else []
    chapters_int = sorted(
        {
            int(chapter)
            for chapter in (chapters_completed or [])
            if str(chapter).strip().lstrip("-").isdigit()
        }
    )

    if chapters_int:
        st.subheader("Chapter History")
        for chapter in chapters_int:
            chapter_col, delete_col = st.columns([0.9, 0.1], gap="small")
            with chapter_col:
                st.write(f"Chapter {chapter}")
            with delete_col:
                if st.button(
                    "🗑️",
                    key=f"delete_chapter_btn_{selected_manga_id}_{chapter}",
                    help=f"Delete chapter {chapter} memory",
                ):
                    st.session_state["pending_delete_chapter"] = int(chapter)
                    st.session_state["pending_delete_chapter_manga"] = str(selected_manga_id)

        pending_delete_chapter = st.session_state.get("pending_delete_chapter")
        pending_delete_chapter_manga = st.session_state.get("pending_delete_chapter_manga")
        if (
            pending_delete_chapter is not None
            and str(pending_delete_chapter_manga) == str(selected_manga_id)
        ):
            st.warning(
                f"Delete Chapter {pending_delete_chapter} data? Approved lines for this chapter will be removed from memory."
            )
            chapter_confirm_col, chapter_cancel_col = st.columns(2)
            with chapter_confirm_col:
                if st.button("Yes, delete chapter", key="confirm_delete_chapter"):
                    delete_chapter_data(str(selected_manga_id), int(pending_delete_chapter))
                    remove_chapter(str(selected_manga_id), int(pending_delete_chapter))
                    st.session_state.pop("pending_delete_chapter", None)
                    st.session_state.pop("pending_delete_chapter_manga", None)
                    st.rerun()
            with chapter_cancel_col:
                if st.button("Cancel", key="cancel_delete_chapter"):
                    st.session_state.pop("pending_delete_chapter", None)
                    st.session_state.pop("pending_delete_chapter_manga", None)
                    st.rerun()

        st.divider()

    try:
        _load_characters_for_manga(str(selected_manga_id))
    except Exception as exc:
        st.error(f"Failed to load character profiles: {exc}")
        return

    st.subheader("Upload Chapter JSON")

    uploaded_file = st.file_uploader("chapter.json", type=["json"])

    if uploaded_file is None:
        st.info("Upload a chapter JSON containing a `panels` array.")
        return

    try:
        chapter_data = json.load(uploaded_file)
    except Exception as exc:
        st.error(f"Invalid JSON file: {exc}")
        return

    run_clicked = st.button("🚀 Run Pipeline", type="primary")
    if run_clicked:
        try:
            client = get_client()
        except Exception as exc:
            st.error(f"Failed to initialize Groq client: {exc}")
            return

        chapter_data["manga_id"] = str(selected_manga_id)
        with st.spinner("Pipeline running... this may take a while"):
            try:
                results = process_chapter(chapter_data, client)
            except Exception as exc:
                st.error(f"Pipeline error: {exc}")
                return

        st.session_state["chapter_results"] = results

    if "chapter_results" in st.session_state:
        results = st.session_state["chapter_results"]
        st.divider()
        st.subheader("Per-Panel Results")

        import html

        # Map panel_id -> character so the results table can show character
        # even though `process_chapter()` returns only required fields.
        panel_id_to_character: dict[str, str] = {}
        for panel in (chapter_data.get("panels") or []):
            if not isinstance(panel, dict):
                continue
            pid = panel.get("panel_id") or panel.get("id") or panel.get("index")
            pid_str = str(pid) if pid is not None else ""
            character = str(panel.get("character") or "").strip()
            if pid_str:
                panel_id_to_character[pid_str] = character

        header_html = (
            "<tr>"
            "<th>panel_id</th>"
            "<th>character</th>"
            "<th>original_japanese</th>"
            "<th>final_output</th>"
            "<th>scores</th>"
            "<th>flagged</th>"
            "</tr>"
        )

        rows_html = []
        for r in results:
            panel_id = html.escape(str(r.get("panel_id", "")))
            character = html.escape(panel_id_to_character.get(str(r.get("panel_id", "")), ""))
            original = html.escape(str(r.get("original", "")))
            final_output = html.escape(str(r.get("final_output", "")))
            scores_json = html.escape(
                json.dumps(r.get("scores", {}), ensure_ascii=False)
            )
            flagged = bool(r.get("flagged"))
            flagged_text = "FLAGGED" if flagged else "OK"
            bg = "#ffcc80" if flagged else "transparent"

            rows_html.append(
                "<tr style=\"background-color: %s;\">" % bg
                + f"<td>{panel_id}</td>"
                + f"<td>{character}</td>"
                + f"<td><pre style=\"margin:0;white-space:pre-wrap;\">{original}</pre></td>"
                + f"<td><pre style=\"margin:0;white-space:pre-wrap;\">{final_output}</pre></td>"
                + f"<td><pre style=\"margin:0;white-space:pre-wrap;\">{scores_json}</pre></td>"
                + f"<td>{flagged_text}</td>"
                + "</tr>"
            )

        table_html = (
            "<table style=\"width:100%; border-collapse: collapse;\">"
            + "<thead>" + header_html + "</thead>"
            + "<tbody>" + "".join(rows_html) + "</tbody>"
            + "</table>"
        )

        st.markdown(table_html, unsafe_allow_html=True)

        st.divider()
        st.download_button(
            label="Download Results as JSON",
            data=json.dumps(results, ensure_ascii=False, indent=2),
            file_name="chapter_results.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()

