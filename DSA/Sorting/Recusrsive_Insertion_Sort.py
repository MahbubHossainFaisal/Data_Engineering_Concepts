# Recursive Insertion sort

def compare(arr,n,j):
  if j==0:
    return 
  
  if arr[j]<arr[j-1]:
    arr[j],arr[j-1] = arr[j-1],arr[j]
    
  return compare(arr,n,j-1)

def insertion_sort(arr, n, i):
  if n==i:
    return arr 
  

  compare(arr,n,i)
  
  return insertion_sort(arr,n,i+1)



ans = insertion_sort([2,1,4,3,2,1],6,0)

print(ans)