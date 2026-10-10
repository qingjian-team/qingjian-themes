#!/usr/bin/env python3
"""用本机装的青简把主题画成预览图（preview/ 下的竖排、横排，没锁定外观的再加深色竖排），然后校验。

    python3 tools/preview.py themes/my-theme
    python3 tools/preview.py themes/my-theme --app "D:\\Qingjian\\qingjian-server.exe"

图由青简自己的渲染器画，与输入时看到的一样；封面 cover.png 与额外截图要自己做。
某一张没画出来只提示，不影响其余几张。需要 macOS 或 Windows 上装好青简（0.2.0 起）。
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

FLAG = "--theme-preview"


def find_app():
    """本机装的青简可执行文件；找不到返回 None。"""
    system = platform.system()
    if system == "Darwin":
        candidates = [
            Path.home() / "Library/Input Methods/Qingjian.app/Contents/MacOS/qingjian-macos",
            Path("/Library/Input Methods/Qingjian.app/Contents/MacOS/qingjian-macos"),
        ]
    elif system == "Windows":
        candidates = [
            Path(os.environ.get(var, "")) / "Qingjian" / "qingjian-server.exe"
            for var in ("ProgramFiles", "ProgramW6432", "LOCALAPPDATA")
            if os.environ.get(var)
        ]
    else:
        candidates = []
    return next((path for path in candidates if path.is_file()), None)


def main():
    parser = argparse.ArgumentParser(description="用本机的青简生成主题预览图")
    parser.add_argument("theme", type=Path, help="主题目录，如 themes/my-theme")
    parser.add_argument("--app", type=Path, help="青简可执行文件的路径（装在别处时指定）")
    args = parser.parse_args()

    theme = args.theme.resolve()
    if not (theme / "theme.json").is_file():
        print(f"{args.theme} 里没有 theme.json", file=sys.stderr)
        return 1
    app = args.app or find_app()
    if app is None or not app.is_file():
        print(
            "没找到本机装的青简：主题预览图要用青简自己画，目前支持 macOS 与 Windows。\n"
            "装在别处的话用 --app 指定可执行文件的路径。",
            file=sys.stderr,
        )
        return 1

    # 0.2.0 之前的青简不认这个参数，会照常起输入法服务、不退出：超时就当版本太旧
    try:
        result = subprocess.run([str(app), FLAG, str(theme)], timeout=30)
    except subprocess.TimeoutExpired:
        print("\n青简没有响应，多半是版本太旧（0.2.0 起才能生成预览图），请先升级。", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"启动不了 {app}：{error}\n用安装包装好的青简，不要用自己编译、没签名的版本。", file=sys.stderr)
        return 1
    if result.returncode != 0:
        return result.returncode

    print()
    if not (theme / "preview/cover.png").is_file():
        print("还差封面 preview/cover.png（1200×630），要自己做。")
    check = Path(__file__).resolve().parent / "check.py"
    return subprocess.run([sys.executable, str(check), str(theme)]).returncode


if __name__ == "__main__":
    sys.exit(main())
