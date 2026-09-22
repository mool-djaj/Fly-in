def anagram(s1: str, s2: str) -> bool:
    def count_letters(text: str) -> dict:
        counts = {}
        for char in text:
            if char != " ":            # 1. Ignore spaces
                c = char.lower()       # 2. Ignore case
                if c in counts:
                    counts[c] += 1     # Increase count if we've seen it
                else:
                    counts[c] = 1      # Start at 1 if it's a new letter
        return counts

    return count_letters(s1) == count_letters(s2)


# --- Test Cases ---
print(anagram("listen", "silent"))         # True
print(anagram("Triangle", "Integral"))     # True
print(anagram("Dormitory", "Dirty Room"))  # True
print(anagram("hello", "world"))           # False
print(anagram("", ""))                     # True
print(anagram("abc", "abcc"))              # False
print(anagram("aab", "abb"))               # False (Your original code failed this one)