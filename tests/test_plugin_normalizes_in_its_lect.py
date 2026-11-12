"""The plugin normalizes text in the lect it was built for, not in "ar"."""
import pytest

import arbtok.plugin
from arbtok.plugin import ArbtokG2PPlugin


@pytest.fixture
def received(monkeypatch):
    langs = []
    real = arbtok.plugin.normalize_for_tts

    def record(text, lang="ar", *args, **kwargs):
        langs.append(lang)
        return real(text, lang, *args, **kwargs)

    monkeypatch.setattr(arbtok.plugin, "normalize_for_tts", record)
    return langs


# Each code is an orthography2ipa spec key, so the plugin's lect is the key itself.
@pytest.mark.parametrize("lect", ["arz-EG", "ars-SA", "apc-LB", "ary-MA"])
def test_normalize_passes_the_lect(received, lect):
    ArbtokG2PPlugin(lang=lect, diacritize=False).normalize("عنده 12 كتابا")
    assert received == [lect]


def test_transcribe_normalizes_in_the_lect(received):
    ArbtokG2PPlugin(lang="arz-EG", diacritize=False).transcribe("عنده 12 كتابا")
    assert received == ["arz-EG"]
