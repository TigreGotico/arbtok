"""
gold test set

TODO: waiting for human review, LLM generated test cases
      I need an arabic speaker to validate IPA values
"""

# --- TEST CATEGORIES ---

# Basic Vowels and Consonants
# Tests standard letter-to-IPA mapping without complex interactions.
BASIC_TESTS = [
    ("مَرْحَبًا", "marħaban", "Basic CV structure with Tanwin (nunation) 'an'"),
    ("فِيل", "fiːl", "Long vowel 'i' (Ya)"),
    ("بَيْت", "bajt", "Diphthong 'ay'"),
    ("يَوْم", "jawm", "Diphthong 'aw'"),
    ("قَلَمٌ", "qalamun", "Standard consonant + Tanwin 'un'"),
]
# Sun Letter Assimilation (Shamsiyya)
# In Arabic, the 'l' of the definite article 'Al-' is silent and the
# following consonant is doubled if it's a "Sun Letter".
SUN_LETTER_TESTS = [
    ("الشَّمْس", "aʃʃams", "Sun Letter: sh (shams)"),
    ("السَّمَك", "assamak", "Sun Letter: s (samak)"),
    ("التَّاج", "attaːdʒ", "Sun Letter: t (taj)"),

    ("الثَّوْب", "aθθawb", "Sun Letter: ث"),  # ث
    ("الذَّهَب", "aððahab", "Sun Letter:  ذ"),  # ذ
    ("الرَّجُل", "arradʒul", "Sun Letter:  ر"),  # ر
    ("الزَّيْت", "azzajt", "Sun Letter: ز"),  # ز
    ("الطَّعَام", "atˤtˤaʕaːm", "Sun Letter:  ط"),  # ط
    ("الظَّبْي", "aðˤðˤabj", "Sun Letter:  ظ"),  # ظ

    ("اللَّوْن", "allawn", "Sun Letter: l (lawn)"),  # ل
    ("النَّار", "annaːr", "Sun Letter: n (nar)"),  # ن
    ("الصَّوْت", "asˤsˤawt", "Sun Letter: sˤ (emphatic s)"),  # ص

    ("الدَّار", "addaːr", "Sun Letter: د"),  # د
    ("الضَّوْء", "adˤdˤawʔ", "Sun Letter:  ض"),  # ض
]
# Moon Letters (Qamariyya)
# The 'l' in 'Al-' is pronounced clearly before "Moon Letters".
MOON_LETTER_TESTS = [
    ("الْقَمَر", "alqamar", "Moon Letter: q"),
    ("الْكِتَاب", "alkitaːb", "Moon Letter: k"),
    ("الْمَسْجِد", "almasdʒid", "Moon Letter: m"),
]
# Hamzat al-Wasl & Proclitics
# This is "Connecting Hamza". It is pronounced at the start of a sentence
# but dropped (elided) when preceded by a word or a proclitic (like 'wa' or 'bi').
WASL_TESTS = [
    ("بِ الْمَدِينَة", "bi lmadiːna", "Connected speech: bi + al -> bil"),
    ("لِ النَّاس", "li nnaːs", "lam + sun-letter"),  #
    ("بِ الطَّبِيب", "bi tˤtˤabiːb", "bi + al + ṭāʔ"),  #
    ("فِي الشَّرِكَة", "fiː ʃʃarika", "Wasl interaction in phrases"),
    ("لِ الْكِتَاب", "li lkitaːb", "Wasl interaction in phrases"),
    ("فِي الْقَلَم", "fiː lqalam", "Wasl interaction in phrases"),

    ("وَاسْمُه", "wasmuhu", "Wasl: 'Alif' dropped after 'wa' (and)"),  # TODO - failing
    ("بِ اسْمِ", "bismi", "Wasl: 'Alif' dropped after 'bi' (with/in)"),  # TODO - failing
    ("فِي الْبَيْت", "fiː albajt", "Article 'a' dropped after preposition"),  # TODO - failing
]
# Hamza Variants
# The Glottal Stop (ʔ) can sit on different 'chairs' (Alif, Waw, Ya) or stand alone.
HAMZA_TESTS = [
    ("أَمِير", "ʔamiːr", "Hamza on Alif (initial)"),
    ("سُؤَال", "suʔaːl", "Hamza on Waw (medial)"),
    ("بِئْر", "biʔr", "Hamza on Ya (medial)"),
    ("شَيْء", "ʃajʔ", "Standalone Hamza (final)"),
    ("آكُل", "ʔaːkul", "Alif Madda (Hamza + long vowel)"),
    ("قُرْآن", "qurʔaːn", "The Glottal Stop (ʔ) can sit on different 'chairs' (Alif, Waw, Ya) or stand alone."),
    ("مِائَة", "miʔa", "The Glottal Stop (ʔ) can sit on different 'chairs' (Alif, Waw, Ya) or stand alone."),
    ("رَأْس", "raʔs", "The Glottal Stop (ʔ) can sit on different 'chairs' (Alif, Waw, Ya) or stand alone."),
    ("مَسْأَلَة", "masʔala", "The Glottal Stop (ʔ) can sit on different 'chairs' (Alif, Waw, Ya) or stand alone."),
    ("مَسْئُول", "masʔuːl", "The Glottal Stop (ʔ) can sit on different 'chairs' (Alif, Waw, Ya) or stand alone."),

    # === Hamza seated / madda / complex clusters ===
    ("آمِن", "ʔaːmin", " madda-medial"),  # madda-medial
    ("مُسَاء", "musaːʔ", "final hamza after long vowel"),  # final hamza after long vowel
    ("جِئْتُ", "dʒiʔtu", "hamza between front vowel & cluster"),  # hamza between front vowel & cluster
    ("شِئْتَ", "ʃiʔta", "Hamza seated / madda / complex clusters"),
    ("فِئَات", "fiʔaːt", "morphological plural w/ medial hamza"),  # morphological plural w/ medial hamza
    ("مَلَائِكَة", "malaːʔika", "hamza + long vowel + broken plural"),  # hamza + long vowel + broken plural

    # Various final hamza
    ("مَاء", "maːʔ", "Various final hamza"),

    # === End-hamza alternations ===
    ("جُزْء", "dʒuzʔ", "End-hamza alternations"),
    ("بُرْء", "burʔ", "End-hamza alternations"),
    ("نَبَأ", "nabaʔ", "End-hamza alternations"),
    ("يَبْدَأ", "jabdaʔ", "End-hamza alternations"),
    ("يَلْجَأ", "jaldʒaʔ", "End-hamza alternations"),

    # Clitic + hamza initial nouns (cutting hamza retained)
    ("قِرَاءَتُهُمْ", "qiraːʔatuhum", "Clitic + hamza initial nouns (cutting hamza retained)"),
    ("مَأْسَاة", "maʔsaːta", "Various final hamza"),  # TODO - failing; gold disputed: ta marbuta is silent in pausal form; connected-form ta requires following vowel
    ("أَبُو الْقُرْآن", "ʔabu lqurʔaːn", "Clitic + hamza initial nouns (cutting hamza retained)"),  # TODO - failing; gold disputed: أَبُو is long /ʔabuː/ in MSA (DAMMA+WAW = long u), not short ʔabu
]
# Special Exceptions & Divine Names
# Words with irregular spellings (e.g., hidden vowels or silent letters).
EXCEPTION_TESTS = [
    ("هٰذَا", "haːðaː", "Dagger Alif: unwritten long 'a'"),
    ("اللّٰه", "allaːh", "Allah: heavy 'l' and unwritten Alif"),
    ("عَمْرٌو", "ʕamrun", "Silent Waw used to distinguish name 'Amr' from 'Umar"),
    ("مِائَة", "miʔa", "Silent Alif in the word for 'hundred'"),
    ("الرِّسَالَة", "arrisala", " sun-letter + shadda on r"),  # TODO - failing; gold disputed: correct MSA is arrisaːla (long a from alif mater lectionis)
]
# Sandhi & Assimilation (N-sounds)
TANWIN_SANDHI_TESTS = [
    # Tanwīn + sandhi + case endings
    ("كُتُبٌ", "kutubun", "Tanwīn + sandhi + case endings"),
    ("قَلَمٌ", "qalamun", "Tanwīn + sandhi + case endings"),
    ("مَاءٌ", "maːʔun", "Tanwīn + sandhi + case endings"),
]
# How sounds change at word boundaries (Tajweed-lite rules).
SANDHI_TESTS = [
    ("بِ الظَّرْف", "bi ðˤðˤarf", "assimilation across word boundaries (sandhi)"),
    ("مِنَ النَّاس", "mina nnaːs", "assimilation across word boundaries (sandhi)"),

    # Idgham (n assimilation)
    ("مِنْ رَبِّهِمْ", "mir rabbihim", "Total assimilation n+r -> rr"),
    ("مَنْ يَقُولُ", "maj jaquːlu", "Partial assimilation n+j -> jj"),

    # "Iqlab: n becomes 'm' before 'b'"
    ("مِنْ بَيْتِكَ", "mim bajtika", "Iqlab: n becomes 'm' before 'b'"),
    ("مِنْ بَعْد", "mimbaʕd", "Iqlab: n becomes 'm' before 'b'"),

    ("عَلَى الشَّاطِئ", "ʕala ʃʃaːtˤiʔ", "assimilation across word boundaries (sandhi)"),  # TODO - failing; gold disputed: عَلَى has alif maqsura = long /ʕalaː/, inconsistent with إِلَى الرَّجُل gold
    ("فِي الضَّوْءِ", "fiː ðˤðˤawʔ", "assimilation across word boundaries (sandhi)"),  # TODO - failing; gold disputed: عَلَى ends in alif maqsura = long ʕalaː, not short ʕala
    ("إِلَى الرَّجُل", "ʔilaː rradʒul", "assimilation across word boundaries (sandhi)"),

]

# In Arabic, word endings (like Tanwin) are often dropped at the end of a sentence.
PAUSAL_TESTS = [
    # === Pausal forms (end-of-utterance) ===
    ("كِتَابًا.", "kitaːbaː", "pausal form; loss of tanwīn"),
    ("مَدِينَةٌ.", "madiːna", "Pausal: Ta Marbuta and Tanwin dropped"),
    ("مَرْحَبًا!", "marħabaː", "Pausal: 'an' becomes long 'a' at end"),

]

WEAK_TESTS = [
    # Broken plurals / weak radicals
    ("ذَهَبُوا", "ðahabuː", "Broken plurals / weak radicals"),
    ("سَكَنُوا", "sakanuː", "Broken plurals / weak radicals"),
    ("قَالُوا", "qaːluː", "Broken plurals / weak radicals"),
    ("تَوَاصَلُوا", "tawaːsˤaluː", "Broken plurals / weak radicals"),

    # Weak root nouns
    ("إِيْمَان", "iːmaːn", "Weak root nouns"),
    ("انْتِمَاء", "intimaːʔ", "Weak root nouns"),

    # Defective Verbs (Final weak radicals)
    ("رَمَى", "ramaː", "Alif Maqsura as long a"),
    ("دَعَا", "daʕaː", "Alif Mamduda as long a"),
    ("قَاضٍ", "qaːdˤin", "Defective noun with Tanwin Kasra"),

    # === Weak radicals / defective & hollow verbs ===
    ("بَاعُوا", "baːʕuː", "Weak radicals / defective & hollow verbs"),
    ("سَارُوا", "saːruː", "Weak radicals / defective & hollow verbs"),
    ("نَامُوا", "naːmuː", "Weak radicals / defective & hollow verbs"),
    ("بِيعَ", "biːʕa", "passive with weak second radical"),  # passive with weak second radical
    ("قِيلَ", "qiːla", "Weak radicals / defective & hollow verbs"),
    ("عُيِّنَ", "ʕujjina", "form II passive, glide assimilation"),  # form II passive, glide assimilation
]
INTERNAL_HAMZA_TESTS = [
    # Internal hamza + derived forms
    ("مُؤْتَمَر", "muʔtamar", "Internal hamza + derived forms"),
    ("مُؤْمِن", "muʔmin", "Internal hamza + derived forms"),
    ("تَأْثِير", "taʔθiːr", "Internal hamza + derived forms"),
    ("مَأْكُول", "maʔkuːl", "Internal hamza + derived forms"),
    ("مَأْمُون", "maʔmuːn", "Internal hamza + derived forms"),
]
GEMINATION_EMPHATICS_TESTS = [
    # Imperfect verb with gemination + emphatics
    ("يُصَلِّي", "jusˤalliː", "Imperfect verb with gemination + emphatics"),
    ("ظَلَّ", "ðˤalla", "Imperfect verb with gemination + emphatics"),
    ("طَبَق", "tˤabaq", "Imperfect verb with gemination + emphatics"),
]
LOANWORD_TESTS = [
    # Loanwords / clusters atypical in CA/MSA
    ("فِلْم", "film", "Loanwords / clusters atypical in CA/MSA"),

    ("تِيكْنُولُوجْيَا", "tiːknuluːdʒjaː", "Loanwords / clusters atypical in CA/MSA"),  # TODO - failing; gold disputed: WAW+DAMMA = long /uː/ in MSA orthography; tiːknuːluːdʒjaː is consistent
]
COMPLEX_MULTI_WORD_TESTS = [
    # Complex multiword assimilation (sun letters, hamza, wasl)
    ("مُعَلِّمُ الطِّفْل", "muʕallimu tˤtˤifl", "Complex multiword assimilation (sun letters, hamza, wasl)"),
    ("رِسَالَةُ النَّاس", "risaːlatu nnaːs", "Complex multiword assimilation (sun letters, hamza, wasl)"),
    ("مَدِينَةُ الطِّفْل", "madiːnatu tˤtˤifl", "Complex multiword assimilation (sun letters, hamza, wasl)"),

    # Multiword, mixed assimilation + waṣl + hamza interactions
    ("فِي الشَّمْس", "fiː ʃʃams", "Multiword, mixed assimilation + waṣl + hamza interactions"),

    ("كِتَابٌ عَلَى الْمَكْتَب", "kitaːbun ʕala almaktab", "Multiword, mixed assimilation + waṣl + hamza interactions"),
    # TODO - failing
    ("الشَّمْس وَالشَجَرَة", "aʃʃams wa ʃʒajara", "Multiword, mixed assimilation + waṣl + hamza interactions"),
    # TODO - failing
    ("يَوْمُ الشَّمْس", "jawm ʃʃams", "Multiword, mixed assimilation + waṣl + hamza interactions"),  # TODO - failing; gold disputed: terminal case vowel (damma) drop is inconsistent with الطَّالِبُ keeping its damma
]
HAMZAT_AL_WASL_TESTS = [
    # Hamzat al-waṣl initial forms (istifʿāl, iftiʿāl)
    ("اِسْتِقْبَال", "istiqbaːl", "Hamzat al-waṣl initial forms"),
    ("اِسْتِعْدَاد", "istiʕdaːd", "Hamzat al-waṣl initial forms"),
    ("اِبْتِدَاء", "ibtidaːʔ", "Hamzat al-waṣl initial forms"),
    ("اِجْتِمَاع", "ijtimaːʕ", "Hamzat al-waṣl initial forms"),
    ("اِعْتِمَاد", "iʕtimaːd", "Hamzat al-waṣl initial forms"),
    # === Additional waṣl-based verb forms ===
    ("اِنْقَطَع", "inqatˤaʕ", " waṣl-based verb forms"),
    ("اِنْفِعَال", "infiʕaːl", " waṣl-based verb forms"),
    ("اِفْعَوَّل", "ifʕawwal", " waṣl-based verb forms"),
    ("اِحْمِرَار", "iħmiraːr", " waṣl-based verb forms"),

    ("اِسْوَدَّ", "iswaddaː", " waṣl-based verb forms"),  # TODO - failing; gold disputed: Form IX اسودّ ends in short fatha, not long aː
    # === Hamzat al-waṣl / proclitic stacking ===
    ("وَبِاسْمِ", "wabismi", "wa + bi + ism, both join through wasl"),
    ("فَبِالْحَقِّ", "fabilħaqqi", "fa + bi + al-, qamariyya retained"),
    ("وَلِلنَّاس", "walinnaːs", "wa + li + sun-letter"),
]
DEVOICING_TESTS = [
    # Devoicing / syllable-boundary stressors
    ("بَوْت", "bawt", "Devoicing / syllable-boundary stressors"),
    ("غُرُوب", "ɣuruːb", "Devoicing / syllable-boundary stressors"),

]
LEXICAL_TESTS = [
    # === Miscellaneous lexical fillers ===
    ("مِفْتَاح", "miftaːħ", "Miscellaneous lexical fillers"),
    ("عِلْم", "ʕilm", "Miscellaneous lexical fillers"),
    ("صَحْرَاء", "sˤaħraːʔ", "Miscellaneous lexical fillers"),
    ("غَيْم", "ɣajm", "Miscellaneous lexical fillers"),

    # Additional lexical stressors
    ("أُمّ", "ʔumm", "lexical stressors"),
    ("سَائِق", "saːʔiq", "lexical stressors"),
    ("أَثَاث", "ʔaθaːθ", "lexical stressors"),

    ("دُخَان", "duħaːn", "Miscellaneous lexical fillers"),  # TODO - failing; gold disputed: خ = /x/ in MSA, not /ħ/
    ("سُيوف", "sujuːf", "Miscellaneous lexical fillers"),  # TODO - failing; gold disputed: deficient spelling without kasra on ي, needs lexical fix
    ("أُمُّ الْمُسْلِمِينَ", "ʔummu lmuslimiːn", "lexical stressors"),  # TODO - failing; gold disputed: final -na drop inconsistent with يَسْتَخْدِمُونَ gold which keeps final vowel
    ("أَبْيَض", "ʔabjaðˤ", "lexical stressors"),  # TODO - failing; gold disputed: ض = /dˤ/ in MSA, not /ðˤ/
]

VARIANT_TESTS = [
    # === Unicode / orthographic variants ===
    ("ﷲ", "allaːh", "Unicode / orthographic variants: Allah ligature"),  # Allah ligature
    ("ﻻ", "laː", "Unicode / orthographic variants: lam-alif ligature"),
    # lam-alif ligature("هٰذَا", "haːðaː", "Dagger Alif (superscript Alif)"),
    ("اللّٰه", "allaːh", "Full spelling of Allah with Dagger Alif"),

    ("الرِّسَالَة", "arrisala", "Sun letter with Shadda and Kasra ordering"),  # TODO - failing; gold disputed: correct MSA is arrisaːla
]
HIDDEN_GEMINATION_TESTS = [
    # === Hidden gemination (morphological) ===
    ("كَأَنَّمَا", "kaʔannamaː", "Hidden gemination (morphological)"),
    ("عَمَّ", "ʕamma", "Hidden gemination (morphological)"),
    ("كُلّ", "kull", "Hidden gemination (morphological)"),

    ("حَتَّى", "ħattaː", "Hidden gemination (morphological)"),
    ("إِلَّا", "ʔillaː", "Hidden gemination (morphological)"),
]
DIPHTHONG_TESTS = [
    # === Diphthongs vs monophthongization ===
    ("حَوْل", "ħawl", "Diphthongs vs monophthongization"),
    ("زَيْن", "zajn", "Diphthongs vs monophthongization"),
    ("طَوْر", "tˤawr", "Diphthongs vs monophthongization"),
    ("زَيْتُون", "zajtuːn", "Diphthongs vs monophthongization"),

]
EPHENTESIS_TESTS = [
    # === Epenthesis / phonotactic repair (cluster handling) ===
    ("وِلْد", "wild", "borrowed-like shape, no epenthesis"),  # borrowed-like shape, no epenthesis
    ("سْتْر", "sitar", "synthetic test of illegal initial cluster"),  # TODO - failing; gold disputed: imsallːa has spurious ː, correct epenthesis gives imsalla
    ("مْسَلَّة", "imsallːa", "m + cluster; expected epenthetic i"),  # TODO - failing; gold disputed: expected form is imsalla; imsallːa has spurious length mark
]
NUNATION_TESTS = [
    ("كِتَابٌ قَدِيم", "kitaːbun qadiːm", "no assimilation before uvular"),  # no assimilation before uvular
    ("كِتَابٌ جَدِيد", "kitaːbun dʒadiːd", "no assimilation before /dʒ/"),  # no assimilation before /dʒ/

    ("مِنْ يَوْم", "mijjawm", "idgham w/ ghunna into /j/ (/y/) glide"),
    ("مِنْ لَبَن", "millaban", "idgham into lam"),
    ("مِنْ تَحْت", "mintˤaħt", "ikhfa: nasalized n before /tˤ/"),  # TODO - failing; gold disputed: the consonant is TEH (ت = /t/) not TA (ط = /tˤ/)
]
MISC_TESTS = [
    # Miscellaneous additions for good coverage
    ("أَبْوَاب", "ʔabwaːb", "Miscellaneous additions for good coverage"),
    ("مَدِينَة", "madiːna", "Miscellaneous additions for good coverage"),
    ("رِسَالَة", "risaːla", "Miscellaneous additions for good coverage"),
    ("قِرْد", "qird", "Miscellaneous additions for good coverage"),
    ("تَدْرِيس", "tadriːs", "Miscellaneous additions for good coverage"),

    # Complex narrative sequence
    ("ذَهَبَ الطَّالِبُ إِلَى الْمَكْتَبَةِ لِقِرَاءَةِ كِتَابٍ عَنْ تَارِيخِ الأَنْدَلُس",
     "ðahaba tˤtˤaːlibu ʔilaː almaktabati liqiraːʔati kitaːbin ʕan taːriːxi alʔandalus",
     "Complex narrative sequence"),  # TODO - failing; gold disputed: inconsistent wasl — ʔilaː almaktabati contradicts wasl-elision rule
    ("ذَهَبَ الطَّالِبُ إِلَى الْمَكْتَبَةِ", "ðahaba tˤtˤaːlibu ʔilaː almaktabati",
     "Alif in Al- is dropped in connected speech"),  # TODO - failing; gold disputed: inconsistent wasl — ʔilaː almaktabati contradicts wasl-elision rule

]
STRESS_TESTS = [
    # === Stress / syllable-weight contrasts (if marking stress) ===
    ("مَكْتُوب", "maktuːb", "heavy final"),  # heavy final
    ("مَفَاتِيح", "mafaːtiːħ", "long penult"),  # long penult

    # MORPHOLOGICAL_STRESS_TESTS
    ("كَتَبَتَا", "katabataː", "Dual feminine past"),
    ("مُدَرِّسُونَ", "mudarrisuːna", "Masculine plural active participle"),
    ("يَسْتَخْدِمُونَ", "jastaxdimuːna", "Form X present plural"),

    # from wordlist exceptions - TODO should not need wordlist
    ("مَدْرَسَة", "madrasah", "default penult (open)"),
    ("مُسْتَشْفَى", "mustashfaː", "derived pattern, final long"),
]

# --- PYTEST ENGINE ---
ALL_TEST_CASES = (
        BASIC_TESTS +
        SUN_LETTER_TESTS +
        MOON_LETTER_TESTS +
        WASL_TESTS +
        HAMZA_TESTS +
        EXCEPTION_TESTS +
        SANDHI_TESTS +
        TANWIN_SANDHI_TESTS +
        PAUSAL_TESTS +
        WEAK_TESTS +
        INTERNAL_HAMZA_TESTS +
        GEMINATION_EMPHATICS_TESTS +
        LOANWORD_TESTS +
        COMPLEX_MULTI_WORD_TESTS +
        HAMZAT_AL_WASL_TESTS +
        DEVOICING_TESTS +
        LEXICAL_TESTS +
        VARIANT_TESTS +
        HIDDEN_GEMINATION_TESTS +
        DIPHTHONG_TESTS +
        EPHENTESIS_TESTS +
        NUNATION_TESTS +
        MISC_TESTS +
        STRESS_TESTS
)
