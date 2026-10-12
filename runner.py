"""Default offline. Live operation requires all explicit phase-specific gates."""
import argparse
import datetime
import json
import subprocess
from pathlib import Path
from common import ROOT, read, save, sha, integrity, request_bytes
from classifier import classify

def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()

def authorize(phase, authorization, live, zero_cost):
    if not live or authorization is None:
        raise PermissionError('OFFLINE: separate live authorization required')
    integrity()
    a=read(authorization)
    head=git('rev-parse','HEAD')
    tag=read(ROOT/'freeze_manifest.json')['tag']
    if git('status','--porcelain') or git('rev-parse',tag+'^{commit}')!=head:
        raise PermissionError('Frozen clean tagged commit required')
    required={'phase':phase,'commit':head,'protocol_sha256':sha((ROOT/'protocol.json').read_bytes()),'authorize_live':True,'public_freeze_verified':True}
    if any(a.get(k)!=v for k,v in required.items()):
        raise PermissionError('Authorization does not match phase/freeze/no-spend gates')
    if not (zero_cost and a.get('zero_cost_project_verified') is True):
        amendment=read(ROOT/'billing_amendment.json')
        if datetime.datetime.now(datetime.timezone.utc).date().isoformat()>amendment['pricing_valid_through']:
            raise PermissionError('Frozen billing rates expired; refreeze rates before inference')
        if phase!='pilot' or a.get('authorize_paid') is not True or a.get('budget_usd')!=amendment['pilot_budget_usd'] or a.get('billing_amendment_sha256')!=sha((ROOT/'billing_amendment.json').read_bytes()):
            raise PermissionError('Paid pilot requires exact amended budget authorization')
    if not isinstance(a.get('public_commit_url'),str) or not a['public_commit_url'].startswith('https://github.com/') or not a['public_commit_url'].endswith('/commit/'+head):
        raise PermissionError('Public frozen commit reference required')
    if not a.get('project_reference') or not a.get('operator'):
        raise PermissionError('Operator and verified project reference required (no secret values)')
    return a

def transmit(body, key, timeout):
    # No redirects, proxies, retry library, SDK defaults, diagnostics, or fallback.
    import http.client
    conn=http.client.HTTPSConnection('generativelanguage.googleapis.com',timeout=timeout)
    status=None
    headers=[]
    raw=b''
    transport_error=None
    try:
        conn.request('POST','/v1beta/models/gemini-3.6-flash:generateContent',body=body,headers={'Content-Type':'application/json','x-goog-api-key':key,'Accept-Encoding':'identity'})
        response=conn.getresponse()
        status=response.status
        headers=response.getheaders()
        try:
            raw=response.read()
        except http.client.IncompleteRead as exc:
            raw=exc.partial
            transport_error='IncompleteRead'
    except Exception as exc:
        # Never serialize an exception message that could include credentials.
        transport_error=type(exc).__name__
    finally:
        conn.close()
    return status,headers,raw,transport_error

def execute(phase, authorization, live=False, zero_cost=False, key_file=None, output=None):
    auth=authorize(phase,authorization,live,zero_cost)
    if not key_file or not output:
        raise ValueError('Explicit key file and new output directory required')
    dest=Path(output).resolve()
    if ROOT not in dest.parents or not str(dest.relative_to(ROOT)).startswith('runs/'):
        raise ValueError('Output must be a new directory under runs/')
    dest.mkdir(parents=True,exist_ok=False)
    # Credential access is downstream of every permission gate.
    key=Path(key_file).read_text(encoding='utf-8').strip()
    if not key or any(c.isspace() for c in key):
        raise ValueError('Key file must contain one raw key, not explanatory text')
    protocol=read(ROOT/'protocol.json')
    schedule=read(ROOT/'schedules'/(phase+'.json'))
    save(dest/'run.json',{'phase':phase,'commit':git('rev-parse','HEAD'),'authorization':auth,'schedule_sha256':sha((ROOT/'schedules'/(phase+'.json')).read_bytes()),'protocol_sha256':sha((ROOT/'protocol.json').read_bytes()),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    previous='0'*64
    returned=None
    spent_usd=0.0
    for row in schedule:
        integrity()
        folder=dest/row['slot_id']
        folder.mkdir()
        body=request_bytes(row['cell'])
        if auth.get('authorize_paid'):
            # Conservative input allowance; all generated thinking is charged.
            reserve=(len(body)+1024)*0.75/1e6+protocol['generationConfig']['maxOutputTokens']*3.75/1e6
            if spent_usd+reserve>auth['budget_usd']:
                save(dest/'STOPPED.json',{'reason':'BUDGET_RESERVE','slot_id':row['slot_id'],'last_event_sha256':previous,'decision':'INCONCLUSIVE','estimated_cost_usd':spent_usd})
                return
        if sha(body)!=row['request_sha256']:
            raise ValueError('Request hash drift')
        (folder/'request.bin').write_bytes(body)
        started=datetime.datetime.now(datetime.timezone.utc).isoformat()
        status,headers,raw,error=transmit(body,key,protocol['timeout_seconds'])
        (folder/'response.bin').write_bytes(raw)
        classification=classify(None if error else status,raw)
        save(folder/'classification.json',classification)
        event={**row,'http_status':status,'response_headers':headers,'transport_error':error,'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'response_sha256':sha(raw),'classification_sha256':sha((folder/'classification.json').read_bytes()),'previous_event_sha256':previous,'requested_model':protocol['model'],'endpoint':protocol['endpoint']}
        save(folder/'event.json',event)
        previous=sha((folder/'event.json').read_bytes())
        if auth.get('authorize_paid') and status==200 and not error:
            usage=json.loads(raw).get('usageMetadata',{})
            counts=[usage.get('promptTokenCount'),usage.get('candidatesTokenCount',0),usage.get('thoughtsTokenCount',0)]
            if not all(isinstance(n,int) and n>=0 for n in counts):
                save(dest/'STOPPED.json',{'reason':'MISSING_BILLING_USAGE','slot_id':row['slot_id'],'last_event_sha256':previous,'decision':'INCONCLUSIVE'})
                return
            spent_usd+=(counts[0]*0.75+(counts[1]+counts[2])*3.75)/1e6
            save(dest/'cost.json',{'estimated_cost_usd':spent_usd,'budget_usd':auth['budget_usd'],'tax_excluded':True})
        print(row['slot_id'],row['cell'],status,classification['class'],flush=True)
        mv=classification['modelVersion']
        reason=None
        if status==404:
            reason='MODEL_UNAVAILABLE'
        elif classification['class']=='ERROR':
            reason='ERROR'
        elif not isinstance(mv,str) or not mv:
            reason='MISSING_MODEL_VERSION'
        elif returned is not None and returned!=mv:
            reason='MODEL_VERSION_CHANGED'
        if returned is None:
            returned=mv
        if reason:
            save(dest/'STOPPED.json',{'reason':reason,'slot_id':row['slot_id'],'last_event_sha256':previous,'decision':'INCONCLUSIVE'})
            return
    save(dest/'COMPLETE.json',{'slots':len(schedule),'last_event_sha256':previous})

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--phase',choices=['pilot','confirmatory'],default='pilot')
    p.add_argument('--live',action='store_true')
    p.add_argument('--zero-cost-project-verified',action='store_true')
    p.add_argument('--authorization',type=Path)
    p.add_argument('--key-file',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if not a.live:
        integrity()
        print('OFFLINE ONLY: %d scheduled requests; no credentials read; no requests sent.' % len(read(ROOT/'schedules'/(a.phase+'.json'))))
        return
    execute(a.phase,a.authorization,a.live,a.zero_cost_project_verified,a.key_file,a.output)

if __name__=='__main__':
    main()
