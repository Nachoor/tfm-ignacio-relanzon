import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util
from pathlib import Path

APP_FILE = Path(__file__).resolve().parents[1] / "caiq_app.py"
spec = importlib.util.spec_from_file_location("caiq_app_runtime", APP_FILE)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)
main = module.main

if __name__ == '__main__':
    main()
