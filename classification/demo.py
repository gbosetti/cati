import json

full_bigrams = {}
bigrams = [(('☠️FDL', '☠️FDL'), 2), (('☠️FDL', '☠️FDL'), 1), (('.☠️FDL', '☠️FDL'), 1), (('☠️FDL', '☠️'), 1), (('☠️', 'Bad'), 1), (('Bad', 'woman'), 1), (('woman', 'know'), 1)]


for k, v in bigrams:
    try:
        full_bigrams[k].append(v)
    except KeyError:
        full_bigrams[k] = [v]

partial_bigrams = {k:full_bigrams[k] for k in full_bigrams if len(full_bigrams[k]) > 1}

print(partial_bigrams)

