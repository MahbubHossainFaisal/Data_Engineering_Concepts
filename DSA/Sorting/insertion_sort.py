## Insertion sort 

def Insertion_sort(arr):
  for i in range(1,len(arr)):
    j=i
    while (j>0 and arr[j]<=arr[j-1]):
        arr[j],arr[j-1]=arr[j-1],arr[j]
        j=j-1
      
  
  return arr;
  
  
ans = Insertion_sort([21,12,14,15,20,2,1])

print(ans)