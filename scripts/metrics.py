import jiwer
import string
from arbtok.test import ALL_TEST_CASES
from arbtok.espeak_wrapper import EspeakPhonemizer
from arbtok.tokenizer import Sentence, PUNCT


def calculate_metrics(test_suite, espeak=False):
    total_chars = 0
    total_char_errors = 0
    total_words = 0
    total_word_errors = 0

    table = []

    for text, expected, desc in test_suite:
        if espeak:
            # NOTE: drop IPA stress marks, not present in ground_truth
            result = EspeakPhonemizer().phonemize_string(text, "ar").\
                replace(".", "").\
                replace("ˈ", "").\
                replace("ˌ", "")
        else:
            result = Sentence(text).ipa.strip(PUNCT + string.whitespace)
        expected = expected.strip(PUNCT + string.whitespace)

        cer = jiwer.cer(expected, result) * 100
        wer = jiwer.wer(expected, result) * 100

        total_char_errors += cer * len(expected) / 100
        total_chars += len(expected)
        total_word_errors += wer * len(expected.split()) / 100
        total_words += len(expected.split())

        status = "✅" if result == expected else "❌"
        table.append(f"{text:<25} | {result:<35} | {expected:<35} | {status} ")

        if status == "❌":
            print("-" * 120)
            print(f"Text: {text}")
            print(f"Test: {desc}")
            print(f"Result:   {result}")
            print(f"Expected: {expected}")

    overall_cer = (total_char_errors / total_chars) * 100 if total_chars > 0 else 0
    overall_wer = (total_word_errors / total_words) * 100 if total_words > 0 else 0

    table = ["-" * 120,
             f"{'Text':<25} | {'Result':<35} | {'Expected':<35} | {'Status'}  ",
             "-" * 120] + sorted(table)
    print("\n".join(table))
    print("-" * 120)
    print(f"Character Error Rate (CER): {overall_cer:.2f}%")
    print(f"Word Error Rate (WER):      {overall_wer:.2f}%")



calculate_metrics(ALL_TEST_CASES, espeak=False)
# ------------------------------------------------------------------------------------------------------------------------
# Text: الدَّار
# Test: Sun Letter: د
# Result:   addaːr
# Expected: addar
# ------------------------------------------------------------------------------------------------------------------------
# Text: الضَّوْء
# Test: Sun Letter:  ض
# Result:   adˤdˤawʔ
# Expected: aðˤːawʔ
# ------------------------------------------------------------------------------------------------------------------------
# Text: وَاسْمُه
# Test: Wasl: 'Alif' dropped after 'wa' (and)
# Result:   waːsmuh
# Expected: wasmuhu
# ------------------------------------------------------------------------------------------------------------------------
# Text: بِ اسْمِ
# Test: Wasl: 'Alif' dropped after 'bi' (with/in)
# Result:   bi smi
# Expected: bismi
# ------------------------------------------------------------------------------------------------------------------------
# Text: فِي الْبَيْت
# Test: Article 'a' dropped after preposition
# Result:   fiː lbajt
# Expected: fiː albajt
# ------------------------------------------------------------------------------------------------------------------------
# Text: مَأْسَاة
# Test: Various final hamza
# Result:   maʔsaː
# Expected: maʔsaːta
# ------------------------------------------------------------------------------------------------------------------------
# Text: أَبُو الْقُرْآن
# Test: Clitic + hamza initial nouns (cutting hamza retained)
# Result:   ʔabuː lqurʔaːn
# Expected: ʔabu lqurʔaːn
# ------------------------------------------------------------------------------------------------------------------------
# Text: الرِّسَالَة
# Test:  sun-letter + shadda on r
# Result:   arrisaːla
# Expected: arrisala
# ------------------------------------------------------------------------------------------------------------------------
# Text: مِنْ يَوْم
# Test: Assimilation: n + j -> jj
# Result:   min jawm
# Expected: mijjawm
# ------------------------------------------------------------------------------------------------------------------------
# Text: مِنْ لَبَن
# Test: Assimilation: n + l -> ll
# Result:   min laban
# Expected: millaban
# ------------------------------------------------------------------------------------------------------------------------
# Text: مِنْ بَعْد
# Test: Iqlab: n becomes 'm' before 'b'
# Result:   min baʕd
# Expected: membaʕd
# ------------------------------------------------------------------------------------------------------------------------
# Text: عَلَى الشَّاطِئ
# Test: assimilation across word boundaries (sandhi)
# Result:   ʕala: aʃʃaːtˤiʔ
# Expected: ʕala ʃʃaːtˤiʔ
# ------------------------------------------------------------------------------------------------------------------------
# Text: فِي الضَّوْءِ
# Test: assimilation across word boundaries (sandhi)
# Result:   fiː dˤdˤawʔi
# Expected: fiː ðˤðˤawʔ
# ------------------------------------------------------------------------------------------------------------------------
# Text: إِلَى الرَّجُل
# Test: assimilation across word boundaries (sandhi)
# Result:   ila: arradʒul
# Expected: ʔilaː rradʒul
# ------------------------------------------------------------------------------------------------------------------------
# Text: مَرْحَبًا!
# Test: Pausal: 'an' becomes long 'a' at end
# Result:   marħaban !
# Expected: marħabaː
# ------------------------------------------------------------------------------------------------------------------------
# Text: مَدِينَةٌ.
# Test: Pausal: Ta Marbuta and Tanwin dropped
# Result:   madiːnatun .
# Expected: madiːna
# ------------------------------------------------------------------------------------------------------------------------
# Text: كِتَابًا.
# Test: pausal form; loss of tanwīn
# Result:   kitaːban .
# Expected: kitaːbaː
# ------------------------------------------------------------------------------------------------------------------------
# Text: تِيكْنُولُوجْيَا
# Test: Loanwords / clusters atypical in CA/MSA
# Result:   tiːknuːluːdʒjaː
# Expected: tiːknuluːdʒjaː
# ------------------------------------------------------------------------------------------------------------------------
# Text: كِتَابٌ عَلَى الْمَكْتَب
# Test: Multiword, mixed assimilation + waṣl + hamza interactions
# Result:   kitaːbun ʕala: almaktab
# Expected: kitaːbun ʕala almaktab
# ------------------------------------------------------------------------------------------------------------------------
# Text: الشَّمْس وَالشَجَرَة
# Test: Multiword, mixed assimilation + waṣl + hamza interactions
# Result:   aʃʃams waːlʃadʒara
# Expected: aʃʃams wa ʃʒajara
# ------------------------------------------------------------------------------------------------------------------------
# Text: يَوْمُ الشَّمْس
# Test: Multiword, mixed assimilation + waṣl + hamza interactions
# Result:   jawmu ʃʃams
# Expected: jawm ʃʃams
# ------------------------------------------------------------------------------------------------------------------------
# Text: اِسْوَدَّ
# Test:  waṣl-based verb forms
# Result:   iswadda
# Expected: iswaddaː
# ------------------------------------------------------------------------------------------------------------------------
# Text: وَبِاسْمِ
# Test: wa + bi + ism, both join through wasl
# Result:   wabiaːsmi
# Expected: wabismi
# ------------------------------------------------------------------------------------------------------------------------
# Text: فَبِالْحَقِّ
# Test: fa + bi + al-, qamariyya retained
# Result:   fabiaːlħaqqi
# Expected: fabilħaqqi
# ------------------------------------------------------------------------------------------------------------------------
# Text: وَلِلنَّاس
# Test: wa + li + sun-letter
# Result:   walilnnaːs
# Expected: walinnaːs
# ------------------------------------------------------------------------------------------------------------------------
# Text: دُخَان
# Test: Miscellaneous lexical fillers
# Result:   duxaːn
# Expected: duħaːn
# ------------------------------------------------------------------------------------------------------------------------
# Text: سُيوف
# Test: Miscellaneous lexical fillers
# Result:   sujwf
# Expected: sujuːf
# ------------------------------------------------------------------------------------------------------------------------
# Text: أُمُّ الْمُسْلِمِينَ
# Test: lexical stressors
# Result:   ʔummu lmuslimiːna
# Expected: ʔummu lmuslimiːn
# ------------------------------------------------------------------------------------------------------------------------
# Text: أَبْيَض
# Test: lexical stressors
# Result:   ʔabjadˤ
# Expected: ʔabjaðˤ
# ------------------------------------------------------------------------------------------------------------------------
# Text: الرِّسَالَة
# Test: Sun letter with Shadda and Kasra ordering
# Result:   arrisaːla
# Expected: arrisala
# ------------------------------------------------------------------------------------------------------------------------
# Text: حَتَّى
# Test: Hidden gemination (morphological)
# Result:   ħatta:
# Expected: ħattaː
# ------------------------------------------------------------------------------------------------------------------------
# Text: إِلَّا
# Test: Hidden gemination (morphological)
# Result:   illaː
# Expected: ʔillaː
# ------------------------------------------------------------------------------------------------------------------------
# Text: سْتْر
# Test: synthetic test of illegal initial cluster
# Result:   str
# Expected: sitar
# ------------------------------------------------------------------------------------------------------------------------
# Text: مْسَلَّة
# Test: m + cluster; expected epenthetic i
# Result:   msalla
# Expected: imsallːa
# ------------------------------------------------------------------------------------------------------------------------
# Text: ذَهَبَ الطَّالِبُ إِلَى الْمَكْتَبَةِ لِقِرَاءَةِ كِتَابٍ عَنْ تَارِيخِ الأَنْدَلُس
# Test: Complex narrative sequence
# Result:   ðahaba tˤtˤaːlibu ila: almaktabati liqiraːʔati kitaːbin ʕan taːriːxi lʔandalus
# Expected: ðahaba tˤtˤaːlibu ʔilaː almaktabati liqiraːʔati kitaːbin ʕan taːriːxi alʔandalus
# ------------------------------------------------------------------------------------------------------------------------
# Text: ذَهَبَ الطَّالِبُ إِلَى الْمَكْتَبَةِ
# Test: Alif in Al- is dropped in connected speech
# Result:   ðahaba tˤtˤaːlibu ila: almaktabati
# Expected: ðahaba tˤtˤaːlibu ʔilaː almaktabati
# ------------------------------------------------------------------------------------------------------------------------
# Text: مَدْرَسَة
# Test: default penult (open)
# Result:   madrasa
# Expected: madrasah
# ------------------------------------------------------------------------------------------------------------------------
# Text: مُسْتَشْفَى
# Test: derived pattern, final long
# Result:   mustaʃfa:
# Expected: mustashfaː


# Character Error Rate (CER): 5.40%
# Word Error Rate (WER):      24.88%
