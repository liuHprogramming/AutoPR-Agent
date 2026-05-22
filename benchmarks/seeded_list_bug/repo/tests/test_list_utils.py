import unittest

from src.list_utils import unique_preserve_order


class TestListUtils(unittest.TestCase):
    def test_removes_duplicates(self) -> None:
        self.assertEqual(unique_preserve_order(["a", "a", "b"]), ["a", "b"])

    def test_handles_empty_list(self) -> None:
        self.assertEqual(unique_preserve_order([]), [])


if __name__ == "__main__":
    unittest.main()
