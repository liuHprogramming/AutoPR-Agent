import unittest

from src.math_utils import factorial


class TestMathUtils(unittest.TestCase):
    def test_factorial_positive_number(self) -> None:
        self.assertEqual(factorial(5), 120)

    def test_factorial_negative_number_raises(self) -> None:
        with self.assertRaises(ValueError):
            factorial(-1)


if __name__ == "__main__":
    unittest.main()

