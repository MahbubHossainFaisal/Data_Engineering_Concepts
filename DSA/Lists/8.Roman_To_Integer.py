#Time Complexity: O(n)
#Space Complexity: O(k) since the size of the hash map is constant (7 key-value pairs for the Roman numerals)
class Solution:
    def romanToInt(self, s: str) -> int:
        roman_to_int = {
        "I": 1,
        "V": 5,
        "X": 10,
        "L": 50,
        "C": 100,
        "D": 500,
        "M": 1000}
        sum_num=0
        for i in range(0,len(s)-1):
            print(i)
            if s[i]=='I' and s[i+1]=='V' or s[i]=='I' and s[i+1]=='X':
                sum_num-=roman_to_int[s[i]]
            elif s[i]=='X' and s[i+1]=='L' or s[i]=='X' and s[i+1]=='C':
                sum_num-=roman_to_int[s[i]]
            elif s[i]=='C' and s[i+1]=='D' or s[i]=='C' and s[i+1]=='M':
                sum_num-=roman_to_int[s[i]]
            else:
                sum_num+=roman_to_int[s[i]]
        
        sum_num+=roman_to_int[s[len(s)-1]]
        return sum_num
        
        return sum_num