"""把 classes.dex 塞进 aapt2 产出的 base.apk。

关键点：
- resources.arsc 在 Android 11+（targetSdk >= 30）必须是 STORED（不压缩）且 4 字节对齐，
  否则安装时报 INSTALL_PARSE_FAILED_RESOURCES_ARSC_COMPRESSED / 「解析包出错」。
- 因此这里逐条保留 aapt2 原来的压缩方式，只对 arsc 强制 STORED；
  对齐交给随后的 zipalign -p 4。
"""
import sys
import zipfile

ALWAYS_STORED = {"resources.arsc"}


def main(base, dex, out):
    with zipfile.ZipFile(base) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.external_attr = item.external_attr
            if item.filename in ALWAYS_STORED:
                zi.compress_type = zipfile.ZIP_STORED
            else:
                zi.compress_type = item.compress_type
            zout.writestr(zi, data)
        zout.write(dex, "classes.dex")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
