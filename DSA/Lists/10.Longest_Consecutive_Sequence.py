# TLE


class Solution:
    def longestConsecutive(self, nums: List[int]) -> int:
        
        max_count=0
        count=0
        
        min_ele = min(nums) if nums else 0
        max_ele = max(nums) if nums else 0
        
        library={}
        
        for i in range(0,len(nums)):
            library[nums[i]]=1 
            
        for i in range(min_ele,max_ele+1):
            if i in library.keys():
                count+=1 
                if max_count<count:
                    max_count=count 
            else:
                count=0
            
        return max_count
    
# Efficient Solution
# Time complexity: O(n)
# Space complexity: O(n)
class Solution:
    def longestConsecutive(self, nums: List[int]) -> int:
        
        elements = set(nums)
        cnt=1
        max_count=0
        for i in elements:
            if i-1 not in elements: # means we have found a starting point
                count = 1
                while(i+1 in elements):
                    i+=1
                    count+=1
                if count>max_count:
                    max_count=count
        return max_count
        