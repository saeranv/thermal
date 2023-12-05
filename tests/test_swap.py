"""Tests for swap.py"""

import numpy as np
import swap.swap as swap

# Run with
# python -m pytest -rPx ../tests


def test_tokenize():

    token = swap.tokenize("office !! Building - Medium")
    _token = "office_building_medium"
    assert token == _token, token


def test_match_phrases():

    phrases = list(swap.STDTAG_DICT.keys())
    # phrases: ["Office WholeBuilding - Md Office", "Plenum"]

    # Test plenum w/ caps
    query = "Court Plenum"
    phrase = swap.match_phrase(query, phrases)
    _phrase = "Plenum"
    assert phrase == _phrase, phrase

    # Test plenum w/ caps
    query = "FirstFloor_Plenum"
    phrase = swap.match_phrase(query, phrases)
    _phrase = "Plenum"
    assert phrase == _phrase, phrase

    # Test medium office
    query = "custom_office_md_perimeterRms2"
    phrase = swap.match_phrase(query, phrases)
    _phrase = "Office WholeBuilding - Md Office"
    assert phrase == _phrase, phrase





