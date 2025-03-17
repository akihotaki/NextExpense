from itertools import count

arr = [90, 64, 34, 25, 22, 12, 11]


def bubble_sort(arr):
    count = 0
    n = len(arr)
    for i in range(n-1):
        for j in range(n-i-1):
            count += 1
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return print(count)


bubble_sort(arr)