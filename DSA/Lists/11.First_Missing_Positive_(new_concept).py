# Time Complexity: O(n)
# Space Complexity: O(1)
class Solution:
    def firstMissingPositive(self, nums: List[int]) -> int:
        for i in range(0,len(nums)):
            while 1 <= nums[i] <= len(nums)-1 and nums[i] != nums[nums[i] - 1]:
                correct_idx = nums[i] - 1
                nums[i],nums[correct_idx] = nums[correct_idx],nums[i]
        
        for i in range(0,len(nums)):
            if nums[i] != i+1:
                return i+1

        return len(nums)+1