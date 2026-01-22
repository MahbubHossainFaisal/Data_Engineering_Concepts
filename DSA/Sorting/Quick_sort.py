def partition(arr,low,high):
  pivot = arr[low]
  p=low
  
  for i in range(low+1,high+1):
    if arr[i]<pivot:
      p+=1 
      arr[p],arr[i] = arr[i],arr[p]
      
  arr[low],arr[p] = arr[p],arr[low]
  
  return p


def quicksort(arr,low,high):
  if low<high:
    pivot_index = partition(arr,low,high)
    quicksort(arr,low,pivot_index-1)
    quicksort(arr,pivot_index+1,high)
  
  
arr = [15,21,11,8,10]

quicksort(arr,0,4)

print(arr)