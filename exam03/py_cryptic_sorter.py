def cryptic_sorter(strings: list[str]) -> list[str]:

    def count_vowels(s: str) -> int:
        return sum(1 for c in s if c in "aeiouAEIOU")
    
    n = len(strings)

    for _ in range(n):
        j = 0
        while j < n - 1:
            
            if len(strings[j]) > len(strings[j + 1]):
                arr = strings[j]
                strings[j] = strings[j + 1]
                strings[j + 1] = arr
            elif len(strings[j]) == len(strings[j + 1]):
                if strings[j].lower() > strings[j + 1].lower():
                    arr = strings[j]
                    strings[j] = strings[j + 1]
                    strings[j + 1] = arr
                elif strings[j].lower() == strings[j + 1].lower():
                    if count_vowels(strings[j]) > count_vowels(strings[j + 1]):
                            arr = strings[j]
                            strings[j] = strings[j + 1]
                            strings[j + 1] = arr

            j += 1
    return strings

print(cryptic_sorter(["apple","cat","banana","dog","elephant"]))
#["cat","dog","apple","banana","elephant"]
print(cryptic_sorter(["aaa","bbb","AAA","BBB"]))
#["aaa", "AAA", "bbb", "BBB"]
print(cryptic_sorter(["hello","world","hi","test"]))
#["hi","test","hello","world"]
print(cryptic_sorter(["cat", "dog", "gym", "ooo"]))

print(cryptic_sorter([""]))
#[""]
