def string_permutation_checker(s1: str, s2: str) -> bool:
    if len(s1) != len(s2):
        return False
    def get_counts(text: str) -> dict:
        counts = {}
        for char in text:
            if char in counts:
                counts[char] += 1
            else:
                counts[char] = 1
        return counts

    return get_counts(s1) == get_counts(s2)

# --- Test cases ---
print(string_permutation_checker("abc", "bca"))              # True
print(string_permutation_checker("abc", "def"))              # False
print(string_permutation_checker("listen", "silent"))        # True
print(string_permutation_checker("hello", "bello"))          # False
print(string_permutation_checker("", ""))                    # True
print(string_permutation_checker("a", ""))                   # False
print(string_permutation_checker("Abc", "abc"))              # False
print(string_permutation_checker("a gentleman", "elegant man")) # True