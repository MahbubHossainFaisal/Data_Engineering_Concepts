def factorial(n):
    """Calculate the factorial of a number."""
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)

if __name__ == "__main__":
    # This code will only run when the script is executed directly
    print("Running math_utils.py directly")
    print("5! =", factorial(5))  # Example test
    print("7! =", factorial(7))  # Another test