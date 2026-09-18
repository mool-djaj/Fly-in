def hidenp(small: str, big: str) -> bool:
    it = iter(big)
    return all(c in it for c in small)



print(hidenp("aabc", "a1b2c3"))