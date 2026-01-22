def merge(arr,low,mid,high):
  left = low
  right = mid+1
  temp=[]
  while(left<=mid and right<=high):
    if arr[left]<arr[right]:
      temp.append(arr[left])
      left+=1
    else:
      temp.append(arr[right])
      right+=1
      
  while(left<=mid):
    temp.append(arr[left])
    left+=1
  
  while(right<=high):
    temp.append(arr[right])
    right+=1 
  
  j=0 
  
  for i in range(low,high+1):
    arr[i] = temp[j]
    j+=1 
    

    

def mergesort(arr,low,high):
  if low>=high:
    return 
  
  mid = (low+high)//2 
  
  mergesort(arr,low,mid)
  mergesort(arr,mid+1,high)
  
  merge(arr,low,mid,high)
  


arr= [21,15,1,1,24,2,2,33,44,11]

mergesort(arr,0,9)

print(arr)