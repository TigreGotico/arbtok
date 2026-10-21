"""A unit symbol after a number is read whatever case it is written in."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts
from arbtok.util import normalize


@pytest.mark.parametrize("written, spoken", [
    ("1,500 km", "ألف وخمسمئة كيلومتر"),
    ("100,000 KM", "مئة ألف كيلومتر"),
], ids=["1,500 km", "100,000 KM"])
def test_a_grouped_number_before_a_unit_is_read(written, spoken):
    assert normalize_for_tts(written, "ar") == spoken


# A grouping is groups of three digits, so a dot before fewer than three is a decimal
# point even where the language writes its groupings with dots. The German reading of
# a dot-decimal has a defect of its own in the number pass and is pinned as it stands.
@pytest.mark.parametrize("lang, written, spoken", [
    ("fr", "0.5 km", "zéro virgule cinq kilomètres"),
    ("fr", "2.5 km", "deux virgule cinq kilomètres"),
    ("es", "0.5 km", "cero coma cinco kilómetros"),
    ("es", "2.5 km", "dos coma cinco kilómetros"),
    ("pt", "0.5 km", "zero vírgula cinco quilômetros"),
    ("pt", "2.5 km", "dois vírgula cinco quilômetros"),
    ("de", "2.5 km", "zwei Komma fünf null null Kilometer"),
])
def test_a_dot_decimal_is_not_a_grouping(lang, written, spoken):
    assert normalize_for_tts(written, lang) == spoken


# mironik-tts's saudi_voice_agent_profile (src/mironik_tts/text_normalize.py): codes are
# spelled and every digit a code does not claim is kept for the code table.
_SPELLS_CODES = TtsNorm(
    strip_controls=False, spell_out_codes=True, speak_percent=True, keep_code_digits=True,
    phone_shapes=(), phone_regions=(), long_digit_runs=True, phone_prefixes=(),
    identifier_words=(), cardinal_numbers=True, leave_unspeakable_numbers=True,
    oblique_numbers=True, space_fused_hundreds=True, dialect_numbers=False, number_forms=(),
    spoken_forms=False, canonical_unicode=False, lexicon=(),
)


@pytest.mark.parametrize("written, spoken", [
    ("1.5T", "واحد فاصلة خمسة تِي"),
    ("2.5T", "اثنين فاصلة خمسة تِي"),
], ids=["1.5T", "2.5T"])
def test_a_decimal_glued_to_a_code_keeps_its_decimal_reading(written, spoken):
    """No space carries the fraction's last digit apart from the code that follows it: a
    code's left boundary used to start right after the decimal mark, at "5T", and steal
    the fraction's digit into the code's own reading, leaving the "." as a bare literal
    ("واحد.فَيْفْ تِي"). The decimal now reads its own digit and the code spells its own
    letters, whether or not a space separates the two."""
    assert normalize_for_tts(written, "ar", _SPELLS_CODES) == spoken


@pytest.mark.parametrize("written, spoken", [
    ("1.5 T", "واحد فاصلة خمسة T"),
    ("1.5%", "واحد فاصلة خمسة في المئة"),
    ("X5", "إِكْسْ فَيْفْ"),
    ("G70", "جِي سِفَنْ زِيرُو"),
], ids=["1.5 T", "1.5%", "X5", "G70"])
def test_a_decimal_glued_to_a_code_changes_nothing_else(written, spoken):
    """A space before the code, a percent sign, and a code with no decimal in front of it
    read exactly as they did before the code's left boundary learned to refuse a position
    right after a digit's decimal mark."""
    assert normalize_for_tts(written, "ar", _SPELLS_CODES) == spoken


def test_a_decimal_glued_to_a_longer_code_reads_its_own_digit():
    """A two-digit integer part reads the same way a one-digit one does; the rule that
    decided is the decimal reading's own, not the code's."""
    assert normalize_for_tts("12.5T", "ar", _SPELLS_CODES) == "اثني عشر فاصلة خمسة تِي"


def test_a_comma_glued_to_a_code_is_not_this_rule():
    """A comma is a thousands grouping mark, not a decimal mark, and this rule does not
    touch it: the code's left boundary still starts right after it, so "1,500T" reads as
    it did before this fix, the code stealing the grouped digits."""
    assert normalize_for_tts("1,500T", "ar", _SPELLS_CODES) == "واحد,فَيْفْ زِيرُو زِيرُو تِي"


@pytest.mark.parametrize("written, spoken", [
    ("1.5TB", "واحد فاصلة خمسة TB"),
    ("3.5KM", "ثلاثة فاصلة خمسة KM"),
    ("0.5KW", "صفر فاصلة خمسة KW"),
], ids=["1.5TB", "3.5KM", "0.5KW"])
def test_a_decimal_glued_to_a_unit_keeps_its_decimal_reading(written, spoken):
    """A capitalised unit is never this rule's to spell, only the fraction's digit is: a
    unit glued straight to its decimal used to be handed back unread, "1.5TB" surviving
    as "واحد.5TB" with the raw digit and the unit's own Latin letters both reaching the
    output. The decimal now reads and the unit is left exactly as the spaced form already
    leaves it, "1.5 TB" reading "واحد فاصلة خمسة TB"."""
    assert normalize_for_tts(written, "ar", _SPELLS_CODES) == spoken


@pytest.mark.parametrize("written", ["1.5T's", "1.5T’s"])
def test_a_decimal_glued_to_a_code_drops_a_possessive_clitic(written):
    """An English possessive right after the glued code is not read: "1.5T's" is "1.5T"
    owning something, not a fifth character to spell, straight or curly apostrophe
    alike."""
    assert normalize_for_tts(written, "ar", _SPELLS_CODES) == "واحد فاصلة خمسة تِي"


@pytest.mark.parametrize("lang, written, spoken", [
    ("ar", "1,000,000 km", "مليون كيلومتر"),
    ("en", "1,000,000 %", "one million per cent"),
], ids=["ar", "en"])
def test_a_number_of_several_groups_is_read_whole(lang, written, spoken):
    assert normalize_for_tts(written, lang) == spoken


@pytest.mark.parametrize("lang, written, spoken", [
    ("ar", "12,5 km", "اثنا عشر فاصلة خمسة km"),
    ("ar", "1,0000 km", "واحد km"),
    ("en", "1,0000 %", "one %"),
], ids=["12,5 km", "1,0000 km", "1,0000 %"])
def test_a_separator_that_forms_no_grouping_leaves_the_number_to_the_number_pass(lang, written, spoken):
    """A shape that is no grouping is not this pass to read, and the match may not begin
    inside it either: the whole number goes to the number pass, which reads a comma
    followed by fewer or by more than three digits as a decimal mark, and the unit is
    left as written. The exact reading is pinned because asserting that a wrong one is
    absent passes on every other wrong one."""
    assert normalize_for_tts(written, lang) == spoken



@pytest.mark.parametrize("written, spoken", [
    ("it is 5 km away", "it is five kilometers away"),
    ("it is 5 KM away", "it is five kilometers away"),
    ("it is 5 Km away", "it is five kilometers away"),
])
def test_a_unit_is_read_in_any_case(written, spoken):
    assert normalize(written, "en") == spoken


@pytest.mark.parametrize("written", ["it weighs 3 Kg", "temperature 20 °c", "it costs 10 EUR or 5 KM"])
def test_no_casing_of_a_symbol_raises(written):
    assert isinstance(normalize(written, "en"), str)
