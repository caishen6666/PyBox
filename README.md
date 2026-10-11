# PyBox —— 带界面的 Python 工具箱 App（可打包 APK）

一个**真实可运行**的 Python 图形界面应用，同时支持 **桌面运行** 和 **打包成安卓 APK**。

## 功能

| 模块 | 说明 |
|------|------|
| ⬇️ 下载 | 输入 URL 即可下载任意文件，实时进度条，支持取消 |
| 📦 装库 | 运行时从 **真实 PyPI** 下载纯 Python 包，解压到私有 `site-packages` 并自动加入 `sys.path`，装完立即可 import（先装 `six`、`humanize` 等纯 Python 包试试） |
| ▶️ 运行 | 内置代码运行器，写 Python 代码立即执行，捕获 stdout/stderr，可直接 import 刚装好的库 |

中文界面基于捆绑的 Noto Sans SC 子集字体（GB2312 全集 + ASCII，仅 1.5MB，OFL 开源协议）。

## 项目结构

```
PyBox/
├── main.py               # Kivy 图形界面（4 个标签页）
├── core/
│   ├── downloader.py     # 线程化文件下载器（进度/取消/断错处理）
│   ├── pypi_manager.py   # PyPI 包管理器（wheel/sdist 安装、卸载、sys.path 注入）
│   └── code_runner.py    # 代码运行器（捕获输出、超时保护）
├── assets/
│   └── NotoSansSC.ttf    # 裁剪版中文字体
├── buildozer.spec        # APK 打包配置
├── requirements.txt      # 桌面端依赖
├── build_apk.sh          # 一键构建 APK 脚本（Linux/macOS）
└── README.md
```

## 桌面端直接运行

```bash
pip install -r requirements.txt      # 只需要 kivy
python main.py
```

支持 Windows / macOS / Linux。

## 打包成安卓 APK

### 方式一：本地构建（推荐 Linux）

```bash
pip install buildozer python-for-android cython
./build_apk.sh        # 首次构建会自动下载 Android SDK/NDK，约 30-60 分钟
```

构建产物：`bin/pybox-1.0-arm64-v8a_armeabi-v7a-debug.apk`，
通过数据线或 `adb install bin/*.apk` 安装到手机。

> 首次构建需要网络（Google/GitHub/PyPI）与约 10GB 磁盘空间。
> 国内网络建议先 `export P4A_RELEASES_MIRROR`…或配置代理。

### 方式二：云端构建（无需 Linux）

把本项目推到 GitHub，用 GitHub Actions 的 `ArtemSBulgakov/buildozer-action@v1`，
或使用在线服务（如 Kivy 的官方 CI 模板）自动产出 APK。

### 安装到手机

安卓手机开启「开发者模式 → USB 安装」，或直接把 APK 传到手机点击安装
（调试版 APK 无需签名配置）。

## 打包配置要点（buildozer.spec）

- `requirements = python3,kivy==2.3.1`
- `android.permissions = INTERNET`（下载与访问 PyPI 必需）
- `android.api = 34`，`android.minapi = 24`（支持 Android 7.0+）
- `android.archs = arm64-v8a,armeabi-v7a`（覆盖绝大多数手机）
- 数据写入应用私有目录，无需存储权限

## 已验证

- 逻辑测试：下载器（本地 HTTP 服务）✓；PyPI 真实安装 `six` 并 import ✓；代码运行器输出捕获 ✓
- UI 测试：Xvfb 虚拟屏下完整启动事件循环、4 标签页构建 ✓；截图经视觉模型确认中文无乱码 ✓
- APK：在本沙盒 Linux 环境用 buildozer + Android SDK 34 / NDK 25b 实际构建（见 bin/ 目录）

## 已知限制

- 「装库」支持**纯 Python** 包（如 six、python-dateutil、attrs、idna）；
  含 C 扩展的包（numpy、lxml 等）无法在运行时安装（安卓上没有编译器），
  如需这类库应在 `buildozer.spec` 的 requirements 中静态打包
- 代码运行器在应用进程内 exec，无真正沙箱隔离
- 服务器不支持断点续传时进度按全量计算
