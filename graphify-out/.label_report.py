import json
from pathlib import Path
from graphify.build import build_from_json
from graphify.analyze import suggest_questions
from graphify.report import generate

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding='utf-8'))
raw = Path('graphify-out/.graphify_detect.json').read_bytes()
detection = None
for enc in ('utf-8','utf-16','utf-16-le','utf-16-be'):
    try:
        detection = json.loads(raw.decode(enc))
        break
    except Exception:
        pass
if detection is None:
    raise SystemExit('Cannot decode detect JSON')
analysis = json.loads(Path('graphify-out/.graphify_analysis.json').read_text(encoding='utf-8'))

G = build_from_json(extraction)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
tokens = {'input': extraction.get('input_tokens', 0), 'output': extraction.get('output_tokens', 0)}

labels = {
  0: 'Vector Memory Store',
  1: 'Continuity Voice Logic',
  2: 'Profile Extraction Flow',
  3: 'Cultural Adaptation Logic',
  4: 'Typesetting Constraints',
  5: 'Project Lifecycle',
  6: 'Streamlit UI Workflow',
  7: 'Cross-Agent Quality Links',
  8: 'Pipeline Orchestration Core',
  9: 'Translation Engine',
  10: 'Text Utility Stubs',
  11: 'Package Skeleton Modules',
  12: 'Runtime Integration Bridge'
}

questions = suggest_questions(G, communities, labels)
report = generate(G, communities, cohesion, labels, analysis['gods'], analysis['surprises'], detection, tokens, '.', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding='utf-8')
Path('graphify-out/.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in labels.items()}, indent=2), encoding='utf-8')

analysis['questions'] = questions
Path('graphify-out/.graphify_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')
print('Report updated with community labels')
