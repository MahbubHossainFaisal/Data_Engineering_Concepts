# Leetcode 121
# Time Complexity: O(n^2)
# Space Complexity: O(1)
class Solution:
    def maxProfit(self, prices: List[int]) -> int:
        max_profit = 0
        
        
        for i in range(len(prices)):
            
            for j in range(i + 1, len(prices)):
                
                current_profit = prices[j] - prices[i]
            
                if current_profit > max_profit:
                    max_profit = current_profit
                    
        return max_profit
    


# Optimized Solution
# Time Complexity: O(n) 
# Space Complexity: O(1)

class Solution:
    def maxProfit(self, prices: List[int]) -> int:
        buy = prices[0]
        profit = 0

        for i in range(1, len(prices)):
            if prices[i] < buy:
                buy = prices[i]
            if prices[i] - buy > profit:
                profit = prices[i] - buy
        
        return profit