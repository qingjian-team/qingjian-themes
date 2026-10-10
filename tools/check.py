#!/usr/bin/env python3
"""校验主题目录，可选生成官网用的 index.json。

    python3 tools/check.py                     # 校验 themes/ 与 examples/ 下的全部主题
    python3 tools/check.py themes/foo          # 只校验这几个
    python3 tools/check.py --index index.json  # 校验全部并写出索引

规则见 README「提交主题」；改了规则同步那一节。
"""

import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SQUOOSH = "可以用 https://squoosh.app 转格式、压缩、改尺寸"

# 青简当前支持的主题格式版本（主仓库 crates/qingjian-render/src/theme/file/mod.rs 的 SCHEMA）。
SCHEMA = 1

# 内置主题与外观词：用户主题不能用这些 id（青简会拒绝加载）。examples/ 里放的是内置主题的源文件，不受此限。
RESERVED_IDS = {"qingjian", "system-blue", "wechat", "sakura", "system", "light", "dark"}

ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
EXTRA_PREVIEW = re.compile(r"^\d{2}-[a-z0-9-]+\.png$")

COVER_SIZE = (1200, 630)
MAX_DESCRIPTION = 80
MAX_SCREENSHOTS = 6  # 不含封面
MAX_PREVIEW_BYTES = 500 * 1024
MAX_THEME_BYTES = 5 * 1024 * 1024
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
TOP_LEVEL_FILES = {"theme.json", "README.md", "LICENSE"}


def strip_jsonc(text):
    """去掉 // 与 /* */ 注释和尾逗号（字符串里的不动），得到标准 JSON。"""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i : j + 1])
            i = j + 1
        elif text.startswith("//", i):
            i = text.find("\n", i)
            i = n if i < 0 else i
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        else:
            out.append(c)
            i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def image_refs(node):
    """theme.json 里所有 `"image": "…"` 的值。"""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "image" and isinstance(value, str):
                yield value
            else:
                yield from image_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from image_refs(value)


class Theme:
    def __init__(self, path):
        self.path = path
        self.example = path.parent.name == "examples"
        self.errors = []
        self.meta = {}
        self.previews = []

    def error(self, message):
        self.errors.append(f"{self.path.relative_to(ROOT)}: {message}")

    def check(self):
        self.check_files()
        self.check_theme_json()
        self.check_readme()
        self.check_preview()
        return self

    def check_files(self):
        total = 0
        for file in self.path.rglob("*"):
            if file.is_dir():
                continue
            rel = file.relative_to(self.path)
            total += file.stat().st_size
            top = rel.parts[0]
            if len(rel.parts) == 1:
                if top not in TOP_LEVEL_FILES:
                    self.error(f"多余的文件 {rel}：主题目录顶层只放 theme.json、README.md、LICENSE")
            elif top == "images":
                if file.suffix.lower() not in IMAGE_SUFFIXES:
                    self.error(f"images/ 只放图片（png / jpg / webp / svg）：{rel}")
            elif top != "preview":
                self.error(f"多余的目录 {top}/：只允许 images/ 与 preview/（字体不随主题打包）")
        if total > MAX_THEME_BYTES:
            self.error(f"整个主题 {total / 1024 / 1024:.1f} MB，上限 {MAX_THEME_BYTES // 1024 // 1024} MB")

    def check_theme_json(self):
        file = self.path / "theme.json"
        if not file.is_file():
            self.error("缺 theme.json")
            return
        try:
            data = json.loads(strip_jsonc(file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.error(f"theme.json 解析不了：{e}")
            return
        schema = data.get("schema")
        if not isinstance(schema, int) or not 1 <= schema <= SCHEMA:
            self.error(f'theme.json 的 "schema" 要写 1–{SCHEMA} 的整数，现在是 {schema!r}')
        meta = data.get("meta")
        if not isinstance(meta, dict):
            self.error('theme.json 缺 "meta"')
            return
        self.meta = meta
        theme_id = meta.get("id")
        if theme_id != self.path.name:
            self.error(f'meta.id（{theme_id!r}）要与目录名（{self.path.name!r}）相同')
        if not isinstance(theme_id, str) or not ID_PATTERN.match(theme_id):
            self.error("meta.id 只能用小写字母、数字和连字符，如 my-theme")
        elif theme_id in RESERVED_IDS and not self.example:
            self.error(f"meta.id 不能用 {theme_id!r}：与内置主题或外观设置重名")
        for key in ("name", "author", "license", "description", "version"):
            if not isinstance(meta.get(key), str) or not meta[key].strip():
                self.error(f"meta.{key} 必填")
        if len(meta.get("description") or "") > MAX_DESCRIPTION:
            self.error(f"meta.description 不超过 {MAX_DESCRIPTION} 字，长介绍写在 README.md")
        if isinstance(meta.get("version"), str) and not VERSION_PATTERN.match(meta["version"]):
            self.error("meta.version 写成 1.0.0 这样的三段数字")
        tags = meta.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            self.error("meta.tags 是字符串数组")
        if meta.get("appearance") not in (None, "light", "dark"):
            self.error('meta.appearance 只能是 "light"、"dark" 或不写')
        for ref in image_refs(data):
            target = (self.path / ref).resolve()
            if ref.startswith("/") or ".." in Path(ref).parts or not target.is_relative_to(self.path.resolve()):
                self.error(f"图片路径要写主题目录里的相对路径：{ref}")
            elif not target.is_file():
                self.error(f"引用的图片不存在：{ref}")

    def check_readme(self):
        file = self.path / "README.md"
        if not file.is_file() or not file.read_text(encoding="utf-8").strip():
            self.error("缺 README.md（官网详情页的介绍）")

    def check_preview(self):
        directory = self.path / "preview"
        files = sorted(p.name for p in directory.iterdir()) if directory.is_dir() else []
        required = ["cover.png", "vertical.png", "horizontal.png"]
        if not self.meta.get("appearance"):
            required.append("vertical-dark.png")
        for name in required:
            if name not in files:
                self.error(f"preview/ 缺 {name}")
        for name in files:
            file = directory / name
            if name not in required and not EXTRA_PREVIEW.match(name):
                self.error(f"preview/{name}：额外截图命名为 01-说明.png 这样（两位编号决定详情页顺序）")
                continue
            if file.stat().st_size > MAX_PREVIEW_BYTES:
                self.error(f"preview/{name} 超过 {MAX_PREVIEW_BYTES // 1024} KB，{SQUOOSH}")
            size = png_size(file)
            if size is None:
                self.error(f"preview/{name} 不是 PNG，{SQUOOSH}")
            elif name == "cover.png" and size != COVER_SIZE:
                self.error(f"preview/cover.png 要 {COVER_SIZE[0]}×{COVER_SIZE[1]}，现在是 {size[0]}×{size[1]}，{SQUOOSH}")
        screenshots = [f for f in files if f != "cover.png"]
        if len(screenshots) > MAX_SCREENSHOTS:
            self.error(f"preview/ 截图 {len(screenshots)} 张，不含封面最多 {MAX_SCREENSHOTS} 张")
        order = {name: i for i, name in enumerate(required)}
        self.previews = sorted(screenshots, key=lambda f: (order.get(f, len(order)), f))

    def index_entry(self):
        meta = self.meta
        base = self.path.relative_to(ROOT).as_posix()
        return {
            "id": meta.get("id"),
            "name": meta.get("name"),
            "author": meta.get("author"),
            "license": meta.get("license"),
            "description": meta.get("description"),
            "version": meta.get("version"),
            "tags": meta.get("tags", []),
            "appearance": meta.get("appearance"),
            "example": self.example,
            "path": base,
            "readme": f"{base}/README.md",
            "cover": f"{base}/preview/cover.png",
            "screenshots": [f"{base}/preview/{name}" for name in self.previews],
        }


def all_theme_dirs():
    for parent in ("themes", "examples"):
        for path in sorted((ROOT / parent).iterdir()) if (ROOT / parent).is_dir() else []:
            if path.is_dir():
                yield path


def main():
    parser = argparse.ArgumentParser(description="校验青简主题")
    parser.add_argument("dirs", nargs="*", type=Path, help="只校验这些主题目录")
    parser.add_argument("--index", type=Path, help="校验全部主题并写出索引")
    args = parser.parse_args()
    dirs = [d.resolve() for d in args.dirs] if args.dirs and not args.index else list(all_theme_dirs())
    themes = [Theme(d).check() for d in dirs]
    errors = [e for t in themes for e in t.errors]
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} 处不合规，规则见 README「提交主题」。", file=sys.stderr)
        return 1
    print(f"{len(themes)} 个主题校验通过")
    if args.index:
        index = {"schema": SCHEMA, "themes": [t.index_entry() for t in themes]}
        args.index.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"已写出 {args.index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
