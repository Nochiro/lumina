import json
from pathlib import Path
from networkx.readwrite import json_graph

analysis = json.loads(Path('graphify-out/.graphify_analysis.json').read_text(encoding='utf-8'))
G = json_graph.node_link_graph(json.loads(Path('graphify-out/graph.json').read_text(encoding='utf-8')), edges='links')
communities = {int(k): v for k, v in analysis['communities'].items()}
for cid, nodes in sorted(communities.items()):
    labels = []
    for nid in nodes[:12]:
        labels.append(G.nodes[nid].get('label', nid))
    print(f'Community {cid}:')
    print('  ' + ' | '.join(labels[:8]))
