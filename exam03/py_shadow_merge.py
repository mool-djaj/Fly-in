def shadow_merge(list1: list[int], list2: list[int]) -> list[int]:

    def sorti(lst: list[int]):
        for _ in lst:
            for i in range(len(lst) - 1):
                if lst[i] > lst[i + 1]:
                    tmp = lst[i]
                    lst[i] = lst[i + 1]
                    lst[i + 1] = tmp  # Added "= tmp" here
        return lst

    return sorti(list1 + list2)

# Test cases
print(shadow_merge([1, 3, 5], [2, 4, 6]))
# Output: [1, 2, 3, 4, 5, 6]