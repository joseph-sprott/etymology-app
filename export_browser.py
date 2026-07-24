"""
Precompute recursive etymology chains for every English word and export a
compact JSON the browser page can use directly (no Python at runtime).

Output shape (words.json):
{
  "buckets": { "<iso>": "<bucket>", ... },        # from buckets.py
  "words": {
     "<word>": {"p": "<proximate_iso>|null",
                "d": "<deepest_iso>|null",
                "chain": ["<iso>", ...]}           # foreign donors, prox->deep
  }
}
The browser applies the same proximate/deepest + bucket logic as the Python side.
"""
import json, sys
sys.path.insert(0, ".")
from buckets import CODE_TO_BUCKET, bucket_for

RAW = "/usr/local/lib/python3.12/dist-packages/ety/data/etymologies.json"
ENGLISH_STAGES = {"ang", "enm", "eng"}

data = json.load(open(RAW))

def hops(word, lang):
    """One level of ancestors: list of (word, lang)."""
    entry = data.get(lang, {}).get(word)
    if not entry:
        return []
    out = []
    for h in entry:
        for w, l in h.items():
            out.append((w, l))
    return out

def full_chain(word, lang, seen=None, depth=0):
    """Recursively walk ancestors, returning ordered list of (word,lang)."""
    if seen is None:
        seen = set()
    key = (word, lang)
    if key in seen or depth > 25:
        return []
    seen.add(key)
    result = []
    for w, l in hops(word, lang):
        result.append((w, l))
        result.extend(full_chain(w, l, seen, depth + 1))
    return result

words_out = {}
eng = data.get("eng", {})
for i, word in enumerate(eng):
    chain = full_chain(word, "eng")
    # foreign donors only, in order proximate -> deepest
    foreign = [l for (_w, l) in chain if l not in ENGLISH_STAGES]
    english_stage = None
    for (_w, l) in chain:
        if l in ENGLISH_STAGES:
            english_stage = l  # deepest english stage seen
    if foreign:
        p, dd = foreign[0], foreign[-1]
        words_out[word] = {"p": p, "d": dd, "chain": foreign}
    elif english_stage:
        words_out[word] = {"p": english_stage, "d": english_stage, "chain": []}
    # else: no data at all -> omit (browser treats missing as Unknown)

out = {
    "buckets": CODE_TO_BUCKET,
    "words": words_out,
}
json.dump(out, open("words.json", "w"), ensure_ascii=False)
print("exported words:", len(words_out))
import os
print("file size MB:", round(os.path.getsize("words.json") / 1e6, 2))
