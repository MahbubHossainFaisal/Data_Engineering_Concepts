# Solution 1
# Time Complexity: O(n · k log k)
# Space Complexity: O(n · k)

class Solution:
    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
        temp_st=[]
        for i in strs:
            temp_st.append(''.join(sorted(i)))
  
        library = {}
  
        for i in range(len(temp_st)):
            if temp_st[i] not in library:
                library[temp_st[i]]= []
            library[temp_st[i]].append(i)
    
        main_list=[]
        for key,val in library.items():
            temp_list=[]
            for i in range(0,len(val)):
                temp_list.append(strs[val[i]])
            main_list.append(temp_list)

        return main_list