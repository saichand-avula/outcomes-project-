import json,sys,collections as C
import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from pl.risk_rules import rule_categories, CATEGORIES
from pl.transcript import parse
def run(sp, show=0):
    tp=C.Counter(); fp=C.Counter(); fn=C.Counter(); ex=C.defaultdict(list)
    for l,t in zip(open(f'../data/gold/{sp}.jsonl'),open(f'../data/sft/{sp}.jsonl')):
        g=json.loads(l); s=json.loads(t); tg=g['target']
        if tg['not_applicable']['is_na']: continue
        gold={f['category'] for f in tg['risk_flags']}; hits=rule_categories(parse(s['transcript'])); pred=set(hits)
        for c in CATEGORIES:
            tp[c]+=(c in gold and c in pred); fp[c]+=(c in pred and c not in gold); fn[c]+=(c in gold and c not in pred)
            if c in pred and c not in gold: ex[('fp',c)].append((g['call_id'],hits[c][0]['rule'],hits[c][0]['quote'][:100]))
            if c in gold and c not in pred: ex[('fn',c)].append((g['call_id'],[f['quote'][:80] for f in tg['risk_flags'] if f['category']==c][:1]))
    print(sp)
    for c in CATEGORIES:
        p=tp[c]/max(1,tp[c]+fp[c]); r=tp[c]/max(1,tp[c]+fn[c]); print(f'  {c:22} P={p:.2f} R={r:.2f}  tp={tp[c]} fp={fp[c]} fn={fn[c]}')
    return ex
if __name__=='__main__':
    ex=run(sys.argv[1] if len(sys.argv)>1 else 'train')
    import random; random.seed(1)
    for k,v in ex.items():
        if len(sys.argv)>2 and k[0]==sys.argv[2]:
            print('==',k,len(v))
            for x in random.sample(v,min(6,len(v))): print('   ',x)
