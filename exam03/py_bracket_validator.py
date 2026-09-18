def bracket_validator(s: str) -> bool:

    valide = {"}":"{", "]":"[",")":"("}
    stack = []

    for i in s:
        if i in valide.values():
            stack.append(i)

        elif i in valide:
            if not stack or stack.pop() != valide[i]:
                return False

    return len(stack) == 0




# Test cases
print(bracket_validator("hello(world)"))  # True
print(bracket_validator("{[(])}"))  # False
print(bracket_validator("((("))  # False