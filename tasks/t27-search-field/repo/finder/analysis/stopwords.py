"""Words that carry no meaning in prose and are dropped from long text."""

ENGLISH = frozenset(
    """a an and are as at be but by for from has have in is it its of on or that the their then there
    these this to was were will with""".split()
)


def is_stop(word):
    return word in ENGLISH


def remove(words):
    return [w for w in words if w not in ENGLISH]
