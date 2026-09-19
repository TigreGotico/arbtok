"""Diacritization as a *guarded* step, not a free generation.

Restoring tashkeel is a statistical problem — which vowel follows a letter is
morphological and syntactic, and the letters say none of it — so it belongs to a
model — arbtok's bundled rawi ensemble (:mod:`arbtok._ensemble`). But a model
asked to write
into a word can write *anything*, including a reading the orthography does not
license and a consonant that was never there. Downstream, that is indetectable:
the phonemizer will faithfully transcribe the hallucination.

arbtok is the one library that knows about both the diacritizer and the
orthography2ipa lattice, so it is where the two meet. The model **proposes**; the
lattice **disposes**.

Two of the three guards this once carried live at **decision time**, where they
belong. The ensemble decodes under an orthographic constraint
(:mod:`arbtok.orthography`, applied in :mod:`arbtok._ensemble`): it cannot rewrite
a letter the writing spells, and it cannot overwrite a mark a human wrote, because
the classes that would do so are masked out before the argmax. Those are facts
about Arabic and about the model's class space — no lattice is needed to know
them, so no lattice should have to.

Before any of that, though, comes the cheapest guard of all: **a known word is a
known word**. Which vowels a word carries is a lexical fact, and a model asked to
re-derive a lexical fact will sometimes derive it wrong — so :mod:`arbtok.lexicon`
is consulted first, and the model is only asked about words nobody has written
down (see that module for why the entry is a diacritized *stem* and not IPA).

What is left here is the part that genuinely needs a lattice:

1. **Only act where the writing is actually silent.** orthography2ipa reports
   which letters are underdetermined (:func:`~orthography2ipa.is_underdetermined`),
   so a fully-marked word is never handed to a model at all.
2. **The result must be licensed.** The diacritized word is tokenized against the
   *variety's own* grapheme table. A mark sequence the orthography does not admit
   is not an answer, and only the spec knows which those are.

The lattice guards the lexicon exactly as it guards the model: an entry that the
variety's orthography does not license is refused like any other proposal. The
lexicon is data, and data can be wrong.

A refused proposal falls back to the word as written — an underdetermined reading,
which orthography2ipa reports as such, rather than a confident wrong one. The
skeleton check stays as a cheap backstop: it should now never fire, and if it does,
something upstream has regressed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence

from orthography2ipa import get, is_underdetermined, underdetermined_positions
from orthography2ipa.phonetok import PhonetokTokenizer, TokenKind

from arbtok.dialect_lexicon import DialectLexicon
from arbtok.lexicon import DEFAULT_LEXICON, StemLexicon
from arbtok.nisba import restore_nisba
from arbtok.dialects import DEFAULT_LANG
from arbtok.tokenizer import normalize_unicode

__all__ = ["LatticeDiacritizer", "DiacritizedWord", "DiacritizedText",
           "diacritize", "strip_marks", "repair_skeleton"]

#: Every Arabic mark a diacritizer may add. Anything else it emits is a letter.
_MARKS = set("ًٌٍَُِّْٰٓ")

#: Letters the rawi models legitimately RESTORE rather than merely mark: a bare
#: alif typed for a hamza carrier, and the silent dagger-alef. This is a
#: documented widening of the task (the rawi models fix real,
#: inconsistently-spelled input), so a change confined to these is not a
#: hallucination. Keyed by what may replace what.
_RESTORABLE = {
    "ا": {"أ", "إ", "آ", "ٱ"},   # bare alif → a hamza carrier
    "ه": {"ة"},                   # hāʾ → tāʾ marbūṭa
    "ي": {"ى"},                   # yāʾ → alif maqṣūra
}


#: The definite article's hamzat al-waṣl and its lām. Neither ever carries a
#: mark — the alif is a connective seat and the lām is either the moon /l/ or
#: sun-assimilated — so a word left "underdetermined" *only* at these positions
#: is not underdetermined in any way a model can help with. The article may sit
#: behind a single one-consonant proclitic (wa-, bi-, fa-, ka-, li-).
_ARTICLE_RE = re.compile(r"^[وفبكل]?[َُِ]?(?:ا|ٱ|أ)ل")

#: A leading proclitic consonant written bare against a stem the author has
#: marked. The proclitic's reading is the spec's to fix — orthography2ipa reads
#: an unmarked ⟨و⟩ before a consonant as the clitic cluster /w/ (وكَان →
#: ``wkaːn``, the dialect gold's form), and a modeled fatḥa (وَكَان →
#: ``wakaːn``) is a register guess the author did not write.
_BARE_PROCLITIC_RE = re.compile(r"^[وفبكلس](?=[^\sًٌٍَُِّْٰٓ])")


def _author_complete(word: str, positions) -> bool:
    """True when a human has fully pointed *word* to the gold's convention.

    ``orthography2ipa`` reports the leading article's alif/lām as
    underdetermined because they carry no mark, yet their reading is fixed —
    the alif is hamzat al-waṣl and the lām is resolved by the sun/moon rescorer,
    not by any vowel a diacritizer could add. When those are the *only* silent
    positions the word is complete as written, and handing it to the model can
    only re-guess marks the author already committed (a fully-marked ⟨عِيش⟩
    re-read as a glide /ʕijʃ/ instead of the written /ʕiːʃ/). Such a word is
    passed through untouched.

    The same holds for a bare proclitic consonant heading an otherwise-marked
    stem: an author who pointed كَان but left the و of وكَان bare has written
    the clitic as the dialect says it — /w/, the reading the spec path gives —
    and the only thing a model can add there is a case-register fatḥa the
    author chose not to write. The proclitic position therefore counts as
    already answered *when the rest of the word is*; a bare word stays the
    model's to vocalize.
    """
    if not positions:
        return True
    m = _ARTICLE_RE.match(word)
    if not m:
        return False
    # The alif and the lām are the two characters the match ends on.
    article = {m.end() - 2, m.end() - 1}
    return set(positions) <= article


def _proclitic_complete(word: str, positions) -> bool:
    """True when the ONLY silent position is a bare leading proclitic.

    Checked *after* the closed-class and stem lexicons — a two-letter word
    like كِي is itself a lexicon entry, not a clitic on a one-letter stem —
    and before the model: the author marked everything except the clitic
    consonant, whose bare form the spec path already reads as the cluster
    /w/ the dialect gold records (see ``_BARE_PROCLITIC_RE``).
    """
    return bool(positions) and set(positions) == {0} \
        and _BARE_PROCLITIC_RE.match(word) is not None and len(word) > 2


def strip_marks(text: str) -> str:
    """The consonantal skeleton: *text* with every diacritic removed."""
    return "".join(ch for ch in text if ch not in _MARKS)


def repair_skeleton(original: str, proposed: str) -> Optional[str]:
    """Keep the model's **marks**, restore the original **letters**.

    A diacritizer's job is to mark a word, so when it also swaps a letter the
    marks are usually still right and only the letter is wrong. Rejecting the
    whole proposal throws away good marks with the bad letter; repairing keeps
    them and puts our letter back.

    This is not hypothetical. The rawi models systematically rewrite the alef
    madda ⟨آ⟩ to a plain hamza carrier ⟨أ⟩ — destroying the long /aː/ it stands
    for (آبد /ʔaːbid/ came back as أَبْد /ʔabd/) — on about 6.5% of a WikiPron
    Arabic sweep. Repairing those words rather than dropping them is worth
    ~0.7 PER and ~0.5 WER points on that set, and it is strictly better than
    rejecting on every metric measured.

    Returns ``None`` when the skeletons do not align one-to-one, in which case
    the proposal cannot be repaired and must be refused.
    """
    original_letters = strip_marks(original)
    if len(original_letters) != len(strip_marks(proposed)):
        return None
    out: List[str] = []
    i = 0
    for ch in proposed:
        if ch in _MARKS:
            out.append(ch)
        else:
            out.append(original_letters[i])
            i += 1
    return "".join(out)


def _skeleton_is_preserved(original: str, diacritized: str) -> bool:
    """True when the model only *marked* the word, or restored a licensed letter.

    A diacritizer's contract is to add marks. If the letters come back different,
    the model rewrote the word — and the phonemizer downstream has no way to
    know. The one sanctioned exception is the restoration a rawi model is
    explicitly built to do (a bare alif that should carry a hamza, a hāʾ that
    should be a tāʾ marbūṭa).
    """
    before, after = strip_marks(original), strip_marks(diacritized)
    if before == after:
        return True
    if len(before) != len(after):
        return False
    for a, b in zip(before, after):
        if a == b:
            continue
        if b not in _RESTORABLE.get(a, ()):
            return False
    return True


#: Where a word's marks came from. The one that matters is ``model``: it says the
#: lect contributed nothing but a veto, and the veto cannot fire on a well-formed
#: MSA reading — every Arabic spec declares every ḥaraka — so the model's Modern
#: Standard prior decided the word unopposed. A corpus filtered to words the lect
#: actually constrained is a different corpus from one filtered on the lect label,
#: and this field is what tells them apart.
PROVENANCE = (
    "author",          # the writing already said it; nothing was added
    "closed-class",    # the lect's own lexicon, a hard prior over the model
    "stem-lexicon",    # somebody wrote this stem down
    "proclitic",       # marked but for a bare leading clitic the spec reads bare
    "model",           # rawi proposed it and the orthography licensed it
    "model-repaired",  # rawi rewrote a letter; the marks were kept and the letter put back
    "refused",         # unrepairable or unlicensed: left as written
    "not-arabic",      # no Arabic letter in it: a Latin embed, a number, punctuation
)


def _has_arabic(word: str) -> bool:
    """True when *word* contains a letter in an Arabic block.

    A token with none is not a diacritization failure and must not be counted as
    one. On the code-switched gold every single refusal in ar-EG was an English
    embed — the words that set exists to carry — so a caller filtering on
    ``refused`` to find failures got a pile of English instead.
    """
    return any("\u0600" <= c <= "\u06ff" or "\u0750" <= c <= "\u077f"
               or "\ufb50" <= c <= "\ufdff" or "\ufe70" <= c <= "\ufeff"
               for c in word)


@dataclass(frozen=True)
class DiacritizedWord:
    """One word, its result, and which stage decided it."""

    surface: str
    output: str
    provenance: str

    @property
    def lect_constrained(self) -> bool:
        """True when something the lect declares chose this word's marks.

        ``model`` is excluded deliberately, and the reason is measured rather than
        argued. Licensing is a veto over letters, not a preference over readings, so a
        well-formed MSA vocalization passes it untouched — six MSA vocalizations against
        four dialect specs, zero rejections. The veto is not *inert*, though: over the
        636 model-path words of the shipped gold, 5 carry a reading at least one lect in
        the roster would reject, the narrower Omani and southern Saudi specs among them.
        Five is enough to refute "the veto never fires" and not enough to say how often
        it does: a numerator of 5 over 636, on one gold, is not a rate.
        So ``model`` means the lect did not object, not that it could not — and not
        objecting is weaker evidence than choosing, which is why it does not count here.
        """
        return self.provenance in ("closed-class", "author", "proclitic")

    @property
    def is_failure(self) -> bool:
        """True only for an Arabic word the pipeline could not mark.

        ``not-arabic`` is excluded: a Latin embed has no diacritization to fail at.
        """
        return self.provenance == "refused"


@dataclass(frozen=True)
class DiacritizedText:
    """The diacritized string and a record per word, in order."""

    text: str
    words: Sequence[DiacritizedWord]

    def __str__(self) -> str:
        return self.text

    @property
    def by_provenance(self) -> dict:
        out: dict = {}
        for w in self.words:
            out.setdefault(w.provenance, []).append(w.surface)
        return out


class LatticeDiacritizer:
    """Diacritize a word only where the writing is silent, and only if licensed.

    ``lang`` names the orthography2ipa variety whose grapheme table licenses the
    result. ``waqf`` drops the case endings from the model's output, giving the
    pausal form that is actually spoken rather than the fully-parsed form the
    model restores (see :mod:`arbtok.waqf`). ``lexicon`` names the
    diacritized-stem lexicon consulted before the model — a path, a URL, an
    ``hf://`` id, or ``None`` to ask the model about every word.
    """

    def __init__(
        self,
        lang: str = DEFAULT_LANG,
        waqf: bool = True,
        lexicon: Optional[str] = DEFAULT_LEXICON,
        dialect_lexicon: bool = True,
        model_path: Optional[str] = None,
        vocab_path: Optional[str] = None,
    ) -> None:
        self.lang = lang
        #: An alternative rawi export and its class vocabulary, or None for the
        #: bundled pair. Here so a register-tuned model can be measured against the
        #: bundled one without editing the library.
        self.model_path = model_path
        self.vocab_path = vocab_path
        self.waqf = waqf
        self._diacritizer = None
        self._spec = get(lang)
        self._tokenizer = PhonetokTokenizer(self._spec)
        self.lexicon = StemLexicon(lexicon) if lexicon else None
        #: The lect's closed-class lexicon, consulted as a hard prior *before*
        #: the stem lexicon and the model — the function words a dialect spells
        #: in MSA orthography but vocalizes its own way (see
        #: :mod:`arbtok.dialect_lexicon`). Empty for a lect that ships none.
        self.dialect_lexicon = DialectLexicon(lang) if dialect_lexicon else None
        #: Words the model proposed and the lattice refused outright, in order.
        self.rejected: List[str] = []
        #: Words whose letters the model rewrote and we put back, keeping its
        #: marks. Chiefly the alef-madda class — see :func:`repair_skeleton`.
        self.repaired: List[str] = []
        #: Words answered from the stem lexicon, which the model never saw.
        self.looked_up: List[str] = []
        #: Words answered from the lect's closed-class lexicon (the hard prior),
        #: which neither the stem lexicon nor the model saw.
        self.dialect_looked_up: List[str] = []

    @property
    def diacritizer(self):
        if self._diacritizer is None:
            from arbtok._ensemble import get_ensemble
            self._diacritizer = get_ensemble(self.model_path, self.vocab_path)
        return self._diacritizer

    def _propose(self, word: str) -> str:
        """The model's reading of *word* — constrained argmax over the bundled
        ensemble, reduced to its pausal form when ``waqf`` is on (the transform
        the model cannot know: :func:`arbtok.waqf.pausal`)."""
        proposed = self.diacritizer.diacritize(word)
        if self.waqf:
            from arbtok.waqf import pausal
            proposed = pausal(proposed)
        return proposed

    def _lookup(self, word: str) -> Optional[str]:
        """The lexicon's stem for *word*, if it has one the orthography licenses.

        An entry is held to every check a model's proposal is: it must spell the
        word we were given (marks added, letters untouched) and it must tokenize
        against the variety's grapheme table. A stem that fails either is not a
        fact about this word, and the model is asked instead.
        """
        if self.lexicon is None or not self.waqf:
            return None
        stem = self.lexicon.get(word)
        if stem is None:
            return None
        stem = restore_nisba(stem)
        if strip_marks(stem) != strip_marks(word) or not self._is_licensed(stem):
            return None
        return stem

    def _dialect_lookup(self, word: str) -> Optional[str]:
        """The lect's closed-class vocalization for *word*, if it has one the
        orthography licenses.

        Held to the same guards as a model proposal and a stem entry: the
        vocalization must spell the word we were given (marks added, letters
        untouched) and it must tokenize against the variety's grapheme table.
        These are register-invariant function words with no iʿrāb, so — unlike
        the pausal stem lexicon — the entry answers in both waqf modes.
        """
        if self.dialect_lexicon is None:
            return None
        voc = self.dialect_lexicon.get(word)
        if voc is None:
            return None
        if strip_marks(voc) != strip_marks(word) or not self._is_licensed(voc):
            return None
        return voc

    def _is_licensed(self, word: str) -> bool:
        """True when every part of *word* maps to a grapheme the spec declares."""
        try:
            tokens = self._tokenizer.tokenize(normalize_unicode(word))
        except Exception:
            return False
        return all(t.kind is not TokenKind.UNKNOWN for t in tokens)

    def diacritize_word(self, word: str) -> str:
        """Return *word* diacritized, or unchanged if it needs nothing or the
        proposal is refused."""
        return self.diacritize_word_record(word).output

    def diacritize_word_record(self, word: str) -> DiacritizedWord:
        """*word* diacritized, with the stage that decided it.

        The same pipeline as :meth:`diacritize_word` — this is where it lives, and
        that method reads the ``output`` off this one, so the two cannot drift."""
        # (0) Nothing Arabic in it — a Latin embed, a number, punctuation. Not a
        # refusal: there was never a diacritization to attempt.
        if not _has_arabic(word):
            return DiacritizedWord(word, word, "not-arabic")

        normalized = normalize_unicode(word)
        # (1) The writing already says it — never overwrite a human's marks. A
        # word is "already said" when every silent position is the definite
        # article's alif/lām, whose reading the lattice fixes without a model;
        # re-marking such a word only lets the model overrule the author (see
        # ``_author_complete``).
        positions = underdetermined_positions(normalized, self._spec)
        if _author_complete(normalized, positions):
            return DiacritizedWord(word, word, "author")

        # (2a) The lect writes this word in MSA orthography but does not say it
        # the MSA way — a closed-class function word whose dialect vocalization
        # the grammar records. A hard prior: it is consulted before the stem
        # lexicon and the model, because here the model's answer is not merely
        # uncertain, it is confidently for the wrong variety.
        dialect = self._dialect_lookup(normalized)
        if dialect is not None:
            self.dialect_looked_up.append(word)
            return DiacritizedWord(word, dialect, "closed-class")

        # (2b) Somebody already wrote this word down. A lexicon entry is a pausal
        # stem, so it answers the waqf question and no other: with the case
        # endings asked for, only the model can supply them.
        entry = self._lookup(normalized)
        if entry is not None:
            self.looked_up.append(word)
            return DiacritizedWord(word, entry, "stem-lexicon")

        # (2c) Author-near-complete: everything is marked except a bare leading
        # proclitic. The spec path reads that clitic without a vowel (وكَان →
        # /wkaːn/, the dialect gold's form); the model would only add a
        # register fatḥa the author did not write. Checked after the lexicons
        # so a short closed-class word still gets its recorded vocalization.
        if _proclitic_complete(normalized, positions):
            return DiacritizedWord(word, word, "proclitic")

        proposed = self._propose(normalized)
        how = "model"

        # (3) A diacritizer marks; it does not rewrite. When it did rewrite a
        # letter, the marks are usually still right — so keep them and put our
        # letter back, rather than throwing the whole proposal away. Only a
        # proposal that cannot be repaired (the skeletons do not align) is
        # refused.
        if not _skeleton_is_preserved(normalized, proposed):
            repaired = repair_skeleton(normalized, proposed)
            if repaired is None:
                self.rejected.append(word)
                return DiacritizedWord(word, word, "refused")
            self.repaired.append(word)
            proposed = repaired
            how = "model-repaired"

        # (4) The nisba's shadda is not printed, and the model does not restore
        # it: عربي comes back as a bare yāʾ and reads /ʕarbiː/, not /ʕarabijj/.
        # Put the mark back before licensing, so the result is held to the
        # grapheme table like any other proposal.
        proposed = restore_nisba(proposed)

        # (5) The orthography must license the result.
        if not self._is_licensed(proposed):
            self.rejected.append(word)
            return DiacritizedWord(word, word, "refused")

        return DiacritizedWord(word, proposed, how)

    def diacritize(self, text: str) -> str:
        """Diacritize each word of *text*, guarding every one of them."""
        return self.diacritize_text(text).text

    def diacritize_text(self, text: str) -> DiacritizedText:
        """*text* diacritized, with a record per word in order.

        Whitespace-only tokens keep their place in the string and carry no record,
        so ``words`` is the words and ``text`` is what a caller would have got from
        :meth:`diacritize`."""
        out, records = [], []
        for w in text.split(" "):
            if not w.strip():
                out.append(w)
                continue
            rec = self.diacritize_word_record(w)
            records.append(rec)
            out.append(rec.output)
        return DiacritizedText(" ".join(out), tuple(records))

    __call__ = diacritize


#: Diacritizers are cached per lect: the ONNX session and the lexicons are built
#: once and a caller asking for the same variety twice gets the same reader.
_BY_LECT: dict = {}


def diacritize(text: str, lect: str = DEFAULT_LANG, **kwargs) -> DiacritizedText:
    """Diacritize *text* as *lect* speaks it, with a record per word.

    The lect-aware entry point a caller wants when it needs marks rather than
    phones: no phonemization, no IPA, just the vocalized text and where each
    word's marks came from.

        >>> out = diacritize("كتاب جديد", "ar-EG")       # doctest: +SKIP
        >>> str(out)                                      # doctest: +SKIP
        'كِتَاب جَدِيد'
        >>> [(w.surface, w.provenance) for w in out.words]  # doctest: +SKIP
        [('كتاب', 'model'), ('جديد', 'model')]

    ``provenance`` is the reason this exists rather than a convenience. A word
    marked ``model`` was decided by rawi's Modern Standard prior with nothing from
    the lect opposing it — the orthography licenses letters, not readings, and
    every Arabic spec declares every ḥaraka, so a well-formed MSA vocalization
    passes the check untouched. Filtering a corpus to
    ``w.lect_constrained`` keeps the words the variety actually decided.

    Keyword arguments are passed to :class:`LatticeDiacritizer` (``waqf``,
    ``lexicon``, ``dialect_lexicon``); a call that passes any is not cached.
    """
    if kwargs:
        return LatticeDiacritizer(lang=lect, **kwargs).diacritize_text(text)
    if lect not in _BY_LECT:
        _BY_LECT[lect] = LatticeDiacritizer(lang=lect)
    return _BY_LECT[lect].diacritize_text(text)
