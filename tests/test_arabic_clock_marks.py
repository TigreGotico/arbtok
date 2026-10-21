"""ص and م, the Arabic abbreviations of صباحًا and مساءً, mark a clock time the way "am"
and "pm" do: the time takes its period from them and the letter is not left behind."""
import pytest

from arbtok.textnorm import normalize_for_tts
from tests.voice_agent import VOICE_AGENT

SAID = [
    ("موعدك الساعة 10:30 ص", "موعدك الساعة العاشرة والنصف صباحاً"),
    ("موعدك الساعة 4:15 م", "موعدك الساعة الرابعة والربع مساءً"),
    ("نفتح 9:00 ص ونقفل 5:00 م", "نفتح الساعة التاسعة صباحاً ونقفل الساعة الخامسة مساءً"),
    ("الساعة 7 م", "الساعة السابعة مساءً"),
    ("الساعة ٨:٤٥ م.", "الساعة التاسعة إلا ربعاً مساءً."),
    # on the 24-hour clock the mark repeats what the hour says
    ("الساعة 16:30 م", "الساعة الرابعة والنصف مساءً"),
    # a detached و after the mark is the conjunction, not a post office box
    ("نفتح 9:00 ص و نقفل 5:00 م", "نفتح الساعة التاسعة صباحاً و نقفل الساعة الخامسة مساءً"),
]


@pytest.mark.parametrize("config", [VOICE_AGENT, None], ids=["cardinal_numbers", "default"])
@pytest.mark.parametrize("written, said", SAID, ids=[w for w, _ in SAID])
def test_an_arabic_mark_gives_the_period(written, said, config):
    assert normalize_for_tts(written, "ar", config) == said


@pytest.mark.parametrize("written, said", [("المسافة 100 م", "المسافة مئة م"), ("انظر 5 ص", "انظر خمسة ص"),
                                           ("المسافة 7 م من الباب", "المسافة سبعة م من الباب")])
def test_after_a_bare_number_the_letter_is_no_mark(written, said):
    """After a bare number م is also the metre and ص the page."""
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == said


def test_a_word_starting_with_the_letter_is_no_mark():
    assert normalize_for_tts("الساعة 10:30 مع أحمد", "ar", VOICE_AGENT) == "الساعة العاشرة والنصف مع أحمد"


@pytest.mark.parametrize("written, said", [
    ("نستقبلك 10:30 ص ب 1234", "نستقبلك الساعة العاشرة والنصف ص ب واحد اثنين ثلاثة أربعة"),
    ("نستقبلك 10:30 ص.ب 1234", "نستقبلك الساعة العاشرة والنصف ص.ب واحد اثنين ثلاثة أربعة"),
])
def test_a_post_office_box_after_a_time_is_no_mark(written, said):
    """ص ب and ص.ب are a post office box: the time keeps no period from them."""
    out = normalize_for_tts(written, "ar", VOICE_AGENT)
    assert "صباح" not in out and out.startswith("نستقبلك الساعة العاشرة والنصف ص"), out
