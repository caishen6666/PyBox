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

# SDK / NDK / Ant 位置（build_apk.sh 会自动准备到 .build-tools/，已存在则跳过）
android.sdk_path = .build-tools/android-sdk
android.ndk_path = .build-tools/android-ndk-r25b
android.ant_path = .build-tools/apache-ant-1.10.18
# SDK 组件由脚本预先安装，跳过 sdkmanager 在线更新（离线/受限网络必需）
android.skip_update = True

#
# Buildozer 执行配置
#

[buildozer]
log_level = 2
warn_on_root = 1
