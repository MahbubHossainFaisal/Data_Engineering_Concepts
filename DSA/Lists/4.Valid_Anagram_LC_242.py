# Solution 1 using sorting
# Time Complexity: O(n log n)
# However, O(n) + O(n) + O(n) = O(3n) = O(n)
class Solution:
    def isAnagram(self, s: str, t: str) -> bool:
       sorted_s = ''.join(sorted(s))
       sorted_t = ''.join(sorted(t))
       return sorted_s==sorted_t
    

# Solutio 2 using dictionary
# Time Complexity: O(n)
# Space Complexity: O(1) - Since the size of the hash map will be at most 26 for lowercase letters
class Solution:
    def isAnagram(self, s: str, t: str) -> bool:
        if len(s) != len(t):
            return False
        library = {}

        for i in range(len(s)):
            library[s[i]] = library.get(s[i],0)+1

        for i in range(len(t)):
            if t[i] in library:
                library[t[i]]-=1
            else:
                return False
        for key,value in library.items():
            if value!=0:
                return False
            
        return True
    

# Solution 3 using list
# Time Complexity: O(n) 
# Space Complexity: O(1) - Since the size of the list will be at most 26 for lowercase letters
class Solution:
    def isAnagram(self, s: str, t: str) -> bool:
        if len(s) != len(t):
            return False
        library = [0] * 26 

        for i in range(len(s)):
            library[ord(s[i])-ord('a')] +=1
            library[ord(t[i])-ord('a')] -=1

        for i in library:
            if i!=0:
                return False
        return True 