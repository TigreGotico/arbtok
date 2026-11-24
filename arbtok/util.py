"""Dates, times, units, numbers, contractions and titles written as words.

Taken from phoonnx. :func:`normalize` is the ``spoken_forms`` pass of
:func:`arbtok.textnorm.normalize_for_tts`.
"""
import datetime
import logging
import re
import string
from contextlib import suppress
from datetime import date
from typing import Optional

from ovos_date_parser import nice_time, nice_date
from ovos_number_parser import pronounce_number, pronounce_fraction
from ovos_number_parser.util import is_numeric
from unicode_rbnf import RbnfEngine, FormatPurpose

LOG = logging.getLogger("phoonnx")


# A dictionary of common contractions and their expanded forms.
# This list is very comprehensive for English.
CONTRACTIONS = {
    "en": {
        "I'd": "I would",
        "I'll": "I will",
        "I'm": "I am",
        "I've": "I have",
        "ain't": "is not",
        "aren't": "are not",
        "can't": "can not",
        "could've": "could have",
        "couldn't": "could not",
        "didn't": "did not",
        "doesn't": "does not",
        "don't": "do not",
        "gonna": "going to",
        "gotta": "got to",
        "hadn't": "had not",
        "hasn't": "has not",
        "haven't": "have not",
        "he'd": "he would",
        "he'll": "he will",
        "he's": "he is",
        "how'd": "how did",
        "how'll": "how will",
        "how's": "how is",
        "isn't": "is not",
        "it'd": "it would",
        "it'll": "it will",
        "it's": "it is",
        "might've": "might have",
        "mightn't": "might not",
        "must've": "must have",
        "mustn't": "must not",
        "needn't": "need not",
        "oughtn't": "ought not",
        "shan't": "shall not",
        "she'd": "she would",
        "she'll": "she will",
        "she's": "she is",
        "should've": "should have",
        "shouldn't": "should not",
        "somebody's": "somebody is",
        "someone'd": "someone would",
        "someone'll": "someone will",
        "someone's": "someone is",
        "that'd": "that would",
        "that'll": "that will",
        "that's": "that is",
        "there'd": "there would",
        "there're": "there are",
        "there's": "there is",
        "they'd": "they would",
        "they'll": "they will",
        "they're": "they are",
        "they've": "they have",
        "wasn't": "was not",
        "we'd": "we would",
        "we'll": "we will",
        "we're": "we are",
        "we've": "we have",
        "weren't": "were not",
        "what'd": "what did",
        "what'll": "what will",
        "what're": "what are",
        "what's": "what is",
        "what've": "what have",
        "whats": "what is",
        "when'd": "when did",
        "when's": "when is",
        "where'd": "where did",
        "where's": "where is",
        "where've": "where have",
        "who'd": "who would",
        "who'd've": "who would have",
        "who'll": "who will",
        "who're": "who are",
        "who's": "who is",
        "who've": "who have",
        "why'd": "why did",
        "why're": "why are",
        "why's": "why is",
        "won't": "will not",
        "won't've": "will not have",
        "would've": "would have",
        "wouldn't": "would not",
        "wouldn't've": "would not have",
        "y'ain't": "you are not",
        "y'aint": "you are not",
        "y'all": "you all",
        "ya'll": "you all",
        "you'd": "you would",
        "you'd've": "you would have",
        "you'll": "you will",
        "you're": "you are",
        "you've": "you have",
        "I'm'a": "I am going to",
        "I'm'o": "I am going to",
        "I'll've": "I will have",
        "I'd've": "I would have",
        "Whatcha": "What are you",
        "amn't": "am not",
        "'cause": "because",
        "can't've": "cannot have",
        "couldn't've": "could not have",
        "daren't": "dare not",
        "daresn't": "dare not",
        "dasn't": "dare not",
        "everyone's": "everyone is",
        "gimme": "give me",
        "gon't": "go not",
        "hadn't've": "had not have",
        "he've": "he would have",
        "he'll've": "he will have",
        "he'd've": "he would have",
        "here's": "here is",
        "how're": "how are",
        "how'd'y": "how do you do",
        "howd'y": "how do you do",
        "howdy": "how do you do",
        "'tis": "it is",
        "'twas": "it was",
        "it'll've": "it will have",
        "it'd've": "it would have",
        "kinda": "kind of",
        "let's": "let us",
        "ma'am": "madam",
        "may've": "may have",
        "mayn't": "may not",
        "mightn't've": "might not have",
        "mustn't've": "must not have",
        "needn't've": "need not have",
        "ol'": "old",
        "oughtn't've": "ought not have",
        "sha'n't": "shall not",
        "shan't": "shall not",
        "shalln't": "shall not",
        "shan't've": "shall not have",
        "she'd've": "she would have",
        "shouldn't've": "should not have",
        "so've": "so have",
        "so's": "so is",
        "something's": "something is",
        "that're": "that are",
        "that'd've": "that would have",
        "there'll": "there will",
        "there'd've": "there would have",
        "these're": "these are",
        "they'll've": "they will have",
        "they'd've": "they would have",
        "this's": "this is",
        "this'll": "this will",
        "this'd": "this would",
        "those're": "those are",
        "to've": "to have",
        "wanna": "want to",
        "we'll've": "we will have",
        "we'd've": "we would have",
        "what'll've": "what will have",
        "when've": "when have",
        "where're": "where are",
        "which's": "which is",
        "who'll've": "who will have",
        "why've": "why have",
        "will've": "will have",
        "y'all're": "you all are",
        "y'all've": "you all have",
        "y'all'd": "you all would",
        "y'all'd've": "you all would have",
        "you'll've": "you will have"
    }
}

# Dictionaries for titles, units, and their full word equivalents.
TITLES = {
    "en": {
        "Dr.": "Doctor",
        "Mr.": "Mister",
        "Prof.": "Professor"
    },
    "ca": {
        "Dr.": "Doctor",
        "Sr.": "Senyor",
        "Sra.": "Senyora",
        "Prof.": "Professor"
    },
    "es": {
        "Dr.": "Doctor",
        "Sr.": "Señor",
        "Sra.": "Señora",
        "Prof.": "Profesor",
        "D.": "Don",
        "Dña.": "Doña"
    },
    "pt": {
        "Dr.": "Doutor",
        "Sr.": "Senhor",
        "Sra.": "Senhora",
        "Prof.": "Professor",
        "Drª.": "Doutora",
        "Eng.": "Engenheiro",
        "D.": "Dom",
        "Dª": "Dona"
    },
    "gl": {
        "Dr.": "Doutor",
        "Sr.": "Señor",
        "Sra.": "Señora",
        "Prof.": "Profesor",
        "Srta.": "Señorita"
    },
    "fr": {
        "Dr.": "Docteur",
        "M.": "Monsieur",
        "Mme": "Madame",
        "Mlle": "Mademoiselle",
        "Prof.": "Professeur",
        "Pr.": "Professeur"
    },
    "it": {
        "Dr.": "Dottore",
        "Sig.": "Signore",
        "Sig.ra": "Signora",
        "Prof.": "Professore",
        "Dott.ssa": "Dottoressa",
        "Sig.na": "Signorina"
    },
    "nl": {
        "Dr.": "Dokter",
        "Dhr.": "De Heer",
        "Mevr.": "Mevrouw",
        "Prof.": "Professor",
        "Drs.": "Dokterandus",
        "Ing.": "Ingenieur"
    },
    "de": {
        "Dr.": "Doktor",
        "Prof.": "Professor"
    }
}

UNITS = {
    "en": {
        "€": "euros",
        "%": "per cent",
        "°C": "degrees celsius",
        "°F": "degrees fahrenheit",
        "°K": "degrees kelvin",
        "°": "degrees",
        "$": "dollars",
        "£": "pounds",
        "km": "kilometers",
        "m": "meters",
        "cm": "centimeters",
        "mm": "millimeters",
        "ft": "feet",
        "in": "inches",
        "yd": "yards",
        "mi": "miles",
        "kg": "kilograms",
        "g": "grams",
        "lb": "pounds",
        "oz": "ounces",
        "L": "liters",
        "mL": "milliliters",
        "gal": "gallons",
        "qt": "quarts",
        "pt": "pints",
        "hr": "hours",
        "min": "minutes",
        "s": "seconds"
    },
    "pt": {
        "€": "euros",
        "%": "por cento",
        "°C": "graus celsius",
        "°F": "graus fahrenheit",
        "°K": "graus kelvin",
        "°": "graus",
        "$": "dólares",
        "£": "libras",
        "km": "quilômetros",
        "m": "metros",
        "cm": "centímetros",
        "mm": "milímetros",
        "kg": "quilogramas",
        "g": "gramas",
        "L": "litros",
        "mL": "mililitros",
        "h": "horas",
        "min": "minutos",
        "s": "segundos"
    },
    "es": {
        "€": "euros",
        "%": "por ciento",
        "°C": "grados celsius",
        "°F": "grados fahrenheit",
        "°K": "grados kelvin",
        "°": "grados",
        "$": "dólares",
        "£": "libras",
        "km": "kilómetros",
        "m": "metros",
        "cm": "centímetros",
        "kg": "kilogramos",
        "g": "gramos",
        "L": "litros",
        "mL": "millilitros"
    },
    "fr": {
        "€": "euros",
        "%": "pour cent",
        "°C": "degrés celsius",
        "°F": "degrés fahrenheit",
        "°K": "degrés kelvin",
        "°": "degrés",
        "$": "dollars",
        "£": "livres",
        "km": "kilomètres",
        "m": "mètres",
        "cm": "centimètres",
        "kg": "kilogrammes",
        "g": "grammes",
        "L": "litres",
        "mL": "millilitres"
    },
    "de": {
        "€": "Euro",
        "%": "Prozent",
        "°C": "Grad Celsius",
        "°F": "Grad Fahrenheit",
        "°K": "Grad Kelvin",
        "°": "Grad",
        "$": "Dollar",
        "£": "Pfund",
        "km": "Kilometer",
        "m": "Meter",
        "cm": "Zentimeter",
        "kg": "Kilogramm",
        "g": "Gramm",
        "L": "Liter",
        "mL": "Milliliter"
    }
}

# Arabic unit names come from Unicode CLDR rather than from a list kept here; see
# arbtok.textnorm.cldr_units and data/term_lexicons/units-cldr.tsv.
from arbtok.textnorm import _CAPITALISED_UNITS, cldr_units, spelled_codes  # noqa: E402

UNITS["ar"] = cldr_units("ar")


def _get_number_separators(full_lang: str) -> tuple[str, str]:
    """The decimal and thousands separators of *full_lang*."""
    if full_lang.split("-")[0] in ("pt", "es", "fr", "de"):
        return ",", "."
    return ".", ","


def resolve_thousands_or_decimal(word: str, thousands_separator: str = ",") -> Optional[str]:
    """The number ``word`` reads as, when its ``thousands_separator``s resolve to one
    unambiguous shape, else ``None``.

    Separators that are each followed by exactly three digits are a thousands grouping
    ('1,500', '1,234,567'), and the grouping wins where the shape is ambiguous. One
    separator followed by fewer or more digits ('12,5', '1,0000') marks a decimal
    fraction. Two or more separators that form no grouping resolve nothing: '1,2,3' is
    not 1.23, and '055,123,4567' would lose digits as a float.
    """
    thousands_esc = re.escape(thousands_separator)
    if re.fullmatch(rf"\d{{1,3}}(?:{thousands_esc}\d{{3}})+", word):
        return word.replace(thousands_separator, "")
    if word.count(thousands_separator) == 1:
        head, _, tail = word.partition(thousands_separator)
        candidate = f"{head}.{tail}"
        if is_numeric(candidate):
            return candidate
    return None


def _normalize_number_word(word: str, full_lang: str, rbnf_engine) -> str:
    """*word* spoken when it is a number or a fraction, its trailing punctuation kept."""
    cleaned_word = word.rstrip(string.punctuation)
    trailing = word[len(cleaned_word):]

    if is_fraction(cleaned_word):
        try:
            return pronounce_fraction(cleaned_word, full_lang) + trailing
        except Exception as e:
            LOG.error(f"ovos-number-parser failed to pronounce fraction: {word} - ({e})")
            return word

    decimal_separator, thousands_separator = _get_number_separators(full_lang)
    number = cleaned_word
    if (thousands_separator in number and decimal_separator in number
            and number.index(thousands_separator) < number.index(decimal_separator)):
        # '123.456,78'
        number = number.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif decimal_separator in number and is_numeric(number.replace(decimal_separator, ".", 1)):
        number = number.replace(decimal_separator, ".")
    elif thousands_separator in number:
        # A shape that does not resolve keeps its separators and is not numeric, so it
        # is left to _verbalize_residual_digits_ar, which speaks each digit run.
        resolved = resolve_thousands_or_decimal(number, thousands_separator)
        if resolved is not None:
            number = resolved

    if is_numeric(number):
        try:
            return pronounce_number(float(number) if "." in number else int(number), lang=full_lang) + trailing
        except Exception as e:
            LOG.error(f"ovos-number-parser failed to pronounce number: {word} - ({e})")
            return word

    if rbnf_engine and cleaned_word.isdigit():
        try:
            return rbnf_engine.format_number(cleaned_word, FormatPurpose.CARDINAL).text + trailing
        except Exception as e:
            LOG.error(f"unicode-rbnf failed to pronounce number: {word} - ({e})")
            return word

    return word


def pronounce_date(date_obj: date, full_lang: str) -> str:
    """*date_obj* spoken in *full_lang*, by ovos-date-parser."""
    return nice_date(date_obj, full_lang)


def pronounce_time(time_string: str, full_lang: str) -> str:
    """A 24-hour time written "15h01", spoken in *full_lang* by ovos-date-parser."""
    try:
        hours, mins = time_string.split("h")
        time_obj = datetime.time(int(hours), int(mins))
        return nice_time(time_obj, full_lang, speech=True, use_24hour=True, use_ampm=False)
    except Exception as e:
        LOG.warning(f"Failed to parse time string '{time_string}': {e}")
        return time_string.replace("h", " ")


_TIME_24H = re.compile(r"(\d{1,2})h(\d{2})", re.IGNORECASE)
_NUMERIC_DATE = re.compile(r"(\d{1,4})[/-](\d{1,2})[/-](\d{1,4})")
_WORD_HYPHEN_DIGIT = re.compile(r"(\w+)-(\d+)")


def _normalize_dates_and_times(text: str, full_lang: str, date_format: str = "DMY") -> str:
    """Speak every 24-hour time and the first numeric date in *text*."""
    if full_lang.split("-")[0] == "en":
        text = re.sub(r"(?i)(\d+)(am|pm)", r"\1 \2", text)
        text = text.replace("am", "A M").replace("pm", "P M")

    text = _TIME_24H.sub(lambda m: pronounce_time(m.group(0), full_lang), text)

    match = _NUMERIC_DATE.search(text)
    if not match:
        return text
    part1_str, part2_str, part3_str = match.groups()
    p1, p2, p3 = int(part1_str), int(part2_str), int(part3_str)

    if len(part1_str) == 4:
        year, rest_parts = p1, [p2, p3]
    elif len(part3_str) == 4:
        year, rest_parts = p3, [p1, p2]
    else:
        # The year is last. Two digits read 00-29 as 2000-2029 and 30-99 as 1930-1999.
        year = p3
        if year < 100:
            year = 2000 + year if year < 30 else 1900 + year
        rest_parts = [p1, p2]

    if any(p > 12 and len(str(p)) == 2 for p in rest_parts):
        # A two-digit part above 12 is the day.
        day = next(p for p in rest_parts if p > 12)
        rest_parts.remove(day)
        month = rest_parts[0]
    elif date_format.lower() == "mdy":
        month, day = rest_parts[0], rest_parts[1]
    else:
        day, month = rest_parts[0], rest_parts[1]

    try:
        pronounced_date_str = pronounce_date(date(year, month, day), full_lang)
    except (ValueError, IndexError) as e:
        LOG.warning(f"Could not parse date from '{match.group(0)}': {e}")
        return text
    return text.replace(match.group(0), pronounced_date_str)


def _unit_word(units: dict, symbol: str) -> str:
    # The patterns below match a symbol in any case, so `5 KM` and `20 °c` arrive here
    # as written. The exact symbol wins, since `Cal` and `cal` are different units.
    if symbol in units:
        return units[symbol]
    return {k.lower(): v for k, v in units.items()}[symbol.lower()]


#: CLDR gives "am" and "pm" as the symbols of the attometre and the picometre; after
#: a clock time they are the 12-hour markers, and a time is not a measurement.
_CLOCK_MARKERS = ("am", "pm")


def _is_clock_time(match: re.Match) -> bool:
    """Whether the number before an "am"/"pm" is an hour of the 12-hour clock, or the
    minutes of an ``h:mm`` time."""
    number = match.group(1)
    if match.start() > 0 and match.string[match.start() - 1] == ":":
        return number.isdigit() and int(number) < 60
    return number.isdigit() and 1 <= int(number) <= 12


def _normalize_units(text: str, full_lang: str) -> str:
    """Speak each number written with a unit symbol, the symbol as its unit's name.

    Symbols that are not alphanumeric (``°C``, ``%``) go first, then alphanumeric ones,
    which must end on a word boundary.
    """
    text = text.replace("º", "°")  # the ordinal indicator, typed for the degree sign
    lang_code = full_lang.split("-")[0]
    if lang_code not in UNITS:
        return text
    decimal_separator, thousands_separator = _get_number_separators(full_lang)
    # A grouping is groups of three digits. Any other shape carrying a separator
    # is not a number this pass reads, and is left exactly as it was written: a
    # dot before fewer than three digits is a decimal point, not a grouping.
    thousands, decimal = re.escape(thousands_separator), re.escape(decimal_separator)
    grouped = re.compile(rf"\d{{1,3}}(?:{thousands}\d{{3}})+(?:{decimal}\d+)?")
    # Anchored at both ends: a match may not begin right after a digit or a
    # separator, nor stop in front of one, or a shape that forms no grouping is
    # read from the digits after its separator with the rest left glued in front.
    number_pattern_str = (rf"(?<![\d.,])({grouped.pattern}"
                          rf"|\d+(?:[{decimal}.]\d+)?)(?![\d.,]*\d)")

    def plain_number(match: re.Match) -> str:
        number = match.group(1)
        if grouped.fullmatch(number):
            number = number.replace(thousands_separator, "")
        return number.replace(decimal_separator, ".")

    symbolic_units = {k: v for k, v in UNITS[lang_code].items() if not k.isalnum()}
    alphanumeric_units = {k: v for k, v in UNITS[lang_code].items() if k.isalnum()}

    symbolic_pattern_str = "|".join(re.escape(unit) for unit in sorted(symbolic_units, key=len, reverse=True))
    if symbolic_pattern_str:
        symbolic_pattern = re.compile(number_pattern_str + r"\s*(" + symbolic_pattern_str + r")", re.IGNORECASE)

        def replace_symbolic(match: re.Match) -> str:
            number = plain_number(match)
            unit_symbol = match.group(2)
            unit_word = _unit_word(symbolic_units, unit_symbol)
            try:
                return f"{pronounce_number(float(number) if '.' in number else int(number), full_lang)} {unit_word}"
            except Exception as e:
                LOG.error(f"Failed to pronounce number with unit: {number}{unit_symbol} - ({e})")
                return match.group(0)

        text = symbolic_pattern.sub(replace_symbolic, text)

    alphanumeric_pattern_str = "|".join(re.escape(unit) for unit in sorted(alphanumeric_units, key=len, reverse=True))
    if alphanumeric_pattern_str:
        alphanumeric_pattern = re.compile(number_pattern_str + r"\s*(" + alphanumeric_pattern_str + r")\b",
                                          re.IGNORECASE)

        def replace_alphanumeric(match: re.Match) -> str:
            number = plain_number(match)
            unit_symbol = match.group(2)
            if unit_symbol.lower() in _CLOCK_MARKERS and _is_clock_time(match):
                return match.group(0)
            # Capitals a symbol is not written in are evidence of a code: "3 mg" is
            # milligrams where "3 MG" is the make, and "2 EV" a car rather than two
            # electronvolts. A symbol the table itself capitalises, GB, is untouched,
            # and so are the four people capitalise whatever the table spells them.
            written = next(k for k in alphanumeric_units if k.lower() == unit_symbol.lower())
            if unit_symbol.isupper() and not written.isupper() \
                    and unit_symbol.lower() not in _CAPITALISED_UNITS:
                return match.group(0)
            unit_word = _unit_word(alphanumeric_units, unit_symbol)
            return f"{pronounce_number(float(number) if '.' in number else int(number), full_lang)} {unit_word}"

        text = alphanumeric_pattern.sub(replace_alphanumeric, text)
    return text


def _normalize_word(word: str, full_lang: str, rbnf_engine) -> str:
    """*word* expanded when it is a contraction or a title, else spoken as a number."""
    lang_code = full_lang.split("-")[0]
    if word in CONTRACTIONS.get(lang_code, {}):
        return CONTRACTIONS[lang_code][word]
    if word in TITLES.get(lang_code, {}):
        return TITLES[lang_code][word]
    return _normalize_number_word(word, full_lang, rbnf_engine)


def is_fraction(word: str) -> bool:
    """Whether *word* is a fraction of two digit runs, like '3/4'."""
    parts = word.split("/")
    return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()


# Arabic-Indic and extended (Persian) digits mapped to ASCII so one rule covers them all.
_AR_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
# A digit run that is NOT part of an Arabizi token (Latin+digit, where 3=ع, 7=ح), with an
# optional trailing percent sign. The Latin lookarounds keep "3ala"/"7abibi" for the Arabizi path;
# the digit lookarounds keep the run whole, so a run glued to a letter is never cut short and
# read in part ("520i" is not 52 and a 0).
_RESIDUAL_NUM = re.compile(r"(?<![A-Za-z\d])(\d+)(\s*%)?(?![A-Za-z\d])")
# A run of two digits or more glued to Latin letters, before or after it: a model code
# ("520i", "M340i") or a number and its unit ("100kms"). Arabizi writes a letter with one
# digit at a time, so a run of two or more is a number. The letters on either side are
# taken with it: one letter alone is a code letter, read by its name; more are a word or
# a unit, left as written for the paths that read Latin words.
# A lone small h or s after the number is the hour or the second, their SI symbols
# (https://en.wikipedia.org/wiki/International_System_of_Units): "24h" and "90s" are a
# span of time, read as its unit's name, not as a code letter.
_GLUED_TIME_UNITS = {"h": "ساعة", "s": "ثانية"}
_GLUED_DIGIT_RUN = re.compile(r"(?<![A-Za-z\d])([A-Za-z]*)(\d{2,})([A-Za-z]*)(?![A-Za-z\d])")
# A lone percent sign (ASCII "%" or Arabic "٪") left behind once its number was verbalized.
_RESIDUAL_PERCENT = re.compile(r"\s*[%٪]")
_PERCENT_WORD_AR = "بالمئة"


def _verbalize_residual_digits_ar(text: str) -> str:
    """Speak every digit run the number pass left, so no digit reaches the phoneme map.

    Catches a number glued to punctuation ("10،"), a stray "%" and Arabic-Indic digits.
    A single digit glued to Latin letters is Arabizi and is left for that path.
    """
    text = text.translate(_AR_INDIC_DIGITS)

    def repl(m: "re.Match") -> str:
        words = pronounce_number(int(m.group(1)), lang="ar")
        return f"{words} {_PERCENT_WORD_AR}" if m.group(2) else words

    names = spelled_codes("ar")

    def letters(run: str, after: bool) -> str:
        if after and run in _GLUED_TIME_UNITS:
            return _GLUED_TIME_UNITS[run]
        return names.get(run.upper(), run) if len(run) == 1 else run

    def glued(m: "re.Match") -> str:
        before, digits, after = m.groups()
        if not (before or after):
            return m.group(0)
        return " ".join(part for part in (letters(before, False), pronounce_number(int(digits), lang="ar"),
                                          letters(after, True)) if part)

    text = _GLUED_DIGIT_RUN.sub(glued, text)
    text = _RESIDUAL_NUM.sub(repl, text)
    return _RESIDUAL_PERCENT.sub(f" {_PERCENT_WORD_AR}", text)


def normalize(text: str, lang: str) -> str:
    """*text* with its dates, times, units, numbers, fractions, contractions and titles
    written as words in *lang* (a tag such as "en" or "en-US")."""
    lang_code = lang.split("-")[0]

    date_format = "MDY" if lang.lower() == "en-us" else "DMY"
    with suppress(Exception):  # ovos-date-parser raises on a language it does not support
        text = _normalize_dates_and_times(text, lang, date_format)

    text = _WORD_HYPHEN_DIGIT.sub(r"\1 \2", text)  # 'sub-23' -> 'sub 23'
    text = _normalize_units(text, lang)

    rbnf_engine = None
    try:
        rbnf_engine = RbnfEngine.for_language(lang_code)
    except (ValueError, KeyError) as e:
        LOG.debug(f"RBNF engine not available for language '{lang_code}': {e}")
    text = " ".join(_normalize_word(word, lang, rbnf_engine) for word in text.split())

    if lang_code == "ar":
        text = _verbalize_residual_digits_ar(text)
    return text
