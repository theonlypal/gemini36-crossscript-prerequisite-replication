"""One-time OFFLINE construction. Refuses to overwrite a completed freeze."""
import platform
import sys
from collections import Counter
from pathlib import Path
import numpy
import scipy
import regex
from common import ROOT, read, save, sha, encoded

def build():
    if (ROOT / 'freeze_manifest.json').exists():
        raise SystemExit('Already frozen. Use verify.py; do not regenerate in place.')
    gate = read(ROOT / 'sources/gpt-5.4-shrt-prerequisite-gate-runner/prompts.json')
    reassigned = read(ROOT / 'sources/gpt-5.4-shrt-prerequisite-reassignment-runner/prompts.json')
    for repo, prompts in [('gate', gate), ('reassignment', reassigned)]:
        original = read(ROOT / ('sources/gpt-5.4-shrt-prerequisite-' + repo + '-runner/unicode_manifest.json'))
        for key, text in prompts.items():
            if sha(text.encode()) != original[key]['sha256']:
                raise ValueError('Source Unicode mismatch: ' + key)
    for k in ['S1', 'P1', 'P0', 'HE', 'T1', 'T0']:
        assert gate[k] == reassigned[k]
    assert sha(gate['S1'].encode()) == 'eeedf9deec1d8c46276f0d9cf8d11f64345c33a7d4708d60fb16d4b1c8ef7ca1'
    assert sha(gate['S0'].encode()) == 'dc0f686b011f39e6febd79b7bb800bdcce5f8b27f53a7480b7f0865ca66cc174'
    prompts = dict(S1=gate['S1'], S_no_rule=gate['S0'], S_reassigned=reassigned['S0'], P1=gate['P1'], P0=gate['P0'])
    targets = {k: gate[k] for k in ['T1', 'T0', 'HE']}
    targets.update(GEMINI_ORIGINAL='\u05e9\u05b8\u05c1\u0631\u05b0\u05d8', SHART=gate['P1'], SHAMS=gate['P0'])
    save(ROOT / 'prompts.json', prompts)
    save(ROOT / 'targets.json', targets)
    save(ROOT / 'unicode_manifest.json', {k: {'literal': v, 'codepoints': ['U+%04X' % ord(c) for c in v], 'utf8_hex': v.encode().hex(), 'bytes': len(v.encode()), 'sha256': sha(v.encode())} for k, v in dict(prompts, **targets).items()})
    cells = dict(A=['S1','P1'], B=['S1','P0'], C=['S_no_rule','P1'], D=['S_no_rule','P0'], E=['S1','P1'], F=['S1','P0'], G=['S_reassigned','P1'], H=['S_reassigned','P0'])
    config = {'candidateCount': 1, 'maxOutputTokens': 8192, 'thinkingConfig': {'thinkingLevel': 'MINIMAL', 'includeThoughts': False}}
    protocol = {
        'author': 'Sharthok Rayan Pal', 'preparation_date': '2026-10-12', 'version': '1.0.0',
        'model': 'gemini-3.6-flash', 'endpoint': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent',
        'generationConfig': config, 'cells': cells, 'primary': 'NSTOP = V0 + V2',
        'phases': {'pilot': {'n_per_cell': 5, 'seed': 'rayan-pal-gemini3-crossscript-pilot-2026-10-12', 'inference': 'descriptive only'}, 'confirmatory': {'n_per_cell': 200, 'seed': 'rayan-pal-gemini3-crossscript-confirmatory-2026-10-12', 'inference': 'analysis_plan.md'}},
        'schedule_algorithm': 'Sort by SHA256(UTF8(seed + | + cell + | + decimal repetition)); ties by cell and repetition. Saved schedules authoritative.',
        'concurrency': 1, 'automatic_retries': 0, 'timeout_seconds': 600,
        'omitted': ['temperature','topP','topK','seed','stopSequences','tools','toolConfig','safetySettings','responseSchema','responseMimeType','cachedContent'],
        'normalization': 'none', 'stop_policy': 'Stop on ERROR, MODEL_UNAVAILABLE, missing/different returned modelVersion within a phase, or integrity failure. Preserve all earlier outcomes; no retries/resume.',
        'model_identity': 'The requested model identifier is not a cryptographic weight pin. Require nonempty modelVersion; report all versions and stop if it changes within phase. No claims of matching March weights.',
        'exclusions': 'SAFETY, REFUSAL and TOOL retained in denominator as non-NSTOP; ERROR prevents confirmation.',
        'live_authorization': 'Separate phase-specific operator authorization, published frozen commit/tag, and verified zero-cost project required; never inferred from this freeze.'
    }
    save(ROOT / 'protocol.json', protocol)
    (ROOT / 'requests').mkdir(exist_ok=True)
    for cell, (s, p) in cells.items():
        body = {'systemInstruction': {'parts': [{'text': prompts[s]}]}, 'contents': [{'role': 'user','parts': [{'text': prompts[p]}]}], 'generationConfig': config}
        (ROOT / 'requests' / (cell + '.json')).write_bytes(encoded(body))
    (ROOT / 'schedules').mkdir(exist_ok=True)
    for phase, spec in protocol['phases'].items():
        trials = [{'cell': cell,'repetition': rep} for cell in cells for rep in range(1,spec['n_per_cell']+1)]
        trials.sort(key=lambda r: (sha((spec['seed']+'|'+r['cell']+'|'+str(r['repetition'])).encode()), r['cell'], r['repetition']))
        for i, row in enumerate(trials,1):
            row.update(slot_id='%s-%04d' % (phase,i), request_sha256=sha((ROOT/'requests'/(row['cell']+'.json')).read_bytes()))
        save(ROOT / 'schedules' / (phase+'.json'), trials)
        assert Counter(r['cell'] for r in trials) == Counter({c:spec['n_per_cell'] for c in cells})
    provenance = read(ROOT/'source_manifest.json')
    for row in provenance['sources']:
        row['sha256'] = sha((ROOT/row['path']).read_bytes())
    save(ROOT/'source_manifest.json', provenance)
    save(ROOT/'environment.json', {'python': sys.version, 'platform': platform.platform(), 'numpy': numpy.__version__, 'scipy': scipy.__version__, 'regex': regex.__version__, 'unicode_properties': 'regex==2025.11.3; Unicode 17.0.0', 'network_tested': False})
    files = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(ROOT.rglob('*')) if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.name != '.DS_Store'}
    save(ROOT/'freeze_manifest.json', {'version':'1.0.0', 'tag':'v1.0.0-preregistered', 'files':files})
    (ROOT/'SHA256SUMS.txt').write_text(''.join(d+'  '+p+'\n' for p,d in files.items())+sha((ROOT/'freeze_manifest.json').read_bytes())+'  freeze_manifest.json\n', encoding='utf-8')
    print('OFFLINE freeze created; 40 pilot slots, 1600 confirmatory slots. No requests sent.')

if __name__ == '__main__':
    build()
