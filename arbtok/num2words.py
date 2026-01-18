import re
from functools import partial

from arbtok.pyarabic import araby
from arbtok.pyarabic import number as arnum
from arbtok.pyarabic.trans import normalize_digits

NUM_REGEX = re.compile(r"\d+")
PERCENT_NO_DIAC = "بالمئة"
PERCENT_DIAC = "بِالْمِئَة"


def _convert_num2words(m: re.Match, *, apply_tashkeel):
    number = m.group(0)
    word_representation = arnum.number2text(number)
    if apply_tashkeel:
        return " ".join(arnum.pre_tashkeel_number(word_representation.split(" ")))
    return word_representation


def num2words(text: str, handle_percent=True, apply_tashkeel: bool = True) -> str:
    """
    Converts numbers in `text` to Arabic words.
    Simple conversion. Does not check if the number is date/currency...etc.

    Args:
        text: input text that may contain numbers
        apply_tashkeel: diacritize added words
    """
    text = normalize_digits(text)
    output = NUM_REGEX.sub(
        partial(_convert_num2words, apply_tashkeel=apply_tashkeel), text
    )
    if handle_percent:
        replacement = PERCENT_DIAC if apply_tashkeel else PERCENT_NO_DIAC
        output = output.replace("%", f" {replacement}")
    return araby.fix_spaces(output)

# ------------------------------------------------------
# FEMININE HEAD INFLECTION
# ------------------------------------------------------

FEM_HEAD = {
    "واحد": "واحدة",
    "اثنان": "اثنتان",
    "اثنين": "اثنتين",
    "اثنانِ": "اثنتين",
    "ثلاثة": "ثلاث",
    "أربعة": "أربع",
    "خمسة": "خمس",
    "ستة": "ست",
    "سبعة": "سبع",
    "ثمانية": "ثمان",
    "تسعة": "تسع",
}

TEENS_FEM = {
    "أحد عشر": "إحدى عشرة",
    "اثنا عشر": "اثنتا عشرة",
    "اثني عشر": "اثنتي عشرة",
    "ثلاثة عشر": "ثلاث عشرة",
    "أربعة عشر": "أربع عشرة",
    "خمسة عشر": "خمس عشرة",
    "ستة عشر": "ست عشرة",
    "سبعة عشر": "سبع عشرة",
    "ثمانية عشر": "ثماني عشرة",
    "تسعة عشر": "تسع عشرة",
}

CASE_M = {
    "nom": "ٌ",
    "acc": "ً",
    "gen": "ٍ",
}

# ------------------------------------------------------
# ORDINALS
# ------------------------------------------------------

ORDINAL_BASE = {
    1: ("الأوّل", "الأولى"),
    2: ("الثاني", "الثانية"),
    3: ("الثالث", "الثالثة"),
    4: ("الرابع", "الرابعة"),
    5: ("الخامس", "الخامسة"),
    6: ("السادس", "السادسة"),
    7: ("السابع", "السابعة"),
    8: ("الثامن", "الثامنة"),
    9: ("التاسع", "التاسعة"),
    10: ("العاشر", "العاشرة"),
    11: ("الحادي عشر", "الحادية عشرة"),
    12: ("الثاني عشر", "الثانية عشرة"),
    13: ("الثالث عشر", "الثالثة عشرة"),
    14: ("الرابع عشر", "الرابعة عشرة"),
    15: ("الخامس عشر", "الخامسة عشرة"),
    16: ("السادس عشر", "السادسة عشرة"),
    17: ("السابع عشر", "السابعة عشرة"),
    18: ("الثامن عشر", "الثامنة عشرة"),
    19: ("التاسع عشر", "التاسعة عشرة"),
    20: ("العشرون", "العشرون"),
}

def ordinal_of_number(n: int, feminine=False):
    if n in ORDINAL_BASE:
        return ORDINAL_BASE[n][1 if feminine else 0]
    # Synthetic fallback for 21–99
    # Prepend definite article to the cardinals and add ي/ية to the head token.
    base = arnum.number2text(n).split()
    head = araby.strip_tashkeel(base[-1])
    if feminine:
        base[-1] = head + "ية"
    else:
        base[-1] = head + "ي"
    return "ال" + " ".join(base)

# ------------------------------------------------------
# HEAD EXTRACTION + INFLECTION
# ------------------------------------------------------

def extract_head(tokens):
    return tokens[-1], len(tokens) - 1

def apply_head_feminine(tokens):
    phrase = " ".join(tokens)
    if phrase in TEENS_FEM:
        return TEENS_FEM[phrase]

    head, idx = extract_head(tokens)
    pure = araby.strip_tashkeel(head)
    if pure in FEM_HEAD:
        tokens[idx] = FEM_HEAD[pure]
    return " ".join(tokens)

def apply_head_case(tokens, case):
    head, idx = extract_head(tokens)
    pure = araby.strip_tashkeel(head)
    tokens[idx] = pure + CASE_M[case]
    return " ".join(tokens)

# ------------------------------------------------------
# FULL GENERATION
# ------------------------------------------------------

def generate_variants_for_number(i: int, apply_tashkeel=False):
    base = num2words(str(i), handle_percent=False, apply_tashkeel=apply_tashkeel)
    tokens = base.split()

    # Cardinals
    masc = base
    nom = apply_head_case(tokens.copy(), "nom")
    acc = apply_head_case(tokens.copy(), "acc")
    gen = apply_head_case(tokens.copy(), "gen")
    fem = apply_head_feminine(tokens.copy())

    # Ordinals (masc + fem)
    try:
        n = int(i)
        ordm = ordinal_of_number(n, feminine=False)
        ordf = ordinal_of_number(n, feminine=True)
    except:
        ordm = None
        ordf = None

    out = []

    for w in [masc, nom, acc, gen, fem, ordm, ordf]:
        if w:
            out.append(w)

    return sorted(set(out))
