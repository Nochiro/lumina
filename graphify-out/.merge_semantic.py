import json
from pathlib import Path

chunks_path = Path('graphify-out/.graphify_chunks.json')
chunks = json.loads(chunks_path.read_text(encoding='utf-8')) if chunks_path.exists() else []

valid = {'nodes': [], 'edges': [], 'hyperedges': [], 'input_tokens': 0, 'output_tokens': 0}
missing = 0
invalid = 0
for i, _chunk in enumerate(chunks, start=1):
    p = Path(f'graphify-out/.graphify_chunk_{i:02d}.json')
    if not p.exists():
        print(f'WARNING: chunk {i} missing from disk — subagent may have been read-only. Re-run with general-purpose agent.')
        missing += 1
        continue
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or 'nodes' not in data or 'edges' not in data:
            raise ValueError('missing nodes/edges')
    except Exception as e:
        print(f'WARNING: chunk {i} invalid JSON ({e}) - skipping')
        invalid += 1
        continue
    valid['nodes'].extend(data.get('nodes', []))
    valid['edges'].extend(data.get('edges', []))
    valid['hyperedges'].extend(data.get('hyperedges', []))
    valid['input_tokens'] += int(data.get('input_tokens', 0) or 0)
    valid['output_tokens'] += int(data.get('output_tokens', 0) or 0)

Path('graphify-out/.graphify_semantic_new.json').write_text(json.dumps(valid, indent=2), encoding='utf-8')
print(f'Semantic new: {len(valid["nodes"])} nodes, {len(valid["edges"])} edges, {len(valid["hyperedges"])} hyperedges')

# cache + merge into .graphify_semantic.json
from graphify.cache import save_semantic_cache
saved = save_semantic_cache(valid.get('nodes', []), valid.get('edges', []), valid.get('hyperedges', []))
print(f'Cached {saved} files')

cached_path = Path('graphify-out/.graphify_cached.json')
cached = json.loads(cached_path.read_text(encoding='utf-8')) if cached_path.exists() else {'nodes':[],'edges':[],'hyperedges':[]}
all_nodes = cached['nodes'] + valid.get('nodes', [])
all_edges = cached['edges'] + valid.get('edges', [])
all_hyperedges = cached.get('hyperedges', []) + valid.get('hyperedges', [])
seen = set()
deduped = []
for n in all_nodes:
    nid = n.get('id')
    if nid and nid not in seen:
        seen.add(nid)
        deduped.append(n)

merged = {
    'nodes': deduped,
    'edges': all_edges,
    'hyperedges': all_hyperedges,
    'input_tokens': valid.get('input_tokens', 0),
    'output_tokens': valid.get('output_tokens', 0),
}
Path('graphify-out/.graphify_semantic.json').write_text(json.dumps(merged, indent=2), encoding='utf-8')
print(f'Extraction complete - {len(deduped)} nodes, {len(all_edges)} edges ({len(cached.get("nodes",[]))} from cache, {len(valid.get("nodes",[]))} new)')

# cleanup temp files specified by skill
for fp in ['graphify-out/.graphify_cached.json','graphify-out/.graphify_uncached.txt','graphify-out/.graphify_semantic_new.json']:
    p = Path(fp)
    if p.exists():
        p.unlink()
