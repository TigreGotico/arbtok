"""MSA gold set under arbtok's declared waqf (pausal) policy.

This module retires the legacy ``arbtok/test.py`` gold file (LLM-generated,
never fully human-validated, and internally inconsistent about iʿrāb). Every
one of its cases lives on here as real pytest, resolved under ONE declared
policy instead of fifteen mutually-disputing golds:

**The policy** (``ArbtokG2PPlugin(pausal=True)`` / ``Sentence(pausal=True)``,
the TTS default — Wright, *A Grammar of the Arabic Language*, 3rd ed., I §372;
Ryding, *A Reference Grammar of Modern Standard Arabic*, CUP 2005, §2.4):

- A word standing at a **written pause** (a punctuation token) takes its
  pausal form: the final short vowel (iʿrāb) is dropped; tanwīn -un/-in drop
  with their /n/; tanwīn -an does not vanish but lengthens to /aː/ on its
  written seat alif; a tāʾ marbūṭa voiced only by its ending falls silent
  with it (مَدِينَةٌ. → *madiːna*). The construct-state /at/ (iḍāfa head
  keeping its tāʾ at a pause in careful renditions) is documented as
  UNMODELED.
- A word **not at a written pause keeps every ending it writes**: the pause
  has to be on the page. An utterance handed to us without punctuation may
  continue past the fragment, so no pause is invented at the edge of the
  input (قَلَمٌ → *qalamun*; يَوْمُ الشَّمْس → *jawmu ʃʃams*).
- ``pausal=False`` is the full-iʿrāb passthrough: every written ending is
  read out even at written punctuation — the recitation/pedagogical register.
- Both modes run the SAME lattice and rescorers; the flag is consulted in
  exactly one place (:func:`arbtok.sandhi._pausal`), so nothing is dropped
  twice and nothing is guessed from the IPA.

The reference gold is a SEGMENT gold: authored as phonemes, no stress marks,
broad emphatic vowels. Hypotheses are built unstressed and compared broad
(see :func:`broad`); stress has its own tests in ``test_stress.py`` and the
narrow emphatic backing is asserted in ``test_spec_dialects.py``.
"""
import string

import pytest

from arbtok.tokenizer import Sentence, WORD_EXCEPTIONS, WordToken, PUNCT

# ─── comparison helpers ──────────────────────────────────────────────────

#: arbtok's reference gold is a BROAD transcription: it writes /a/ where the
#: engine, applying the spec's cited emphatic-spreading rules, backs the vowel
#: to [ɑ] next to an emphatic (Watson 2002, ch. Emphasis). Scoring the narrow
#: form against a broad gold penalises the engine for being MORE precise than
#: the reference, so the comparison is made broad on both sides.
def broad(ipa: str) -> str:
    """Fold the narrow emphatic vowels onto the gold's broad tier."""
    return ipa.replace("ɑː", "aː").replace("ɑ", "a")


def transcribe(text: str, pausal: bool = True) -> str:
    return Sentence(text, stress=False, pausal=pausal).ipa


def check(text: str, expected: str, pausal: bool = True):
    result = transcribe(text, pausal=pausal)
    assert broad(result.strip(PUNCT + string.whitespace)) == broad(
        expected.strip(PUNCT + string.whitespace)
    ), f"Input {text!r}"


# ─── the undisputed gold, by phonological category ───────────────────────
# These carried no TODO in the legacy file and pass unchanged.

BASIC = [
    ("مَرْحَبًا", "marħaban", "Basic CV structure with tanwīn -an (no written pause: read in full)"),
    ("فِيل", "fiːl", "Long vowel iː (yāʾ mater lectionis)"),
    ("بَيْت", "bajt", "Diphthong ay"),
    ("يَوْم", "jawm", "Diphthong aw"),
    ("قَلَمٌ", "qalamun", "Tanwīn -un kept: no written pause"),
]

SUN_LETTERS = [
    ("الشَّمْس", "aʃʃams", "Sun letter ʃ"),
    ("السَّمَك", "assamak", "Sun letter s"),
    ("التَّاج", "attaːdʒ", "Sun letter t"),
    ("الثَّوْب", "aθθawb", "Sun letter θ"),
    ("الذَّهَب", "aððahab", "Sun letter ð"),
    ("الرَّجُل", "arradʒul", "Sun letter r"),
    ("الزَّيْت", "azzajt", "Sun letter z"),
    ("الطَّعَام", "atˤtˤaʕaːm", "Sun letter tˤ"),
    ("الظَّبْي", "aðˤðˤabj", "Sun letter ðˤ"),
    ("اللَّوْن", "allawn", "Sun letter l"),
    ("النَّار", "annaːr", "Sun letter n"),
    ("الصَّوْت", "asˤsˤawt", "Sun letter sˤ"),
    ("الدَّار", "addaːr", "Sun letter d"),
    ("الضَّوْء", "adˤdˤawʔ", "Sun letter dˤ"),
]

MOON_LETTERS = [
    ("الْقَمَر", "alqamar", "Moon letter q keeps the lām"),
    ("الْكِتَاب", "alkitaːb", "Moon letter k"),
    ("الْمَسْجِد", "almasdʒid", "Moon letter m"),
]

WASL = [
    ("بِ الْمَدِينَة", "bi lmadiːna", "bi + al → bil (article vowel elides)"),
    ("لِ النَّاس", "li nnaːs", "li + article + sun letter"),
    ("بِ الطَّبِيب", "bi tˤtˤabiːb", "bi + al + ṭāʾ"),
    ("فِي الشَّرِكَة", "fiː ʃʃarika", "Waṣl after vowel-final word + sun letter"),
    ("لِ الْكِتَاب", "li lkitaːb", "Waṣl after proclitic + moon letter"),
    ("فِي الْقَلَم", "fiː lqalam", "Waṣl after vowel-final word + moon letter"),
]

HAMZA = [
    ("أَمِير", "ʔamiːr", "Hamza on alif, initial"),
    ("سُؤَال", "suʔaːl", "Hamza on wāw, medial"),
    ("بِئْر", "biʔr", "Hamza on yāʾ, medial"),
    ("شَيْء", "ʃajʔ", "Standalone hamza, final"),
    ("آكُل", "ʔaːkul", "Alif madda"),
    ("قُرْآن", "qurʔaːn", "Medial madda"),
    ("مِائَة", "miʔa", "Silent alif of miʾa"),
    ("رَأْس", "raʔs", "Hamza + sukūn"),
    ("مَسْأَلَة", "masʔala", "Seated medial hamza"),
    ("مَسْئُول", "masʔuːl", "Hamza on yāʾ before uː"),
    ("آمِن", "ʔaːmin", "Madda, medial vowel"),
    ("مُسَاء", "musaːʔ", "Final hamza after long vowel"),
    ("جِئْتُ", "dʒiʔtu", "Hamza between front vowel and cluster"),
    ("شِئْتَ", "ʃiʔta", "Hamza + suffix vowel (no written pause: kept)"),
    ("فِئَات", "fiʔaːt", "Plural with medial hamza"),
    ("مَلَائِكَة", "malaːʔika", "Hamza + long vowel + broken plural"),
    ("مَاء", "maːʔ", "Final hamza"),
    ("جُزْء", "dʒuzʔ", "End hamza"),
    ("بُرْء", "burʔ", "End hamza"),
    ("نَبَأ", "nabaʔ", "Word-final hamza on alif"),
    ("يَبْدَأ", "jabdaʔ", "Verb-final hamza"),
    ("يَلْجَأ", "jaldʒaʔ", "Verb-final hamza"),
    ("قِرَاءَتُهُمْ", "qiraːʔatuhum", "Clitic + medial hamza chain"),
]

EXCEPTIONS = [
    ("هٰذَا", "haːðaː", "Dagger alif: unwritten long aː"),
    ("اللّٰه", "allaːh", "Allah: heavy l and unwritten alif"),
    ("عَمْرٌو", "ʕamrun", "Silent wāw of ʿAmr"),
    ("مِائَة", "miʔa", "Silent alif in 'hundred'"),
]

TANWIN_NO_PAUSE = [
    ("كُتُبٌ", "kutubun", "Tanwīn kept mid-utterance / no written pause"),
    ("قَلَمٌ", "qalamun", "Tanwīn kept"),
    ("مَاءٌ", "maːʔun", "Tanwīn kept after hamza"),
]

SANDHI = [
    ("بِ الظَّرْف", "bi ðˤðˤarf", "Assimilation across a written boundary"),
    ("مِنَ النَّاس", "mina nnaːs", "min + article + sun letter"),
    ("مِنْ رَبِّهِمْ", "mir rabbihim", "Idghām: n + r → rr"),
    ("مَنْ يَقُولُ", "maj jaquːlu", "Idghām: n + j → jj (no written pause: -u kept)"),
    ("مِنْ بَيْتِكَ", "mim bajtika", "Iqlāb: n → m before b (no written pause: -a kept)"),
    ("مِنْ بَعْد", "mimbaʕd", "Iqlāb joined"),
    ("إِلَى الرَّجُل", "ʔilaː rradʒul", "Waṣl + sun letter after ʔilaː"),
]

PAUSAL = [
    ("كِتَابًا.", "kitaːbaː", "Written pause: tanwīn -an lengthens to aː (Wright I §372)"),
    ("مَدِينَةٌ.", "madiːna", "Written pause: tāʾ marbūṭa and tanwīn drop together"),
    ("مَرْحَبًا!", "marħabaː", "Written pause: -an → aː"),
]

WEAK = [
    ("ذَهَبُوا", "ðahabuː", "Plural verb, silent otiose alif"),
    ("سَكَنُوا", "sakanuː", "Plural verb"),
    ("قَالُوا", "qaːluː", "Hollow verb plural"),
    ("تَوَاصَلُوا", "tawaːsˤaluː", "Form VI plural"),
    ("إِيْمَان", "ʔiːmaːn", "⟨إ⟩ is hamzat al-qaṭʿ, always pronounced (Wright I §19)"),
    ("انْتِمَاء", "intimaːʔ", "Bare waṣl-alif takes helper /i/"),
    ("رَمَى", "ramaː", "Alif maqṣūra as long aː"),
    ("دَعَا", "daʕaː", "Alif mamdūda as long aː"),
    ("قَاضٍ", "qaːdˤin", "Defective noun, tanwīn kasr kept (no written pause)"),
    ("بَاعُوا", "baːʕuː", "Hollow verb plural"),
    ("سَارُوا", "saːruː", "Hollow verb plural"),
    ("نَامُوا", "naːmuː", "Hollow verb plural"),
    ("بِيعَ", "biːʕa", "Passive, weak second radical"),
    ("قِيلَ", "qiːla", "Passive of qāla"),
    ("عُيِّنَ", "ʕujjina", "Form II passive, glide gemination"),
]

INTERNAL_HAMZA = [
    ("مُؤْتَمَر", "muʔtamar", "Internal hamza, derived form"),
    ("مُؤْمِن", "muʔmin", "Internal hamza"),
    ("تَأْثِير", "taʔθiːr", "Hamza + sukūn"),
    ("مَأْكُول", "maʔkuːl", "Internal hamza"),
    ("مَأْمُون", "maʔmuːn", "Internal hamza"),
]

GEMINATION = [
    ("يُصَلِّي", "jusˤalliː", "Gemination + emphatic"),
    ("ظَلَّ", "ðˤalla", "Final geminate + vowel (no written pause: kept)"),
    ("طَبَق", "tˤabaq", "Emphatic onset"),
]

LOANWORDS = [
    ("فِلْم", "film", "Loanword cluster"),
]

MULTIWORD = [
    ("مُعَلِّمُ الطِّفْل", "muʕallimu tˤtˤifl", "Construct + article sun letter"),
    ("رِسَالَةُ النَّاس", "risaːlatu nnaːs", "Construct tāʾ marbūṭa voiced by its ending"),
    ("مَدِينَةُ الطِّفْل", "madiːnatu tˤtˤifl", "Construct + sun letter"),
    ("فِي الشَّمْس", "fiː ʃʃams", "Waṣl + sun letter"),
]

HAMZAT_AL_WASL = [
    ("اِسْتِقْبَال", "istiqbaːl", "Form X maṣdar"),
    ("اِسْتِعْدَاد", "istiʕdaːd", "Form X maṣdar"),
    ("اِبْتِدَاء", "ibtidaːʔ", "Form VIII maṣdar"),
    ("اِجْتِمَاع", "ijtimaːʕ", "Form VIII maṣdar"),
    ("اِعْتِمَاد", "iʕtimaːd", "Form VIII maṣdar"),
    ("اِنْقَطَع", "inqatˤaʕ", "Form VII"),
    ("اِنْفِعَال", "infiʕaːl", "Form VII maṣdar"),
    ("اِفْعَوَّل", "ifʕawwal", "Form XII pattern"),
    ("اِحْمِرَار", "iħmiraːr", "Form IX maṣdar"),
    ("وَبِاسْمِ", "wabismi", "wa + bi + ism through waṣl"),
    ("فَبِالْحَقِّ", "fabilħaqqi", "fa + bi + article, moon letter (no written pause: -i kept)"),
    ("وَلِلنَّاس", "walinnaːs", "wa + li + sun letter"),
]

MISC = [
    ("بَوْت", "bawt", "Diphthong"),
    ("غُرُوب", "ɣuruːb", "ɣ + long uː"),
    ("مِفْتَاح", "miftaːħ", "Lexical filler"),
    ("عِلْم", "ʕilm", "Lexical filler"),
    ("صَحْرَاء", "sˤaħraːʔ", "Emphatic + final hamza"),
    ("غَيْم", "ɣajm", "Diphthong"),
    ("أُمّ", "ʔumm", "Final geminate"),
    ("سَائِق", "saːʔiq", "Hamza seat after long aː"),
    ("أَثَاث", "ʔaθaːθ", "θ twice"),
    ("ﷲ", "allaːh", "Allah ligature"),
    ("ﻻ", "laː", "Lam-alif ligature"),
    ("كَأَنَّمَا", "kaʔannamaː", "Hidden gemination"),
    ("عَمَّ", "ʕamma", "Geminate + final vowel kept (no written pause)"),
    ("كُلّ", "kull", "Final geminate"),
    ("حَتَّى", "ħattaː", "Geminate + alif maqṣūra"),
    ("إِلَّا", "ʔillaː", "Qaṭʿ hamza + geminate"),
    ("حَوْل", "ħawl", "Diphthong"),
    ("زَيْن", "zajn", "Diphthong"),
    ("طَوْر", "tˤawr", "Diphthong after emphatic"),
    ("زَيْتُون", "zajtuːn", "Diphthong + long uː"),
    ("وِلْد", "wild", "No epenthesis needed"),
    ("كِتَابٌ قَدِيم", "kitaːbun qadiːm", "No assimilation before uvular"),
    ("كِتَابٌ جَدِيد", "kitaːbun dʒadiːd", "No assimilation before dʒ"),
    ("مِنْ يَوْم", "mijjawm", "Idghām with ghunna into glide"),
    ("مِنْ لَبَن", "millaban", "Idghām into lām"),
    ("أَبْوَاب", "ʔabwaːb", "Plural pattern"),
    ("مَدِينَة", "madiːna", "Bare tāʾ marbūṭa silent (spec-level, both modes)"),
    ("رِسَالَة", "risaːla", "Bare tāʾ marbūṭa silent"),
    ("قِرْد", "qird", "Lexical filler"),
    ("تَدْرِيس", "tadriːs", "Lexical filler"),
    ("مَكْتُوب", "maktuːb", "Heavy final syllable"),
    ("مَفَاتِيح", "mafaːtiːħ", "Long penult"),
    ("كَتَبَتَا", "katabataː", "Dual feminine past"),
    ("مُدَرِّسُونَ", "mudarrisuːna", "Sound masculine plural, -na kept (no written pause)"),
    ("يَسْتَخْدِمُونَ", "jastaxdimuːna", "Form X present plural, -na kept"),
    ("مَدْرَسَة", "madrasa", "Bare tāʾ marbūṭa silent"),
    ("مُسْتَشْفَى", "mustaʃfaː", "Final alif maqṣūra"),
]

ALL_UNDISPUTED = (BASIC + SUN_LETTERS + MOON_LETTERS + WASL + HAMZA
                  + EXCEPTIONS + TANWIN_NO_PAUSE + SANDHI + PAUSAL + WEAK
                  + INTERNAL_HAMZA + GEMINATION + LOANWORDS + MULTIWORD
                  + HAMZAT_AL_WASL + MISC)

#: The formerly-disputed rows, resolved under the declared policy — each has
#: a named test below whose docstring records the old gold and the
#: justification for the change.
RESOLVED = [
    ("فِي الْبَيْت", "fiː lbajt", "waṣl elision after vowel-final word"),
    ("مَأْسَاة", "maʔsaː", "pausal tāʾ marbūṭa silent"),
    ("أَبُو الْقُرْآن", "ʔabuː lqurʔaːn", "ḍamma+wāw = long uː"),
    ("الرِّسَالَة", "arrisaːla", "alif mater lectionis = aː"),
    ("عَلَى الشَّاطِئ", "ʕalaː ʃʃaːtˤiʔ", "alif maqṣūra = long aː"),
    ("فِي الضَّوْءِ", "fiː dˤdˤawʔi", "ض = dˤ; kasra kept, no written pause"),
    ("تِيكْنُولُوجْيَا", "tiːknuːluːdʒjaː", "ḍamma+wāw = long uː"),
    ("اِسْوَدَّ", "iswadda", "Form IX ends in short fatḥa"),
    ("يَوْمُ الشَّمْس", "jawmu ʃʃams", "ḍamma kept, no written pause"),
    ("أُمُّ الْمُسْلِمِينَ", "ʔummu lmuslimiːna", "-na kept, no written pause"),
    ("كِتَابٌ عَلَى الْمَكْتَب", "kitaːbun ʕalaː lmaktab",
     "long aː + waṣl elision; tanwīn kept mid-phrase"),
    ("دُخَان", "duxaːn", "خ = x"),
    ("أَبْيَض", "ʔabjadˤ", "ض = dˤ"),
    ("مِنْ تَحْت", "mintaħt", "ت = plain t"),
    ("ذَهَبَ الطَّالِبُ إِلَى الْمَكْتَبَةِ",
     "ðahaba tˤtˤaːlibu ʔilaː lmaktabati", "waṣl + full iʿrāb, no pause"),
    ("ذَهَبَ الطَّالِبُ إِلَى الْمَكْتَبَةِ لِقِرَاءَةِ كِتَابٍ عَنْ تَارِيخِ الأَنْدَلُس",
     "ðahaba tˤtˤaːlibu ʔilaː lmaktabati liqiraːʔati kitaːbin ʕan "
     "taːriːxi lʔandalus", "waṣl at both article seams"),
]

#: The full gold set under the declared policy — what external consumers
#: (the fuzzy accuracy gates, scripts/metrics.py) score against. Excludes
#: the six blocked cases below, which are strict xfails, not gold.
ALL_TEST_CASES = ALL_UNDISPUTED + RESOLVED


@pytest.mark.parametrize("text, expected, description", ALL_UNDISPUTED)
def test_msa_gold(text, expected, description):
    """The retained gold set, under pausal=True (the default policy)."""
    check(text, expected)


# ─── the formerly-disputed golds, resolved under the policy ──────────────
# Each legacy "TODO - failing" row appears here exactly once, with the old
# gold, the resolution and its justification in the docstring.


def test_wasl_elision_after_vowel_final_word():
    """Legacy gold said *fiː albajt* ("article a dropped after preposition"
    yet spelled out!). Policy: the article's vowel elides after a vowel-final
    word (waṣl — Wright I §19; Ryding §2.4), consistently with the passing
    فِي الْقَلَم → *fiː lqalam* row → *fiː lbajt*."""
    check("فِي الْبَيْت", "fiː lbajt")


def test_pausal_ta_marbuta_after_long_vowel():
    """Legacy gold *maʔsaːta* was flagged disputed in the file itself: the
    tāʾ marbūṭa is voiced only by a following vowel, and none is written.
    Bare word-final tāʾ marbūṭa is silent (Wright I §372: pausal tāʾ
    marbūṭa) → *maʔsaː*."""
    check("مَأْسَاة", "maʔsaː")


def test_abu_is_long_u():
    """Legacy gold *ʔabu lqurʔaːn* was flagged disputed in the file: أَبُو is
    ḍamma + wāw = long /uː/ (mater lectionis, Wright I §4) → *ʔabuː
    lqurʔaːn*, waṣl elision intact."""
    check("أَبُو الْقُرْآن", "ʔabuː lqurʔaːn")


def test_risala_has_long_a():
    """Legacy gold *arrisala* (twice, in two categories) was flagged disputed
    in the file: the alif is a mater lectionis, so the word carries /aː/
    (Wright I §4) → *arrisaːla*."""
    check("الرِّسَالَة", "arrisaːla")


def test_ala_ends_long():
    """Legacy gold *ʕala ʃʃaːtˤiʔ* was flagged disputed in the file: عَلَى
    ends in alif maqṣūra = long /aː/, exactly as the passing إِلَى الرَّجُل
    row already had it → *ʕalaː ʃʃaːtˤiʔ*."""
    check("عَلَى الشَّاطِئ", "ʕalaː ʃʃaːtˤiʔ")


def test_dad_is_dˤ_and_iraab_kept_without_pause():
    """Legacy gold *fiː ðˤðˤawʔ* had two errors its own comment flagged: ض is
    /dˤ/ in MSA (Watson 2002 §1.2), and the written final kasra stands
    before NO written pause, so the policy keeps it → *fiː dˤdˤawʔi*."""
    check("فِي الضَّوْءِ", "fiː dˤdˤawʔi")


def test_waw_damma_is_long_u_in_loanword():
    """Legacy gold *tiːknuluːdʒjaː* was flagged disputed in the file:
    ḍamma + wāw is long /uː/ in every syllable it writes →
    *tiːknuːluːdʒjaː*."""
    check("تِيكْنُولُوجْيَا", "tiːknuːluːdʒjaː")


def test_form_ix_ends_short():
    """Legacy gold *iswaddaː* was flagged disputed in the file: Form IX
    اِسْوَدَّ ends in a short fatḥa, not /aː/ → *iswadda* (kept: no written
    pause)."""
    check("اِسْوَدَّ", "iswadda")


def test_construct_damma_kept_without_written_pause():
    """Legacy gold *jawm ʃʃams* dropped the ḍamma while the الطَّالِبُ rows
    kept theirs — the exact inconsistency this policy resolves. No written
    pause → the ending is read: *jawmu ʃʃams* (Wright I §372 applies only AT
    the pause)."""
    check("يَوْمُ الشَّمْس", "jawmu ʃʃams")


def test_final_na_kept_without_written_pause():
    """Legacy gold *ʔummu lmuslimiːn* dropped the plural's -a while the
    يَسْتَخْدِمُونَ gold kept its -na — flagged in the file. No written pause
    → *ʔummu lmuslimiːna*."""
    check("أُمُّ الْمُسْلِمِينَ", "ʔummu lmuslimiːna")


def test_tanwin_kept_mid_phrase():
    """Legacy gold *kitaːbun ʕala almaktab* was doubly wrong: عَلَى is long
    /aː/ and the article elides after it (waṣl). The tanwīn is mid-phrase and
    stays → *kitaːbun ʕalaː lmaktab*."""
    check("كِتَابٌ عَلَى الْمَكْتَب", "kitaːbun ʕalaː lmaktab")


def test_kha_is_x():
    """Legacy gold *duħaːn* was flagged disputed in the file: خ is /x/ in
    MSA, not /ħ/ → *duxaːn*."""
    check("دُخَان", "duxaːn")


def test_dad_is_dˤ():
    """Legacy gold *ʔabjaðˤ* was flagged disputed in the file: ض is /dˤ/ in
    MSA → *ʔabjadˤ*."""
    check("أَبْيَض", "ʔabjadˤ")


def test_teh_is_plain_t():
    """Legacy gold *mintˤaħt* was flagged disputed in the file: the consonant
    is ت /t/, not ط /tˤ/ → *mintaħt*."""
    check("مِنْ تَحْت", "mintaħt")


def test_narrative_wasl_and_full_iraab():
    """Legacy gold wrote *ʔilaː almaktabati* — flagged in the file as
    contradicting the waṣl-elision rule its own WASL rows assert. Policy:
    the article elides after vowel-final ʔilaː; every written ending before
    no written pause is read → *ʔilaː lmaktabati*."""
    check("ذَهَبَ الطَّالِبُ إِلَى الْمَكْتَبَةِ",
          "ðahaba tˤtˤaːlibu ʔilaː lmaktabati")


def test_long_narrative_sequence():
    """The long narrative row, with the same waṣl correction applied at both
    article seams (lmaktabati, lʔandalus after vowel-final taːriːxi)."""
    check("ذَهَبَ الطَّالِبُ إِلَى الْمَكْتَبَةِ لِقِرَاءَةِ كِتَابٍ عَنْ تَارِيخِ الأَنْدَلُس",
          "ðahaba tˤtˤaːlibu ʔilaː lmaktabati liqiraːʔati kitaːbin ʕan "
          "taːriːxi lʔandalus")


# ─── genuinely blocked cases (strict xfail, precise reasons) ─────────────


@pytest.mark.xfail(strict=True,
                   reason="cross-proclitic waṣl elision (wa+ismuhu → "
                          "wasmuhu) is a sentence-seam rule not yet applied "
                          "inside a joined token — roadmap E2; engine reads "
                          "the waṣl-alif as long aː")
def test_wasl_through_joined_proclitic():
    """Legacy gold *wasmuhu* (Wright I §19: the alif of ism elides after
    wa-). Blocked on cross-word waṣl completion (E2)."""
    check("وَاسْمُه", "wasmuhu")


@pytest.mark.xfail(strict=True,
                   reason="waṣl elision across a SPACE-separated proclitic "
                          "(bi + ismi → bismi) is cross-word — roadmap E2; "
                          "engine keeps the helper vowel: 'bi ismi'")
def test_wasl_across_space():
    """Legacy gold *bismi* (the basmala contraction, Wright I §19)."""
    check("بِ اسْمِ", "bismi")


@pytest.mark.xfail(strict=True,
                   reason="second word writes no shadda on the sun letter "
                          "(الشَجَرَة) and the waṣl runs through joined "
                          "wa- — both cross-word/lexical gaps (E2); legacy "
                          "gold 'aʃʃams wa ʃʒajara' was itself corrupt")
def test_sun_assimilation_through_joined_wa():
    """Corrected gold *aʃʃams waʃʃadʒara* (article + sun letter behind wa-,
    Wright I §17)."""
    check("الشَّمْس وَالشَجَرَة", "aʃʃams waʃʃadʒara")


@pytest.mark.xfail(strict=True,
                   reason="deficient spelling: no kasra/wāw vocalisation "
                          "written on سُيوف; reading /sujuːf/ is a lexical "
                          "fact the bare Sentence path (no diacritizer) "
                          "cannot know")
def test_deficiently_spelled_plural():
    """Legacy gold *sujuːf*, flagged in the file as needing a lexical fix."""
    check("سُيوف", "sujuːf")


@pytest.mark.xfail(strict=True,
                   reason="phonotactic-repair epenthesis for an illegal "
                          "initial cluster is unimplemented; engine emits "
                          "the raw cluster 'str'")
def test_epenthesis_synthetic_cluster():
    """Legacy gold *sitar* for the synthetic سْتْر — itself dubious (the
    expected repair vowel and site were never cited); kept as the marker for
    the missing epenthesis capability."""
    check("سْتْر", "sitar")


@pytest.mark.xfail(strict=True,
                   reason="prothetic /i/ before an initial sukūn cluster "
                          "(مْسَلَّة → imsalla) is unimplemented; legacy "
                          "gold 'imsallːa' also carried a spurious length "
                          "mark its own comment flagged")
def test_epenthesis_initial_m_cluster():
    """Corrected gold *imsalla* (the legacy row's comment already said the
    ː was spurious)."""
    check("مْسَلَّة", "imsalla")


# ─── the policy switch itself ────────────────────────────────────────────


@pytest.mark.parametrize("text, pausal_ipa, full_ipa", [
    ("كِتَابًا.", "kitaːbaː", "kitaːban"),
    ("مَدِينَةٌ.", "madiːna", "madiːnatun"),
    ("مَرْحَبًا!", "marħabaː", "marħaban"),
    ("فَبِالْحَقِّ.", "fabilħaqq", "fabilħaqqi"),
    ("ذَهَبَ الطَّالِبُ إِلَى الْمَكْتَبَةِ.",
     "ðahaba tˤtˤaːlibu ʔilaː lmaktaba",
     "ðahaba tˤtˤaːlibu ʔilaː lmaktabati"),
])
def test_both_modes_round_trip_the_same_lattice(text, pausal_ipa, full_ipa):
    """pausal=True gives Wright I §372 pausal forms at the written pause;
    pausal=False reads the full iʿrāb — and the two differ ONLY there, since
    the flag is consulted in exactly one place (arbtok.sandhi)."""
    check(text, pausal_ipa, pausal=True)
    check(text, full_ipa, pausal=False)


def test_no_pause_is_invented_at_end_of_input():
    """Without written punctuation there is no pause: the utterance may
    continue past the fragment, so both modes read the ending."""
    for pausal in (True, False):
        check("قَلَمٌ", "qalamun", pausal=pausal)


def test_lexical_final_vowel_survives_the_pause():
    """The pronoun's final vowel is lexical, not iʿrāb, and survives waqf
    (closed class shared with text2tashkeel.waqf.LEXICAL_FINAL_VOWEL)."""
    check("هُوَ.", "huwa")


# ─── retained infrastructure tests from the legacy module ────────────────


def test_hardcoded_wordlist():
    """Built-in word dictionary."""
    for text, expected in WORD_EXCEPTIONS.items():
        assert WordToken(text, word_idx=0).ipa == expected


def test_punctuation_preservation():
    """Non-Arabic characters and punctuation survive transcription."""
    result = transcribe("يَوْم جميل!")
    assert "!" in result
    assert result.startswith("jawm")
