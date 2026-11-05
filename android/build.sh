#!/usr/bin/env bash
# 归岸 APK 一键构建
#   网页资源 → aapt2 编译资源 → 链接 → javac → d8 → 合并 dex → 对齐 → 签名 → 校验
#
# 用法：
#   ANDROID_SDK=/path/to/sdk JAVA_HOME=/path/to/jdk17 bash android/build.sh
#
# 需要：JDK 17、Android SDK（platforms/android-34 + build-tools/34.0.0）、Python 3（PIL 非必需）
# 产物：android/build/guian.apk
set -euo pipefail

PROJ="$(cd "$(dirname "$0")" && pwd)"      # 本文件所在目录（仓库里的 android/）
APPDIR="$(cd "$PROJ/.." && pwd)"           # 网页版根目录
OUT="${OUT:-$PROJ/build}"

ANDROID_SDK="${ANDROID_SDK:-$HOME/android-sdk}"
export JAVA_HOME="${JAVA_HOME:-$HOME/jdk17}"
PYTHON="${PYTHON:-py}"

BT="$ANDROID_SDK/build-tools/34.0.0"
AND="$ANDROID_SDK/platforms/android-34/android.jar"
JAVAC="$JAVA_HOME/bin/javac.exe"
KEYTOOL="$JAVA_HOME/bin/keytool.exe"
[ -x "$JAVAC" ] || JAVAC="$JAVA_HOME/bin/javac"
[ -x "$KEYTOOL" ] || KEYTOOL="$JAVA_HOME/bin/keytool"
NAME="guian"

for f in "$JAVAC" "$BT/aapt2.exe" "$AND"; do
  [ -e "$f" ] || { echo "缺少依赖：$f" >&2; exit 1; }
done

echo "== 1/8 同步网页资源 =="
rm -rf "$PROJ/assets/www"
mkdir -p "$PROJ/assets/www/assets"
cp "$APPDIR/index.html" "$APPDIR/manifest.webmanifest" "$APPDIR/sw.js" "$PROJ/assets/www/"
cp "$APPDIR/assets/styles.css" "$APPDIR/assets/app.js" \
   "$APPDIR/assets/icon.svg" "$APPDIR/assets/icon-maskable.svg" "$PROJ/assets/www/assets/"

echo "== 2/8 编译资源 =="
rm -rf "$OUT/compiled" "$OUT/gen" "$OUT/classes" "$OUT/dex"
mkdir -p "$OUT/compiled" "$OUT/gen" "$OUT/classes" "$OUT/dex"
"$BT/aapt2.exe" compile --dir "$PROJ/res" -o "$OUT/compiled/res.zip"

echo "== 3/8 链接资源 =="
"$BT/aapt2.exe" link -o "$OUT/base.apk" -I "$AND" \
  --manifest "$PROJ/AndroidManifest.xml" -R "$OUT/compiled/res.zip" \
  --java "$OUT/gen" --auto-add-overlay -A "$PROJ/assets"

echo "== 4/8 编译 Java =="
"$JAVAC" -source 8 -target 8 -encoding UTF-8 -bootclasspath "$AND" -classpath "$AND" \
  -Xlint:-options -d "$OUT/classes" \
  "$OUT/gen/com/guian/app/R.java" "$PROJ/java/com/guian/app/MainActivity.java"

echo "== 5/8 dex =="
"$BT/d8.bat" --release --min-api 21 --lib "$AND" --output "$OUT/dex" \
  $(find "$OUT/classes" -name "*.class" | tr '\n' ' ')

echo "== 6/8 合并 dex 并压缩对齐 =="
"$PYTHON" "$PROJ/tools/pack.py" "$OUT/base.apk" "$OUT/dex/classes.dex" "$OUT/withdex.apk"
"$BT/zipalign.exe" -p -f 4 "$OUT/withdex.apk" "$OUT/aligned.apk"

echo "== 7/8 签名 =="
if [ ! -f "$OUT/debug.keystore" ]; then
  "$KEYTOOL" -genkeypair -v -keystore "$OUT/debug.keystore" -storepass android \
    -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Android Debug,O=Android,C=US"
fi
"$BT/apksigner.bat" sign --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --ks "$OUT/debug.keystore" --ks-pass pass:android \
  --key-pass pass:android --ks-key-alias androiddebugkey --out "$OUT/$NAME.apk" "$OUT/aligned.apk"

echo "== 8/8 校验 =="
"$BT/apksigner.bat" verify --print-certs "$OUT/$NAME.apk" | head -4
"$BT/aapt2.exe" dump badging "$OUT/$NAME.apk" | head -3
"$PYTHON" "$PROJ/tools/verify_apk.py" "$OUT/$NAME.apk"
ls -l "$OUT/$NAME.apk"
