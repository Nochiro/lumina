import json
from pathlib import Path
from graphify.benchmark import run_benchmark, print_benchmark

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

result = run_benchmark('graphify-out/graph.json', corpus_words=detection['total_words'])
print_benchmark(result)
