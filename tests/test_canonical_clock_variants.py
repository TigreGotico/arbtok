"""A time read with a one-letter variant is still compared as a time: the cost of the variant is
its letters, not the whole clock string against words."""
import pytest

from arbtok import textnorm
from arbtok.textnorm import CER_NORM_MARKS_FIRST, normalize_asr

CER_CANONICAL = getattr(textnorm, "CER_CANONICAL", CER_NORM_MARKS_FIRST)


def edits(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cost(written, heard):
    return edits(normalize_asr(written, CER_CANONICAL), normalize_asr(heard, CER_CANONICAL))


SAME = [
    ("احجزلك دور الساعة 15 ودقيقة 45 إذا يناسبك.", "احجز لك دور الساعة الثالثة مساءنا ودقيقة خمسة واربعين اذا يناسبك"),
    ("احجزلك دور الساعة 15 ودقيقة 45 إذا يناسبك.", "احجز لك دور الساعة الثالثة مساءن ودقيقة خمسة واربعين اذا يناسبك"),
    ("موعدك الساعة 9 ودقيقة 15", "موعدك الساعة التاسعة صباحن ودقيقة خمسة عشر"),
    ("دور الساعة 19 ودقيقة 15 إذا يناسبك", "دور الساعة سبعة المغرب ودقيقة خمستاشر اذا يناسبك"),
]
# (written, heard, most edits): a filler heard in place of و costs its own letters
CLOSE = [
    ("احجزلك دور الساعة 19 ودقيقة 15 إذا يناسبك.", "احجز لك دور الساعة السابعة مساء انه دقيقة خمسة عشر اذا يناسبك", 4),
    ("من الساعة 18 ودقيقة 30 فقط.", "من الساعة السادسة مسائيه ودقيقة ثلاثين فقط", 12),
    # the hour in digits, so the clock reading has nothing to read: the time is still one time
    ("الساعة 15 ودقيقة 45", "الساعة 3 مساءنا ودقيقة 45", 9),
]
DIFFERENT = [
    ("احجزلك دور الساعة 15 ودقيقة 45", "احجز لك دور الساعة الرابعة مساءنا ودقيقة خمسة واربعين"),
    ("احجزلك دور الساعة 15 ودقيقة 45", "احجز لك دور الساعة الثالثة مساءنا ودقيقة خمسة وثلاثين"),
    ("احجزلك دور الساعة 19 ودقيقة 15", "احجز لك دور الساعة السابعة مساء انه دقيقة عشرين"),
    ("الساعة 9:30", "الساعة تسعة وربع"),
    ("الساعة 15:30", "الساعة الثالثة مساءنا وربع"),
    ("الساعة 19:15", "الساعة ستة المغرب وربع"),
    ("الساعة 7:15", "الساعة سبعة المغرب وربع"),
    # المغرب is 6 and 7 in the evening, not any hour
    ("الساعة 21:15", "الساعة تسعة المغرب وربع"),
]


@pytest.mark.parametrize("written, heard", SAME, ids=[h for _, h in SAME])
def test_a_period_word_with_its_tanween_heard_reads_as_the_period(written, heard):
    assert cost(written, heard) == 0


@pytest.mark.parametrize("written, heard, most", CLOSE, ids=[h for _, h, _ in CLOSE])
def test_a_time_half_read_costs_its_letters_not_the_clock(written, heard, most):
    assert 0 < cost(written, heard) <= most


@pytest.mark.parametrize("written, heard", DIFFERENT, ids=[h for _, h in DIFFERENT])
def test_a_wrong_hour_or_minute_still_counts(written, heard):
    assert cost(written, heard) > 0


def test_the_evening_word_is_read_only_under_number_forms():
    """spoken_numbers_to_digits alone reads المغرب as it always has: as no period word."""
    assert normalize_asr("الساعة سبعة المغرب", spoken_numbers_to_digits=True) == "الساعة 7 المغرب"
