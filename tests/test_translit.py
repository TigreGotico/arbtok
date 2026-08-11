"""A Latin-script word in an Arabic sentence."""

import pytest

from arbtok.plugin import ArbtokG2PPlugin
from arbtok.translit import (
    SEGMENT_MAP,
    is_latin,
    nativization_table,
    nativize,
    transliterate,
)

NAJD = "ar-SA-x-najd"
EG = "ar-EG"


class TestIsLatin:
    def test_latin(self):
        assert is_latin("meeting")

    def test_arabic(self):
        assert not is_latin("كتاب")


class TestNativization:
    """Alhoody (2019), Qassimi (= Najdi) — the variety we transcribe."""

    def test_p_becomes_b(self):
        """English /p/ has no Arabic counterpart (§5.1).

        No geminate: English orthographic doubling is not gemination (Venezky
        1999), so the donor reading has a single /z/ — the Italian /ts/ is a
        lexical fact, lexicon territory, not a rule."""
        assert transliterate("pizza", NAJD) == "biza"

    def test_v_becomes_f(self):
        assert transliterate("video", NAJD).startswith("f")

    def test_ng_is_ng_when_not_before_k(self):
        """§5.1.10: /ŋ/ → [nɡ] elsewhere — meeting ends [-inɡ]."""
        assert transliterate("meeting", NAJD) == "miːtinɡ"

    def test_ng_is_n_before_k(self):
        assert nativize("ŋk", NAJD) == "nk"

    def test_donor_stress_is_not_carried_over(self):
        """Stress is re-derived by the matrix rule, not imported."""
        assert "ˈ" not in nativize("ˈmiːtɪŋ", NAJD)

    def test_a_symbol_outside_the_inventory_projects_to_the_nearest(self):
        """MSA declares /q/ and /dʒ/ and no /ɡ/ — /ɡ/ is a Gulf reflex of qāf. So
        the Najdi reading of `meeting` is not an MSA reading of anything."""
        assert transliterate("meeting", "ar") == "miːtink"  # ɡ → nearest MSA [k]
        assert transliterate("meeting", "ar", strict=True) is None
        assert transliterate("meeting", NAJD) is not None


class TestInSentence:
    def test_a_loanword_is_read_not_spelled(self):
        """Left to the engine, `meeting` comes back as `meeˈting` — not IPA."""
        out = ArbtokG2PPlugin(lang=NAJD, diacritize=True).transcribe(
            "عندي meeting الساعة")
        assert out == "ˈʕindiː miːtinɡ asˈsaːʕa"

    def test_the_latin_letters_do_not_survive_into_the_ipa(self):
        """`meeting` used to come back as `meeˈting`: the letters themselves, which
        are not phonemes and have no embedding in a TTS frontend."""
        out = ArbtokG2PPlugin(lang=NAJD, diacritize=True).transcribe("Google مفيد")
        assert "G" not in out and "oo" not in out

    def test_the_arabic_around_it_is_unaffected(self):
        """أحب keeps its real shape — final geminate /bb/ (root ḥ-b-b) with the
        stress the weight rule assigns it — while the loan is nativized."""
        p = ArbtokG2PPlugin(lang=NAJD, diacritize=True)
        assert p.transcribe("أحب pizza") == "ʔaˈħabb biza"


class TestTableSelection:
    """The nativisation table is chosen by walking o2i's parent chain — no
    hardcoded lang→zone map. A leaf inherits its group's table; an un-studied
    lect lands on the conservative default."""

    def test_najdi_takes_the_alhoody_table(self):
        assert nativization_table(NAJD) is SEGMENT_MAP

    def test_egyptian_takes_its_own_table(self):
        """ar-EG carries a table cited to Hafez (1996)/Watson (2002)."""
        assert nativization_table(EG).get("θ") == "t"

    def test_lebanese_inherits_the_levantine_group_table(self):
        """ar-LB → ar-x-levantine: the leaf has no own table, its group does."""
        assert nativization_table("ar-LB") is nativization_table("ar-x-levantine")
        assert nativization_table("ar-SY") is nativization_table("ar-LB")
        assert nativization_table("ar-PS") is nativization_table("ar-LB")

    def test_kuwaiti_falls_back_to_the_default(self):
        """ar-KW walks ar-x-gulf → ar-x-peninsular → arb, none of which carries a
        table, so it lands on the conservative pan-Arabic default (documented
        fallback: Kuwaiti is served by the default, not a Gulf-specific map)."""
        assert nativization_table("ar-KW") is nativization_table("ar")
        assert nativization_table("ar-QA") is nativization_table("ar")

    def test_unknown_lect_falls_back_to_the_default(self):
        assert nativization_table("xx-YY") is nativization_table("ar")


class TestEgyptianTable:
    """Egyptian (Cairene) loanword phonology — Hafez (1996), *Phonological and
    Morphological Integration of Loanwords into Egyptian Arabic*, Égypte/Monde
    arabe 27–28, 383–410; consonant inventory from Watson (2002), *The Phonology
    and Morphology of Arabic*."""

    def test_p_becomes_b(self):
        """/p/ → [b] (Hafez p. 383)."""
        assert transliterate("pizza", EG) == "biza"

    def test_v_becomes_f(self):
        """/v/ → [f] (Hafez p. 385)."""
        assert transliterate("video", EG).startswith("f")

    def test_loan_dʒ_lands_on_the_cairene_stop_gim(self):
        """The Cairene ǧīm is the stop [ɡ] (Watson 2002), so a loan /dʒ/ adapts
        to it: *manager* → [manaɡa], where the Najdi keeps the affricate. The
        donor English reading is non-rhotic (o2i #846), so the final /r/ of
        *manager* is absent from the donor IPA in both dialects — this is a
        donor-reading fact upstream of the ǧīm reflex under test here, not a
        Cairene-vs-Najdi difference."""
        assert transliterate("manager", EG) == "manaɡa"
        assert transliterate("manager", NAJD) == "manadʒa"
        assert transliterate("manager", EG) != transliterate("manager", NAJD)

    def test_interdental_merges_into_the_dental_stop(self):
        """Cairene merged the interdentals into the stops (Hafez p. 385): /θ/ →
        [t]. The Najdi retains [θ], which its inventory declares."""
        assert transliterate("think", EG) == "tink"
        assert transliterate("think", NAJD) == "θink"

    def test_ʒ_is_retained_where_najdi_has_none(self):
        """/ʒ/ is a retained marginal loan phoneme in Cairene; Najdi has no /ʒ/
        and maps it to [dʒ] (Alhoody §5.1). Tested at the map layer because the
        English G2P renders orthographic ⟨g⟩/⟨ge⟩ as /dʒ/, not /ʒ/."""
        assert nativize("ɡaraːʒ", EG) == "ɡaraːʒ"
        assert nativize("ɡaraːʒ", NAJD) == "ɡaraːdʒ"

    def test_every_egyptian_output_stays_inside_the_eg_inventory(self):
        """The refusal path is per-table: what the Egyptian map emits must be
        realizable in the ar-EG inventory, else :func:`transliterate` returns
        ``None`` rather than an unpronounceable symbol."""
        for word in ("manager", "think", "video", "pizza", "meeting"):
            out = transliterate(word, EG)
            assert out is None or "θ" not in out  # θ is not an EG phoneme


class TestLevantineTable:
    """Levantine loanword phonology — Al-Saidat (2011), *English Loanwords in
    Jordanian Arabic*; Syrian vowel system from Cowell (1964), *A Reference
    Grammar of Syrian Arabic*."""

    def test_front_diphthong_monophthongises_to_the_native_mid_vowel(self):
        """The native mid long vowels [eː]/[oː] (Cowell 1964) give /eɪ/ → [eː],
        which the three-vowel Egyptian map has no target for — so *email* differs
        between the two lects."""
        assert transliterate("email", "ar-LB") == "imeːl"
        assert transliterate("email", EG) == "imil"

    def test_interdentals_are_kept(self):
        """The Levantine group declares /θ/ /ð/ (unlike Cairene), so they are
        retained rather than merged."""
        assert transliterate("think", "ar-PS") == "θink"


class TestDefaultTable:
    def test_msa_refuses_a_gulf_only_reflex(self):
        """The default table applies to plain ``ar``. MSA declares no /ɡ/, so the
        Najdi-style [-inɡ] of *meeting* maps its /ɡ/ onto MSA's nearest segment — the
        pre-per-table behaviour, preserved."""
        assert transliterate("meeting", "ar") == "miːtink"

    def test_default_still_nativizes_the_pan_arabic_core(self):
        """/p/ → [b], /v/ → [f] hold in the default too."""
        assert transliterate("pizza", "ar") == "biza"
        assert transliterate("video", "ar").startswith("f")


class TestNativizeFlag:
    """G3: ``nativize`` routes Latin runs. Default ``True`` (TTS) adapts them;
    ``False`` (linguistic output) leaves them untranscribed rather than inventing
    a reading."""

    def test_on_by_default_a_latin_run_is_read(self):
        assert ArbtokG2PPlugin(lang=NAJD).transcribe_word("meeting") == "miːtinɡ"

    def test_off_a_latin_word_is_left_untouched(self):
        assert ArbtokG2PPlugin(lang=NAJD, nativize=False).transcribe_word(
            "meeting") == "meeting"

    def test_off_a_latin_run_survives_in_a_sentence(self):
        out = ArbtokG2PPlugin(lang=NAJD, diacritize=True,
                              nativize=False).transcribe("عندي meeting الساعة")
        assert "meeting" in out
        assert out == "ˈʕindiː meeting asˈsaːʕa"
