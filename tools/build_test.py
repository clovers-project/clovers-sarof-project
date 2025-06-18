from pathlib import Path
import shutil

path = Path(__file__).parent.parent

package_path = path / "test-package" / "clovers_sarof"
modules_path = [x for x in path.iterdir() if x.is_dir() and x.name.startswith("clovers-sarof")]
for module_path in modules_path:
    shutil.copytree(module_path / "clovers_sarof", package_path, dirs_exist_ok=True)
