def decorator_1(func):
    def wrapper_top(*args, **kwargs):
        print("1111111111111")
        result = func(*args, **kwargs)
        return result
    return wrapper_top

def decorator_2(func):
    def wrapper_bottom(*args, **kwargs):
        print("222222222222.")
        result = func(*args, **kwargs)
        return result
    return wrapper_bottom


@decorator_1
@decorator_2
def say_hello():
    print("Hello")


print("\n=== PHASE 2: CALLING THE FUNCTION ===")
say_hello()