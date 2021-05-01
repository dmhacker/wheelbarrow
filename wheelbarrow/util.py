import string


def get_word_mask(word: str):
    mask = 0
    for c in set(word):
        if c not in string.ascii_lowercase:
            return None
        tmp = 1
        tmp <<= string.ascii_lowercase.index(c)
        mask |= tmp
    return mask


def get_prefixes(word: str):
    for p in range(2, 5):
        if p > len(word):
            break
        for i in range(len(word) - p + 1):
            yield word[i: i + p]


def get_word_ranking(word_mask: int, player_mask: int):
    '''
    The word ranking system is at the heart of the bot.
    Given what the player's current bonus letters are, it will
    derive a relative ranking of the word, where a higher ranking indicates
    that the word is more desirable to be played.
    '''
    def popcount(x):
        x -= (x >> 1) & 0x5555555555555555
        x = (x & 0x3333333333333333) + ((x >> 2) & 0x3333333333333333)
        x = (x + (x >> 4)) & 0x0f0f0f0f0f0f0f0f
        return ((x * 0x0101010101010101) & 0xffffffffffffffff) >> 56
    prev_count = popcount(player_mask & AVAILABLE_MASK)
    next_count = popcount((player_mask | word_mask) & AVAILABLE_MASK)
    return (next_count - prev_count, -popcount(word_mask & AVAILABLE_MASK))


AVAILABLE_MASK = ~get_word_mask("kwyz")
