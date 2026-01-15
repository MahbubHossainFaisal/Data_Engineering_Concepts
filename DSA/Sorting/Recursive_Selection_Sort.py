
def find_min(arr,n,j,min_index):
  if j>=n:
    return min_index
  if arr[j] < arr[min_index]:
    min_index=j 
  
  return find_min(arr,n,j+1,min_index)


def selection_sort(arr,n,i):
  if n==i:
    return arr
    
  min_index = i
  output = find_min(arr,n,i,min_index) 
  
  arr[i],arr[output] = arr[output],arr[i]
  
  return selection_sort(arr,n,i+1)
  
  
ans = selection_sort([1,5,4,3,2],5,0)
print(ans)
  