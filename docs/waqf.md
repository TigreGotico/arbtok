# Waqf, the register switch

<!-- agent-hint
covers: the pausal and full registers, the register argument, and which reductions a dialect lect keeps
source: arbtok/waqf.py, arbtok/sandhi.py, arbtok/plugin.py
generated: no
verify: .venv/bin/python scripts/check_docs_examples.py docs/waqf.md
see: tashkeel.md, api.md, benchmarks.md
-->

Read aloud, Arabic **pauses in waqf form** (Wright, *A Grammar of the Arabic
Language*, 3rd ed., I §372. Ryding, *A Reference Grammar of MSA*, CUP 2005,
§2.4). At a phrase boundary the word-final short vowel, the case or mood ending
(iʿrāb), is not pronounced. Tanwīn *-un* and *-in* drop with their /n/. Tanwīn
*-an* lengthens to /aː/ on its written seat alif. A tāʾ marbūṭa that only its
ending voices falls silent with it: `مَدِينَةٌ.` reads *madiːna*. The
construct-state /at/, where an iḍāfa head pauses with its tāʾ, is **not
modeled**.

## The `register` argument

The named switch is `register`. `"pausal"` is the default, the TTS register.
`"full"` is continuous full-iʿrāb passthrough. Under `"full"` every waqf
reduction is off and every written ending is read out. This is the recitation
and pedagogical register. It is also the mode for fully vocalized MSA that
should be read exactly as its author pointed it, and for scoring against
iʿrāb-keeping gold:

```python
from arbtok.plugin import ArbtokG2PPlugin

print(ArbtokG2PPlugin(register="pausal").transcribe("رَأَيْتُ كِتَابًا."))
# raˈʔajtu kiˈtaːbaː
print(ArbtokG2PPlugin(register="full").transcribe("رَأَيْتُ كِتَابًا."))
# raˈʔajtu kiˈtaːban
print(ArbtokG2PPlugin(register="pausal").transcribe("مَدِينَةٌ."))
# maˈdiːna
print(ArbtokG2PPlugin(register="full").transcribe("مَدِينَةٌ."))
# maˈdiːnatun
```

Under `register="pausal"`, a pause has to be **written**, as a punctuation
token. The engine invents no pause at the edge of the input. When the
diacritizer runs on bare text, it restores the pausal register throughout,
because the modern spoken register keeps no iʿrāb at all. The boolean
`pausal=True` or `pausal=False` is the original spelling of the same switch. It
wins when you pass it explicitly.

## Dialect lects

The iʿrāb-driven reductions are facts about the MSA and Classical registers
only. A dialect lect has no case endings to drop. Its final short vowels and its
lexicalized *-an* adverbs are read as written under either register:

```python
print(ArbtokG2PPlugin(lang="ar-EG", register="full").transcribe("أَهْلًا وَسَهْلًا"))
# ˈʔahlan waˈsahlan
print(ArbtokG2PPlugin(lang="ar-EG").transcribe("أَهْلًا وَسَهْلًا"))
# ˈʔahlan waˈsahlan
```

Both modes run the same lattice and the same rescorers. The flag is consulted in
one place, `arbtok.sandhi`, so the transform applies exactly once.

---
[← Varieties](dialects.md) · [Home](index.md) · [Arabizi input →](arabizi.md)
