from collections import defaultdict
from loguru import logger
from nltk.corpus import brown, inaugural, wordnet

import requests
import string
import time


def get_word_mask(word: str):
    """
    A word mask is a number representing a subset
    of the lowercase ASCII character set.
    """
    mask = 0
    for c in set(word):
        if c not in string.ascii_lowercase:
            return None
        tmp = 1
        tmp <<= string.ascii_lowercase.index(c)
        mask |= tmp
    return mask


def get_syllables(word: str):
    """
    Decomposes a word down into a set of syllables that are part of the word.
    The syllables range from 2 to 4 characters.
    """
    for window in range(2, 5):
        if window > len(word):
            break
        for i in range(len(word) - window + 1):
            yield word[i : i + window]


AVAILABLE_MASK = ~get_word_mask("kwyz")


def get_word_ranking(word_mask: int, player_mask: int):
    """
    The word ranking system is at the heart of the bot.
    Given what the player's current bonus letters are, it will
    derive a relative ranking of the word, where a higher ranking indicates
    that the word is more desirable to be played.
    """
    def popcount(x):
        x -= (x >> 1) & 0x5555555555555555
        x = (x & 0x3333333333333333) + ((x >> 2) & 0x3333333333333333)
        x = (x + (x >> 4)) & 0x0F0F0F0F0F0F0F0F
        return ((x * 0x0101010101010101) & 0xFFFFFFFFFFFFFFFF) >> 56

    prev_count = popcount(player_mask & AVAILABLE_MASK)
    next_count = popcount((player_mask | word_mask) & AVAILABLE_MASK)
    return (next_count - prev_count, -popcount(word_mask & AVAILABLE_MASK))


class Corpus:
    """
    A corpus represents a list of acceptable words that Bomb Party takes.
    All of the words in a corpus are expected to belong to the same language.
    """
    def __init__(self):
        self.words = {}

    def add_words(self, words: [str]):
        for word in words:
            mask = get_word_mask(word)
            if mask is not None:
                self.words[word] = mask

    def add_words_from_url(self, url: str):
        txt = requests.get(url).text.lower()
        words = txt.split()
        self.add_words(words)


def english_corpus():
    """
    The standard corpus for the English language.
    """
    logger.info("Loading new English corpus ...")
    timestamp = time.time()
    corpus = Corpus()
    # Known corporal additions
    corpus.add_words_from_url("http://norvig.com/ngrams/sowpods.txt")
    logger.info("English corpus is now at {} words.", len(corpus.words))
    corpus.add_words_from_url("http://norvig.com/ngrams/enable1.txt")
    logger.info("English corpus is now at {} words.", len(corpus.words))
    corpus.add_words_from_url("https://pastebin.com/raw/UegdKLq8")
    logger.info("English corpus is now at {} words.", len(corpus.words))
    logger.info(
        "Took {:.2f} seconds to load full English corpus.".format(
            time.time() - timestamp
        )
    )
    return corpus


class Searcher:
    """
    A searcher is spawned for the duration of a Bomb Party game round and
    provides an interface through which words can be looked up by syllable.
    The searcher also keeps track of the current player's bonus points and
    also which words were used in the past.
    """

    def __init__(self, corpus: Corpus):
        self.syllables = defaultdict(dict)
        for word, mask in corpus.words.items():
            for syllable in get_syllables(word):
                self.syllables[syllable][word] = mask
        self.bonus_mask = 0
        self.last_mask = 0

    def search(self, syllable: str):
        if syllable not in self.syllables:
            return None
        word_map = self.syllables[syllable]
        words = list(word_map.items())
        (best_word, _) = max(
            words, key=lambda x: get_word_ranking(x[1], self.bonus_mask)
        )
        return best_word

    def confirm_bonus(self):
        self.bonus_mask = 0

    def confirm_correct(self, word):
        self.bonus_mask |= get_word_mask(word)
        self.confirm_used(word)

    def confirm_used(self, word: str):
        for syllable in get_syllables(word):
            if syllable in self.syllables:
                words = self.syllables[syllable]
                if word in words:
                    del words[word]
