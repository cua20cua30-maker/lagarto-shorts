import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(path):
    with (ROOT/path).open('r',encoding='utf-8') as f: return json.load(f)

def main():
    creators=read(Path('config/creators.json')); auth=read(Path('data/authorization_manifest.json')); candidates=read(Path('data/candidates.json')); moments=read(Path('data/moments.json')); plans=read(Path('data/clip_plans.json')); queue=read(Path('data/render_queue.json')); analytics=read(Path('data/analytics_snapshots.json')); learning=read(Path('data/learning_records.json')); published=read(Path('data/published.json')); emotions=read(Path('data/emotion_events.json'))
    assert len(creators['creators'])==11
    assert auth['schema_version']==1 and isinstance(auth['authorized_sources'],list)
    assert candidates['schema_version']==1 and isinstance(candidates['candidates'],list)
    assert moments['schema_version']>=2 and isinstance(moments['moments'],list)
    assert plans['schema_version']==1 and isinstance(plans['plans'],list)
    assert queue['schema_version']==1 and isinstance(queue['jobs'],list)
    assert analytics['schema_version']>=1 and isinstance(analytics['snapshots'],list)
    assert isinstance(learning, list) or isinstance(learning.get('records'), list)
    assert emotions['schema_version']==1 and isinstance(emotions['events'],list)
    assert published['schema_version']==1 and isinstance(published['items'],list)
    authorized=set(auth['authorized_sources'])
    for c in candidates['candidates']:
        assert c['publishable'] is False or c['authorization_status']=='authorized'
        if c['source_url'] not in authorized: assert c['publishable'] is False
    print(f'Pipeline self-test: OK; candidates={len(candidates["candidates"])} moments={len(moments["moments"])} plans={len(plans["plans"])}')

if __name__=='__main__': main()
