"""
Project management utilities for Lumina.

Stores per-manga progress in `data/projects.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_PATH = PROJECT_ROOT / "data" / "projects.json"


def _ensure_projects_file_exists() -> None:
    """
    Ensure `data/projects.json` exists and contains a valid structure.
    """
    if PROJECTS_PATH.exists():
        return
    PROJECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROJECTS_PATH.write_text(json.dumps({"projects": []}, ensure_ascii=False, indent=2), encoding="utf-8")


def load_projects() -> list:
    """
    reads data/projects.json, returns projects list
    """
    _ensure_projects_file_exists()
    raw = PROJECTS_PATH.read_text(encoding="utf-8")
    data = json.loads(raw or "{}")
    return data.get("projects") or []


def _normalize_manga_id(manga_id: str) -> str:
    """
    manga_id must be lowercase, no spaces (replace spaces with underscore)
    """
    normalized = "_".join((manga_id or "").strip().lower().split())
    normalized = normalized.replace(" ", "_")
    return normalized


def _save_projects(projects: list) -> None:
    _ensure_projects_file_exists()
    PROJECTS_PATH.write_text(
        json.dumps({"projects": projects}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def create_project(manga_id: str, display_name: str, language: str) -> dict:
    """
    adds new project to projects.json
    manga_id must be lowercase, no spaces (replace spaces with underscore)
    returns the created project dict
    """
    manga_id_norm = _normalize_manga_id(manga_id)
    if not manga_id_norm:
        raise ValueError("manga_id must not be empty.")

    projects = load_projects()
    existing = get_project(manga_id_norm)
    if existing is not None:
        # Keep any existing progress; just refresh display_name/language if provided.
        existing["display_name"] = display_name
        existing["language"] = language
        _save_projects(projects)
        return existing

    project = {
        "manga_id": manga_id_norm,
        "display_name": display_name,
        "language": language,
        "chapters_completed": [],
    }

    projects.append(project)
    _save_projects(projects)
    return project


def get_project(manga_id: str) -> dict | None:
    """
    returns project dict or None if not found
    """
    manga_id_norm = _normalize_manga_id(manga_id)
    projects = load_projects()
    for project in projects:
        if str(project.get("manga_id") or "").strip().lower() == manga_id_norm:
            return project
    return None


def mark_chapter_complete(manga_id: str, chapter_number: int) -> None:
    """
    adds chapter_number to project's chapters_completed list
    saves back to projects.json
    """
    manga_id_norm = _normalize_manga_id(manga_id)
    if not manga_id_norm:
        raise ValueError("manga_id must not be empty.")

    projects = load_projects()
    found = False
    for project in projects:
        if str(project.get("manga_id") or "").strip().lower() != manga_id_norm:
            continue
        found = True

        chapters = project.get("chapters_completed") or []
        # Ensure consistent int storage.
        chapters_int: List[int] = []
        for ch in chapters:
            try:
                chapters_int.append(int(ch))
            except Exception:
                continue

        if int(chapter_number) not in chapters_int:
            chapters_int.append(int(chapter_number))
        chapters_int.sort()
        project["chapters_completed"] = chapters_int
        break

    if not found:
        raise ValueError(f"Project not found for manga_id='{manga_id_norm}'.")

    _save_projects(projects)


def delete_project(manga_id: str) -> None:
    """
    Remove a project by manga_id and save projects.json.
    """
    manga_id_norm = _normalize_manga_id(manga_id)
    projects = load_projects()
    updated_projects = [
        project
        for project in projects
        if str(project.get("manga_id") or "").strip().lower() != manga_id_norm
    ]
    _save_projects(updated_projects)


def remove_chapter(manga_id: str, chapter: int) -> None:
    """
    Remove a completed chapter number from a project's chapters_completed list.
    """
    manga_id_norm = _normalize_manga_id(manga_id)
    projects = load_projects()

    for project in projects:
        if str(project.get("manga_id") or "").strip().lower() != manga_id_norm:
            continue

        chapters = project.get("chapters_completed") or []
        chapters_int: List[int] = []
        for ch in chapters:
            try:
                chapters_int.append(int(ch))
            except Exception:
                continue

        project["chapters_completed"] = [ch for ch in chapters_int if ch != int(chapter)]
        break

    _save_projects(projects)

