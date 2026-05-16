from functools import wraps
def decorator_1(func):
    function = func
    def wrapper_top(*args, **kwargs):
        result = function(*args, **kwargs)
        print("1111111111111")
        return result
    return wrapper_top

def decorator_2(func):
    def wrapper_bottom(*args, **kwargs):
        result = func(*args, **kwargs)
        print("222222222222.")
        return result
    return wrapper_bottom


# @decorator_1
# @decorator_2
def say_hello():
    print("Hello")

# # dec1 = decorator_2(say_hello)
# # dec2 = decorator_1(dec1)
# # # dec2()
# decorator_1(decorator_2(say_hello))()
# # print(dec2())
# say_hello()
# decorator_1(say_hello)
say_hello  =  decorator_2(decorator_1(say_hello)) 
# say_hello = decorator_1(say_hello)
# say_hello = decorator_2(say_hello)
# say_hello()
print(say_hello.__name__)