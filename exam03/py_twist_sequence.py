def twist_sequence(arr: list[int], k: int) -> list[int]:
    # 1. Edge case: if the array is empty, return it immediately
    if not arr:
        return []
        
    # 2. Simplify k in case it is larger than the length of the array
    # This also prevents errors if k is huge!
    k = k % len(arr)
    
    # 3. If k becomes 0, there is no rotation needed
    if k == 0:
        return arr
        
    # 4. Use slicing to cut the list in two pieces and swap them
    # arr[-k:] grabs the last k elements
    # arr[:-k] grabs everything else from the start
    return arr[-k:] + arr[:-k]

# --- Test cases ---
print(twist_sequence([1,2,3,4,5], 2))  # [4, 5, 1, 2, 3]
print(twist_sequence([1,2,3], 1))      # [3, 1, 2]
print(twist_sequence([1,2,3,4], 0))    # [1, 2, 3, 4]
print(twist_sequence([1,2,3], 5))      # [2, 3, 1]
print(twist_sequence([], 3))           # []