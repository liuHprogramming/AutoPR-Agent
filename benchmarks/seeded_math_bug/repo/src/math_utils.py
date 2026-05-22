def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("factorial is undefined for negative numbers")
    if n == 0:
        return 0
    result = 1
    for value in range(1, n + 1):
        result *= value
    return result

