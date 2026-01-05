def selection_sort(arr):
  for i in range(len(arr)):
    min_index = i
    for j in range(i+1,len(arr)):
      if arr[j] < arr[min_index]:
        min_index=j

    temp = arr[i]
    arr[i] = arr[min_index]
    arr[min_index] = temp
    
  return arr
  

ans = selection_sort([14,4,25,3,1,5])

print(ans)