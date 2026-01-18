import os
import re
import string
import subprocess
from typing import List, Optional
from typing import Tuple

import numpy as np
import onnxruntime
import requests
from quebra_frases import sentence_tokenize

from arbtok.tashkeel import TashkeelDiacritizer
from arbtok.util import normalize, match_lang

# list of (substring, terminator, end_of_sentence) tuples.
TextChunks = List[Tuple[str, str, bool]]
# list of (phonemes, terminator, end_of_sentence) tuples.
RawPhonemizedChunks = List[Tuple[str, str, bool]]

PhonemizedChunks = list[list[str]]


class EspeakError(Exception):
    """Custom exception for espeak-ng related errors."""
    pass


class EspeakPhonemizer:
    """
    A phonemizer class that uses the espeak-ng command-line tool to convert text into phonemes.
    It segments the input text heuristically based on punctuation to mimic clause-by-clause processing.
    """
    ESPEAK_LANGS = ['es-419', 'ca', 'qya', 'ga', 'et', 'ky', 'io', 'fa-latn', 'en-gb', 'fo', 'haw', 'kl',
                    'ta', 'ml', 'gd', 'sd', 'es', 'hy', 'ur', 'ro', 'hi', 'or', 'ti', 'ca-va', 'om', 'tr', 'pa',
                    'smj', 'mk', 'bg', 'cv', "fr", 'fi', 'en-gb-x-rp', 'ru', 'mt', 'an', 'mr', 'pap', 'vi', 'id',
                    'fr-be', 'ltg', 'my', 'nl', 'shn', 'ba', 'az', 'cmn', 'da', 'as', 'sw',
                    'piqd', 'en-us', 'hr', 'it', 'ug', 'th', 'mi', 'cy', 'ru-lv', 'ia', 'tt', 'hu', 'xex', 'te', 'ne',
                    'eu', 'ja', 'bpy', 'hak', 'cs', 'en-gb-scotland', 'hyw', 'uk', 'pt', 'bn', 'mto', 'yue',
                    'be', 'gu', 'sv', 'sl', 'cmn-latn-pinyin', 'lfn', 'lv', 'fa', 'sjn', 'nog', 'ms',
                    'vi-vn-x-central', 'lt', 'kn', 'he', 'qu', 'ca-ba', 'quc', 'nb', 'sk', 'tn', 'py', 'si', 'de',
                    'ar', 'en-gb-x-gbcwmd', 'bs', 'qdb', 'sq', 'sr', 'tk', 'en-029', 'ht', 'ru-cl', 'af', 'pt-br',
                    'fr-ch', 'ka', 'en-gb-x-gbclan', 'ko', 'is', 'ca-nw', 'gn', 'kok', 'la', 'lb', 'am', 'kk', 'ku',
                    'kaa', 'jbo', 'eo', 'uz', 'nci', 'vi-vn-x-south', 'el', 'pl', 'grc', ]

    def __init__(self, taskeen_threshold: Optional[float] = 0.8):
        self.taskeen_threshold = taskeen_threshold  # arabic only
        self._tashkeel: Optional[TashkeelDiacritizer] = None

    @classmethod
    def get_lang(cls, target_lang: str) -> str:
        """
        Validates and returns the closest supported language code.

        Args:
            target_lang (str): The language code to validate.

        Returns:
            str: The validated language code.

        Raises:
            ValueError: If the language code is unsupported.
        """
        if target_lang.lower() == "en-gb":
            return "en-gb-x-rp"
        if target_lang in cls.ESPEAK_LANGS:
            return target_lang
        if target_lang.lower().split("-")[0] in cls.ESPEAK_LANGS:
            return target_lang.lower().split("-")[0]
        return cls.match_lang(target_lang, cls.ESPEAK_LANGS)

    @property
    def tashkeel(self) -> TashkeelDiacritizer:
        if self._tashkeel is None:
            self._tashkeel = TashkeelDiacritizer()
        return self._tashkeel

    @staticmethod
    def _run_espeak_command(args: List[str], input_text: str = None, check: bool = True) -> str:
        """
        Helper function to run espeak-ng commands via subprocess.
        Executes 'espeak-ng' with the given arguments and input text.
        Captures stdout and stderr, and raises EspeakError on failure.

        Args:
            args (List[str]): A list of command-line arguments for espeak-ng.
            input_text (str, optional): The text to pass to espeak-ng's stdin. Defaults to None.
            check (bool, optional): If True, raises a CalledProcessError if the command returns a non-zero exit code. Defaults to True.

        Returns:
            str: The stripped standard output from the espeak-ng command.

        Raises:
            EspeakError: If espeak-ng command is not found, or if the subprocess call fails.
        """
        command: List[str] = ['espeak-ng'] + args

        # Standard arguments for subprocess.run
        subprocess_args = {
            'input': input_text,
            'capture_output': True,
            'text': True,
            'check': check,
            'encoding': 'utf-8',
            'errors': 'replace'  # Replaces unencodable characters with a placeholder
        }

        # Add 'creationflags' to hide the terminal window on Windows
        if os.name == 'nt':
            subprocess_args['creationflags'] = 0x08000000

        try:
            process: subprocess.CompletedProcess = subprocess.run(
                command,
                **subprocess_args  # Use the dynamic arguments
            )
            return process.stdout.strip()
        except FileNotFoundError:
            raise EspeakError(
                "espeak-ng command not found. Please ensure espeak-ng is installed "
                "and available in your system's PATH."
            )
        except subprocess.CalledProcessError as e:
            raise EspeakError(
                f"espeak-ng command failed with error code {e.returncode}:\n"
                f"STDOUT: {e.stdout}\n"
                f"STDERR: {e.stderr}"
            )
        except Exception as e:
            raise EspeakError(f"An unexpected error occurred while running espeak-ng: {e}")

    def phonemize_string(self, text: str, lang: str) -> str:
        lang = self.get_lang(lang)
        return self._run_espeak_command(
            ['-q', '-x', '--ipa', '-v', lang],
            input_text=text
        )

    def phonemize_to_list(self, text: str, lang: str = "ar") -> List[str]:
        return list(self.phonemize_string(text, lang))

    def add_diacritics(self, text: str, lang: str= "ar") -> str:
        if lang.startswith("ar"):
            return self.tashkeel.diacritize(text, self.taskeen_threshold)
        return text

    def phonemize(self, text: str, lang: str= "ar") -> PhonemizedChunks:
        if not text:
            return [('', '', True)]
        results: RawPhonemizedChunks = []
        text = normalize(text, lang)
        for chunk, punct, eos in self.chunk_text(text):
            phoneme_str = self.phonemize_string(self.remove_punctuation(chunk), lang)
            results += [(phoneme_str, punct, True)]
        return self._process_phones(results)

    @staticmethod
    def _process_phones(raw_phones: RawPhonemizedChunks) -> PhonemizedChunks:
        """Text to phonemes grouped by sentence."""
        all_phonemes: list[list[str]] = []
        sentence_phonemes: list[str] = []
        for phonemes_str, terminator_str, end_of_sentence in raw_phones:
            # Filter out (lang) switch (flags).
            # These surround words from languages other than the current voice.
            phonemes_str = re.sub(r"\([^)]+\)", "", phonemes_str)
            sentence_phonemes.extend(list(phonemes_str))
            if end_of_sentence:
                all_phonemes.append(sentence_phonemes)
                sentence_phonemes = []
        if sentence_phonemes:
            all_phonemes.append(sentence_phonemes)
        return all_phonemes

    @staticmethod
    def match_lang(target_lang: str, valid_langs: List[str]) -> str:
        """
        Validates and returns the closest supported language code.

        Args:
            target_lang (str): The language code to validate.

        Returns:
            str: The validated language code.

        Raises:
            ValueError: If the language code is unsupported.
        """
        lang, score = match_lang(target_lang, valid_langs)
        if score > 10:
            # raise an error for unsupported language
            raise ValueError(f"unsupported language code: {target_lang}")
        return lang

    @staticmethod
    def remove_punctuation(text):
        """
        Removes all punctuation characters from a string.
        Punctuation characters are defined by string.punctuation.
        """
        # Create a regex pattern that matches any character in string.punctuation
        punctuation_pattern = r"[" + re.escape(string.punctuation) + r"]"
        return re.sub(punctuation_pattern, '', text).strip()

    @staticmethod
    def chunk_text(text: str, delimiters: Optional[List[str]] = None) -> TextChunks:
        if not text:
            return [('', '', True)]

        results: TextChunks = []
        delimiters = delimiters or [":", ";", "...", "|"]

        # Create a regex pattern that matches any of the delimiters
        delimiter_pattern = re.escape(delimiters[0])
        for delimiter in delimiters[1:]:
            delimiter_pattern += f"|{re.escape(delimiter)}"

        for sentence in sentence_tokenize(text):
            # Default punctuation if no specific punctuation found
            default_punc = sentence[-1] if sentence and sentence[-1] in string.punctuation else "."

            # Use regex to split the sentence by any of the delimiters
            parts = re.split(f'({delimiter_pattern})', sentence)

            # Group parts into chunks (text + delimiter)
            chunks = []
            for i in range(0, len(parts), 2):
                # If there's a delimiter after the text, use it
                delimiter = parts[i + 1] if i + 1 < len(parts) else default_punc

                # Last chunk is marked as complete
                is_last = (i + 2 >= len(parts))

                chunks.append((parts[i].strip(), delimiter.strip(), is_last))

            results.extend(chunks)

        return results
