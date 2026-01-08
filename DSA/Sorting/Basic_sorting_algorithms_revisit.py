# Bubble sort

def bubble_sort(arr):
  for i in range(len(arr)):
    for j in range(len(arr)-i-1):
      if arr[j+1]<arr[j]:
        arr[j],arr[j+1] = arr[j+1],arr[j]
    
  return arr
  
  
arr = [41,21,27,21,9,19,1]

ans = bubble_sort(arr)

print(arr)



# Insertion sort 

def insertion_sort(arr):
  for i in range(len(arr)):
    j=i
    while j>0 and arr[j]<arr[j-1]:
      arr[j],arr[j-1] = arr[j-1],arr[j]
      j-=1 
  
  return arr
  

ans2 = insertion_sort(arr)
print(ans)


# Selection sort 

def Selection_sort(arr):
  for i in range(len(arr)):
    min_index=i #Start by assuming current index is the minimum!
    for j in range(i+1,len(arr)):
      if arr[j] < arr[min_index]:
        min_index = j
    arr[i],arr[min_index] = arr[min_index],arr[i]
    
  return arr 
  
  
ans3 = Selection_sort(arr)

print(ans3)
  
  
        