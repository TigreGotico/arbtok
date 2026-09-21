"""The configuration a voice agent composes from TtsNorm's options, as the README shows it."""
from arbtok.textnorm import ARAB_PHONE_REGIONS, IDENTIFIER_WORDS, TtsNorm

VOICE_AGENT = TtsNorm(speak_percent=True, keep_code_digits=True, phone_regions=ARAB_PHONE_REGIONS,
                      long_digit_runs=True, identifier_words=IDENTIFIER_WORDS, cardinal_numbers=True,
                      leave_unspeakable_numbers=True, oblique_numbers=True, space_fused_hundreds=True,
                      spoken_forms=False, canonical_unicode=False)
