# Time Complexity: O(n*m)
# Space Complexity: O(1)
# Optimized Solution
# We use a library to store the order of the characters in the alien dictionary
# We then compare the words in the alien dictionary to the order of the characters in the alien dictionary
# If the words are not in the order of the characters in the alien dictionary, we return False
# If the words are in the order of the characters in the alien dictionary, we return True
# We use a for loop to iterate through the words and the characters in the words
# We use a nested for loop to iterate through the characters in the words
# We use a conditional statement to check if the characters are in the order of the characters in the alien dictionary
# If the characters are not in the order of the characters in the alien dictionary, we return False
class Solution:
    def isAlienSorted(self, words: List[str], order: str) -> bool:
        library = {}
        count=1
        for i in range(0,len(order)):
            if order[i] not in library:
                library[order[i]]=count
                count+=1
        #print(library)

        for i in range(0,len(words)-1):
            x=words[i]
            y=words[i+1]

            for j in range(0,len(x)):
                if j!=len(x) and j==len(y) :
                    return False
                elif library[x[j]]>library[y[j]]:
                    return False
                elif library[x[j]]==library[y[j]]:
                    continue
                elif library[x[j]]<library[y[j]]:
                    break
            
        return True
