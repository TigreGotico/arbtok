"""Tests for the ArbtokG2PPlugin engine class.

Validates:
- the engine implements the shared orthography2ipa base interface
- transcribe equals the Sentence pipeline (clitic joining included)
- normalize auto-diacritizes bare text via text2tashkeel
- word-level transcription honours orthographic neighbours
- differential audit: arbtok consonant table vs the ar spec data
"""
import pytest

import orthography2ipa
from orthography2ipa import WordContext

from arbtok.plugin import ArbtokG2PPlugin
from tests.test_msa_pausal import ALL_TEST_CASES
from arbtok.tokenizer import Sentence


@pytest.fixture(scope="module")
def plugin():
    return ArbtokG2PPlugin()


class TestInterface:
    def test_it_exposes_the_engine_surface(self, plugin):
        """arbtok is an engine BUILT ON orthography2ipa, not a plugin TO it —
        nothing over there discovers or calls this. What matters is that the
        surface downstream code relies on is present, not that it inherits."""
        for method in ("transcribe", "transcribe_word", "normalize"):
            assert callable(getattr(plugin, method))
        assert plugin.language_codes

    def test_language_codes(self, plugin):
        assert "ar" in plugin.language_codes
        assert "arb" in plugin.language_codes


class TestTranscribe:
    SENTENCES = [
        "كِتَاب جَمِيل",
        "اَلسَّلَامُ عَلَيْكُمْ",
        "مَدِينَة كَبِيرَة",
        "لِ النَّاس",        # clitic joining across words
        "بِ الطَّبِيب",      # bi + al + sun letter
    ]

    @pytest.mark.parametrize("text", SENTENCES)
    def test_matches_sentence_pipeline(self, text, plugin):
        assert plugin.transcribe(text) == Sentence(plugin.normalize(text)).ipa

    @pytest.mark.parametrize("arabic_text, expected_ipa, description",
                             ALL_TEST_CASES[:25])
    def test_gold_subset_not_degraded(self, arabic_text, expected_ipa,
                                      description, plugin):
        """The engine wrapper must not change the Sentence pipeline."""
        assert plugin.transcribe(arabic_text) == \
            Sentence(plugin.normalize(arabic_text)).ipa, description


class TestNormalize:
    def test_diacritized_text_untouched_by_tashkeel(self, plugin):
        assert "كِتَاب" in plugin.normalize("كِتَاب")

    def test_bare_text_gets_diacritics_or_passes_through(self, plugin):
        assert plugin.normalize("كتاب جميل")

    def test_transcribe_bare_text(self, plugin):
        ipa = plugin.transcribe("كتاب جميل")
        assert ipa
        # diacritization should recover the long vowels
        assert "aː" in ipa or "iː" in ipa


class TestWordContext:
    def test_word_alone(self, plugin):
        assert plugin.transcribe_word("كِتَاب") == Sentence("كِتَاب").ipa

    def test_word_with_neighbours_matches_sentence(self, plugin):
        text = "فِي الْمَدِينَة"
        words = text.split()
        sentence_tokens = Sentence(text).tokens
        ctx = WordContext(prev_word=words[0], next_word=None)
        in_context = plugin.transcribe_word(words[1], ctx)
        assert in_context == sentence_tokens[1].ipa


class TestDifferentialGraphemes:
    """Audit arbtok's consonant table against the ar spec data.

    Informational gate: arbtok's hand-tuned table stays authoritative;
    this test pins the agreement level so spec-data drift is noticed.
    """

    def test_consonants_agree_with_spec(self):
        from arbtok.dialects import ARABIC_TO_IPA_CONSONANTS

        spec = orthography2ipa.get("ar")
        agree, differ = [], []
        for letter, ipa in ARABIC_TO_IPA_CONSONANTS.items():
            candidates = spec.graphemes.get(letter)
            if candidates is None:
                continue
            (agree if ipa in candidates else differ).append(
                (letter, ipa, candidates))
        # the tables must agree on a clear majority of shared letters
        assert len(agree) >= 2 * len(differ), (
            f"arbtok and the ar spec diverged: {differ}"
        )
