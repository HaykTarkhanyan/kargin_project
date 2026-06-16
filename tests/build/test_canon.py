from scripts.kargin_build.canon import (
    canonicalize_actors, canonicalize_location, canonicalize_languages,
)

ALLOW = {"Հայկո", "Մկո", "Հասմիկ", "Լևոն", "Անդո", "Քրիստինե", "Աշոտ", "Արմինե"}
TYPOS = {"Հակյո": "Հայկո", "ՄԿո": "Մկո"}


def test_actors_comma_separated():
    actors, roles = canonicalize_actors("Հայկո, Մկո", ALLOW, TYPOS)
    assert actors == ["Հայկո", "Մկո"] and roles == []

def test_actors_space_joined_no_comma():
    actors, _ = canonicalize_actors("Հայկո Մկո", ALLOW, TYPOS)
    assert actors == ["Հայկո", "Մկո"]

def test_actors_typo_mapped():
    actors, _ = canonicalize_actors("Հակյո, ՄԿո", ALLOW, TYPOS)
    assert actors == ["Հայկո", "Մկո"]

def test_actors_role_word_goes_to_roles_not_actors():
    actors, roles = canonicalize_actors("Հայկո, ոստիկան", ALLOW, TYPOS)
    assert actors == ["Հայկո"] and roles == ["ոստիկան"]

def test_actors_two_word_role_with_comma_not_split():
    # comma present, so we do NOT space-split — "փոքր երեխա" stays one token
    actors, roles = canonicalize_actors("Հայկո, փոքր երեխա", ALLOW, TYPOS)
    assert actors == ["Հայկո"] and roles == ["փոքր երեխա"]

def test_actors_empty():
    assert canonicalize_actors("", ALLOW, TYPOS) == ([], [])
    assert canonicalize_actors(None, ALLOW, TYPOS) == ([], [])

def test_location_known_passes_through():
    assert canonicalize_location("Տուն") == "Տուն"

def test_location_noise_bucketed_to_other():
    assert canonicalize_location("Այլ(գրեք ավելացնենք)") == "Այլ"
    assert canonicalize_location("") == "Այլ"

def test_languages_split_and_normalized():
    assert canonicalize_languages("հայերեն+ռուսերեն") == ["հայերեն", "ռուսերեն"]
    assert canonicalize_languages("այլ") == ["այլ"]
    assert canonicalize_languages("") == []
