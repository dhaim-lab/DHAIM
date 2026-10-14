from pathlib import Path
import argparse,collections,hashlib,json
p=argparse.ArgumentParser(description='Offline replay using public name-substituted fixtures, no API calls')
p.add_argument('--execute-reviewed-code',action='store_true')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
if not a.execute_reviewed_code:p.error('Use an isolated disposable Linux environment with GCC, no secrets/network/host mounts')
if a.output.exists():p.error('Output already exists; refusing to overwrite')
root=Path(__file__).resolve().parent
manifest=json.loads((root/'SHA256_MANIFEST.json').read_text(encoding='utf-8'))
for name,digest in manifest.items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
import verifier
rows=[]
for row in json.loads((root/'program_index.json').read_text(encoding='utf-8')):
    code=(root/row['program']).read_bytes()
    assert hashlib.sha256(code).hexdigest()==row['program_sha256']
    result=verifier.evaluate_suite_c(code.decode('utf-8'),row['condition'])
    rows.append({'run_id':row['run_id'],'result':result,'original_automatic_status':row['original_automatic_status'],
        'status_matches_original':result['status']==row['original_automatic_status'],
        'replay_kind':'PUBLIC_NAME_SUBSTITUTED_FIXTURES_NOT_EXACT_ORIGINAL_REPLAY'})
summary={'counts':dict(collections.Counter(r['result']['status'] for r in rows)),
    'all_statuses_match_original':all(r['status_matches_original'] for r in rows),
    'independent_gate':'PASS' if all(r['status_matches_original'] for r in rows) else 'CHANGES_REQUIRED',
    'rows':rows}
a.output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='rows'},indent=2))
