from collections import defaultdict

import requests
import util


class WordBank:
    def __init__(self, lang: str):
        self.lang = lang
        self.prefixes = defaultdict(list)

    def add_words(self, words: [str]):
        for word in words:
            mask = util.get_word_mask(word)
            assert(mask is not None)
            for prefix in util.get_prefixes(word):
                self.prefixes[prefix].append((word, mask))

    def add_words_from_link(self, url: str):
        txt = requests.get(url).text.lower()
        words = txt.split()
        self.add_words(words)


def english_word_bank():
    bank = WordBank("en")
    bank.add_words_from_link("http://norvig.com/ngrams/sowpods.txt")
    bank.add_words_from_link("http://norvig.com/ngrams/enable1.txt")
    bank.add_words_from_link("https://pastebin.com/raw/UegdKLq8")
    return bank
