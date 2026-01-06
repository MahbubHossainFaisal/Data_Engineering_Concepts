def bubble_sort(arr):
  n=len(arr)
  for i in range(n):
      for j in range(n-i-1):
        if arr[j+1]<arr[j]:
          arr[j+1],arr[j] = arr[j],arr[j+1]
          
  return arr 
    

ans =bubble_sort([44,212,32,1,45,24,66,11,12])

print(ans)


# More optimized bubble sort
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False  # Track if any swaps occurred
        for j in range(n-i-1):
            if arr[j+1] < arr[j]:
                arr[j+1], arr[j] = arr[j], arr[j+1]
                swapped = True
        
        # If no swaps were made, array is sorted
        if not swapped:
            break
    
    return arr

ans = bubble_sort([44, 212, 32, 1, 45, 24, 66, 11, 12])
print(ans)