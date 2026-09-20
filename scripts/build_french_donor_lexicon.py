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
probable pronunciation it gives for the word. A word it does not hold is reported and left
out; none is written by hand.

Two files come out. `fr-FR.tsv` is word and IPA, the shape orthography2ipa's lexicon overlay
reads. `fr-FR.sources.tsv` adds, for each word, its class here, the dictionary's own phone
string and the probability the dictionary gives it.
"""
import sys
from pathlib import Path

SOURCE = "French MFA dictionary v3.0.0 (McAuliffe and Sonderegger 2024), CC BY 4.0"

CLOSED_CLASSES = {
    "article": "le la les l' un une des du au aux",
    "preposition": "à de d' en dans sur sous avec sans pour par chez vers entre contre depuis pendant "
                   "avant après devant derrière près loin jusqu'à selon malgré",
    "conjunction": "et ou mais donc or ni car que qu' si quand comme lorsque puisque parce",
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
    "auxiliary": "suis es est sommes êtes sont ai as a avons avez ont était c'est j'ai",
    "number": "zéro deux trois quatre cinq six sept huit neuf dix vingt cent mille",
}

# The dictionary writes allophones its acoustic models use; a lexicon for a phonemic G2P does not.
PHONES = {"c": "k", "ɟ": "ɡ", "mʲ": "m", "ʎ": "lj"}


def read_dictionary(path):
    """word -> (probability, phones) for the most probable pronunciation of each word."""
    best = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) < 6:
            continue
        word, probability, phones = fields[0], float(fields[1]), fields[5].split()
        if word not in best or probability > best[word][0]:
            best[word] = (probability, phones)
    return best


def build(dictionary_path, out_dir):
    dictionary = read_dictionary(dictionary_path)
    rows, absent, elided = {}, [], []
    for word_class, words in CLOSED_CLASSES.items():
        for word in words.split():
            if word in rows:
                continue
            # orthography2ipa splits a word at an apostrophe before it consults a lexicon, so
            # an entry for l', c'est or aujourd'hui would never be read. They stay in the list
            # above as members of their class and are left out of the file until it can be.
            if "'" in word:
                elided.append(word)
                continue
            if word not in dictionary:
                absent.append(word)
                continue
            probability, phones = dictionary[word]
            rows[word] = (word_class, "".join(PHONES.get(p, p) for p in phones), " ".join(phones), probability)
    out = Path(out_dir)
    with open(out / "fr-FR.tsv", "w", encoding="utf-8") as lexicon:
        lexicon.writelines(f"{word}\t{ipa}\n" for word, (_, ipa, _, _) in sorted(rows.items()))
    with open(out / "fr-FR.sources.tsv", "w", encoding="utf-8") as sources:
        sources.write(f"# {SOURCE}\n# word\tclass\tipa\tdictionary_phones\tdictionary_probability\n")
        sources.writelines(f"{word}\t{c}\t{ipa}\t{phones}\t{p}\n" for word, (c, ipa, phones, p) in sorted(rows.items()))
    return len(rows), absent, elided


if __name__ == "__main__":
    written, absent, elided = build(sys.argv[1], sys.argv[2])
    print(written, "words written;", len(absent), "not in the dictionary:", " ".join(absent))
    print(len(elided), "elided forms left out:", " ".join(elided))
