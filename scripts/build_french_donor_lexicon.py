"""Build the bundled French donor lexicon: the closed classes of French, read from a cited dictionary.

    python scripts/build_french_donor_lexicon.py french_mfa.dict arbtok/data/donor_lexicons

French reaches Arabic speech mostly as grammar: articles, prepositions, conjunctions,
pronouns, a few adverbs and the words a conversation is steered with (*alors*, *donc*,
*déjà*, *voilà*, *d'accord*). Those classes are closed, so they can be listed, and they are
the words French spelling misleads a rule system on most: *les* and *des* end in a letter
that is not said, *et* and *est* are one sound each, *six* and *dix* keep a consonant that
*prix* does not.

The list below is membership only. Every pronunciation comes from the French MFA dictionary
v3.0.0 (McAuliffe and Sonderegger 2024, Montreal Forced Aligner, CC BY 4.0), the most
probable pronunciation it gives for the word, unless the word has sandhi forms (see
`choose`). A word it does not hold is reported and left out; none is written by hand.

Two files come out. `fr-FR.tsv` is word and IPA, the shape orthography2ipa's lexicon overlay
reads. `fr-FR.sources.tsv` adds, for each word, its class here, the dictionary's own phone
string, the probability the dictionary gives it and the probability that a pause follows it.
"""
import sys
from pathlib import Path

SOURCE = "French MFA dictionary v3.0.0 (McAuliffe and Sonderegger 2024), CC BY 4.0"

CLOSED_CLASSES = {
    "article": "le la les l' un une des du au aux",
    "preposition": "à de d' en dans sur sous avec sans pour par chez vers entre contre depuis pendant "
                   "avant après devant derrière près loin jusqu'à selon malgré",
    "conjunction": "et ou mais donc or ni car que qu' qu'il qu'elle qu'on si quand comme lorsque "
                   "puisque parce",
    "pronoun": "je j' tu il elle on nous vous ils elles me m' te t' se s' lui leur y moi toi soi eux "
               "ce c' ça cela ceci celui celle ceux celles qui quoi dont où lequel laquelle quel quelle",
    "determiner": "mon ma mes ton ta tes son sa ses notre nos votre vos leurs cet cette ces chaque "
                  "quelque quelques plusieurs tout toute tous toutes même autre autres",
    "negation": "ne n' pas plus jamais rien personne aucun aucune",
    "adverb": "très trop peu beaucoup bien mal assez aussi encore déjà toujours souvent parfois "
              "maintenant hier demain aujourd'hui ici là là-bas alors enfin ensuite puis vraiment "
              "justement exactement normalement franchement seulement peut-être presque vite tard tôt",
    "discourse": "oui non si voilà bon ben bah hein euh d'accord ok merci pardon bonjour bonsoir salut "
                 "normal grave désolé bref sûr s'il plaît revoir",
    "auxiliary": "suis es est sommes êtes sont ai as a avons avez ont était c'est j'ai n'est s'est",
    "number": "zéro deux trois quatre cinq six sept huit neuf dix vingt cent mille",
}

# The dictionary writes allophones its acoustic models use; a lexicon for a phonemic G2P does not.
PHONES = {"c": "k", "ɟ": "ɡ", "mʲ": "m", "ʎ": "lj"}

# A word whose attributive use dominates is read in the form it takes there, which is before
# a consonant, not before a pause. *tous* is [tu] as the determiner of *tous les jours* and
# *tous les deux*, and [tus] only as the stressed pronoun of *ils sont tous là*. A word-to-IPA
# map sees one token either way, so it gives the common case.
ATTRIBUTIVE = {"tous"}

VOWELS = {"a", "ɑ", "e", "ɛ", "i", "o", "ɔ", "u", "y", "ø", "œ", "ə", "ɛ̃", "ɑ̃", "ɔ̃", "œ̃"}


def read_dictionary(path):
    """word -> [(probability, pause probability, phones)] for every pronunciation of each word."""
    variants = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) < 6:
            continue
        variants.setdefault(fields[0], []).append((float(fields[1]), float(fields[2]), fields[5].split()))
    return variants


def _final_consonant_apart(a, b):
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    return len(longer) == len(shorter) + 1 and longer[:-1] == shorter and longer[-1] not in VOWELS


def choose(variants, alone=True):
    """The reading a lexicon consulted one word at a time should give.

    That is the most probable pronunciation, except where the word has sandhi forms: variants
    that differ only by a final consonant, sounded or dropped by what follows. *six* is [si]
    before a consonant, [siz] before a vowel and [sis] before a pause, and the dictionary
    ranks [si] first. A word read on its own stands before a pause, so among those variants
    the one taken is the one the dictionary most often puts there: the largest product of
    pronunciation probability and the probability that a pause follows. A word that is rarely
    said alone (``alone=False``) keeps the most probable pronunciation.
    """
    top = max(variants, key=lambda v: v[0])
    if not alone:
        return top
    sandhi = [v for v in variants if v is top or _final_consonant_apart(v[2], top[2])]
    return max(sandhi, key=lambda v: (v[0] * v[1], v is top))


def build(dictionary_path, out_dir):
    dictionary = read_dictionary(dictionary_path)
    rows, absent = {}, []
    for word_class, words in CLOSED_CLASSES.items():
        for word in words.split():
            if word in rows:
                continue
            if word not in dictionary:
                absent.append(word)
                continue
            probability, pause, phones = choose(dictionary[word], alone=word not in ATTRIBUTIVE)
            rows[word] = (word_class, "".join(PHONES.get(p, p) for p in phones), " ".join(phones),
                          probability, pause)
    out = Path(out_dir)
    with open(out / "fr-FR.tsv", "w", encoding="utf-8") as lexicon:
        lexicon.writelines(f"{word}\t{ipa}\n" for word, (_, ipa, _, _, _) in sorted(rows.items()))
    with open(out / "fr-FR.sources.tsv", "w", encoding="utf-8") as sources:
        sources.write(f"# {SOURCE}\n"
                      "# word\tclass\tipa\tdictionary_phones\tdictionary_probability\tdictionary_pause_probability\n")
        sources.writelines(f"{word}\t{c}\t{ipa}\t{phones}\t{p}\t{pause}\n"
                           for word, (c, ipa, phones, p, pause) in sorted(rows.items()))
    return len(rows), absent


if __name__ == "__main__":
    written, absent = build(sys.argv[1], sys.argv[2])
    print(written, "words written;", len(absent), "not in the dictionary:", " ".join(absent))
