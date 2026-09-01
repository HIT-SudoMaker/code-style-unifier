from __future__ import annotations

import importlib
import unittest


EXAMPLE_MODULE_NAMES = (
    "utils.devices.stage.examples.bring_up",
    "utils.devices.stage.examples.move_axis",
)


class StageExampleTests(unittest.TestCase):
    """
    验证运动台示例入口
    """

    def test_example_modules_use_action_names(self) -> None:
        """
        示例入口使用动作命名
        """
        for module_name in EXAMPLE_MODULE_NAMES:
            with self.subTest(module=module_name):
                imported_module = importlib.import_module(module_name)
                self.assertEqual(imported_module.__name__, module_name)


if __name__ == "__main__":
    unittest.main()
