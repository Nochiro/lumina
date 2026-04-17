import json
from pathlib import Path
from graphify.extract import collect_files, extract

raw = Path('graphify-out/.graphify_detect.json').read_bytes()
detect = None
for enc in ('utf-8','utf-16','utf-16-le','utf-16-be'):
    try:
        detect = json.loads(raw.decode(enc))
        break
    except Exception:
        pass
if detect is None:
    raise SystemExit('Cannot decode detect JSON')

code_files = []
for f in detect.get('files', {}).get('code', []):
    p = Path(f)
    code_files.extend(collect_files(p) if p.is_dir() else [p])

if code_files:
    result = extract(code_files)
    Path('graphify-out/.graphify_ast.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f"AST: {len(result['nodes'])} nodes, {len(result['edges'])} edges")
else:
    Path('graphify-out/.graphify_ast.json').write_text(json.dumps({'nodes':[],'edges':[],'input_tokens':0,'output_tokens':0}, indent=2), encoding='utf-8')
    print('No code files - skipping AST extraction')
