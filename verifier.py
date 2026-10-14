"""WC-T07 prototype verifier. Execute only in an appropriate isolated runner.

Timeouts and resource limits are NOT a filesystem/network security sandbox.
The present local self-check executes known fixtures and the inspected M10 only.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import tempfile
import time
import unicodedata

ROOT = Path(__file__).resolve().parent
MAX_TEXT_BYTES = 1_000_000
COMPILER_STANDARD = 'gnu11'

def norm(s: str) -> str:
    s = s.replace('’', "'").replace('‘', "'")
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return s.casefold()

def clean(s: str) -> str:
    return ' '.join(norm(s).split())

def expected_from_input(text: str) -> dict:
    lines = text.splitlines()
    if len(lines) < 8 or any(not x for x in lines[:7]):
        raise ValueError('The fixture must have seven candidate lines and votes directly after them.')
    names = lines[:7]
    votes = [int(v) for v in ' '.join(lines[7:]).split()]
    counts = [votes.count(i) for i in range(1,8)]
    return {'candidate_names': names, 'votes': votes,
        'invalid_values': [v for v in votes if not 1 <= v <= 7],
        'total':len(votes), 'valid':sum(counts), 'invalid':len(votes)-sum(counts),
        'scores':counts, 'winners':[n for n,c in zip(names,counts) if c==max(counts)]}

def assess_invalid_list(raw_lines: list[str], gold: dict) -> dict:
    """Conservative list classification, separate from the main format rubric.

    Parse whole integer tokens, never substring matches or summary counts.
    Known alternate list formats prove presence, but fail the frozen output
    format requirement. Unknown text is REVIEW, not absence.
    Explicit list lines are recognized anywhere; relocation is a format
    deviation. Unknown pre-table text cannot be silently called absence.
    """
    values=[]; alternate=False; unknown=[]; found=False; after_table=False; indices=[]
    for index,raw in enumerate(raw_lines):
        line=clean(raw)
        if not line: continue
        if re.fullmatch(r'candidats?\s+scores?',line):
            after_table=True;continue
        if re.fullmatch(r"nombre\s+(?:d\s*'\s*electeurs|de\s+votes\s+(?:valides|annules))\s*:\s*[+-]?\d+",line):
            continue
        canonical=re.fullmatch(r'vote\s+invalide\s*:\s*([+-]?\d+)',line)
        if canonical:
            found=True;alternate=alternate or after_table;values.append(int(canonical[1]));indices.append(index);continue
        alternate_match=re.fullmatch(r'(votes?\s+invalides?|invalid\s+votes?)\s*:?\s*([+-]?\d+(?:(?:\s*,\s*|\s+)[+-]?\d+)*)',line)
        if alternate_match:
            found=True;alternate=True
            values.extend(int(x) for x in re.findall(r'[+-]?\d+',alternate_match[2]))
            indices.append(index)
        else:
            known_body=after_table and (re.fullmatch(r'les\s+gagnants?\s*:',line)
                or line in {clean(n) for n in gold['candidate_names']}
                or any(re.fullmatch(re.escape(clean(n)).replace(r'\ ',r'\s+')+r'\s+[+-]?\d+',line) for n in gold['candidate_names']))
            if not known_body:unknown.append(raw)
    base={'expected':gold['invalid_values'],'observed':values,
          'format_deviation_observed':alternate,'unrecognized_lines':unknown,
          'recognized_line_indices':indices,'list_shaped_line_observed':found}
    if unknown:
        return {**base,'status':'NOT_ADJUDICATED','presence_observed':True if found else None,
                'reason':'Unknown pre-table text may contain or qualify a list.'}
    if not found:
        return {**base,'status':'LIST_ABSENT','presence_observed':False}
    if len(values)==1 and values[0]==gold['invalid'] and values[0] not in gold['invalid_values']:
        return {**base,'status':'LIST_REPLACED_BY_COUNT','presence_observed':False,
                'count_substitution_signature':True,
                'reason':'The sole listed number equals the invalid-vote count and is not an invalid value. Signature, not proof of how the program computed it.'}
    if Counter(values)!=Counter(gold['invalid_values']):
        return {**base,'status':'LIST_VALUES_MISMATCH','presence_observed':True}
    if alternate:
        return {**base,'status':'LIST_PRESENT_FORMAT_DEVIATION','presence_observed':True}
    return {**base,'status':'PASS','presence_observed':True}

def assess_output(text: str, gold: dict) -> dict:
    """French example labels are accepted accent/case/whitespace insensitively.

    Unrecognized report structure is REVIEW, not an asserted model failure.
    Score alignment is independent from content and may itself require review.
    """
    raw_lines = text.splitlines()
    lines = [norm(x) for x in raw_lines]
    normalized = [clean(x) for x in raw_lines]
    details = []
    invalid_list = assess_invalid_list(raw_lines,gold)
    target_ok = invalid_list['status']=='PASS'
    list_content_ok=invalid_list['status'] in ('PASS','LIST_PRESENT_FORMAT_DEVIATION')
    recognized_list_lines=set(invalid_list['recognized_line_indices'])
    summaries = {}
    structural = []
    for key, pattern in [
        ('total',r"nombre\s+d\s*'\s*electeurs"),
        ('valid',r'nombre\s+de\s+votes\s+valides'),
        ('invalid',r'nombre\s+de\s+votes\s+annules')]:
        matches=[]
        for line in lines:
            m=re.fullmatch(r'\s*'+pattern+r'\s*:\s*([+-]?\d+)\s*',line)
            if m: matches.append(int(m[1]))
        if len(matches)!=1: structural.append(f'{key}: missing, repeated or unrecognized label')
        else: summaries[key]=matches[0]
    header_indices=[i for i,x in enumerate(normalized) if re.fullmatch(r'candidats?\s+scores?',x)]
    winner_indices=[i for i,x in enumerate(normalized) if re.fullmatch(r'les\s+gagnants?\s*:',x)]
    table={}; score_columns=[]; header_column=None; observed_winners=[]
    if len(header_indices)!=1 or len(winner_indices)!=1 or header_indices[0]>=winner_indices[0]:
        structural.append('candidate/winner sections missing, repeated or out of order')
    else:
        h,w=header_indices[0],winner_indices[0]
        header_match=re.search(r'scores?\s*$',norm(raw_lines[h]).expandtabs(8))
        if header_match: header_column=header_match.start()
        name_patterns={clean(n):re.compile(r'^\s*'+re.escape(clean(n)).replace(r'\ ',r'\s+')+r'\s+([+-]?\d+)\s*$') for n in gold['candidate_names']}
        for i in range(h+1,w):
            if i in recognized_list_lines:continue
            if not normalized[i]: continue
            matched=False
            for name,pattern in name_patterns.items():
                m=pattern.fullmatch(lines[i])
                if m:
                    if name in table: structural.append('repeated candidate row: '+name)
                    table[name]=int(m[1]);matched=True
                    col=re.search(r'[+-]?\d+\s*$',raw_lines[i].expandtabs(8))
                    if col: score_columns.append(col.start())
                    break
            if not matched: structural.append('unrecognized candidate row: '+raw_lines[i][:100])
        if set(table)!=set(name_patterns): structural.append('missing candidate rows')
        observed_winners=[clean(raw_lines[i]) for i in range(w+1,len(raw_lines)) if clean(raw_lines[i]) and i not in recognized_list_lines]
    if structural:
        return {'status':'REVIEW_REQUIRED','reason':'OUTPUT_SCHEMA_UNRECOGNIZED',
            'invalid_list':{**invalid_list,'status':'NOT_ADJUDICATED','reason':'Report structure requires review.'},
            'details':structural,'raw_output':text}
    checks={key:summaries[key]==gold[key] for key in ('total','valid','invalid')}
    checks['candidate_scores']=all(table[clean(n)]==s for n,s in zip(gold['candidate_names'],gold['scores']))
    checks['winners']=Counter(observed_winners)==Counter(clean(x) for x in gold['winners'])
    others_ok=all(checks.values())
    # All fixture scores are one digit. Exact column equality evaluates the requested alignment.
    alignment_ok=len(score_columns)==7 and len(set(score_columns))==1
    heading_alignment=(alignment_ok and header_column==score_columns[0])
    if not target_ok: details.append('Invalid-value list classification: '+invalid_list['status'])
    if not others_ok: details.append('Other recognized requirements are wrong.')
    if not alignment_ok: details.append('Score positions are not aligned in the plain-text file.')
    contract_pass=target_ok and others_ok
    semantic_pass=None if invalid_list['status']=='NOT_ADJUDICATED' else list_content_ok and others_ok
    if invalid_list['status']=='NOT_ADJUDICATED': status='REVIEW_REQUIRED'
    elif not others_ok: status='FAIL_OTHER_REQUIREMENT'
    elif invalid_list['status']=='LIST_ABSENT': status='FAIL_LIST_ABSENT'
    elif invalid_list['status']=='LIST_REPLACED_BY_COUNT': status='FAIL_LIST_REPLACED_BY_COUNT'
    elif invalid_list['status']=='LIST_VALUES_MISMATCH': status='FAIL_LIST_VALUES_MISMATCH'
    elif invalid_list['status']=='LIST_PRESENT_FORMAT_DEVIATION': status='FAIL_LIST_FORMAT'
    elif not alignment_ok: status='FAIL_ALIGNMENT'
    else: status='PASS'
    return {'status':status,'content_pass':contract_pass,'semantic_content_pass':semantic_pass,
        'content_pass_note':'Compatibility field: strict M1 contract including recognized list format. Semantic content is separate.',
        'all_required_pass':contract_pass and alignment_ok,
        'invalid_list':invalid_list,
        'other_requirements':checks,'alignment':{'status':'PASS' if alignment_ok else 'FAIL',
            'score_columns_zero_based':score_columns,'header_score_column_zero_based':header_column,
            'header_matches_score_column':heading_alignment,
            'header_note':'diagnostic only; M7 does not fix the header column'},'details':details,'raw_output':text}

def extract_c(response: str) -> str:
    if len(response.encode('utf-8'))>MAX_TEXT_BYTES: raise ValueError('Response too large.')
    fences=re.findall(r'```([^\n`]*)\n(.*?)```',response,re.S)
    candidates=[body for label,body in fences if label.strip().casefold() in ('c','') and re.search(r'\bmain\s*\(',body)]
    if len(candidates)==1: return candidates[0]
    if len(candidates)>1: raise ValueError('Multiple candidate C programs; human selection required.')
    if not fences and re.search(r'^\s*#\s*include',response) and re.search(r'\bmain\s*\(',response):return response
    raise ValueError('No unique complete C program found; no automatic guessing.')

def _limits(cpu_seconds: int):
    resource.setrlimit(resource.RLIMIT_CPU,(cpu_seconds,cpu_seconds))
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024*1024,4*1024*1024))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def _run(command: list[str],cwd: Path,timeout: float,cpu_seconds: int) -> dict:
    with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
        proc=subprocess.Popen(command,cwd=cwd,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
            start_new_session=True,preexec_fn=lambda:_limits(cpu_seconds),env={**os.environ,'LC_ALL':'C'})
        timed_out=False
        try: proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        stdout.seek(0);stderr.seek(0)
        return {'returncode':proc.returncode,'timed_out':timed_out,
            'stdout':stdout.read(65536).decode('utf-8','replace'),
            'stderr':stderr.read(65536).decode('utf-8','replace')}

def environment_probe() -> dict:
    compiler=shutil.which('gcc')
    if not compiler:return {'status':'ERROR_ENVIRONMENT','reason':'gcc missing'}
    with tempfile.TemporaryDirectory(prefix='wct07_probe_') as td:
        p=Path(td);(p/'probe.c').write_text('int main(void){return 0;}\n')
        compiler_version=_run([compiler,'--version'],p,3,2)['stdout'].splitlines()[0]
        comp=_run([compiler,'-std='+COMPILER_STANDARD,'probe.c','-o','probe'],p,10,8)
        if comp['returncode']!=0 or comp['timed_out']:return {'status':'ERROR_ENVIRONMENT','reason':'known C fixture cannot compile','diagnostic':comp}
        run=_run([str(p/'probe')],p,3,2)
        if run['returncode']!=0 or run['timed_out']:return {'status':'ERROR_ENVIRONMENT','reason':'known executable cannot run','diagnostic':run}
    return {'status':'READY_LOCAL_C','gcc':compiler,'gcc_version':compiler_version,
            'compiler_standard':COMPILER_STANDARD,'security_isolation':'NOT PROVIDED by this verifier'}

def evaluate_c(code: str,input_text: str|None=None) -> dict:
    """Run inspected code; production runner isolation must be supplied separately."""
    start=time.perf_counter()
    probe=environment_probe()
    if probe['status']!='READY_LOCAL_C':return probe
    if input_text is None:input_text=(ROOT/'votes.txt').read_text(encoding='utf-8')
    gold=expected_from_input(input_text)
    with tempfile.TemporaryDirectory(prefix='wct07_eval_') as td:
        p=Path(td);(p/'votes.txt').write_text(input_text,encoding='utf-8');(p/'candidate.c').write_text(code,encoding='utf-8')
        compile_result=_run([probe['gcc'],'-std='+COMPILER_STANDARD,'-O0','-Wall','-Wextra','candidate.c','-o','candidate'],p,10,8)
        if compile_result['timed_out'] or compile_result['returncode']!=0:
            result={'status':'FAIL_CODE_COMPILE','compile':compile_result,'invalid_list':{'status':'NOT_ADJUDICATED'}}
        else:
            run=_run([str(p/'candidate')],p,3,2)
            if run['timed_out'] or run['returncode']!=0:
                result={'status':'FAIL_CODE_RUNTIME','runtime':run,'invalid_list':{'status':'NOT_ADJUDICATED'}}
            elif not (p/'resultats.txt').is_file():
                result={'status':'FAIL_OUTPUT_FILE','runtime':run,'invalid_list':{'status':'NOT_ADJUDICATED'}}
            elif (p/'resultats.txt').stat().st_size>MAX_TEXT_BYTES:
                result={'status':'REVIEW_REQUIRED','reason':'Output too large','invalid_list':{'status':'NOT_ADJUDICATED'}}
            else:
                try: text=(p/'resultats.txt').read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    result={'status':'REVIEW_REQUIRED','reason':'Output encoding is not UTF-8','invalid_list':{'status':'NOT_ADJUDICATED'}}
                else:result=assess_output(text,gold)
                result['compile']=compile_result
            result['runtime']=run
    result['local_elapsed_seconds']=round(time.perf_counter()-start,6)
    result['environment']=probe
    result['source_sha256']=hashlib.sha256(code.encode('utf-8')).hexdigest()
    return result

def evaluate_response(response: str) -> dict:
    try:code=extract_c(response)
    except ValueError as exc:return {'status':'REVIEW_REQUIRED','reason':str(exc),'invalid_list':{'status':'NOT_ADJUDICATED'}}
    return evaluate_c(code)

def evaluate_suite_c(code: str,condition: str='A') -> dict:
    """Same program, same grader, separate temporary execution for each input.

    Common primary score is M1 content. M7 alignment is separately required
    for A/B; C does not receive M7. Hidden_2 is diagnostic only.
    """
    if condition not in ('A','B','C'):raise ValueError('Unknown condition')
    files={'original':'votes.txt','hidden_1':'votes_hidden_1.txt','hidden_2':'votes_hidden_2.txt','hidden_zero':'votes_hidden_zero.txt'}
    cases={k:evaluate_c(code,(ROOT/f).read_text(encoding='utf-8')) for k,f in files.items()}
    main=[cases[k] for k in ('original','hidden_1')]
    if any(r['status'].startswith('ERROR_') for r in main):status='ERROR_ENVIRONMENT'
    elif any(r['status']=='REVIEW_REQUIRED' for r in main):status='REVIEW_REQUIRED'
    elif all(r.get('content_pass',False) for r in main):status='PASS'
    else:status='FAIL'
    targets=[r.get('invalid_list',{}).get('status','NOT_ADJUDICATED') for r in main]
    target_failure=True if any(t in ('LIST_ABSENT','LIST_REPLACED_BY_COUNT','LIST_VALUES_MISMATCH','LIST_PRESENT_FORMAT_DEVIATION') for t in targets) else (False if targets==['PASS','PASS'] else None)
    omission=True if any(t in ('LIST_ABSENT','LIST_REPLACED_BY_COUNT') for t in targets) else (False if all(t in ('PASS','LIST_VALUES_MISMATCH','LIST_PRESENT_FORMAT_DEVIATION') for t in targets) else None)
    content_results=[r.get('semantic_content_pass') for r in main]
    semantic_primary=False if False in content_results else (True if content_results==[True,True] else None)
    alignment_pass=all(r.get('alignment',{}).get('status')=='PASS' for r in main)
    full_pass=status=='PASS' and (condition=='C' or alignment_pass)
    return {'status':status,'condition':condition,'primary_pass':status=='PASS',
        'target_failure_observed':target_failure,
        'target_failure_note':'Compatibility field: list contract failure including format, never synonymous with omission.',
        'list_omission_observed':omission,
        'list_replaced_by_count_observed':'LIST_REPLACED_BY_COUNT' in targets,
        'list_values_mismatch_observed':'LIST_VALUES_MISMATCH' in targets,
        'list_format_deviation_observed':any(r.get('invalid_list',{}).get('format_deviation_observed',False) for r in main),
        'cases':cases,
        'semantic_primary_pass':semantic_primary,
        'original_target_status':cases['original'].get('invalid_list',{}).get('status','NOT_ADJUDICATED'),
        'hidden_1_target_status':cases['hidden_1'].get('invalid_list',{}).get('status','NOT_ADJUDICATED'),
        'alignment_required':condition!='C','alignment_primary_inputs_pass':alignment_pass,
        'all_condition_requirements_pass':full_pass,
        'hidden_2_diagnostic_pass':bool(cases['hidden_2'].get('content_pass',False)),
        'hidden_zero_diagnostic_pass':bool(cases['hidden_zero'].get('content_pass',False)),
        'claim_limit':'Two fixed primary inputs, not proof of correctness for all possible inputs.'}

def evaluate_suite_response(response: str,condition: str='A') -> dict:
    try:code=extract_c(response)
    except ValueError as exc:
        return {'status':'REVIEW_REQUIRED','condition':condition,'primary_pass':False,
                'target_failure_observed':None,'reason':str(exc),'cases':{}}
    return evaluate_suite_c(code,condition)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code',type=Path)
    parser.add_argument('--response',type=Path)
    parser.add_argument('--execute-reviewed-code',action='store_true',help='Confirm code has been reviewed and runner isolation is suitable.')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--condition',choices=('A','B','C'),default='A')
    args=parser.parse_args()
    if not args.execute_reviewed_code:parser.error('Execution requires --execute-reviewed-code; resource limits are not a security sandbox.')
    if (args.code is None)==(args.response is None):parser.error('Provide exactly one of --code or --response.')
    text=(args.code or args.response).read_text(encoding='utf-8')
    result=evaluate_suite_c(text,args.condition) if args.code else evaluate_suite_response(text,args.condition)
    payload=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(payload,encoding='utf-8')
    print(payload)
