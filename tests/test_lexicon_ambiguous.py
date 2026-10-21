"""In a sentence, the stem lexicon steps aside for a spelling whose runner-up reading is common.

Its top reading is right on 62.8% of held-out words whose runner-up holds 25 to 40% of the two
readings, where the model reading the sentence is right on 83.6%, and the model gains in every
sentence length measured from three words up. So in a sentence of at least MIN_CONTEXT_WORDS
words a spelling whose runner-up holds at least AMBIGUOUS_SHARE is left to the model. A word read
alone, or in a shorter sentence, is answered from the lexicon as before.
"""
import os
import tempfile
import unittest

from arbtok.diacritize import LatticeDiacritizer
from arbtok.fusion import FusionDiacritizer
from arbtok.lexicon import AMBIGUOUS_SHARE, MIN_CONTEXT_WORDS, StemLexicon, parse_shares
from arbtok.tokenizer import normalize_unicode

KITAB = "كِتَاب"
ANNA = "أَنَّ"


def _lexicon(rows):
    fd, path = tempfile.mkstemp(suffix=".tsv")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("key\tstem\tcount\trunner_up\n")
        for row in rows:
            fh.write("\t".join(str(x) for x in row) + "\n")
    return path


class TestAmbiguousShare(unittest.TestCase):
    def test_the_rule_is_ten_percent_in_three_words(self):
        self.assertEqual((AMBIGUOUS_SHARE, MIN_CONTEXT_WORDS), (0.10, 3))

    def test_in_a_sentence_an_ambiguous_spelling_is_left_to_the_model(self):
        lex = StemLexicon(_lexicon([("أن", ANNA, 90, 10)]))
        self.assertIsNone(lex.get("أن", 3))
        self.assertTrue(lex.ambiguous("أن"))

    def test_a_word_read_alone_or_in_two_words_is_answered(self):
        lex = StemLexicon(_lexicon([("أن", ANNA, 60, 40)]))
        self.assertEqual(lex.get("أن"), normalize_unicode(ANNA))
        self.assertEqual(lex.get("أن", 2), normalize_unicode(ANNA))

    def test_a_spelling_just_under_the_share_is_answered_in_a_sentence(self):
        lex = StemLexicon(_lexicon([("كتاب", KITAB, 91, 9)]))
        self.assertEqual(lex.get("كتاب", 8), normalize_unicode(KITAB))

    def test_an_entry_without_counts_is_never_ambiguous(self):
        fd, path = tempfile.mkstemp(suffix=".tsv")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(f"كتاب\t{KITAB}\n")
        self.assertEqual(StemLexicon(path).get("كتاب", 8), normalize_unicode(KITAB))

    def test_none_consults_the_lexicon_for_every_spelling(self):
        lex = StemLexicon(_lexicon([("أن", ANNA, 50, 50)]), ambiguous_share=None)
        self.assertEqual(lex.get("أن", 8), normalize_unicode(ANNA))

    def test_the_share_is_runner_up_over_both(self):
        shares = parse_shares("key\tstem\tcount\trunner_up\nأن\tx\t75\t25\nكتاب\ty\t9\t0\n")
        self.assertEqual(shares, {"أن": 0.25, "كتاب": 0.0})


class TestTheDiacritizers(unittest.TestCase):
    def setUp(self):
        self.path = _lexicon([("أن", ANNA, 60, 40), ("كتاب", KITAB, 99, 1)])

    def test_the_fusion_diacritizer_hands_an_ambiguous_word_to_its_sentence(self):
        d = FusionDiacritizer(lexicon=self.path)
        d._context_words = 5
        self.assertIsNone(d._lookup("أن"))
        self.assertIsNotNone(d._lookup("كتاب"))
        d._context_words = 2
        self.assertIsNotNone(d._lookup("أن"))
        d._context_words = None
        self.assertIsNotNone(d._lookup("أن"))

    def test_the_fusion_diacritizer_can_keep_the_old_behaviour(self):
        d = FusionDiacritizer(lexicon=self.path, ambiguous_share=None)
        d._context_words = 5
        self.assertIsNotNone(d._lookup("أن"))

    def test_a_token_without_an_arabic_letter_is_not_a_word_of_the_sentence(self):
        # the measurement counted Arabic words: two of them and a Latin word, a digit or a
        # spaced question mark are still two, and the rule keeps the lexicon for them
        rule, before = FusionDiacritizer(), FusionDiacritizer(ambiguous_share=None)
        for text in ("من لحمك weekend", "من لحمك 5", "من لحمك ؟", "من لحمك ٥"):
            self.assertEqual(rule.diacritize(text), before.diacritize(text), text)

    def test_the_word_by_word_diacritizer_is_unchanged(self):
        # it reads each word alone, so there is no sentence to hand the word to
        d = LatticeDiacritizer(lexicon=self.path)
        self.assertIsNotNone(d._lookup("أن"))


if __name__ == "__main__":
    unittest.main()
