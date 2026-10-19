"""CER_CANONICAL brings a written text and a recognizer's reading of the same speech to one
form: what was said the same way compares equal, and what was said differently still differs.

Every equivalence below is one a written reference and a correct reading of it differ by, or
one two recognizers wrote two ways for the same audio. Every error below is a different thing
said, and must survive the normaliser."""
import dataclasses

import pytest

from arbtok import textnorm
from arbtok.textnorm import CER_NORM_MARKS_FIRST, AsrNorm, normalize_asr

#: The bundle under test, looked up by name, so that a tree without it runs every pair below
#: against the bench bundle it replaces, and fails on the pairs themselves.
CER_CANONICAL = getattr(textnorm, "CER_CANONICAL", CER_NORM_MARKS_FIRST)


def edits(a, b):
    """Levenshtein distance, the quantity a character-error rate counts."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(written, heard):
    ref, hyp = normalize_asr(written, CER_CANONICAL), normalize_asr(heard, CER_CANONICAL)
    return edits(ref, hyp) / len(ref)


SAME = [
    # numbers: the written digits and the words a voice says for them
    ("بعد التفاوض وصلنا لسعر 400,000 ريال.", "بعد التفاوض وصلنا لسعر اربع مية الف ريال"),
    ("السعر 610,200 ريال شامل التسجيل", "السعر ست ماية وعشرة الف وميتين ريال شامل التسجيل"),
    ("قيمة السيارة 62,700.75 ريال", "قيمة السيارة اثنين وستين الف وسبعمية فاصلة سبعة خمسة ريال"),
    ("قيمة السيارة 62,700.75 ريال", "قيمة السيارة اثنين وستين الف وسبع مية فاصلة خمسة وسبعين ريال"),
    ("القيمة ٦٢٬٧٠٠٫٧٥", "القيمة 62700.75"),
    ("جوالك 0569524794، صحيح؟", "جوالك صفر خمسة ستة تسعة خمسة اثنين اربعة سبعة تسعة اربعة صحيح"),
    ("متبقي عندنا 2 سيارات", "متبقي عندنا اثنين سيارات"),
    ("خصم 25% على القطع", "خصم خمسة وعشرين بالمية على القطع"),
    ("خصم 25٪ على القطع", "خصم خمسة وعشرين في المئة على القطع"),
    ("مرة وحدة بس", "مرة واحدة بس"),
    ("الساعة وحدة", "الساعة واحدة"),
    ("بعد أحد عشر يوم", "بعد احداش يوم"),
    ("عندنا اثنا عشر فرع", "عندنا اثناش فرع"),
    ("ثلاثة آلاف ريال", "ثلاث تالاف ريال"),
    ("خصم %25", "خصم خمسة وعشرين بالمية"),
    ("النسبة 5.5", "النسبة خمسة فاصلت خمسة"),
    ("خمسة ونص", "خمسة ونصف"),
    ("الموعد الساعة اطناش", "الموعد الساعة اثناش"),
    ("ربع ساعة وأكون عندك", "ربع ساعة وأكون عندك"),
    ("مشت 50 km", "مشت خمسين كيلومتر"),
    # clock times, the written form and the colloquial and literary readings of it
    ("من الساعة 8 ودقيقة 15 فقط", "من الساعة الثامنة ودقيقة خمسة عشر فقط"),
    ("موعدك الساعة 9:30", "موعدك الساعة تسعة ونص"),
    ("موعدك الساعة 16:30", "موعدك الساعة أربعة ونص العصر"),
    ("موعدك الساعة 8:30", "موعدك الساعة الثامنة والنصف"),
    ("موعدك الساعة 8:30", "موعدك الساعة التامنة والنص"),
    ("موعدك الساعة 7:00", "موعدك الساعة سبعة"),
    ("موعدك الساعة 07:00", "موعدك الساعة سبعة"),
    ("موعدك الساعة 07:30", "موعدك الساعة سبعة ونص"),
    ("موعدك الساعة 08:15", "موعدك الساعة ثمانية وربع"),
    ("الساعة 11:00 ص", "الساعة احداشر الصبح"),
    ("الساعة 11:00 م", "الساعة احداشر بالليل"),
    ("موعدك الساعة 11:00", "موعدك الساعة أحد عشر"),
    ("موعدك الساعة 9:30 م", "موعدك الساعة تسعة ونص مساء"),
    ("موعدك الساعة 21:00", "موعدك الساعة تسعة بالليل"),
    ("موعدك الساعة 4:30 العصر", "موعدك الساعة اربعة ونص العصر"),
    # dates and years
    ("تسليم السيارة يوم 18 سبتمبر 2026.", "تسليم السيارة يوم ثمانية عشر سبتمبر الفين وستة وعشرين"),
    ("تسليم السيارة يوم 18/9/2026", "تسليم السيارة يوم ثمانية عشر سبتمبر عشرين ستة وعشرين"),
    ("موعدك 10/06/2026", "موعدك العاشر من يونيو ألفين وستة وعشرين"),
    ("بتاريخ 2026-06-10", "بتاريخ عشرة يونيو ألفين وستة وعشرين"),
    ("موعدك 10 أيلول", "موعدك عشرة سبتمبر"),
    ("السيارة موديل 2026", "السيارة موديل عشرين ستة وعشرين"),
    ("وصلت في 2026", "وصلت في عشرين ستة وعشرين"),
    ("العرض ينتهي 30/6", "العرض ينتهي ثلاثين يونيو"),
    ("تسليمك يوم الاثنين 5 مايو", "تسليمك يوم الاثنين خمسة مايو"),
    ("الفئة 5 متوفرة", "الفئة الخامسة متوفرة"),
    ("الدور 3", "الدور الثالث"),
    ("لوحة ABC 1234", "لوحة ايه بي سي واحد اثنين ثلاثة اربعة"),
    ("ينتهي الضمان سنة 2030", "ينتهي الضمان سنة عشرين ثلاثين"),
    # terms: the Latin name, its Arabic spellings, and the proclitic written onto either
    ("بصراحة LAND ROVER من أكثر الماركات", "بصراحة لاند روفر من اكثر الماركات"),
    ("لو حاب تجرب سيارة INFINITI", "لو حاب تجرب سيارة إنفينيتي"),
    ("عندنا Test Drive اليوم", "عندنا تست درايف اليوم"),
    ("عندنا Test-Drive اليوم", "عندنا تست درايف اليوم"),
    ("بصراحة LAND ROVER", "بصراحة لاندروفر"),
    ("الحين متوفر عندنا 5 SERIES", "الحين متوفر عندنا الفية الخامسة"),
    ("اسأل عن أسعار وBMW", "اسال عن اسعار وبي ام دبليو"),
    # codes: letter names, and the digits said in English or in Arabic
    ("متوفر عندنا X5 بعدة ألوان", "متوفر عندنا اكس فايف بعدة الوان"),
    ("متوفر عندنا X5 بعدة ألوان", "متوفر عندنا اكس خمسة بعدة الوان"),
    ("متوفر عندنا X3", "متوفر عندنا اكستري"),
    ("متوفر عندنا GV70", "متوفر عندنا جي في سيفن زيرو"),
    ("متوفر عندنا QX60", "متوفر عندنا كيو اكس سكس زيرو"),
    ("متوفر عندنا 520i", "متوفر عندنا خمس مية وعشرين اي"),
    ("متوفر عندنا i7 و iX", "متوفر عندنا اي سيفن واي اكس"),
    ("متوفر عندنا i7", "متوفر عندنا اي سفن"),
    ("متوفر عندنا M2", "متوفر عندنا ام تو"),
    ("السعر 1,500.50", "السعر الف وخمس مية فاصلة خمسين"),
    ("فئة MG 3 وصلت", "فئة ام جي ثري وصلت"),
    ("بخيار M Sport", "بخيار ام سبورت"),
    ("بخيار M-Sport", "بخيار ام سبورت"),
    ("متوفر عندنا Q50", "متوفر عندنا كيو فيفتي"),
    ("متوفر عندنا Q75", "متوفر عندنا كيو سفنتي فايف"),
    ("الحروف J و G", "الحروف جاي و جي"),
    # dialect spellings two recognizers wrote both ways for the same audio
    ("هذي الفئة تجيك", "هذه الفئة تجيك"),
    ("نتواصل معك", "نتواصل معاك"),
    ("ايوا بكرا لسا", "ايوه بكره لسه"),
    ("حاب أساعدك", "حابب اساعدك"),
    ("كده تمام", "كذا تمام"),
    # words written apart or together
    ("احجزلك موعد", "احجز لك موعد"),
    ("يعملوا لك الصيانة", "يعملولك الصيانة"),
    ("بياناتك و ندخلها", "بياناتك وندخلها"),
    ("عبد العزيز ان شاء الله", "عبدالعزيز انشاء الله"),
    ("يا رب الحمد لله ما في شي", "يارب الحمدلله مافي شي"),
    ("رينج روڤر", "رينج روفر"),
]

DIFFERENT = [
    # a wrong number
    ("لسعر 400,000 ريال", "لسعر خمس مية الف ريال"),
    ("لسعر 400,000 ريال", "لسعر اربعين الف ريال"),
    ("قيمة السيارة 62,700.75 ريال", "قيمة السيارة اثنين وستين الف وسبعمية فاصلة سبعة ستة ريال"),
    ("خمسة ونص", "خمسة خمسة"),
    ("جوالك 0569524794", "جوالك صفر خمسة ستة تسعة خمسة اثنين اربعة سبعة تسعة تسعة"),
    ("خصم 25%", "خصم خمسة وثلاثين بالمية"),
    ("خصم 25%", "خصم خمسة وعشرين"),
    ("مرة وحدة", "مرتين"),
    ("الساعة 9:30", "الساعة تسعة وربع"),
    ("الساعة 16:30", "الساعة أربعة ونص الصباح"),
    ("الساعة 8 ودقيقة 15", "الساعة الثامنة ودقيقة خمسة"),
    ("يوم 18 سبتمبر 2026", "يوم ثمانية عشر أكتوبر الفين وستة وعشرين"),
    ("يوم 18/9/2026", "يوم سبعة عشر سبتمبر الفين وستة وعشرين"),
    ("موديل 2026", "موديل عشرين خمسة وعشرين"),
    ("موديل 2026", "موديل الفين وستة"),
    ("يوم 18/9/2026", "يوم ثمانية عشر اوقست الفين وستة وعشرين"),
    ("مشت 50 km", "مشت خمسين ميل"),
    # a wrong term or code
    ("سيارة LAND ROVER", "سيارة رينج روفر"),
    ("سيارة INFINITI", "سيارة نيسان"),
    ("متوفر عندنا X5", "متوفر عندنا اكس سيفن"),
    ("متوفر عندنا X5", "متوفر عندنا ام فايف"),
    ("متوفر عندنا GV70", "متوفر عندنا جي في سيفن"),
    ("متوفر عندنا 520i", "متوفر عندنا خمس مية وثلاثين اي"),
    ("فئة MG 3", "فئة ام جي فور"),
    ("الحين متوفر عندنا 5 SERIES", "الحين متوفر عندنا الفية السابعة"),
    # a wrong word that a folded spelling must not hide
    ("هذي الفئة", "هذا الفئة"),
    ("فئة MG 3", "في ام جي ثري"),
    ("ربع ساعة", "نص ساعة"),
    ("احجزلك موعد", "احجز موعد"),
    # a letter name that is also a word, before a number read digit by digit
    ("الحجز في 45 دقيقة", "الحجز في اربعة خمسة دقيقة"),
    ("موعدك في 2026", "موعدك في اثنين صفر اثنين ستة"),
    ("الدفعة في 1500 ريال", "الدفعة في واحد خمسة صفر صفر ريال"),
    ("اي 25 سيارة", "اي اثنين خمسة سيارة"),
    ("جي 30 شخص", "جي ثلاثة صفر شخص"),
    # words a dialect fold must not swallow
    ("الله وحده يعلم", "الله واحد يعلم"),
    ("وحدة التحكم", "واحد التحكم"),
    ("كلية الطب", "كلية الطيب"),
    ("في السيارة", "فيه السيارة"),
    ("ثانية واحدة", "تانية واحدة"),
    ("انه جاي", "انو جاي"),
    ("طب الاسنان", "طيب الاسنان"),
    ("أتفضل القهوة", "تفضل القهوة"),
    ("أتشرف بمعرفتك", "تشرف بمعرفتك"),
    ("أرسل لهم الطلب", "أرسلهم الطلب"),
    ("قال له", "قاله"),
    ("أهل لك", "أهلك"),
    ("كده تمام", "هذا تمام"),
    # a weekday is no ordinal
    ("تسليمك يوم الاثنين خمسة مايو", "تسليمك يوم خمسة مايو"),
    # an Arabic word that is also an English digit name, beside a letter name that is a word
    ("اتصل بي فور وصولك", "اتصل بي اربعة وصولك"),
    ("سنتصل في فور وصولكم", "سنتصل في اربعة وصولكم"),
    ("وصلت في تو", "وصلت في اثنين"),
    ("بكرة او تو", "بكرة او اثنين"),
    ("نصف 1/2", "نصف 1 فبراير"),
    ("الفئة 7 متوفرة", "الفئة السابعة السابعة متوفرة"),
    ("يوم 18 مايو", "يوم الثامن عشر عشر من مايو"),
    ("راح للمعرض امس", "رح للمعرض امس"),
    # letters a recognizer writes apart
    ("الحرف J", "الحرف جي"),
    # times placed in the day
    ("الساعة 4:30 العصر", "الساعة اربعة ونص الصبح"),
    ("الساعة 9:30 م", "الساعة تسعة ونص الصبح"),
    ("الساعة 7:00", "الساعة ثمانية"),
]


@pytest.mark.parametrize("written, heard", SAME, ids=[w for w, _ in SAME])
def test_the_same_speech_written_two_ways_scores_zero(written, heard):
    assert normalize_asr(written, CER_CANONICAL) == normalize_asr(heard, CER_CANONICAL)


@pytest.mark.parametrize("written, heard", DIFFERENT, ids=[f"{w} / {h}" for w, h in DIFFERENT])
def test_a_different_thing_said_still_counts(written, heard):
    assert cer(written, heard) > 0


@pytest.mark.parametrize("written, heard", SAME[:12], ids=[w for w, _ in SAME[:12]])
def test_the_bench_bundle_charged_these(written, heard):
    """The equivalences are the canonical bundle's: the bundle the bench scores with charges them."""
    assert normalize_asr(written, CER_NORM_MARKS_FIRST) != normalize_asr(heard, CER_NORM_MARKS_FIRST)


def test_the_marks_inside_a_number_survive_the_punctuation_rule():
    assert normalize_asr("السعر 5.5 والموعد 8:15 يوم 18/9/2026 بخصم 25%.", CER_CANONICAL) \
        == "السعر 5.5 والموعد الساعه 8:15 يوم 18 سبتمبر 2026 بخصم 25%"
    assert normalize_asr("السعر 5.5.", CER_NORM_MARKS_FIRST) == "السعر 5 5"


def test_a_fraction_that_follows_no_number_stays_a_word():
    assert normalize_asr("ربع ساعة", CER_CANONICAL) == "ربع ساعه"
    assert normalize_asr("بعد ساعة ونص", CER_CANONICAL) == "بعد ساعه ونصف"
    assert normalize_asr("خمسة وربع", CER_CANONICAL) == "5.25"


def test_letter_names_that_are_words_need_a_code_beside_them():
    """في, اي and ام are also "in", "which" and "mother": one of them beside digits is no code,
    a word made of names that are words is no fused code, and فور beside one of them is "at
    once"."""
    assert normalize_asr("في اي مدينة", CER_CANONICAL) == "في اي مدينه"
    assert normalize_asr("انتي ايدي التو", CER_CANONICAL) == "انتي ايدي التو"
    assert normalize_asr("في 4 5 دقايق", CER_CANONICAL) == "في 4 5 دقايق"
    assert normalize_asr("ام فايف", CER_CANONICAL) == "ام 5"
    assert normalize_asr("بي فور", CER_CANONICAL) == "بي فور"


def test_the_month_father_is_a_month_only_after_a_day():
    assert normalize_asr("اب العميل", CER_CANONICAL) == "اب العميل"
    assert normalize_asr("يوم 5 اب", CER_CANONICAL) == "يوم 5 اغسطس"


def test_category_spelled_like_there_is_keeps_its_letters():
    """A recognizer writes فئة as فية, which folds to the letters of فيه "there is"."""
    assert normalize_asr("فية ام جي", CER_CANONICAL) == normalize_asr("فئة ام جي", CER_CANONICAL)


@pytest.mark.parametrize("flag", ["split_term_proclitics", "unify_dialect_spellings", "number_forms",
                                  "spell_codes", "unify_loan_letters", "join_clitics"])
def test_each_rule_is_off_by_default_named_when_on_and_in_the_bundle(flag):
    assert getattr(AsrNorm(), flag) is False
    assert getattr(CER_CANONICAL, flag) is True
    assert flag in AsrNorm(**{flag: True}).describe()
    assert flag not in CER_NORM_MARKS_FIRST.describe()


def test_the_bundle_is_the_bench_bundle_and_more():
    """Everything the bench bundle does, the canonical bundle does too."""
    for field in dataclasses.fields(AsrNorm):
        if getattr(CER_NORM_MARKS_FIRST, field.name) is True:
            assert getattr(CER_CANONICAL, field.name) is True, field.name


def test_the_canonical_lexicon_writes_every_spelling_of_a_term_one_way():
    lexicon = textnorm.canonical_term_lexicon()
    assert lexicon["Land Rover"] == lexicon["لاند روڤر"]
    assert lexicon["MG"] == lexicon["ام جي"] == lexicon["إم جي"]


def test_the_word_rules_are_arabic_only():
    assert normalize_asr("هذي X5 و ندخلها", CER_CANONICAL, lang="fa") == "هذي x5 و ندخلها"


def test_a_long_run_of_name_fragments_reads_in_linear_time():
    import time
    word = "ايتي" * 22 + "ب"
    start = time.perf_counter()
    normalize_asr(word, CER_CANONICAL)
    assert time.perf_counter() - start < 0.5
