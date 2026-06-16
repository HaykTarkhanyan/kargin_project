from scripts.kargin_build.stats import (
    co_occurrence, word_counts, bigram_counts, composition, name_mentions, ACTOR_SUFFIXES,
)

def _sk(**kw):
    base = dict(actors=[], text="", textCommon="", location="Այլ", durationSec=120, viewCount=0, seq=1)
    base.update(kw); return base

def test_co_occurrence_counts_pairs_symmetric():
    d = [_sk(actors=["Հայկո", "Մկո"]), _sk(actors=["Հայկո", "Մկո"]), _sk(actors=["Հայկո", "Աշոտ"])]
    actors, m = co_occurrence(d, top=3)
    i, j = actors.index("Հայկո"), actors.index("Մկո")
    assert m[i][j] == 2 and m[j][i] == 2
    assert m[i][i] == 0  # diagonal is zero

def test_word_counts_skips_stopwords_and_short():
    d = [_sk(text="ախպեր ջան բայց ա")]   # "ա" too short, "ջան" len 3 kept, stopwords removed
    wc = dict(word_counts(d, min_len=4))
    assert wc.get("ախպեր") == 1 and "ա" not in wc

def test_bigram_counts():
    d = [_sk(text="ցավդ տանեմ ախպեր"), _sk(text="ցավդ տանեմ")]
    bg = dict(bigram_counts(d))
    assert bg.get("ցավդ տանեմ") == 2

def test_composition_buckets():
    d = [_sk(actors=["Հայկո", "Մկո"]), _sk(actors=["Հայկո"]), _sk(actors=["Հայկո", "Մկո", "Աշոտ"]), _sk(actors=[])]
    c = composition(d)
    assert c == {"duo": 1, "solo": 1, "ensemble": 1, "uncurated": 1}

def test_name_mentions_declension_aware_not_substring():
    # "Անի" must NOT match inside "պատուհանից"; must match "Անիին"
    d = [_sk(text="բարև Անիին"), _sk(text="ընկավ պատուհանից")]
    assert name_mentions("Անի", d) == 1
