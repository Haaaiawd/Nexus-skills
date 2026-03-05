"""测试配置：将 scripts/ 目录加入 sys.path，使 extract_ast 和 git_detective 可直接 import"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
