"""The nisba: a shadda the writing does not print.

The relative adjective — the *nisba* — is formed with the suffix **/-ijj/**,
written ⟨ـيّ⟩: عَرَبِيّ *ʕarabijj* 'Arab', مِصْرِيّ *misˤrijj* 'Egyptian' (Wright I
§249; Ryding 2005 §10.1). The suffix is a doubled yāʾ, and the doubling is what
makes it a nisba rather than a long vowel.

But ordinary Arabic prints no shadda, so the page shows a bare ⟨ـي⟩ — the *same*
letter that spells a plain long /iː/. The doubling is real and it is inaudible in
the writing, which is precisely the class of fact a diacritizer exists to restore.
It does not restore this one: given عربي it proposes عَرْبِي, a bare yāʾ, and the
word comes out */ʕarbiː/* instead of /ʕarabijj/.

So this puts the shadda back. Given the mark, the engine already reads the word
correctly — عَرَبِيّ has always transcribed as *ʕarabijj*. Nothing here touches
phonology; it restores an orthographic mark the writing omits, and the grapheme
table does the rest.

## When a final ⟨ي⟩ is *not* a nisba

The bare letter is genuinely ambiguous, and three classes take a plain /iː/:

* **Defective active participles** — the فاعِل pattern of a III-weak root, whose
  final radical *is* the yāʾ: بَاقِي *baːqiː* 'remaining', ثَانِي *θaːniː*
  'second', جَارِي *dʒaːriː* 'current'. These are identifiable from the spelling:
  the pattern is C-ā-C-ī, an alif in second position and the yāʾ final.
* **The 1sg possessive clitic** ‑ī — كِتَابِي *kitaːbiː* 'my book'. This is a
  clitic, not a suffix, and it is **not** decidable from the word alone: كتابي is
  *kitaːbiː* 'my book' and *kitaːbijj* 'bookish', and only the sentence says
  which. Out of context the nisba is the commoner reading, so that is what is
  given, and a caller who knows better supplies a lexicon.
* **Loanwords and foreign names** — تَاكْسِي *taːksiː*, تْشِيلِي *tʃiːliː*,
  زِيمْبَابْوِي *ziːmbaːbwiː*. A borrowed final /iː/ is a lexical fact about a
  word that was never built from an Arabic root, so no rule can reach it. This is
  what a lexicon is for.

The closed function words (الَّذِي, ذِي …) are listed, because a closed class is a
list and pretending otherwise is how a rule acquires exceptions it cannot state.
"""

from __future__ import annotations

import re
from typing import Set

__all__ = ["restore_nisba", "NOT_NISBA"]

_YA = "ي"        # ي
_SHADDA = "ّ"    # ّ
_KASRA = "ِ"     # ِ
_ALIF = "ا"      # ا
_MARKS = "ًٌٍَُِّْٰ"

#: A bare final ⟨ي⟩ that is a long vowel, not the nisba suffix. A closed class, so
#: it is a list rather than a rule.
#:
#: The nisba is formed on a NOUN or ADJECTIVE — it makes a relative adjective out of
#: a thing (مِصْر → مِصْرِيّ). A **preposition** has no nisba to form, so a final ⟨ي⟩
#: on one is not the suffix at all: it is the 1sg clitic ‑ī, 'me/my'. عِنْدِي is
#: 'I have', not *'ʕindijj'. Prepositions are a closed class, which is what makes
#: this statable (Wright I §§ 349-353).
NOT_NISBA: Set[str] = {
    # relative pronouns and demonstratives
    "الذي", "التي", "ذي", "اللذي", "اللتي",
    # preposition (or quasi-preposition) + the 1sg clitic
    "عندي", "لدي", "إلي", "الي", "علي", "في", "لي", "بي", "معي", "مني", "عني",
    # pronouns
    "هي",
    "الاولي",
}


def _strip(word: str) -> str:
    return "".join(c for c in word if c not in _MARKS)


def _is_defective_participle(skeleton: str) -> bool:
    """The فاعِل pattern of a III-weak root: بَاقِي, ثَانِي, جَارِي.

    Written C-ā-C-ī — the alif of the participle in second position and the yāʾ,
    which here is the root's own final radical and so a long vowel, not a suffix.
    """
    return bool(re.fullmatch(rf"[^{_ALIF}]{_ALIF}[^{_ALIF}]{_YA}", skeleton))


def restore_nisba(word: str) -> str:
    """Mark a final ⟨ي⟩ as the nisba /-ijj/ — ⟨ـِيّ⟩ — where it is one.

    The word is returned unchanged when the writing already decides the question
    (a shadda is printed, or the yāʾ carries a mark), and when the yāʾ belongs to
    one of the classes that take a plain long /iː/.
    """
    if not word.endswith(_YA) or len(_strip(word)) < 3:
        return word

    skeleton = _strip(word)
    if skeleton in NOT_NISBA or _is_defective_participle(skeleton):
        return word

    # A yāʾ the writing has already spoken for is not ours to respell.
    if _SHADDA in word:
        return word

    # The letter before the yāʾ carries the suffix's kasra: ـِيّ. Replace whatever
    # mark the model put there — a sukun before a nisba is not a reading of the
    # word, it is the model having missed the suffix.
    body = word[:-1]
    while body and body[-1] in _MARKS:
        body = body[:-1]
    if not body:
        return word

    return body + _KASRA + _YA + _SHADDA
