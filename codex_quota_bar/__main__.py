import argparse
import json
import sys
import time
from dataclasses import asdict

from . import __version__
from .client import UsageError, fetch_quota
from .controller import Controller
from .model import present


def main():
    parser = argparse.ArgumentParser(description="Codex Quota Bar — 五小时 / 周余量状态栏")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--codex", help="Codex CLI 可执行文件路径")
    parser.add_argument("--once", action="store_true", help="打印一次额度，不启动界面")
    parser.add_argument("--json", action="store_true", help="配合 --once 输出 JSON")
    parser.add_argument("--demo", action="store_true", help="使用明确标记的演示数据")
    parser.add_argument("--smoke-test", action="store_true", help="演示界面运行 3 秒后退出")
    args = parser.parse_args()
    if args.json and not args.once:
        parser.error("--json 需要 --once")
    if args.smoke_test and not args.demo:
        parser.error("--smoke-test 需要 --demo")
    controller = Controller(args.codex, args.demo)
    if args.once:
        try:
            quota = controller.quota if args.demo else fetch_quota(args.codex)
        except UsageError as error:
            print(str(error), file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({**asdict(quota), "demo": args.demo}, ensure_ascii=False))
        else:
            title, rows = present(quota, time.time(), demo=args.demo)
            print("\n".join([title, *rows]))
        return 0
    try:
        if sys.platform == "darwin":
            from .macos import run
        elif sys.platform.startswith("linux"):
            from .linux import run
        else:
            parser.error("目前支持 Ubuntu 和 macOS。")
        run(controller, smoke_test=args.smoke_test)
    except (ImportError, ValueError) as error:
        print(f"无法启动状态栏：{error}\n请参阅 README 中的系统依赖安装说明。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
