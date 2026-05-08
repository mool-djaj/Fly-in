import sys

sys.setrecursionlimit(20000000)

def fc():
    for i in range(99999999999):
        fc()
   
fc()
