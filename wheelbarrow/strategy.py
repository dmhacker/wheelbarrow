from collections import defaultdict
from loguru import logger
from selenium.webdriver.common.keys import Keys

import requests
import string
import time
import numpy as np
import random


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


def get_word_ranking(word: str, word_mask: int, word_freq: int, player_mask: int, human: bool, lives: int, max_lives: int):
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

    word_count = popcount(word_mask & AVAILABLE_MASK)
    prev_count = popcount(player_mask & AVAILABLE_MASK)
    next_count = popcount((player_mask | word_mask) & AVAILABLE_MASK)
    if human:
        freq_level = 0
        if word_freq > 400:
            freq_level = 2
        elif word_freq > 0:
            freq_level = 1
        if lives < max_lives:
            return (freq_level, next_count - prev_count, -word_count)
        else:
            return (freq_level, -len(word), -word_count)
    else:
        if lives < max_lives:
            return (next_count - prev_count, -word_count)
        else:
            return (-word_count)


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
                self.words[word] = (mask, 0)

    def add_words_from_url(self, url: str):
        txt = requests.get(url).text.lower()
        words = txt.split()
        self.add_words(words)

    def add_frequencies_from_url(self, url: str):
        txt = requests.get(url).text.lower()
        lines = txt.splitlines()
        parsing = False
        for line in lines:
            data = line.split()
            if parsing:
                if len(data) >= 3:
                    word = data[1]
                    freq = int(data[2])
                    if word in self.words:
                        (mask, _) = self.words[word]
                        self.words[word] = (mask, freq)
            else:
                if len(data) > 0 and data[0] == "rank":
                    parsing = True


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
    corpus.add_frequencies_from_url("https://www.wordfrequency.info/samples/words_219k.txt")
    logger.info("Added frequencies to corpus.", len(corpus.words))
    logger.info(
        "Took {:.2f} seconds to load full English corpus.".format(
            time.time() - timestamp
        )
    )
    return corpus


class Typist:
    """
    Controls how a word is typed out. The typist interface provides
    support for mimicing human behaviour, so that the bot doesn't appear
    overpowered.
    """

    def __init__(self):
        self.word_accuracy = 0.8
        self.keystroke_accuracy = 0.92
        self.keystroke_delay_avg = 0.11
        self.keystroke_delay_std = 0.04
        self.initial_delay_avg = 0.9
        self.initial_delay_std = 0.2
        self.backtrack_delay_avg = 0.5
        self.backtrack_delay_std = 0.3
        self.error_count_lambda = 0.85

    def __keystroke_delay(self, word_size, previous_errors):
        return max(
            0,
            np.random.normal(
                self.keystroke_delay_avg - word_size * 0.001 - previous_errors * 0.01,
                self.keystroke_delay_std,
                1,
            )[0],
        )

    def __initial_delay(self, word_size):
        return max(
            0,
            np.random.normal(
                self.initial_delay_avg - word_size * 0.02, self.initial_delay_std, 1
            )[0],
        )

    def __backtrack_delay(self):
        return max(
            0,
            np.random.normal(self.backtrack_delay_avg, self.backtrack_delay_std, 1)[0],
        )

    def __error_count(self):
        return max(
            0, int(np.round(np.random.exponential(self.error_count_lambda, 1)[0]))
        )

    def act(self, word: str, syllable: str, human: bool, lives: int, max_lives: int):
        if not human:
            return [("press", word + Keys.RETURN)]
        actions = []
        actions.append(("wait", self.__initial_delay(len(word))))
        previous_errors = 0
        fail_probability = (1.0 + (self.word_accuracy - 1) / (max_lives - 1) * (lives - 1))
        fail_destiny = random.random() > fail_probability
        fail_index = word.index(syllable) + len(syllable)
        fail_index += random.randrange(0, len(word) - fail_index + 1)
        for i, c in enumerate(word):
            if fail_destiny and fail_index == i:
                break
            remaining = len(word) - i
            if random.random() > self.keystroke_accuracy:
                mistakes = int(np.ceil(self.__error_count()))
                for j in range(mistakes):
                    mc = random.choice(string.ascii_lowercase)
                    if j > 0 and i + j < len(word) and random.random() < 0.7:
                        mc = word[i + j]
                    actions.append(("wait", self.__keystroke_delay(remaining, previous_errors)))
                    actions.append(("press", mc))
                actions.append(("wait", self.__backtrack_delay()))
                for _ in range(mistakes):
                    actions.append(("wait", self.__keystroke_delay(remaining, previous_errors)))
                    actions.append(("press", Keys.BACKSPACE))
                previous_errors += 1
            actions.append(("wait", self.__keystroke_delay(remaining, previous_errors)))
            actions.append(("press", c))
        actions.append(("press", Keys.RETURN))
        return actions


class Bot:
    """
    A bot is spawned for the duration of a Bomb Party game round and
    provides an interface through which words can be looked up by syllable.
    The bot also keeps track of its bonus points and also which words
    were used in the past.
    """

    def __init__(self, corpus: Corpus, human: bool):
        self.bonus_mask = 0
        self.last_mask = 0
        self.human = human
        self.typist = Typist()
        self.syllables = defaultdict(dict)
        self.lives = 0
        self.max_lives = 0
        for word, data in corpus.words.items():
            if len(word) > 12 and human:
                continue
            for syllable in get_syllables(word):
                self.syllables[syllable][word] = data

    def search_syllable(self, syllable: str):
        if syllable not in self.syllables:
            return None
        word_map = self.syllables[syllable]
        words = list(word_map.items())
        (best_word, _) = max(
            words, key=lambda x: get_word_ranking(x[0], x[1][0], x[1][1], self.bonus_mask, self.human, self.lives, self.max_lives)
        )
        return best_word

    def on_search_syllable(self, syllable: str):
        word = self.search_syllable(syllable)
        if word is None:
            return []
        return self.typist.act(word, syllable, self.human, self.lives, self.max_lives)

    def on_start(self, lives, max_lives):
        self.lives = lives
        self.max_lives = max_lives

    def on_bonus_life(self):
        self.bonus_mask = 0
        self.lives += 1

    def on_lost_life(self):
        self.lives -= 1

    def on_correct_word(self, word):
        self.bonus_mask |= get_word_mask(word)
        self.on_use_word(word)

    def on_use_word(self, word: str):
        for syllable in get_syllables(word):
            if syllable in self.syllables:
                words = self.syllables[syllable]
                if word in words:
                    del words[word]
