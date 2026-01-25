# Time Complexity: O(n)
# Space Complexity: O(n)

class Solution:
    def containsNearbyDuplicate(self, nums: List[int], k: int) -> bool:
        seen = {}
        seen[nums[0]]=0

        for i in range(1,len(nums)):
            if nums[i] in seen:
                if abs(i-seen[nums[i]])<=k:
                    return True
            
            seen[nums[i]]=i
            #print(seen)
        
        return False
    
# Another solution which makes space complexity O(k)

class Solution:
    def containsNearbyDuplicate(self, nums: List[int], k: int) -> bool:
        seen = set()

        for i in range(len(nums)):
            if i>k:
                seen.remove(nums[i-k-1])
            if nums[i] in seen:
                return True
            seen.add(nums[i])
        return False