import unittest

from src.dict_utils import merge_defaults


class TestMergeDefaults(unittest.TestCase):
    def test_overrides_replace_default_values(self) -> None:
        result = merge_defaults({"theme": "light"}, {"theme": "dark"})

        self.assertEqual(result["theme"], "dark")


if __name__ == "__main__":
    unittest.main()
