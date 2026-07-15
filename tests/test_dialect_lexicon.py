"""The per-lect closed-class lexicon: a hard prior for the function words a
dialect writes in MSA orthography but vocalizes its own way."""
import os
import tempfile
import unittest
from pathlib import Path

from orthography2ipa import get
from orthography2ipa.phonetok import PhonetokTokenizer, TokenKind

from arbtok.diacritize import LatticeDiacritizer, strip_marks
from arbtok.dialect_lexicon import (
    DialectLexicon, available_lects, lexicon_dir, lexicon_file, parse,
)
from arbtok.tokenizer import normalize_unicode

# A pan-Maghrebi entry that every Maghrebi lect inherits.
KI, KI_VOC = "كي", "كِي"          # how/like → /kiː/, not the MSA كَي /kaj/
# A Moroccan-specific entry.
DYAL, DYAL_VOC = "ديال", "دْيَال"  # genitive exponent, Moroccan only


class TestParse(unittest.TestCase):
    def test_header_blank_and_comment_lines_are_skipped(self):
        entries = parse("key\tvocalization\tsource\tgloss\n"
                        "# a comment\n"
                        "\n"
                        f"{KI}\t{KI_VOC}\tmarcais1977\thow\n")
        self.assertEqual(entries, {KI: KI_VOC})

    def test_first_entry_for_a_key_wins(self):
        entries = parse(f"{KI}\t{KI_VOC}\ta\n{KI}\tكَي\tb\n")
        self.assertEqual(entries[KI], KI_VOC)

    def test_the_source_and_gloss_columns_are_ignored_by_lookup(self):
        # A row with only key+vocalization is as valid as a fully-annotated one.
        self.assertEqual(parse(f"{KI}\t{KI_VOC}\n"), {KI: KI_VOC})


class TestDialectLexicon(unittest.TestCase):
    def test_a_lect_reads_its_own_entries(self):
        lex = DialectLexicon("ar-x-maghrebi")
        self.assertEqual(lex.get(KI), KI_VOC)

    def test_a_lect_inherits_its_parents_entries(self):
        # ar-MA carries its own ديال *and* the pan-Maghrebi كي from its parent.
        lex = DialectLexicon("ar-MA")
        self.assertEqual(lex.get(DYAL), DYAL_VOC, "Moroccan-specific entry")
        self.assertEqual(lex.get(KI), KI_VOC, "inherited pan-Maghrebi entry")

    def test_the_more_specific_file_wins_on_a_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "ar-x-maghrebi.tsv").write_text("شي\tشِي\tgroup\n",
                                                 encoding="utf-8")
            (d / "ar-MA.tsv").write_text("شي\tشَي\tleaf\n", encoding="utf-8")
            self.assertEqual(DialectLexicon("ar-MA", data_dir=d).get("شي"),
                             normalize_unicode("شَي"), "the leaf overrides group")

    def test_a_lect_with_no_file_is_a_cost_free_empty_map(self):
        lex = DialectLexicon("ar")  # MSA ships no closed-class lexicon
        self.assertEqual(len(lex), 0)
        self.assertIsNone(lex.get(KI))

    def test_loading_is_lazy(self):
        lex = DialectLexicon("ar-x-maghrebi")
        self.assertIsNone(lex._entries, "constructing one reads nothing")
        lex.get(KI)
        self.assertIsNotNone(lex._entries)


class TestPrecedence(unittest.TestCase):
    """The dialect lexicon is a hard prior: before the stem lexicon and the
    model, and answered without loading the model at all."""

    def _stem_lexicon(self, rows):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "stem.tsv")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("key\tstem\tcount\trunner_up\n")
            for k, v in rows:
                fh.write(f"{k}\t{v}\t9\t0\n")
        return path

    def test_a_dialect_word_is_answered_without_the_model(self):
        d = LatticeDiacritizer(lang="ar-x-maghrebi", lexicon=None)
        self.assertEqual(d.diacritize_word(KI), KI_VOC)
        self.assertEqual(d.dialect_looked_up, [KI])
        self.assertIsNone(d._diacritizer, "the model was never loaded")

    def test_the_dialect_lexicon_beats_the_stem_lexicon(self):
        # The stem lexicon offers a competing (MSA) reading for the same key;
        # the dialect prior is consulted first and wins.
        stem = self._stem_lexicon([(KI, "كَيّ")])
        d = LatticeDiacritizer(lang="ar-x-maghrebi", lexicon=stem)
        self.assertEqual(d.diacritize_word(KI), KI_VOC)
        self.assertEqual(d.dialect_looked_up, [KI])
        self.assertEqual(d.looked_up, [], "the stem lexicon was not consulted")

    def test_a_word_the_lect_does_not_list_falls_through(self):
        d = LatticeDiacritizer(lang="ar-x-maghrebi", lexicon=None)
        self.assertIsNone(d._dialect_lookup("قلم"))

    def test_disabling_the_dialect_lexicon_silences_it(self):
        d = LatticeDiacritizer(lang="ar-x-maghrebi", lexicon=None,
                               dialect_lexicon=False)
        self.assertIsNone(d.dialect_lexicon)
        self.assertIsNone(d._dialect_lookup(KI))


class TestGuards(unittest.TestCase):
    """An entry is data, and data can be wrong — so it is held to every guard a
    model proposal is."""

    def _with_entry(self, lang, key, voc):
        tmp = tempfile.mkdtemp()
        Path(tmp, f"{lang}.tsv").write_text(f"{key}\t{voc}\n", encoding="utf-8")
        d = LatticeDiacritizer(lang=lang, lexicon=None)
        d.dialect_lexicon = DialectLexicon(lang, data_dir=Path(tmp))
        return d

    def test_an_entry_that_respells_the_word_is_refused(self):
        # vocalization must add marks only; a different skeleton is not this word
        d = self._with_entry("ar-x-maghrebi", "كي", "كُتُب")
        self.assertIsNone(d._dialect_lookup("كي"))

    def test_an_unlicensed_entry_is_refused(self):
        # a Perso-Arabic گ the Maghrebi grapheme table does not declare
        d = self._with_entry("ar-x-maghrebi", "گي", "گِي")
        self.assertIsNone(d._dialect_lookup("گي"))

    def test_a_vocalized_input_is_never_overridden(self):
        # The author-complete gate runs first, and a marked surface form never
        # matches an undiacritized key: a human's marks stand.
        d = LatticeDiacritizer(lang="ar-x-maghrebi", lexicon=None)
        self.assertEqual(d.diacritize_word(KI_VOC), KI_VOC)
        self.assertEqual(d.dialect_looked_up, [])


class TestBundledData(unittest.TestCase):
    """Every shipped entry is well-formed: it marks its key, and the lect's own
    orthography licenses its vocalization."""

    def test_there_are_bundled_lexicons(self):
        self.assertTrue(available_lects())
        self.assertIn("ar-x-maghrebi", available_lects())

    def test_every_entry_marks_its_key_and_is_licensed(self):
        for lect in available_lects():
            spec = get(lect)
            tokenizer = PhonetokTokenizer(spec)
            entries = parse(lexicon_file(lect).read_text(encoding="utf-8"))
            self.assertTrue(entries, f"{lect} lexicon is empty")
            for key, voc in entries.items():
                self.assertEqual(
                    strip_marks(normalize_unicode(voc)), key,
                    f"{lect}: {voc!r} does not spell its key {key!r}")
                tokens = tokenizer.tokenize(normalize_unicode(voc))
                self.assertTrue(
                    all(t.kind is not TokenKind.UNKNOWN for t in tokens),
                    f"{lect}: {voc!r} is not licensed by its own spec")


if __name__ == "__main__":
    unittest.main()
