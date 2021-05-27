a = None
print(a)

def test():
    global a

    a = 4
test()
print(a)