from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLE_SCRIPTS = (
    REPO_ROOT / "utils/devices/slm/examples/bring_up.py",
    REPO_ROOT / "utils/devices/slm/examples/display.py",
)
EXAMPLE_MODULE_NAMES = (
    "utils.devices.slm.examples.bring_up",
    "utils.devices.slm.examples.display",
)


class ExampleEntrypointTests(unittest.TestCase):
    """
    测试 SLM 示例脚本入口点
    """

    def test_example_modules_support_package_style_imports(self) -> None:
        """
        测试示例模块支持包风格导入
        """
        for module_name in EXAMPLE_MODULE_NAMES:
            with self.subTest(module=module_name):
                imported_module = importlib.import_module(module_name)
                self.assertEqual(imported_module.__name__, module_name)

    def test_example_scripts_support_direct_help_execution(self) -> None:
        """
        测试示例脚本支持直接执行帮助命令
        """
        for script_path in EXAMPLE_SCRIPTS:
            with self.subTest(script=script_path.name):
                completed_process = subprocess.run(
                    [sys.executable, str(script_path), "--help"],
                    capture_output=True,
                    text=True,
                    cwd=REPO_ROOT,
                    check=False,
                )

                self.assertEqual(
                    completed_process.returncode,
                    0,
                    msg=(
                        "stdout:\n%s\nstderr:\n%s"
                        % (
                            completed_process.stdout,
                            completed_process.stderr,
                        )
                    ),
                )
                self.assertIn("usage:", completed_process.stdout)

    def test_display_help_has_no_pillow_import_dependency(
        self,
    ) -> None:
        """
        测试显示帮助命令不依赖 Pillow 导入
        """
        with tempfile.TemporaryDirectory() as temporary_directory:
            sitecustomize_path = Path(temporary_directory) / "sitecustomize.py"
            sitecustomize_path.write_text(
                "import builtins\n"
                "_original_import = builtins.__import__\n"
                "def _blocked_import(\n"
                "    name, globals=None, locals=None, fromlist=(), level=0\n"
                "):\n"
                "    if name == 'PIL' or name.startswith('PIL.'):\n"
                "        raise ModuleNotFoundError(\n"
                "            \"No module named 'PIL'\", name='PIL'\n"
                "        )\n"
                "    return _original_import(name, globals, locals, fromlist, level)\n"
                "builtins.__import__ = _blocked_import\n",
                encoding="utf-8",
            )

            environment = os.environ.copy()
            python_path_entries = [temporary_directory, str(REPO_ROOT)]
            if environment.get("PYTHONPATH"):
                python_path_entries.append(environment["PYTHONPATH"])
            environment["PYTHONPATH"] = os.pathsep.join(python_path_entries)

            completed_process = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "utils/devices/slm/examples/display.py"),
                    "--help",
                ],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                env=environment,
                check=False,
            )

        self.assertEqual(
            completed_process.returncode,
            0,
            msg=(
                "stdout:\n%s\nstderr:\n%s"
                % (completed_process.stdout, completed_process.stderr)
            ),
        )
        self.assertIn("usage:", completed_process.stdout)


if __name__ == "__main__":
    unittest.main()
