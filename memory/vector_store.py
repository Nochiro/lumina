"""
ChromaDB setup and query utilities.

This module provides:
- A configured ChromaDB client instance.
- Collection initialization for character profiles and dialogue snippets.
- High-level helper functions for agents to query and update memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import time

import json

import chromadb
from chromadb.api.models.Collection import Collection


@dataclass
class VectorStoreConfig:
    """
    Configuration for the ChromaDB vector store.

    This includes:
    - Persistent directory path.
    - Collection name for character profiles.
    """

    persist_directory: Path
    character_collection_name: str = "character_profiles"
    approved_lines_collection_name: str = "approved_lines"
    localization_decisions_collection_name: str = "localization_decisions"


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Default configuration: persist vector data under `data/chroma_db/`.
DEFAULT_CONFIG = VectorStoreConfig(
    persist_directory=PROJECT_ROOT / "data" / "chroma_db",
)

_CLIENT: Optional[chromadb.PersistentClient] = None
_CHARACTER_COLLECTION: Optional[Collection] = None
_APPROVED_LINES_COLLECTION: Optional[Collection] = None
_LOCALIZATION_DECISIONS_COLLECTION: Optional[Collection] = None


def get_chroma_client(config: VectorStoreConfig = DEFAULT_CONFIG) -> chromadb.PersistentClient:
    """
    Initialize and return a ChromaDB client instance.

    Args:
        config: Vector store configuration. Defaults to `DEFAULT_CONFIG`.

    Returns:
        A ChromaDB client object.
    """
    global _CLIENT

    if _CLIENT is None:
        config.persist_directory.mkdir(parents=True, exist_ok=True)
        _CLIENT = chromadb.PersistentClient(path=str(config.persist_directory))

    return _CLIENT


def get_character_collection(
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> Collection:
    """
    Get or create the ChromaDB collection used for character profiles.

    Args:
        config: Vector store configuration. Defaults to `DEFAULT_CONFIG`.

    Returns:
        A ChromaDB Collection for character data.
    """
    global _CHARACTER_COLLECTION

    if _CHARACTER_COLLECTION is None:
        client = get_chroma_client(config)
        _CHARACTER_COLLECTION = client.get_or_create_collection(
            name=config.character_collection_name,
        )

    return _CHARACTER_COLLECTION


def get_approved_lines_collection(
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> Collection:
    """
    Get or create the ChromaDB collection used for approved panel outputs.
    """
    global _APPROVED_LINES_COLLECTION

    if _APPROVED_LINES_COLLECTION is None:
        client = get_chroma_client(config)
        _APPROVED_LINES_COLLECTION = client.get_or_create_collection(
            name=config.approved_lines_collection_name,
        )

    return _APPROVED_LINES_COLLECTION


def get_localization_decisions_collection(
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> Collection:
    """
    Get or create the ChromaDB collection used for recurring localization decisions.
    """
    global _LOCALIZATION_DECISIONS_COLLECTION

    if _LOCALIZATION_DECISIONS_COLLECTION is None:
        client = get_chroma_client(config)
        _LOCALIZATION_DECISIONS_COLLECTION = client.get_or_create_collection(
            name=config.localization_decisions_collection_name,
        )

    return _LOCALIZATION_DECISIONS_COLLECTION


def _character_id_from_name(manga_id: str, character_name: str) -> str:
    """
    Derive a stable identifier for a character based on their name.
    """
    return f"{manga_id}::character:{character_name.strip().lower()}"


def add_character_profile(
    character_name: str,
    profile_data: Dict[str, Any],
    manga_id: str,
    *,
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> None:
    """
    Add or update a single character profile in the vector store.

    Args:
        character_name: Display name of the character.
        profile_data: Dictionary containing profile details.
        manga_id: Project/manga identifier used to isolate data.
    """
    collection = get_character_collection(config)
    character_id = _character_id_from_name(manga_id, character_name)

    document = json.dumps(profile_data, ensure_ascii=False)

    # Use upsert so re-running loaders will refresh profiles.
    collection.upsert(
        ids=[character_id],
        documents=[document],
        metadatas=[{"name": character_name}],
    )


def query_character_profile_dict(
    character_name: str,
    manga_id: str,
    *,
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a character profile from ChromaDB as a Python dict.
    """
    raw = query_character_profile(
        character_name,
        manga_id,
        config=config,
    )
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def query_character_profile(
    character_name: str,
    manga_id: str,
    *,
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> Optional[str]:
    """
    Retrieve a character profile document from ChromaDB.

    Args:
        character_name: Display name of the character.

    Returns:
        The stored profile as a JSON string, or None if not found.
    """
    collection = get_character_collection(config)
    character_id = _character_id_from_name(manga_id, character_name)

    result = collection.get(ids=[character_id])

    documents = result.get("documents") or []
    if not documents or not documents[0]:
        return None

    # `documents` is a list of lists for some Chroma versions; handle both shapes.
    doc = documents[0]
    if isinstance(doc, list):
        return doc[0] if doc else None
    return doc


def _approved_line_id_from(
    manga_id: str,
    panel_id: Any,
    character_name: str,
) -> str:
    """
    Derive a stable identifier for an approved panel line.
    """
    return f"{manga_id}::approved_line:{panel_id}:{character_name.strip().lower()}"


def add_approved_line(
    panel_id: Any,
    character_name: str,
    manga_id: str,
    original_japanese: str,
    final_output: str,
    scores: Dict[str, Any],
    flagged: bool = False,
    chapter: int | None = None,
    *,
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> None:
    """
    Store an approved panel output with metadata for later continuity context.
    """
    collection = get_approved_lines_collection(config)
    approved_id = _approved_line_id_from(manga_id, panel_id, character_name)

    # Use epoch seconds for simple recency ordering.
    created_at = int(time.time())

    collection.upsert(
        ids=[approved_id],
        documents=[final_output],
        metadatas=[
            {
                "panel_id": str(panel_id),
                "character_name": character_name,
                "manga_id": manga_id,
                "chapter": chapter,
                "original_japanese": original_japanese,
                "created_at": created_at,
                "scores_json": json.dumps(scores, ensure_ascii=False),
                "flagged": bool(flagged),
            }
        ],
    )


def query_last_approved_lines(
    character_name: str,
    manga_id: str,
    *,
    limit: int = 10,
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> List[Dict[str, Any]]:
    """
    Retrieve the last approved lines for a character, sorted by created_at.
    """
    collection = get_approved_lines_collection(config)

    # Chroma "get" does not guarantee ordering, so we sort after retrieving.
    result = collection.get(
        where={
            "$and": [
                {"character_name": {"$eq": character_name}},
                {"manga_id": {"$eq": manga_id}},
            ]
        },
    )

    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    rows: List[Dict[str, Any]] = []
    for doc, meta in zip(documents, metadatas):
        meta = meta or {}
        rows.append(
            {
                "panel_id": meta.get("panel_id"),
                "original_japanese": meta.get("original_japanese"),
                "final_output": doc,
                "created_at": meta.get("created_at", 0),
            }
        )

    rows.sort(key=lambda r: int(r.get("created_at") or 0))
    return rows[-limit:]


def upsert_localization_decision(
    manga_id: str,
    source_phrase: str,
    translated_phrase: str,
    *,
    context: Optional[str] = None,
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> None:
    """
    Store a recurring phrase translation decision.
    """
    collection = get_localization_decisions_collection(config)
    decision_id = f"{manga_id}::decision:{source_phrase.strip().lower()}"

    created_at = int(time.time())

    collection.upsert(
        ids=[decision_id],
        documents=[translated_phrase],
        metadatas=[
            {
                "manga_id": manga_id,
                "source_phrase": source_phrase,
                "context": context or "",
                "created_at": created_at,
            }
        ],
    )


def load_characters_from_json(
    folder_path: str | Path,
    manga_id: str,
) -> None:
    """
    Load all JSON character profiles from the specified folder into ChromaDB.

    Args:
        folder_path: Path to the folder containing `.json` character files.
        manga_id: Project/manga identifier used to isolate data.
    """
    folder = Path(folder_path)
    if not folder.exists():
        print(f"[VectorStore] Character folder not found: {folder}")
        return

    for json_file in folder.glob("*.json"):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"[VectorStore] Failed to read {json_file.name}: {exc}")
            continue

        character_name = data.get("name") or json_file.stem
        add_character_profile(character_name, data, manga_id)
        print(f"[VectorStore] Loaded character profile: {character_name}")


def delete_manga_data(
    manga_id: str,
    *,
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> None:
    """
    Delete all vector-store data for a manga_id across all collections.
    """
    character_collection = get_character_collection(config)
    character_rows = character_collection.get()
    character_ids = [
        row_id
        for row_id in (character_rows.get("ids") or [])
        if str(row_id).startswith(f"{manga_id}::")
    ]
    if character_ids:
        character_collection.delete(ids=character_ids)

    approved_collection = get_approved_lines_collection(config)
    approved_rows = approved_collection.get(where={"manga_id": {"$eq": manga_id}})
    approved_ids = approved_rows.get("ids") or []
    if approved_ids:
        approved_collection.delete(ids=approved_ids)

    localization_collection = get_localization_decisions_collection(config)
    localization_rows = localization_collection.get()
    localization_ids = [
        row_id
        for row_id in (localization_rows.get("ids") or [])
        if str(row_id).startswith(f"{manga_id}::")
    ]
    if localization_ids:
        localization_collection.delete(ids=localization_ids)

    print(f"[VectorStore] Deleted all data for manga_id: {manga_id}")


def delete_chapter_data(
    manga_id: str,
    chapter: int,
    *,
    config: VectorStoreConfig = DEFAULT_CONFIG,
) -> None:
    """
    Delete approved lines for a single chapter within a manga project.
    """
    approved_collection = get_approved_lines_collection(config)
    rows = approved_collection.get(where={"manga_id": {"$eq": manga_id}})

    ids = rows.get("ids") or []
    metadatas = rows.get("metadatas") or []
    chapter_prefix = f"{chapter}-"
    ids_to_delete: List[str] = []

    for row_id, metadata in zip(ids, metadatas):
        metadata = metadata or {}
        panel_id = str(metadata.get("panel_id") or "")
        if panel_id.startswith(chapter_prefix):
            ids_to_delete.append(str(row_id))

    if ids_to_delete:
        approved_collection.delete(ids=ids_to_delete)

    print(f"[VectorStore] Deleted chapter {chapter} data for {manga_id}")


def test_vector_store() -> None:
    """
    Simple test helper to validate that the vector store is working.

    This will:
    - Load character profiles from `data/characters/`.
    - Query back the sample character "Kira".
    - Print the result for manual inspection.
    """
    characters_folder = PROJECT_ROOT / "data" / "characters"
    load_characters_from_json(characters_folder, manga_id="default")

    profile_str = query_character_profile("Kira", manga_id="default")
    if profile_str is None:
        print("[VectorStore Test] Failed to retrieve profile for 'Kira'.")
        return

    print("[VectorStore Test] Retrieved profile for 'Kira':")
    print(profile_str)

