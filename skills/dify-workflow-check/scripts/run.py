"""Dify Workflow Checker — 统一入口

用法:
  python run.py analyze <yml文件或目录>
  python run.py query <analysis.json> <command> [args...]
  python run.py heal <yml文件> <fixes.json> <输出路径>
  python run.py report <analysis.json> <fixes.json> <输出目录>
  python run.py init_fixes <fixes.json>
  python run.py append_fixes <fixes.json> <new_fixes.json> <source>
  python run.py validate_fixes <fixes.json>
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run_analysis_cli
from node_query import run_query_cli
from healer import run_heal_cli
from report_generator import run_report_cli
from fixes_io import run_init_fixes_cli, run_append_cli, run_validate_fixes_cli

COMMANDS = {
    'analyze': run_analysis_cli,
    'query': run_query_cli,
    'heal': run_heal_cli,
    'report': run_report_cli,
    'init_fixes': run_init_fixes_cli,
    'append_fixes': run_append_cli,
    'validate_fixes': run_validate_fixes_cli,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print(f"可用命令: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    cmd = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    COMMANDS[cmd]()


if __name__ == '__main__':
    main()
