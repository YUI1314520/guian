"""APK 结构自检：模拟 Android 安装器会做的几项硬性检查。

注意：对齐要读「本地文件头」里的 extra 长度——zipalign 的填充字节写在那里，
中央目录里的 extra 长度不等于本地头里的，用 zipfile 直接算会误报。

用法：py android/tools/verify_apk.py android/build/guian.apk
"""
import struct
import sys
import zipfile

LOCAL_SIG = b"PK\x03\x04"


def local_entry(data, want):
    """按名字在本地文件头里定位一条记录，返回 {method, data_offset}。"""
    idx = 0
    while True:
        i = data.find(want.encode(), idx)
        if i < 0:
            return None
        hdr = i - 30
        if data[hdr:hdr + 4] == LOCAL_SIG:
            nlen, elen = struct.unpack_from("<HH", data, hdr + 26)
            if nlen == len(want.encode()):
                method = struct.unpack_from("<H", data, hdr + 8)[0]
                return {"method": method, "data": hdr + 30 + nlen + elen}
        idx = i + 1


def main(path):
    problems = []
    print(f"检查 {path}")
    raw = open(path, "rb").read()
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        for need in ("AndroidManifest.xml", "classes.dex", "resources.arsc"):
            if need not in names:
                problems.append(f"缺 {need}")
        if problems:
            print("\n".join("FAIL  " + p for p in problems))
            return 1

        # 1. resources.arsc：Android 11+（targetSdk>=30）必须 STORED 且 4 字节对齐
        arsc = local_entry(raw, "resources.arsc")
        if arsc["method"] != 0:
            problems.append("resources.arsc 被压缩（method=%d），Android 11+ 会拒装" % arsc["method"])
        elif arsc["data"] % 4:
            problems.append(f"resources.arsc 数据未 4 字节对齐（{arsc['data']}）")
        else:
            print(f"OK    resources.arsc STORED 且 4 字节对齐（data@{arsc['data']}）")

        # 2. dex 魔数
        if z.read("classes.dex")[:4] != b"dex\n":
            problems.append("classes.dex 魔数不对")
        else:
            print("OK    classes.dex 魔数正常")

        # 3. 清单是二进制 XML（首两字节 0x0003）
        if z.read("AndroidManifest.xml")[:2] != b"\x03\x00":
            problems.append("AndroidManifest.xml 不是编译后的二进制 XML")
        else:
            print("OK    AndroidManifest.xml 为二进制 XML")

        # 4. 条目名合法
        for n in names:
            if n.startswith("/") or ".." in n.split("/"):
                problems.append(f"非法条目名 {n}")
            if any(ord(c) > 126 or ord(c) < 32 for c in n):
                problems.append(f"条目名含非 ASCII 字符 {n!r}")

        # 5. 其余 STORED 条目对齐（只告警，不致命）
        for n in names:
            e = local_entry(raw, n)
            if e and e["method"] == 0 and e["data"] % 4:
                print(f"WARN  {n} 未 4 字节对齐（data@{e['data']}）")

        metas = [n for n in names if n.startswith("META-INF/")]
        print(f"OK    条目 {len(names)} 个，META-INF {len(metas)} 个")

    if problems:
        print("\n".join("FAIL  " + p for p in problems))
        print(f"\n共 {len(problems)} 处问题")
        return 1
    print("\n结构自检全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
