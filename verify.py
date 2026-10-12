"""Offline hash, schedule and independent receipt verification."""
import argparse
import json
from collections import Counter
from pathlib import Path
from common import ROOT, read, sha, integrity, encoded
from independent import inspect_response

def verify_freeze():
    manifest=integrity()
    protocol=read(ROOT/'protocol.json')
    prompts=read(ROOT/'prompts.json')
    for row in read(ROOT/'source_manifest.json')['sources']:
        assert sha((ROOT/row['path']).read_bytes())==row['sha256']
    for name, entry in read(ROOT/'unicode_manifest.json').items():
        s=entry['literal']
        assert sha(s.encode())==entry['sha256'] and s.encode().hex()==entry['utf8_hex']
        assert ['U+%04X'%ord(c) for c in s]==entry['codepoints']
    for cell,(s,u) in protocol['cells'].items():
        expected={'systemInstruction':{'parts':[{'text':prompts[s]}]},'contents':[{'role':'user','parts':[{'text':prompts[u]}]}],'generationConfig':protocol['generationConfig']}
        assert (ROOT/'requests'/(cell+'.json')).read_bytes()==encoded(expected)
    for phase,spec in protocol['phases'].items():
        actual=read(ROOT/'schedules'/(phase+'.json'))
        expected=[{'cell':c,'repetition':i} for c in protocol['cells'] for i in range(1,spec['n_per_cell']+1)]
        expected.sort(key=lambda r:(sha((spec['seed']+'|'+r['cell']+'|'+str(r['repetition'])).encode()),r['cell'],r['repetition']))
        for i,r in enumerate(expected,1):
            r.update(slot_id='%s-%04d'%(phase,i),request_sha256=sha((ROOT/'requests'/(r['cell']+'.json')).read_bytes()))
        assert actual==expected
    return {'status':'PASS','frozen_files':len(manifest['files']),'pilot_slots':40,'confirmatory_slots':1600}

def verify_run(folder):
    verify_freeze()
    root=Path(folder)
    run=read(root/'run.json')
    phase=run['phase']
    schedule=read(ROOT/'schedules'/(phase+'.json'))
    issues=[]
    rows=[]
    previous='0'*64
    versions=set()
    if run['schedule_sha256']!=sha((ROOT/'schedules'/(phase+'.json')).read_bytes()) or run['protocol_sha256']!=sha((ROOT/'protocol.json').read_bytes()):
        issues.append('run manifest hash mismatch')
    for slot in schedule:
        d=root/slot['slot_id']
        if not d.exists():
            issues.append('missing '+slot['slot_id'])
            continue
        try:
            e=read(d/'event.json')
            req=(d/'request.bin').read_bytes()
            raw=(d/'response.bin').read_bytes()
            assert all(e[k]==v for k,v in slot.items())
            assert req==(ROOT/'requests'/(slot['cell']+'.json')).read_bytes()
            assert sha(req)==e['request_sha256'] and sha(raw)==e['response_sha256']
            assert e['previous_event_sha256']==previous
            assert e['requested_model']=='gemini-3.6-flash'
            assert e['endpoint']==read(ROOT/'protocol.json')['endpoint']
            assert sha((d/'classification.json').read_bytes())==e['classification_sha256']
            independent=inspect_response(None if e['transport_error'] else e['http_status'],raw)
            assert independent==read(d/'classification.json')
            previous=sha((d/'event.json').read_bytes())
            mv=independent['modelVersion']
            if not isinstance(mv,str) or not mv:
                issues.append('missing modelVersion '+slot['slot_id'])
            else:
                versions.add(mv)
            rows.append({**slot,**independent})
        except (AssertionError,KeyError,ValueError,OSError,TypeError) as exc:
            issues.append('invalid '+slot['slot_id']+': '+type(exc).__name__)
    extras={p.name for p in root.iterdir() if p.is_dir()}-{r['slot_id'] for r in schedule}
    if extras:
        issues.append('unexpected slot directories')
    if len(versions)!=1:
        issues.append('missing or varying modelVersion')
    if any(r['class']=='ERROR' for r in rows):
        issues.append('operational/protocol ERROR')
    try:
        complete=read(root/'COMPLETE.json')
        assert complete=={'slots':len(schedule),'last_event_sha256':previous}
        assert not (root/'STOPPED.json').exists()
    except (AssertionError,ValueError,OSError):
        issues.append('not completed cleanly')
    return {'status':'PASS' if not issues else 'FAIL','phase':phase,'issues':issues,'returned_models':sorted(versions),'rows':rows}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path)
    a=p.parse_args()
    result=verify_run(a.run) if a.run else verify_freeze()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['status']=='PASS' else 1)
