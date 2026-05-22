import unittest

from src.text_utils import normalize_whitespace


class TestTextUtils(unittest.TestCase):
    def test_strips_outer_whitespace(self) -> None:
        self.assertEqual(normalize_whitespace("  hello  "), "hello")

    def test_keeps_single_spaces(self) -> None:
        self.assertEqual(normalize_whitespace("hello world"), "hello world")


if __name__ == "__main__":
    unittest.main()
