# Solution O(n2)) time complexity and O(1) space complexity
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        for i in range(len(nums)):
            for j in range(i+1,len(nums)):
                if nums[i] + nums[j] == target:
                    return [i,j]
        
        return []
    

# Solution O(n) time complexity and O(n) space complexity

class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        seen[nums[0]]=0
        
        for i in range(1,len(nums)):
            ele = target-nums[i]
            if ele in seen:
                return [seen[ele],i]
            else:
                seen[nums[i]]=i
        return []