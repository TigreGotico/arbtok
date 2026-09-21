"""normalize_asr's named bundles reproduce the instruments they name, rule for rule.

Each reference below is written the way the instrument it stands for is written:
a fixed sequence of substitutions, with no flags. A bundle is correct when it and
its reference agree on every string of a corpus built to reach every rule.
"""
import dataclasses
import random
import re
import unicodedata

import pytest

from arbtok import textnorm
from tests.voice_agent import VOICE_AGENT
from arbtok.textnorm import (AsrNorm, TtsNorm, CER_MARKS_FIRST, CER_NORM, CER_NORM_MARKS_FIRST,
                             CER_STRIP, INTELLIGIBILITY_GATE, TRUTH_CHECK,
                             normalize_asr, normalize_for_tts)

_FULL_MARKS = re.compile("[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED\u0640]")
_NARROW_MARKS = re.compile("[\u064B-\u0652\u0640]")
_GATE_MARKS = re.compile("[\u064B-\u0652\u0670\u0653-\u065F\u0640]")
_LETTERS = str.maketrans({"آ": "ا", "أ": "ا", "إ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ئ": "ي", "ؤ": "و"})
_PUNCT = re.compile(r"[^\w\s]")


def ref_truth_check(text):
    if not text:
        return ""
    text = _FULL_MARKS.sub("", unicodedata.normalize("NFC", text)).translate(_LETTERS)
    return re.sub(r"\s+", " ", text).strip()


def ref_cer_strip(text):
    return _NARROW_MARKS.sub("", _PUNCT.sub(" ", text)).split()


def _ref_letter_forms(tokens):
    tokens = [t.translate(_LETTERS) for t in tokens]
    tokens = [t[:-1] if t.endswith("ء") else t for t in tokens]
    return [t for t in tokens if t]


def ref_cer_norm(text):
    return _ref_letter_forms(ref_cer_strip(text))


def ref_cer_marks_first(text):
    text = textnorm._LANGUAGE_WRAPPER.sub(r" \1 ", textnorm._EVENT.sub(" ", text))
    return _PUNCT.sub(" ", _FULL_MARKS.sub("", text)).split()


def ref_cer_norm_marks_first(text):
    return _ref_letter_forms(ref_cer_marks_first(text))


def ref_gate(text):
    text = _GATE_MARKS.sub("", text).translate(_LETTERS)
    return re.sub(r"\s+", " ", re.sub("[^\u0600-\u06FF\\s]", " ", text)).strip()


HAND = [
    "", " ", "مَرْحَبًا بِكُمْ!", "الرَّحْمٰنِ الرَّحِيمِ", "المـــرء", "شيء جزء ء ءء سماء.",
    "أحمد إلى آخر ٱلكتاب مدرسة على شاطئ مؤمن", "١٢٣ و 456 و ۷۸۹", "BMW X5 في الرياض",
    "قال [noise] نعم <laughter> و [[sigh] ثم [00:08] و [01:02:03]",
    "[french: au moins] و [EN: hello there] و <foreign lang=\"en\">hello</foreign>",
    "[foreign: au moins] و [whatever] و (آه) و [موسيقى]", "كلمة\u200Bكلمة\u200F \u202Bنص\u202C \uFEFF",
    "سطر\nسطر\tسطر سطر سطر\x1cسطر", "é é ﻻ ﷲ", "صلى الله عليه وسلم ۖ ۗ ؐ", "ـ َ ُ ِ ّ ْ",
    "هل؟ نعم، لا؛ «نص» ٪ ـ _ snake_case", "İstanbul STRASSE ǅ",
    "السعر خمسة وأربعون ألف ريال", "عندي ثلاثة كتب", "الرقم 0 5 5 3 1 7 9 2 4 5",
]

_ALPHABET = (list("ابتثجحخدذرزسشصضطظعغفقكلمنهويءآأإٱؤئةىپچڤگ") + list("ًٌٍَُِّْ")
             + list("ٰ۪ٓٔؐۖۡـ") + list(" \t\n    ") + list(".,!?؟،؛:-()[]<>\"'_٪")
             + list("0123456789٠١٢٣٤٥٦٧٨٩۰۱۲۳") + list("abcXYZ") + list("\u200B\u200F\u202B\uFEFF")
             + ["[noise]", "<laughter>", "[french: ", "[00:12]", "[foreign]", "]", "ء ", " ء"])


def corpus():
    rng = random.Random(20260920)
    return HAND + ["".join(rng.choice(_ALPHABET) for _ in range(rng.randint(1, 40))) for _ in range(4000)]


CORPUS = corpus()


@pytest.mark.parametrize("bundle, reference, tokens", [
    (TRUTH_CHECK, ref_truth_check, False),
    (CER_STRIP, ref_cer_strip, True),
    (CER_NORM, ref_cer_norm, True),
    (CER_MARKS_FIRST, ref_cer_marks_first, True),
    (CER_NORM_MARKS_FIRST, ref_cer_norm_marks_first, True),
    (INTELLIGIBILITY_GATE, ref_gate, False),
], ids=["truth check", "cer strip", "cer norm", "cer marks first", "cer norm marks first", "intelligibility gate"])
def test_a_bundle_agrees_with_its_instrument_on_every_string(bundle, reference, tokens):
    disagree = [s for s in CORPUS
                if (normalize_asr(s, bundle).split() if tokens else normalize_asr(s, bundle)) != reference(s)]
    assert not disagree, f"{len(disagree)} of {len(CORPUS)} strings differ, first: {disagree[0]!r}"


def test_the_corpus_reaches_every_rule_of_every_reference():
    """A bundle can only be shown equal to its reference on strings the rule touches."""
    for name, rule in (("full marks", _FULL_MARKS), ("punctuation", _PUNCT), ("event", textnorm._EVENT),
                       ("wrapper", textnorm._LANGUAGE_WRAPPER), ("final hamza", re.compile(r"ء(?!\S)"))):
        assert sum(bool(rule.search(s)) for s in CORPUS) >= 50, name
    for letter in "آأإٱةىئؤ":
        assert sum(letter in s for s in CORPUS) >= 50, letter


@pytest.mark.parametrize("flag", [f.name for f in dataclasses.fields(AsrNorm) if f.type is bool or f.type == "bool"])
def test_every_flag_changes_some_output(flag):
    # The order flag only means something once both rules it orders are on.
    base = dict(blank_punctuation=True, strip_harakat=True) if flag == "punctuation_before_marks" else {}
    assert any(normalize_asr(s, **base, **{flag: True}) != normalize_asr(s, **base) for s in CORPUS)


def test_the_package_exports_what_the_documentation_imports():
    import arbtok
    for name in ("AsrNorm", "TtsNorm", "normalize_asr", "normalize_for_tts"):
        assert getattr(arbtok, name) is getattr(textnorm, name) and name in arbtok.__all__


def test_with_nothing_on_the_text_is_returned_as_given():
    assert all(normalize_asr(s) == s for s in CORPUS)


@pytest.mark.parametrize("not_text", [None, float("nan"), 5, b"bytes"], ids=["None", "nan", "int", "bytes"])
def test_what_is_not_text_is_refused_by_both_functions(not_text):
    """A missing reference must not score as an empty one."""
    with pytest.raises(TypeError, match="takes a str"):
        normalize_asr(not_text, CER_NORM)
    with pytest.raises(TypeError, match="takes a str"):
        normalize_for_tts(not_text)


def test_the_legacy_order_breaks_a_pointed_word_and_the_other_order_keeps_it():
    assert normalize_asr("مَرْحَبا", CER_STRIP).split() == ["م", "ر", "ح", "با"]
    assert normalize_asr("مَرْحَبا", CER_MARKS_FIRST).split() == ["مرحبا"]


def test_the_dagger_alif_is_an_extended_mark_not_a_haraka():
    assert normalize_asr("الرحمٰن", strip_harakat=True) == "الرحمٰن"
    assert normalize_asr("الرحمٰن", strip_extended_marks=True) == "الرحمن"


def test_a_flag_overrides_a_bundle_and_the_description_says_so():
    assert normalize_asr("١٢", TRUTH_CHECK) == "١٢"
    assert normalize_asr("١٢", TRUTH_CHECK, fold_digits=True) == "12"
    folded = dataclasses.replace(TRUTH_CHECK, fold_digits=True)
    assert folded.describe() != TRUTH_CHECK.describe()
    assert folded.describe().startswith(f"arbtok-asr-norm {textnorm.ASR_NORM_VERSION}: ")
    assert "fold_digits" in folded.describe() and "fold_digits" not in TRUTH_CHECK.describe()


def test_a_flag_that_does_not_exist_is_refused():
    with pytest.raises(TypeError):
        normalize_asr("نص", strip_everything=True)


def test_the_module_needs_nothing_beyond_the_standard_library_to_import():
    import subprocess, sys
    code = ("import importlib.util, sys; "
            f"spec = importlib.util.spec_from_file_location('textnorm', {textnorm.__file__!r}); "
            "m = importlib.util.module_from_spec(spec); sys.modules['textnorm'] = m; spec.loader.exec_module(m); "
            "heavy = [n for n in sys.modules if n.split('.')[0] in ('arbtok', 'orthography2ipa', 'onnxruntime', 'ovos_number_parser')]; "
            "assert not heavy, heavy")
    subprocess.run([sys.executable, "-S", "-c", code], check=True)


def test_tts_normalization_speaks_numbers_and_canonicalizes():
    assert not re.search(r"\d", normalize_for_tts("عندي 3 كتب"))
    assert normalize_for_tts("عندي 3 كتب", spoken_forms=False) == "عندي 3 كتب"
    assert normalize_for_tts("المـرء", spoken_forms=False) == "المرء"
    assert normalize_for_tts("المـرء", spoken_forms=False, canonical_unicode=False) == "المـرء"
    assert normalize_for_tts("نص\u200Bنص", spoken_forms=False, strip_controls=True) == "نصنص"
    assert "\u200B" in normalize_for_tts("نص\u200Bنص", spoken_forms=False)


def test_the_plugin_normalizes_through_the_same_function():
    from arbtok.plugin import ArbtokG2PPlugin
    text = "المـرء عنده 12 كتابًا"
    assert ArbtokG2PPlugin(diacritize=False).normalize(text) == normalize_for_tts(text, "ar")


LEXICON = {"بي إم دبليو": "BMW", "اكس فايف": "X5", "اكس": "X", "اكس خمسة": "X5"}


def test_a_lexicon_writes_a_spelling_back_as_its_term():
    assert normalize_asr("مجموعة اكس فايف معك", AsrNorm().with_lexicon(LEXICON)) == "مجموعة X5 معك"


def test_the_longest_spelling_wins_and_a_shorter_one_still_matches_alone():
    assert normalize_asr("اكس فايف و اكس", AsrNorm().with_lexicon(LEXICON)) == "X5 و X"


def test_a_spelling_is_read_under_the_rules_that_are_on():
    text = "مجموعة بي ام دبليو"
    assert normalize_asr(text, AsrNorm().with_lexicon(LEXICON)) == text
    assert normalize_asr(text, AsrNorm().with_lexicon(LEXICON), unify_alef=True) == "مجموعة BMW"
    assert normalize_asr("مجموعة بِي إِمْ دَبْلْيُو", AsrNorm().with_lexicon(LEXICON), strip_harakat=True) == "مجموعة BMW"


def test_a_spelling_matches_whole_words_only():
    assert normalize_asr("اكسفايف والاكس فايف", AsrNorm().with_lexicon(LEXICON)) == "اكسفايف والاكس فايف"


def test_punctuation_around_a_match_stays_and_punctuation_inside_prevents_one():
    assert normalize_asr("سيارة (اكس فايف)، نعم.", AsrNorm().with_lexicon(LEXICON)) == "سيارة (X5)، نعم."
    assert normalize_asr("اكس، فايف", AsrNorm().with_lexicon(LEXICON)) == "X، فايف"


def test_text_without_a_match_keeps_its_whitespace():
    assert normalize_asr("نص  بدون\tتغيير\n", AsrNorm().with_lexicon(LEXICON)) == "نص  بدون\tتغيير\n"
    assert normalize_asr("نص", AsrNorm().with_lexicon({})) == "نص"


def test_a_term_spelled_with_a_number_word_is_a_term_before_it_is_a_number():
    assert normalize_asr("اكس خمسة", AsrNorm().with_lexicon(LEXICON), spoken_numbers_to_digits=True) == "X5"
    assert normalize_asr("اكس خمسة", spoken_numbers_to_digits=True) == "اكس 5"


@pytest.mark.parametrize("spoken, written", [
    ("السعر خمسة وأربعون ألف ريال", "السعر 45000 ريال"),
    ("سنة ألفين وثلاثة وعشرين", "سنة 2023"),
    ("عندي خَمْسَةُ كتب", "عندي 5 كتب"),
    ("نص بدون ارقام", "نص بدون ارقام"),
])
def test_spoken_numbers_become_digits(spoken, written):
    assert normalize_asr(spoken, spoken_numbers_to_digits=True) == written


def test_reading_numbers_leaves_text_without_numbers_exactly_as_it_came():
    for text in ("  نص  بمسافتين\tوتاب \n", " \n", ""):
        assert normalize_asr(text, spoken_numbers_to_digits=True) == text


def test_reading_numbers_keeps_the_whitespace_at_the_ends():
    assert normalize_asr("  خمسة كتب \n", spoken_numbers_to_digits=True) == "  5 كتب \n"


def test_a_phone_number_read_aloud_becomes_one_run_and_short_runs_stay_apart():
    heard = "جوالي صفر خمسة خمسة ثلاثة واحد سبعة تسعة اثنين اربعة خمسة"
    assert normalize_asr(heard, spoken_numbers_to_digits=True) == "جوالي 0 5 5 3 1 7 9 2 4 5"
    assert normalize_asr(heard, spoken_numbers_to_digits=True, join_dictated_digits=True) == "جوالي 0553179245"
    assert normalize_asr("في 2019 3 سيارات و 1 2 3", join_dictated_digits=True) == "في 2019 3 سيارات و 1 2 3"


def test_digits_are_the_inverse_of_what_tts_normalization_speaks():
    for number in ("7", "45000", "2023"):
        spoken = normalize_for_tts(f"العدد {number}")
        assert not re.search(r"\d", spoken)
        assert normalize_asr(spoken, TRUTH_CHECK, spoken_numbers_to_digits=True) == f"العدد {number}"


def test_the_description_names_the_lexicon_by_its_content():
    plain, with_lexicon = CER_NORM.describe(), CER_NORM.with_lexicon(LEXICON).describe()
    assert with_lexicon.startswith(plain + "; lexicon 4 entries sha256:")
    assert CER_NORM.with_lexicon(dict(reversed(list(LEXICON.items())))).describe() == with_lexicon
    assert CER_NORM.with_lexicon({**LEXICON, "ام تو": "M2"}).describe() != with_lexicon
    assert CER_NORM.with_lexicon({}).describe() == plain


def test_a_lexicon_cannot_be_applied_without_the_config_saying_so():
    """Two error rates under different lexicons must never carry one description: the
    only way to apply a lexicon is through the config, and the config describes it."""
    for call, config in ((normalize_asr, CER_NORM), (lambda t, c, **kw: normalize_for_tts(t, "ar", c, **kw), TtsNorm())):
        with pytest.raises(TypeError, match="with_lexicon"):
            call("نص", config, lexicon=LEXICON)
        a, b = config.with_lexicon({"اكس": "X"}), config.with_lexicon({"اكس": "EX"})
        assert len({config.describe(), a.describe(), b.describe()}) == 3
    assert normalize_asr("اكس", CER_NORM.with_lexicon({"اكس": "X"})) == "X"
    assert normalize_asr("اكس", CER_NORM) == "اكس"


def test_the_rule_set_name_is_computed_from_the_rules():
    assert re.fullmatch(r"[0-9a-f]{12}", textnorm.ASR_NORM_VERSION)
    flags = [f.name for f in dataclasses.fields(AsrNorm)]
    assert textnorm._rule_set(flags, textnorm._HARAKAT) == textnorm._rule_set(list(flags), textnorm._HARAKAT)
    assert textnorm._rule_set(flags + ["one_more_rule"], textnorm._HARAKAT) != textnorm._rule_set(flags, textnorm._HARAKAT)
    assert textnorm._rule_set(flags, textnorm._HARAKAT + "\u0653") != textnorm._rule_set(flags, textnorm._HARAKAT)
    assert textnorm._rule_set(list(reversed(flags)), textnorm._HARAKAT) != textnorm._rule_set(flags, textnorm._HARAKAT)
    assert textnorm.ASR_NORM_VERSION != textnorm.TTS_NORM_VERSION


def test_a_description_is_still_written_when_the_parsers_version_cannot_be_read(monkeypatch):
    import importlib.metadata
    def absent(name):
        raise importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(importlib.metadata, "version", absent)
    assert AsrNorm(spoken_numbers_to_digits=True).describe().endswith("; ovos-number-parser unknown")
    assert VOICE_AGENT.describe().endswith("; ovos-number-parser unknown")


def test_the_version_names_the_rules_and_the_description_names_the_configuration():
    other_words = dataclasses.replace(VOICE_AGENT, identifier_words=("رقم",))
    other_shapes = dataclasses.replace(VOICE_AGENT, phone_shapes=(r"07[0-9]{8}",))
    descriptions = {c.describe() for c in (VOICE_AGENT, other_words, other_shapes)}
    assert len(descriptions) == 3
    assert all(f"arbtok-tts-norm {textnorm.TTS_NORM_VERSION}: " in d for d in descriptions)


def test_a_description_names_the_number_parser_when_numbers_are_read():
    assert "ovos-number-parser " in AsrNorm(spoken_numbers_to_digits=True).describe()
    assert "ovos-number-parser" not in CER_NORM.describe()
    assert "ovos-number-parser " in VOICE_AGENT.describe()


SAID = {"BMW": "بِي إِمْ دَبَلْيُو", "X5": "إِكْسْ فَيْفْ", "X5 M": "إِكْسْ فَيْفْ إِمْ"}
AS_WRITTEN = dict(spoken_forms=False, canonical_unicode=False)


def test_a_tts_lexicon_writes_a_term_the_way_it_is_said():
    assert normalize_for_tts("سيارة BMW جديدة", "ar", TtsNorm().with_lexicon(SAID), **AS_WRITTEN) == "سيارة بِي إِمْ دَبَلْيُو جديدة"


def test_a_term_matches_in_any_case_and_the_longest_term_wins():
    assert normalize_for_tts("bmw x5 m", "ar", TtsNorm().with_lexicon(SAID), **AS_WRITTEN) == "بِي إِمْ دَبَلْيُو إِكْسْ فَيْفْ إِمْ"


def test_an_arabic_prefix_stays_attached_and_punctuation_stays_put():
    assert normalize_for_tts("بالBMW، (X5).", "ar", TtsNorm().with_lexicon(SAID), **AS_WRITTEN) == "بالبِي إِمْ دَبَلْيُو، (إِكْسْ فَيْفْ)."


def test_a_term_inside_a_longer_latin_run_is_not_a_term():
    assert normalize_for_tts("BMWX و X55 و 2X5", "ar", TtsNorm().with_lexicon(SAID), **AS_WRITTEN) == "BMWX و X55 و 2X5"


def test_codes_are_spelled_out_and_words_and_numbers_are_not():
    said = normalize_for_tts("موديل GV70 و M2 سنة 2023 و service و 7", spell_out_codes=True, **AS_WRITTEN)
    assert said == "موديل جِي فِي سِفَنْ زِيرُو و إِمْ تُو سنة 2023 و service و 7"


def test_the_lexicon_claims_a_term_before_it_is_spelled_out():
    lexicon = {"GV70": "جِي فِي سِفِنْتِي"}
    assert normalize_for_tts("GV70 و X5", "ar", TtsNorm().with_lexicon(lexicon), spell_out_codes=True, **AS_WRITTEN) == \
        "جِي فِي سِفِنْتِي و إِكْسْ فَيْفْ"


def test_a_spelled_code_leaves_no_digit_for_the_number_rules_and_a_bare_number_is_still_spoken():
    said = normalize_for_tts("X5 سنة 2023", spell_out_codes=True)
    assert "إِكْسْ فَيْفْ" in said and not re.search(r"[A-Za-z0-9]", said)


def test_without_the_new_arguments_nothing_latin_changes():
    assert normalize_for_tts("سيارة BMW X5", **AS_WRITTEN) == "سيارة BMW X5"


def test_a_language_without_a_bundled_table_is_refused_by_name():
    with pytest.raises(ValueError, match="pt"):
        textnorm.spelled_codes("pt")


def _code_rows():
    from pathlib import Path
    path = Path(textnorm.__file__).parent / "data" / "tts_lexicons" / "en-codes.ar.tsv"
    return [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")]


def test_the_bundled_table_names_every_capital_and_every_digit_once():
    import string
    characters = [row[0] for row in _code_rows()]
    assert sorted(characters) == sorted(string.ascii_uppercase + string.digits)
    assert textnorm.spelled_codes("ar") == {c: pointed for c, _, pointed in _code_rows()}


@pytest.mark.parametrize("character, word, pointed", _code_rows(), ids=[row[0] for row in _code_rows()])
def test_a_bundled_spelling_reads_as_the_nativized_english_name(character, word, pointed):
    """The basis of every row: the donor lexicon's pronunciation of the English word,
    nativized by arbtok.translit, with the glottal onset Arabic gives a vowel-initial word."""
    from arbtok.donor_lexicon import bundled_path
    from arbtok.tokenizer import Sentence
    from arbtok.translit import nativize
    donor = dict(line.split("\t")[:2] for line in bundled_path().read_text(encoding="utf-8").splitlines()
                 if "\t" in line)
    target = nativize(donor[word], "ar")
    if target[0] in "aiu":
        target = "ʔ" + target
    assert Sentence(pointed, lang="ar", stress=False, pausal=False).ipa == target


def test_the_diacritizer_leaves_a_pointed_spelling_as_it_was_given():
    from arbtok.plugin import ArbtokG2PPlugin
    from arbtok.tokenizer import normalize_unicode
    plugin = ArbtokG2PPlugin()
    said = normalize_for_tts("سيارتي BMW X5", spell_out_codes=True)
    restored = plugin.normalize(said)
    assert not plugin._diacritizer_failed, "the diacritizer did not run, so this checked nothing"
    for word in "بِي إِمْ دَبَلْيُو إِكْسْ فَيْفْ".split():
        assert normalize_unicode(word) in restored.split()


def test_every_bundled_spelling_names_the_public_page_it_was_read_from():
    rows = textnorm._term_rows("cars-sa")
    assert len(rows) > 100
    for row in rows:
        assert row["latin"] and row["arabic_form"] and row["form_kind"] in textnorm._PUBLISHED_BY
        assert row["source_url"].startswith("https://") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date_read"])


def test_the_build_refuses_a_form_no_public_page_published(tmp_path):
    import json, subprocess, sys
    from pathlib import Path
    script = Path(textnorm.__file__).parents[1] / "scripts" / "build_term_lexicon.py"
    row = dict(brand="Toyota", model=None, arabic_form="تويوتا", source_url="https://toyota.com.sa/ar",
               date_read="2026-01-01")
    harvest = tmp_path / "harvest.jsonl"
    harvest.write_text("\n".join(json.dumps(dict(row, form_kind=kind, arabic_form=form), ensure_ascii=False)
                                  for kind, form in (("brand-site", "تويوتا"), ("spoken-mined", "طيوطا"))))
    out = tmp_path / "out.tsv"
    subprocess.run([sys.executable, str(script), str(harvest), str(out)], check=True)
    assert "تويوتا" in out.read_text(encoding="utf-8") and "طيوطا" not in out.read_text(encoding="utf-8")


def test_the_bundled_asr_lexicon_keeps_every_published_spelling_of_a_name():
    lexicon = textnorm.bundled_asr_lexicon()
    assert lexicon["باليسيد"] == lexicon["باليسايد"] == "PALISADE"
    assert normalize_asr("عندي سوناتا وباليسايد جديدة، هيونداي.", AsrNorm().with_lexicon(lexicon)) == \
        "عندي SONATA وباليسايد جديدة، Hyundai."


def test_the_bundled_tts_lexicon_prefers_the_spelling_nearest_the_maker():
    rows = textnorm._term_rows("cars-sa")
    rank = lambda row: textnorm._PUBLISHED_BY.index(row["form_kind"])
    lexicon = textnorm.bundled_tts_lexicon()
    assert set(lexicon) == {row["latin"] for row in rows}
    for latin, arabic in lexicon.items():
        best = min(rank(row) for row in rows if row["latin"] == latin)
        assert any(row["latin"] == latin and row["arabic_form"] == arabic and rank(row) == best for row in rows)
    assert normalize_for_tts("سيارة Hyundai Sonata", "ar", TtsNorm().with_lexicon(lexicon), **AS_WRITTEN) == "سيارة هيونداي سوناتا"


def _common_rows():
    return textnorm._term_rows("common-en")


@pytest.mark.parametrize("row", _common_rows(), ids=[row["latin"] for row in _common_rows()])
def test_an_authored_term_keeps_its_conventional_letters_and_reads_as_recorded(row):
    from arbtok.tokenizer import Sentence
    assert row["basis"] == "authored"
    assert normalize_asr(row["pointed"], strip_harakat=True) == row["arabic_form"]
    assert Sentence(row["pointed"], lang="ar", stress=False, pausal=False).ipa == row["reading"]


def test_the_common_terms_read_both_ways_and_pointed_or_plain():
    said = textnorm.bundled_tts_lexicon("common-en")
    assert normalize_for_tts("فيها WiFi و Apple CarPlay", "ar", TtsNorm().with_lexicon(said), **AS_WRITTEN) == \
        "فيها وَايْ فَايْ و أَبِلْ كَارْبْلَايْ"
    plain = textnorm.bundled_tts_lexicon("common-en", pointed=False)
    assert normalize_for_tts("فيها wifi", "ar", TtsNorm().with_lexicon(plain), **AS_WRITTEN) == "فيها واي فاي"
    heard = textnorm.bundled_asr_lexicon("common-en")
    assert normalize_asr("فيها واي فاي وبلوتوث و بلوتوث", AsrNorm().with_lexicon(heard)) == "فيها WiFi وبلوتوث و Bluetooth"


def test_a_lexicon_that_is_not_bundled_is_refused_with_the_names_that_are():
    with pytest.raises(ValueError, match="cars-sa"):
        textnorm.bundled_asr_lexicon("boats")


KSA = VOICE_AGENT


@pytest.mark.parametrize("written, said", [
    ("السعر النهائي 355,000 ريال", "السعر النهائي ثلاث مئة وخمسة وخمسين ألف ريال"),
    ("خلني أسجل رقمك 0551234567 عشان أرسل العرض.",
     "خلني أسجل رقمك صفر خمسة خمسة واحد اثنين ثلاثة أربعة خمسة ستة سبعة عشان أرسل العرض."),
    ("كود العرض 4471 صالح", "كود العرض أربعة أربعة سبعة واحد صالح"),
    ("نسبة التمويل 4.5% على خمس سنوات.", "نسبة التمويل أربعة فاصلة خمسة في المئة على خمس سنوات."),
], ids=["price", "phone", "identifier", "percent"])
def test_the_voice_agent_bundle_reads_what_a_reply_holds(written, said):
    assert normalize_for_tts(written, "ar", KSA) == said


def test_a_context_word_makes_a_reference_and_a_quantity_word_does_not():
    assert normalize_for_tts("الكود 4729", "ar", KSA) == "الكود أربعة سبعة اثنين تسعة"
    assert normalize_for_tts("برقم الحجز 3401", "ar", KSA) == "برقم الحجز ثلاثة أربعة صفر واحد"
    assert "أربعة سبعة" not in normalize_for_tts("موديل 4729", "ar", KSA)


def test_a_reference_written_in_arabic_indic_digits_is_read_out_not_dropped():
    assert normalize_for_tts("رقمك ٤٥٥٥", "ar", KSA) == "رقمك أربعة خمسة خمسة خمسة"


def test_the_digits_of_a_model_name_are_kept_from_the_number_rules():
    assert normalize_for_tts("سيارة MG 5 بسعر 5 ريال", "ar", KSA).startswith("سيارة MG 5 بسعر خمسة")
    assert normalize_for_tts("سيارة MG 5", "ar", KSA, keep_code_digits=False) != "سيارة MG 5"


def test_hundreds_are_spaced_in_numbers_this_speaks_and_left_alone_in_words_the_author_wrote():
    assert "ثلاث مئة" in normalize_for_tts("300 ريال", "ar", KSA)
    assert "ثلاثمئة" in normalize_for_tts("300 ريال", "ar", KSA, space_fused_hundreds=False)
    assert normalize_for_tts("ألف وخمسمئة ريال", "ar", KSA) == "ألف وخمسمئة ريال"


def test_a_phone_number_does_not_run_on_into_an_arabic_indic_number_after_it():
    said = normalize_for_tts("+966 55-398-8621 ٩٦٧٦٠", "ar", KSA)
    phone = "تسعة ستة ستة خمسة خمسة ثلاثة تسعة ثمانية ثمانية ستة اثنين واحد"
    assert said == phone + " " + normalize_for_tts("٩٦٧٦٠", "ar", KSA)
    # With Arabic-Indic digits allowed inside the pattern, a number one digit short takes
    # its last digit from the number written after it. The number is written with the
    # trunk prefix: one led by + is read digit by digit whatever its length.
    greedy = dataclasses.replace(KSA, phone_shapes=(r"(?:(?:\+|00)?966[\s\-]*5|05)(?![\s\-])\d(?:(?:\s*-\s*|\s+)?\d){7}(?!\d)",))
    short = "055-398-862 ٩"
    assert normalize_for_tts(short, "ar", greedy) != normalize_for_tts(short, "ar", KSA)


def test_a_number_that_cannot_be_spoken_is_left_or_raised_as_the_config_says(monkeypatch):
    spoken = textnorm._cardinal
    def refuses_300(number, lang, config):
        if number == "300":
            raise RuntimeError("boom")
        return spoken(number, lang, config)
    monkeypatch.setattr(textnorm, "_cardinal", refuses_300)
    said = normalize_for_tts("السعر 300 ريال و 5 كتب", "ar", KSA)
    assert "300" in said and "خمسة" in said
    with pytest.raises(RuntimeError):
        normalize_for_tts("السعر 300 ريال", "ar", KSA, leave_unspeakable_numbers=False)


def test_a_long_run_and_a_prefixed_run_are_read_digit_by_digit():
    assert normalize_for_tts("12345678901", "ar", KSA).split()[:3] == ["واحد", "اثنين", "ثلاثة"]
    assert normalize_for_tts("8001000341", "ar", KSA).split()[:3] == ["ثمانية", "صفر", "صفر"]
    assert normalize_for_tts("12500000 ريال", "ar", KSA).split()[0] != "واحد"


# The lexicon has its own tests, and leave_unspeakable_numbers shows only when a number cannot be
# spoken, which test_a_number_that_cannot_be_spoken_is_left_or_raised_as_the_config_says arranges.
@pytest.mark.parametrize("flag", [f.name for f in dataclasses.fields(textnorm.TtsNorm)
                                  if f.name not in ("lexicon", "leave_unspeakable_numbers")])
def test_every_tts_rule_changes_some_output(flag):
    # A grouped phone number is what phone_shapes alone catches, 25 is a number whose
    # case shows, and spoken_forms has something to say only where the cardinals are off.
    texts = ["نص\u200bنص", "X5", "4.5%", "MG 5", "055 123 4567", "12345678901", "8001000341", "الكود 4729",
             "300 ريال", "25 ريال", "٣٠٠", "المـرء", "15 رسالة", "350 ريال",
             "اتصل على 010 01234567",  # libphonenumber example number, MOBILE, EG
             "80012345"]  # a caller's own prefix, shorter than long_digit_runs reaches
    # phone_regions reads these numbers too, so a caller's own pattern is shown on its own.
    alone = {"phone_regions": ()} if flag in ("phone_shapes", "phone_prefixes") else {}
    off = dataclasses.replace(KSA, spoken_forms=False, canonical_unicode=False, strip_controls=False,
                              spell_out_codes=False, cardinal_numbers=flag != "spoken_forms", **alone)
    # A rule that reads a lect's own words has nothing to say under a tag that names no lect.
    lang = "ar-SA-x-hejaz" if flag == "dialect_numbers" else "ar"
    # What a non-boolean rule holds when it is on: turning it on and off is what this compares.
    when_on = {"phone_shapes": (r"05[0-9](?:\s?[0-9]){7}",), "phone_regions": textnorm.ARAB_PHONE_REGIONS,
               "phone_prefixes": (r"800[0-9]{5}",),
               "identifier_words": textnorm.IDENTIFIER_WORDS, "number_forms": ((15, "خمستاشر"),)}
    current = getattr(off, flag)
    other = (not current) if isinstance(current, bool) else (() if current else when_on[flag])
    assert any(normalize_for_tts(t, lang, off) != normalize_for_tts(t, lang, dataclasses.replace(off, **{flag: other}))
               for t in texts)


def test_the_tts_description_names_what_is_on_and_digests_the_patterns():
    assert textnorm.TtsNorm(spoken_forms=False).describe() == f"arbtok-tts-norm {textnorm.TTS_NORM_VERSION}: canonical_unicode"
    assert "phone_regions=" in KSA.describe() and KSA.describe() != dataclasses.replace(KSA, phone_regions=("SA",)).describe()


def test_a_mark_at_the_end_of_a_word_is_part_of_the_word_not_punctuation_after_it():
    pointed = AsrNorm().with_lexicon({"إِكْسْ فَيْفْ": "X5"})
    assert normalize_asr("سيارة إِكْسْ فَيْفْ.", pointed) == "سيارة X5."
    assert normalize_asr("«إِكْسْ فَيْفْ»", pointed) == "«X5»"


def test_a_config_takes_a_mapping_or_a_list_and_holds_what_can_be_hashed():
    assert AsrNorm(lexicon={"اكس": "X"}) == AsrNorm().with_lexicon({"اكس": "X"})
    assert normalize_asr("اكس", AsrNorm(lexicon={"اكس": "X"})) == "X"
    listed = TtsNorm(phone_regions=["SA"], lexicon=[("BMW", "بي إم")])
    assert hash(listed) == hash(TtsNorm(phone_regions=("SA",)).with_lexicon({"BMW": "بي إم"}))


@pytest.mark.parametrize("lexicon", [{"": "X"}, {"  ": "X"}, {"اكس": None}, [("اكس",)]],
                         ids=["empty spelling", "blank spelling", "no term", "not a pair"])
def test_a_lexicon_entry_that_could_match_everywhere_or_nothing_is_refused(lexicon):
    for config in (AsrNorm, TtsNorm):
        with pytest.raises(ValueError, match="lexicon entry"):
            config(lexicon=lexicon)


def test_a_private_use_character_of_the_texts_own_survives_the_digits_being_held():
    text = "\ue000 سيارة MG 5 و \ue001"
    assert normalize_for_tts(text, "ar", KSA) == text


def test_rules_that_speak_arabic_refuse_another_language():
    with pytest.raises(ValueError, match="speak_percent"):
        normalize_for_tts("50%", "en", spoken_forms=False, speak_percent=True)
    assert "في المئة" in normalize_for_tts("50%", "ar-SA", spoken_forms=False, speak_percent=True)
    assert normalize_for_tts("50%", "en", spoken_forms=False, canonical_unicode=False) == "50%"


def test_the_public_names_exist():
    assert all(hasattr(textnorm, name) for name in textnorm.__all__) and len(set(textnorm.__all__)) == len(textnorm.__all__)


def test_no_test_source_and_not_this_module_hides_a_format_character():
    """Zero-width and bidirectional characters belong in escapes, where a reader can see them."""
    import unicodedata
    from pathlib import Path
    for path in (Path(textnorm.__file__), *sorted(Path(__file__).parent.glob("*.py"))):
        hidden = [(n, f"U+{ord(c):04X}") for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                  for c in line if unicodedata.category(c) == "Cf"]
        assert not hidden, f"{path.name}: {hidden[:5]}"


@pytest.mark.parametrize("config", [AsrNorm, TtsNorm], ids=["asr", "tts"])
def test_the_documentation_lists_every_rule_in_the_order_it_runs(config):
    from pathlib import Path
    page = (Path(textnorm.__file__).parents[1] / "docs" / "normalization.md").read_text(encoding="utf-8")
    tables = [re.findall(r"^\| `([a-z_]+)` \|", block.split("\n\n")[0], flags=re.M)
              for block in page.split("| Flag | Rule |")[1:]]
    rules = [f.name for f in dataclasses.fields(config) if f.name != "lexicon"]
    assert rules in tables, f"no table of docs/normalization.md lists exactly {rules}"


CLDR_TABLES = ["units-cldr", "currencies-cldr", "territories-cldr", "languages-cldr"]


@pytest.mark.parametrize("name", CLDR_TABLES)
def test_every_cldr_row_names_its_release_file_and_licence(name):
    rows = textnorm._term_rows(name)
    assert len(rows) > 200
    for row in rows:
        assert row["source_url"].startswith("https://raw.githubusercontent.com/unicode-org/cldr-json/48.2.1/")
        assert re.fullmatch(r"[0-9a-f]{64}", row["fetch_sha256"]) and row["licence"] == "Unicode-3.0"
        assert row["latin"] and row["arabic_form"] and row["cldr_key"]


@pytest.mark.parametrize("name", CLDR_TABLES)
def test_a_cldr_lexicon_holds_only_names_a_voice_can_say(name):
    lexicon = textnorm.bundled_tts_lexicon(name)
    assert len(lexicon) > 150
    for latin, arabic in lexicon.items():
        assert re.fullmatch("[\u0621-\u064A\u064B-\u0652\u0670\u0671 ]+", arabic), (latin, arabic)
    unsayable = [r for r in textnorm._term_rows(name) if not textnorm._SPEAKABLE.fullmatch(r["arabic_form"])]
    assert all(r["arabic_form"] not in lexicon.values() for r in unsayable)


def test_the_filters_have_something_to_refuse():
    """CLDR gives some units a symbol or an abbreviation as their Arabic name, and names its pseudo-locales."""
    assert sum(not textnorm._SPEAKABLE.fullmatch(r["arabic_form"]) for r in textnorm._term_rows("units-cldr")) >= 20
    assert {"XA", "XB", "ZZ"} <= {r["cldr_key"].split("/")[-1] for r in textnorm._term_rows("territories-cldr")}
    places = textnorm.bundled_tts_lexicon("territories-cldr")
    assert "Pseudo-Bidi" not in places and places["Saudi Arabia"] == "المملكة العربية السعودية"


def test_a_currency_is_found_by_its_name_and_by_its_code():
    money = textnorm.bundled_tts_lexicon("currencies-cldr")
    assert money["SAR"] == money["Saudi Riyal"] == "ريال سعودي"
    said = normalize_for_tts("السعر 500 SAR", "ar", TtsNorm().with_lexicon(money))
    assert "ريال سعودي" in said and "SAR" not in said


def test_a_cldr_table_is_not_read_backwards():
    with pytest.raises(ValueError, match="translate"):
        textnorm.bundled_asr_lexicon("territories-cldr")


def test_a_unit_after_a_number_is_read_in_arabic_and_a_bare_symbol_is_left():
    assert normalize_for_tts("المسافة 5 km") == "المسافة خمسة كيلومتر"
    assert "كيلوغرام" in normalize_for_tts("الوزن 3 kg")
    assert normalize_for_tts("in km", spoken_forms=True) == "in km"
    units = textnorm.cldr_units("ar")
    assert units["km"] == "كيلومتر" and units["m"] == "متر"
    assert not [s for s in units if len(s) == 1 and s.isascii() and s.isalpha() and s != "m"]
    with pytest.raises(ValueError, match="pt"):
        textnorm.cldr_units("pt")


def test_a_percentage_keeps_the_spelling_this_package_already_speaks_it_in():
    from arbtok.util import normalize
    assert "%" not in textnorm.cldr_units("ar") and "\u066A" not in textnorm.cldr_units("ar")
    assert normalize("خصم 30%", "ar") == "خصم ثلاثون بالمئة"

