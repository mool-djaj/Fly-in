def inter(s1: str, s2: str) -> str:

    res = ""
    seen = ""

    for x in s1:
        if x in s2 and x not in seen:
            res += x
            seen += x

    return res

print(inter("banana", "band"))