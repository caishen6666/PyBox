#!/usr/bin/env bash
# PyBox 一键构建 APK 脚本（Linux/macOS）
# 用法: ./build_apk.sh
# 首次运行会自动下载 Android SDK/NDK 并编译，约 30-60 分钟。
set -euo pipefail
cd "$(dirname "$0")"

# ---- 1. 安装构建工具 ----
pip install -q buildozer python-for-android cython || true

# ---- 2. 准备 SDK/NDK（已存在则跳过）----
SDK="$PWD/.build-tools/android-sdk"
NDK="$PWD/.build-tools/android-ndk-r25b"
mkdir -p .build-tools

if [ ! -d "$SDK/cmdline-tools/latest" ]; then
  echo ">> 下载 Android cmdline-tools ..."
  curl -L -o .build-tools/cmdline-tools.zip \
    "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
  unzip -q .build-tools/cmdline-tools.zip -d .build-tools/ct
  mkdir -p "$SDK/cmdline-tools"
  mv .build-tools/ct/cmdline-tools "$SDK/cmdline-tools/latest"
fi

if [ ! -d "$NDK" ]; then
  echo ">> 下载 Android NDK r25b ..."
  curl -L -o .build-tools/ndk.zip \
    "https://dl.google.com/android/repository/android-ndk-r25b-linux.zip"
  unzip -q .build-tools/ndk.zip -d .build-tools/
  rm .build-tools/ndk.zip
fi

if [ ! -d "$SDK/platforms/android-34" ]; then
  echo ">> 安装 SDK 组件 (platform 34 / build-tools) ..."
  yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null || true
  "$SDK/cmdline-tools/latest/bin/sdkmanager" \
    "platform-tools" "platforms;android-34" "build-tools;34.0.0" >/dev/null
fi

# ---- 3. 构建 APK ----
echo ">> 开始 buildozer 构建 ..."
buildozer -v android debug

echo ""
echo "完成！APK 在: $(ls bin/*.apk)"
