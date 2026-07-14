"""The lexicon answers for the words it knows, and only for those."""
import os
import unittest

from arbtok.diacritize import LatticeDiacritizer
from arbtok.lexicon import LexiconUnavailable, StemLexicon, parse

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))
from build_stem_lexicon import (  # noqa: E402
    count_tokens, select, stem, stems_by_key, undiacritize,
)

KITAB = "كِتَاب"
MADRASA = "مَدْرَسَة"


class TestStem(unittest.TestCase):
    def test_case_ending_is_stripped(self):
        for form in ("كِتَابٌ", "كِتَابَ", "كِتَابِ", "كِتَابُ"):
            self.assertEqual(stem(form), KITAB)

    def test_tanween_fath_takes_its_mute_alif_with_it(self):
        self.assertEqual(stem("كِتَابًا"), KITAB)

    def test_shadda_is_lexical_and_survives(self):
        self.assertEqual(stem("عَرَبِيٌّ"), "عَرَبِيّ")

    def test_pausal_sukun_is_an_ending_too(self):
        self.assertEqual(stem("كِتَابْ"), KITAB)

    def test_undiacritized_key(self):
        self.assertEqual(undiacritize(KITAB), "كتاب")


class TestMining(unittest.TestCase):
    def test_the_three_cases_collapse_into_one_entry(self):
        tokens = count_tokens(["كِتَابٌ كِتَابَ كِتَابِ"])
        from orthography2ipa import get
        grouped = stems_by_key(tokens, get("ar"))
        self.assertEqual(dict(grouped["كتاب"]), {KITAB: 3})

    def test_frequency_decides_and_the_runner_up_is_recorded(self):
        from orthography2ipa import get
        tokens = count_tokens(["كِتَابٌ " * 4 + "كَتَابٌ " * 2])
        entries = list(select(stems_by_key(tokens, get("ar")), min_count=2))
        self.assertEqual(entries, [("كتاب", KITAB, 4, 2)])

    def test_the_frequency_floor_drops_a_single_sighting(self):
        from orthography2ipa import get
        tokens = count_tokens(["كِتَابٌ"])
        self.assertEqual(list(select(stems_by_key(tokens, get("ar")),
                                     min_count=3)), [])

    def test_a_half_marked_word_is_not_evidence(self):
        from orthography2ipa import get
        tokens = count_tokens(["كِتاب " * 5])
        self.assertEqual(dict(stems_by_key(tokens, get("ar"))), {})

    def test_only_arabic_words_are_counted(self):
        tokens = count_tokens(["كِتَابٌ، hello 42 كتاب"])
        self.assertEqual(dict(tokens), {"كِتَابٌ": 1},
                         "punctuation is trimmed; Latin, digits and an unmarked "
                         "token are not evidence about vowels")


class TestStemLexicon(unittest.TestCase):
    def test_parse_keeps_the_first_entry_and_ignores_the_header(self):
        entries = parse("key\tstem\tcount\trunner_up\n"
                        f"كتاب\t{KITAB}\t120\t3\n"
                        "كتاب\tكَتَاب\t1\t0\n")
        self.assertEqual(entries, {"كتاب": KITAB})

    def test_an_unreachable_source_is_an_error(self):
        """A lexicon that was asked for and cannot be read is an error.

        Falling back to the model quietly would leave a caller with a system that
        looks like it has a lexicon, transcribes as if it has none, and says
        nothing — which is how a broken lexicon scores identically to a working
        one and nobody notices.
        """
        lex = StemLexicon("/nonexistent/ar-stems.tsv")
        with self.assertRaises(LexiconUnavailable):
            lex.get("كتاب")


class TestLookup(unittest.TestCase):
    """The lexicon is consulted before the model, and guarded like the model."""

    def _diacritizer(self, tmp, rows):
        path = os.path.join(tmp, "lex.tsv")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("key\tstem\tcount\trunner_up\n")
            for k, v in rows:
                fh.write(f"{k}\t{v}\t9\t0\n")
        return LatticeDiacritizer(lexicon=path)

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()

    def test_a_known_word_is_answered_without_the_model(self):
        d = self._diacritizer(self.tmp, [("كتاب", KITAB), ("مدرسة", MADRASA)])
        self.assertEqual(d.diacritize_word("كتاب"), KITAB)
        self.assertEqual(d.diacritize_word("مدرسة"), MADRASA)
        self.assertEqual(d.looked_up, ["كتاب", "مدرسة"])
        self.assertIsNone(d._diacritizer, "the model was never loaded")

    def test_an_entry_that_respells_the_word_is_refused(self):
        d = self._diacritizer(self.tmp, [("كتاب", "كُتُب")])
        self.assertIsNone(d._lookup("كتاب"))

    def test_an_unknown_word_is_left_to_the_model(self):
        d = self._diacritizer(self.tmp, [("كتاب", KITAB)])
        self.assertIsNone(d._lookup("مدرسة"))

    def test_a_marked_word_is_never_looked_up(self):
        d = self._diacritizer(self.tmp, [("كتاب", KITAB)])
        self.assertEqual(d.diacritize_word(KITAB), KITAB)
        self.assertEqual(d.looked_up, [])

    def test_the_full_iraab_is_not_the_lexicon_s_to_give(self):
        d = self._diacritizer(self.tmp, [("كتاب", KITAB)])
        d.waqf = False
        self.assertIsNone(d._lookup("كتاب"))

    def test_no_lexicon_means_no_lookup(self):
        d = LatticeDiacritizer(lexicon=None)
        self.assertIsNone(d.lexicon)
        self.assertIsNone(d._lookup("كتاب"))


if __name__ == "__main__":
    unittest.main()
