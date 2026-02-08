# Time Complexity: O(n log n) where n is the number of elements in the input list. This is because we need to sort the frequency of the elements.
# Space Complexity: O(n) where n is the number of unique elements in the input list


class Solution:
    def topKFrequent(self, nums: List[int], k: int) -> List[int]:
        library = {
        }

        for i in range(0,len(nums)):
            if nums[i] not in library:
                library[nums[i]]=0
            library[nums[i]]+=1
        
        sorted_library = dict(sorted(library.items(), key=lambda item: item[1], reverse=True))
        ans = []
        count = 1
        for key,pair in sorted_library.items():
            ans.append(key)
            count+=1
            if count>k:
                break
        return ans