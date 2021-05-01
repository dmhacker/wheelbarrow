import bank
import util


class WordSearch:
    def __init__(self, wb: bank.WordBank):
        self.lang = wb.lang
        self.prefixes = {}
        for prefix, words in wb.prefixes.items():
            self.prefixes[prefix] = {word: mask for (word, mask) in words}

    def search(self, prefix: str, player_mask: int):
        if prefix not in self.prefixes:
            return None
        word_map = self.prefixes[prefix]
        words = list(word_map.items())
        (best_word, best_mask) = max(words, key=lambda x: util.get_word_ranking(x[1], player_mask))
        return (best_word, player_mask | best_mask)

    def use(self, word: str):
        for prefix in util.get_prefixes(word):
            words = self.prefixes[prefix]
            if word in words:
                del words[word]
