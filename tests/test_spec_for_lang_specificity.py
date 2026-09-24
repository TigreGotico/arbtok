"""A more specific language tag never resolves to something less specific.

``ar-EG-x-cairo`` names a place inside Egypt. No spec carries Cairo, so the tag
must read as ``ar-EG`` does, not as MSA: naming the city cannot lose the country.
The same holds for every region and every spec code with a subtag no spec or
dialect alias names appended — private use, a variant, an extension — and for
the underscore spellings.
"""
import pytest
from orthography2ipa import get

from arbtok.dialects import _DIALECT_NAME_ALIASES, lect_code, spec_for_lang, supported_lects

SPECS = [lect.code for lect in supported_lects()]
TOKENS = sorted({c.split("-x-")[-1] for c in SPECS if "-x-" in c} | set(_DIALECT_NAME_ALIASES))
REGIONS = sorted({c.split("-")[1] for c in SPECS if len(c.split("-")) > 1
                  and len(c.split("-")[1]) == 2} | {"SA", "EG", "MA", "ZZ", "US"})

#: Subtags no spec and no alias names. ``unknownplace`` is over eight characters,
#: which langcodes refuses to parse.
UNKNOWN = ["-x-cairo", "-x-unknownplace", "-x-a", "-cairo", "-u-nu-latn"]


def _parents():
    tags = set(SPECS) | {"ar", "ar-Arab"}
    tags |= {f"ar-{r}" for r in REGIONS} | {f"ar-Arab-{r}" for r in REGIONS}
    for token in TOKENS:
        tags |= {f"ar-x-{token}", f"ar-{token}", f"ar-SA-{token}", f"ar-SA-x-{token}"}
    return sorted(tags)


PAIRS = [(parent, parent + suffix) for parent in _parents() for suffix in UNKNOWN]
PAIRS += [(p.replace("-", "_"), c.replace("-", "_")) for p, c in PAIRS]


def _ancestors(code):
    seen = []
    code = get(code).parent
    while code and code not in seen:
        seen.append(code)
        code = get(code).parent
    return seen


def test_cairo_reads_as_egypt():
    assert spec_for_lang("ar-EG-x-cairo") == "ar-EG"
    assert lect_code("ar-EG-x-cairo") == "arz"


@pytest.mark.parametrize("tag,expected", [
    ("ar-SA-x-riyadh", "ar-SA-x-najd"),
    ("ar-SA-x-unknownplace", "ar-SA-x-najd"),
    ("ar-MA-x-unknownplace", "ar-MA"),
    ("ar_EG_x_cairo", "ar-EG"),
    ("ar-EG-cairo", "ar-EG"),
    ("ar-EG-u-nu-latn", "ar-EG"),
    ("ar-SA-x-najd-x-unknownplace", "ar-SA-x-najd"),
    # No Arabic region: the parent is MSA, and so is the tag.
    ("ar-x-unknownplace", "ar"),
    ("ar-x-cairo", "ar"),
    # An unknown region is not forced onto a region it does not name.
    ("ar-ZZ-x-cairo", "ar"),
    ("ar-ZZ-x-unknownplace", "ar"),
    ("en-x-cairo", "ar"),
])
def test_unrecognised_subtags_are_ignored(tag, expected):
    assert spec_for_lang(tag) == expected


@pytest.mark.parametrize("alias", sorted(_DIALECT_NAME_ALIASES))
def test_every_alias_still_names_its_spec(alias):
    token = _DIALECT_NAME_ALIASES[alias]
    target = next(c for c in SPECS if c.endswith(f"-x-{token}"))
    for tag in (f"ar-x-{alias}", f"ar-{alias}", f"ar-SA-{alias}", f"ar-SA-x-{alias}",
                f"ar-x-{alias}-x-unknownplace", f"ar_x_{alias}"):
        assert spec_for_lang(tag) == target, tag


def test_a_subtag_that_names_nothing_changes_nothing():
    wrong = [(p, c, spec_for_lang(p), spec_for_lang(c))
             for p, c in PAIRS if spec_for_lang(c) != spec_for_lang(p)]
    assert not wrong, wrong[:20]


def test_a_more_specific_tag_is_never_less_specific_than_its_parent():
    wrong = [(p, c, spec_for_lang(p), spec_for_lang(c)) for p, c in PAIRS
             if spec_for_lang(c) in _ancestors(spec_for_lang(p))]
    assert not wrong, wrong[:20]
