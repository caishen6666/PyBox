[app]
title = PyBox
package.name = pybox
package.domain = cn.pybox

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,otf,json,txt
source.exclude_dirs = appdata, __pycache__, .buildozer, .build-tools, bin, docs

version = 1.0

# Python 3.12 + Kivy 界面框架（hostpython3 与 python3 版本必须一致）
requirements = hostpython3==3.12.8,python3==3.12.8,kivy==2.3.1

orientation = portrait
fullscreen = 0
android.allow_backup = True

# Android 版本：目标 API 34，最低支持 Android 7.0 (API 24)
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a

# 网络权限（下载文件 / 访问 PyPI 必需）
android.permissions = INTERNET

# 图标与启动页（可选，缺失时使用默认）
#icon.filename = %(source.dir)s/assets/icon.png
#presplash.filename = %(source.dir)s/assets/presplash.png

# SDK / NDK 由 buildozer 在构建时自动下载到 ~/.buildozer/（CI 环境）
# android.sdk_path =
# android.ndk_path =
# android.ant_path =
# android.skip_update = False

#
# Buildozer 执行配置
#

[buildozer]
log_level = 2
warn_on_root = 1
