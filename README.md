# 青简主题

[青简输入法](https://github.com/qingjian-team/qingjian)的候选窗口主题合集。官网的主题页从这里拉取。

主题支持 macOS 与 Windows，只对青简渲染器生效（「偏好设置 / 设置 → 候选窗口 → 渲染引擎」选「青简渲染器」）。主题文件的写法见青简使用说明的[「主题」页](https://qingjian.app/docs/settings/themes)。

## 安装主题

1. 下载主题文件夹（`themes/<主题 id>/` 整个文件夹）。
2. 放进青简数据目录的 `themes/` 里，文件夹名不改：
   - macOS：`~/Library/Application Support/Qingjian/themes/`
   - Windows：`%APPDATA%\Qingjian\themes\`
3. 在「偏好设置 / 设置 → 候选窗口 → 主题」里选它。放进去就能选，不用重启。

## 目录

```
themes/<id>/            投稿的主题，一个主题一个文件夹，文件夹名等于主题 id
examples/sakura/        青简内置「樱花」主题的源文件，写主题时照着改
tools/check.py          校验脚本，CI 与本地提交钩子都跑它
```

## 提交主题

在 `themes/` 下新建一个文件夹，提 PR。CI 会跑 `tools/check.py`，不合规的 PR 不会合。

一个主题的文件夹：

```
themes/my-theme/
  theme.json            主题文件
  README.md             官网详情页的介绍：风格、设计说明、素材出处、更新记录
  LICENSE               可选，许可证全文
  images/               主题用到的图片（png / jpg / webp / svg）
  preview/
    cover.png           封面，1200×630，官网卡片与分享图
    vertical.png        竖排候选窗口截图
    horizontal.png      横排候选窗口截图
    vertical-dark.png   深色外观的竖排截图（主题锁定了一种外观时不用）
    01-xxx.png          其他截图，两位编号决定详情页里的顺序
```

规则：

- **`theme.json`**：`"schema"` 写青简支持的格式版本（现在是 `1`）。`meta` 里这些必填：
  - `id`：小写字母、数字、连字符，与文件夹名相同；不能用内置主题的 id（`qingjian` `system-blue` `wechat` `sakura`）和 `system` `light` `dark`
  - `name`：显示名
  - `author`：作者
  - `license`：SPDX 许可证标识，如 `CC-BY-4.0`、`GPL-3.0-or-later`
  - `description`：一句话介绍，不超过 80 字
  - `version`：主题自己的版本号，如 `1.0.0`，更新时递增
  - `tags`：可选，字符串数组，如 `["深色", "简约"]`
- **图片**：只引用主题文件夹里的相对路径；不随主题打包字体，写系统字体或常见字体的名字。
- **截图**：都是 PNG，每张不超过 500 KB；不算封面最多 6 张。截图要是青简里实际显示的样子。转格式、压缩、改尺寸可以用 [Squoosh](https://squoosh.app)，网页版，不用安装。
- **大小**：整个主题文件夹不超过 5 MB。
- **素材**：图片要是你自己画的，或者你有权使用并按 `license` 发布。PR 模板里有一项要勾选确认。

提交前在本地跑一遍：

```sh
python3 tools/check.py themes/my-theme
```

## 提交信息

`<类型>(<范围>): <说明>`，范围写主题 id，例如 `feat(my-theme): 新增「我的主题」`、`fix(my-theme): 修深色下文字看不清`。
类型：`feat` 新主题 / `fix` 修主题 / `docs` 只改文字 / `ci` / `chore`。

启用本地钩子（提交前跑校验、检查提交信息）：

```sh
git config core.hooksPath .githooks
```

## 许可

校验脚本与仓库配置按 GPL-3.0-or-later 发布。每个主题按它 `meta.license` 写的许可证发布，版权归各自作者。
