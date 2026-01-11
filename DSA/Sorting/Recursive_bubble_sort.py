# 1 recursive bubble sort

# Decreasing n by 1 method.

def sort_func(arr,n,i,j):
  if j>n-i-1:
    return
  
  if arr[j-1] > arr[j]:
      arr[j-1],arr[j] = arr[j],arr[j-1]
  
  return sort_func(arr,n,i,j+1)
  

def bubble_sort(arr,n,i):
  if i==n:
    return arr
  
  sort_func(arr,n,i,1)
  return bubble_sort(arr,n-1,i)
  
  
ans = bubble_sort([18,22,2,21,5,15,16],7,0)

print(ans)