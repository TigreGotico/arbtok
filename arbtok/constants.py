import string
from typing import Set

# ==============================================================================
# ARABIC CONSTANTS
# ==============================================================================

# --- Diacritics (Tashkeel) ---
FATHA = '\u064E'  # َ (short a)
DAMMA = '\u064F'  # ُ (short u)
KASRA = '\u0650'  # ِ (short i)
SHADDA = '\u0651'  # ّ (consonant doubling/gemination)
SUKUN = '\u0652'  # ْ (no vowel/silence)
TANWIN_FATH = '\u064B'  # ً (an)
TANWIN_DAMM = '\u064C'  # ٌ (un)
TANWIN_KASR = '\u064D'  # ٍ (in)
DAGGER_ALIF = '\u0670'  # ٰ (superscript alef, long a)
MADD = '\u0653'  # ٓ (madda, vowel elongation)

# --- Letters & Variants ---
HAMZA = '\u0621'  # ء (standalone hamza)
ALEF_MADDA = '\u0622'  # آ (alef with madda)
ALEF_HAMZA_ABOVE = '\u0623'  # أ (alef with hamza above)
WAW_HAMZA = '\u0624'  # ؤ (waw with hamza)
ALEF_HAMZA_BELOW = '\u0625'  # إ (alef with hamza below)
YA_HAMZA = '\u0626'  # ئ (ya with hamza)
ALIF = '\u0627'  # ا (bare alef)
TA_MARBUTA = '\u0629'  # ة (tied ta, fem. marker)
WAW = '\u0648'  # و
ALIF_MAKSURA = '\u0649'  # ى (broken alef)
YA = '\u064A'  # ي
LAM = '\u0644'  # ل
HAMZAT_AL_WASL = '\u0671'  # ٱ (wasl, connecting hamza)

ALEF_VARIANTS = {ALIF, ALEF_MADDA, ALEF_HAMZA_ABOVE, ALEF_HAMZA_BELOW, HAMZAT_AL_WASL}

# --- Punctuation ---
ARABIC_PUNCT = "،؛؟ـ…"  # Comma, Semicolon, Question mark, Tatweel, Ellipsis
PUNCT = string.punctuation + ARABIC_PUNCT

# --- Sun Letters (Shamsiyya) ---
# These consonants assimilate the 'l' of the definite article 'al-'.
# e.g., al-shams -> ash-shams.
SUN_LETTERS: Set[str] = {
    '\u062A',  # ت (t)
    '\u062B',  # ث (th)
    '\u062F',  # د (d)
    '\u0630',  # ذ (dh)
    '\u0631',  # ر (r)
    '\u0632',  # ز (z)
    '\u0633',  # س (s)
    '\u0634',  # ش (sh)
    '\u0635',  # ص (sad)
    '\u0636',  # ض (dad)
    '\u0637',  # ط (ta)
    '\u0638',  # ظ (dha)
    '\u0644',  # ل (l)
    '\u0646',  # ن (n)
}

# --- Proclitics ---
# Short prepositions/conjunctions that attach to the following word in writing.
CLITIC_BASES = {
    WAW,  # و (and)
    '\u0641',  # ف (so/then)
    '\u0628',  # ب (by/with)
    '\u0643',  # ك (like/as)
    LAM,  # ل (for/to)
    '\u0633'  # س (future marker 'sa-')
}

# --- IPA Mappings ---
# for easy unambiguous phoneme reference in the code when the unicode maps to a specific IPA sound
B = '\u0628'
R = '\u0631'
Z = '\u0632'
S = '\u0633'
F = '\u0641'
Q = '\u0642'
K = '\u0643'
M = '\u0645'
N = '\u0646'
H = '\u0647'
T = '\u062A'
DJ = '\u062C'
X = '\u062E'
D = '\u062F'
