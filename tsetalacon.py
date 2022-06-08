ls = [['a', 'b'], ['c', 'd']]

if any(isinstance(i, list) for i in ls):
    print('nest detected')
    res = [item for sublist in ls for item in sublist]
    print(res)