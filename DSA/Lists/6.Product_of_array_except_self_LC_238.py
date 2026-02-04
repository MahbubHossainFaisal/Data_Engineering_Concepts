# Time Complexity: O(n)
# Space Complexity: O(n)

class Solution:
    def productExceptSelf(self, nums: List[int]) -> List[int]:
        prefix=[0]*len(nums)
        prefix[0]=-99999
        for i in range(1,len(nums)):
            if i==1:
                prefix[i]=nums[i-1]
                continue
            prefix[i] = prefix[i-1]*nums[i-1]
            
        #print(prefix)
        
        postfix=[0]*len(nums)
        postfix[len(nums)-1]=-99999
        

        for i in range(len(nums)-2,-1,-1):
            if i==len(nums)-2:
                postfix[i]=nums[i+1]
                continue
            postfix[i]=postfix[i+1]*nums[i+1]
            
        #print(postfix)

        result =[]
        for i in range(len(nums)):
            if prefix[i] == -99999:
                result.append(postfix[i])
            elif postfix[i] == -99999:
                result.append(prefix[i])
            else:
                result.append(prefix[i]*postfix[i])

        return result
                
# Better Solution
class Solution:
    def productExceptSelf(self, nums: List[int]) -> List[int]:
        prefix=[0]*len(nums)
        prefix[0]=1
        for i in range(1,len(nums)):
            if i==1:
                prefix[i]=nums[i-1]
                continue
            prefix[i] = prefix[i-1]*nums[i-1]
            
        #print(prefix)
        
       
        
        temp_val = 1
        for i in range(len(nums)-2,-1,-1):
            temp_val = temp_val*nums[i+1]
            if i==1:
              prefix[i]=temp_val
              continue
            prefix[i] = prefix[i]*temp_val
            
            
        #print(postfix)

        return prefix
                
# Currently failed in 16th test case