"""
I'm just a dude trying to create TTS voices to help the visually impaired arabic community.

I am not an arabic speaker, I never had any previous interaction with the arabic script, this might be a pointless experiment powered by LLM hallucinations.

You have been warned.

if you speak MSA pull requests welcome!

- test.py contains a reference dataset to benchmark the code against, IPA transcriptions have been LLM generated
- main logic is in tokenizer.py
- see tests folder for some benchmarks and comparison against pre existing (low quality) datasets
- varieties are orthography2ipa specs, named by code (ar, ar-SA-x-najd,
  ar-SA-x-hejaz, ar-EG, ar-x-gulf, …): the spec supplies the grapheme table and
  the allophone rules, so a variety's phonology comes from cited spec data.
  Pass `lang=` — see docs/dialects.md

``supported_lects()`` enumerates every variety `lang=` resolves to, each with
its orthography2ipa quality tier.
"""

from arbtok.dialects import Lect, spec_for_lang, supported_lects

__all__ = ["Lect", "spec_for_lang", "supported_lects"]