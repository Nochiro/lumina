# Graph Report - .  (2026-04-18)

## Corpus Check
- Corpus is ~10,527 words - fits in a single context window. You may not need a graph.

## Summary
- 232 nodes · 341 edges · 13 communities detected
- Extraction: 86% EXTRACTED · 14% INFERRED · 1% AMBIGUOUS · INFERRED: 47 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Vector Memory Store|Vector Memory Store]]
- [[_COMMUNITY_Continuity Voice Logic|Continuity Voice Logic]]
- [[_COMMUNITY_Profile Extraction Flow|Profile Extraction Flow]]
- [[_COMMUNITY_Cultural Adaptation Logic|Cultural Adaptation Logic]]
- [[_COMMUNITY_Typesetting Constraints|Typesetting Constraints]]
- [[_COMMUNITY_Project Lifecycle|Project Lifecycle]]
- [[_COMMUNITY_Streamlit UI Workflow|Streamlit UI Workflow]]
- [[_COMMUNITY_Cross-Agent Quality Links|Cross-Agent Quality Links]]
- [[_COMMUNITY_Pipeline Orchestration Core|Pipeline Orchestration Core]]
- [[_COMMUNITY_Translation Engine|Translation Engine]]
- [[_COMMUNITY_Text Utility Stubs|Text Utility Stubs]]
- [[_COMMUNITY_Package Skeleton Modules|Package Skeleton Modules]]
- [[_COMMUNITY_Runtime Integration Bridge|Runtime Integration Bridge]]

## God Nodes (most connected - your core abstractions)
1. `run_pipeline()` - 27 edges
2. `process_chapter()` - 21 edges
3. `main()` - 14 edges
4. `load_environment()` - 9 edges
5. `load_projects()` - 9 edges
6. `get_approved_lines_collection()` - 8 edges
7. `query_character_profile_dict()` - 8 edges
8. `query_character_profile()` - 8 edges
9. `run_continuity_director()` - 7 edges
10. `run_typesetting_editor()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Runtime Dependencies` --conceptually_related_to--> `Streamlit App Main Flow`  [INFERRED]
  requirements.txt → ui/app.py
- `CrewAI Orchestration Intent` --conceptually_related_to--> `run_pipeline()`  [AMBIGUOUS]
  agents/__init__.py → main.py
- `Voice Consistency Rationale` --references--> `run_continuity_director`  [EXTRACTED]
  data/characters/README.md → agents/continuity_agent.py
- `run_pipeline()` --calls--> `detect_language()`  [INFERRED]
  main.py → agents\translation_agent.py
- `run_pipeline()` --calls--> `run_translation_agent()`  [INFERRED]
  main.py → agents\translation_agent.py

## Hyperedges (group relationships)
- **Pipeline Execution Flow** — main_run_pipeline, translation_run_translation_agent, cultural_run_cultural_adaptor, continuity_run_continuity_director, typesetting_run_typesetting_editor [EXTRACTED 1.00]
- **Chapter Processing Feedback Loop** — main_process_chapter, profile_extract_profiles, profile_update_or_create_profile, vectorstore_add_approved_line, vectorstore_query_character_profile_dict [INFERRED 0.86]
- **UI Project Memory Management** — ui_streamlit_main, projectmanager_projects_registry, vectorstore_query_approved_lines_for_chapter, vectorstore_approved_lines_memory [INFERRED 0.81]

## Communities

### Community 0 - "Vector Memory Store"
Cohesion: 0.1
Nodes (29): add_approved_line(), add_character_profile(), _approved_line_id_from(), _character_id_from_name(), delete_chapter_data(), delete_manga_data(), get_approved_lines_collection(), get_character_collection() (+21 more)

### Community 1 - "Continuity Voice Logic"
Cohesion: 0.11
Nodes (22): _build_character_prompt_snippet(), ContinuityDirectorAgent, ContinuityDirectorConfig, grade_continuity_output(), Continuity Director Agent.  Ensures that adapted dialogue matches each charact, Backward-compatible path (used nowhere in the updated pipeline)., Grade how well the continuity-directed line matches the character and input., Simple manual test for the Continuity Director Agent.      Steps:     - Use c (+14 more)

### Community 2 - "Profile Extraction Flow"
Cohesion: 0.1
Nodes (23): Character Profile Schema, process_chapter(), Process an uploaded chapter JSON through the 4-step pipeline per panel.      R, extract_profiles, extract_profiles(), _merge_list_field(), _merge_profile_dicts(), Profile extractor for Lumina Pipeline.  Uses an LLM to infer character profile (+15 more)

### Community 3 - "Cultural Adaptation Logic"
Cohesion: 0.11
Nodes (17): CulturalAdaptorAgent, CulturalAdaptorConfig, grade_cultural_output(), Cultural Adaptor Agent.  Responsible for: - Interpreting Japanese/Korean idioms,, Ask the LLM to grade the cultural adaptation quality.      The grading dimension, Simple manual test for the Cultural Adaptor agent.      Steps:     - Use the sam, # TODO: Import CrewAI Agent/Task abstractions when integrating with orchestratio, Configuration for the Cultural Adaptor Agent.      This may include:     - Model (+9 more)

### Community 4 - "Typesetting Constraints"
Cohesion: 0.14
Nodes (18): _get_max_chars_for_bubble(), grade_typesetting_output(), load_bubble_config(), Typesetting Editor Agent.  Takes continuity-approved dialogue and ensures it p, Grade the typesetting output quality.      Metrics:     - fits_constraint (1-, Simple manual test for the Typesetting Editor Agent.      Steps:     - Use bu, Configuration for the Typesetting Editor Agent.      This can be extended late, Thin wrapper class kept for future CrewAI integration. (+10 more)

### Community 5 - "Project Lifecycle"
Cohesion: 0.21
Nodes (19): main(), create_project(), delete_project(), _ensure_projects_file_exists(), get_project(), load_projects(), mark_chapter_complete(), _normalize_manga_id() (+11 more)

### Community 6 - "Streamlit UI Workflow"
Cohesion: 0.13
Nodes (17): _bubble_limit(), _build_panel_character_map(), _init_page(), _load_bubble_config(), _load_characters_for_manga(), _load_characters_on_startup(), _metric_int(), Streamlit frontend for the Lumina Pipeline.  Provides an interactive UI to run (+9 more)

### Community 7 - "Cross-Agent Quality Links"
Cohesion: 0.13
Nodes (19): CrewAI Orchestration Intent, Voice Consistency Rationale, grade_continuity_output, run_continuity_director, Voice Consistency Objective, grade_cultural_output, run_cultural_adaptor, Typesetting Text Utility Intent (+11 more)

### Community 8 - "Pipeline Orchestration Core"
Cohesion: 0.12
Nodes (16): get_client(), load_environment(), Load environment variables from the .env file and initialize the Groq client., build_crew(), _flagged_from_scores(), main(), Flag True if any non-skipped/non-batch numeric score is < 6., # TODO: Import CrewAI orchestration primitives when implementing multi-agent Cre (+8 more)

### Community 9 - "Translation Engine"
Cohesion: 0.21
Nodes (12): detect_language(), grade_translation_output(), Translation Agent (Step 0).  Takes raw Japanese manga/webtoon script text and, Run the Translation Agent on a raw Japanese line.      Args:         raw_text, Grade the translation quality.      Metrics:     - contextual_accuracy (1-10), Placeholder configuration for the Translation Agent., Simple manual test for the Translation Agent.      Uses the sample Japanese te, # NOTE: Original spec requested `llama3-70b-8192`, but that model has been (+4 more)

### Community 10 - "Text Utility Stubs"
Cohesion: 0.18
Nodes (10): hard_wrap_to_limit(), join_lines(), measure_text_length(), Helper utilities for string length checks and formatting.  These functions wil, Measure the length of a given text.      This abstraction allows the project t, # TODO: Implement a robust length metric (possibly taking into account wide char, Hard-wrap text to a specific character limit.      This function will be used, # TODO: Implement deterministic truncation/wrapping strategy. (+2 more)

### Community 11 - "Package Skeleton Modules"
Cohesion: 0.25
Nodes (4): Utility functions for the Lumina Pipeline.  This package currently includes:, # TODO: Export convenience functions/classes from vector_store once implemented., # TODO: Export concrete agent classes here once implemented, e.g.:, # TODO: Re-export common helpers here if convenient, e.g.:

### Community 12 - "Runtime Integration Bridge"
Cohesion: 0.33
Nodes (6): load_environment, Project Registry Management, Runtime Dependencies, Chapter History View, Streamlit App Main Flow, query_approved_lines_for_chapter

## Ambiguous Edges - Review These
- `run_pipeline()` → `CrewAI Orchestration Intent`  [AMBIGUOUS]
  agents/__init__.py · relation: conceptually_related_to
- `run_typesetting_editor` → `Typesetting Text Utility Intent`  [AMBIGUOUS]
  utils/helpers.py · relation: conceptually_related_to

## Knowledge Gaps
- **113 isolated node(s):** `Perform a basic test call to the Groq API to confirm connectivity.      This f`, `Placeholder for future CrewAI-based orchestration.`, `Run an agent step with grading and up to `max_retries` attempts.      The call`, `Run the full Lumina Pipeline on a single line of script.      Pipeline stages:`, `Flag True if any non-skipped/non-batch numeric score is < 6.` (+108 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `run_pipeline()` and `CrewAI Orchestration Intent`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `run_typesetting_editor` and `Typesetting Text Utility Intent`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `run_pipeline()` connect `Cross-Agent Quality Links` to `Continuity Voice Logic`, `Profile Extraction Flow`, `Cultural Adaptation Logic`, `Typesetting Constraints`, `Pipeline Orchestration Core`, `Translation Engine`?**
  _High betweenness centrality (0.403) - this node is a cross-community bridge._
- **Why does `process_chapter()` connect `Profile Extraction Flow` to `Vector Memory Store`, `Continuity Voice Logic`, `Project Lifecycle`, `Cross-Agent Quality Links`, `Pipeline Orchestration Core`, `Translation Engine`, `Runtime Integration Bridge`?**
  _High betweenness centrality (0.337) - this node is a cross-community bridge._
- **Why does `main()` connect `Project Lifecycle` to `Pipeline Orchestration Core`, `Vector Memory Store`, `Profile Extraction Flow`, `Streamlit UI Workflow`?**
  _High betweenness centrality (0.181) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `run_pipeline()` (e.g. with `detect_language()` and `run_translation_agent()`) actually correct?**
  _`run_pipeline()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `process_chapter()` (e.g. with `translate_literal_metadata()` and `grade_translation_output()`) actually correct?**
  _`process_chapter()` has 9 INFERRED edges - model-reasoned connections that need verification._