"""一条命令：采一次 /data，打印"命中 M/N"和未命中清单。

第 2 周目标。用法：

    python main.py                 # 连设备采（需要模拟器在跑）
    python main.py --offline       # 不连设备，用 samples/du-data.txt

输出示例：

    共 1732 行原始数据，清单 5 条
    命中 5/5
    全部命中。
"""

import subprocess
import sys

import parse

# 两个硬编码：第一版故意的妥协，以后要改成"自动发现"（见 README）。
ADB = r"D:\leidian\LDPlayer14\adb.exe"
SERIAL = "emulator-5554"


def run_on_device(command: str) -> str:
    """在设备上执行一条命令，返回它的标准输出。"""
    result = subprocess.run(
        [ADB, "-s", SERIAL, "shell", command],
        capture_output=True,   # 把输出接住，而不是漏到屏幕上
        text=True,             # 按文本解码，不是一堆字节
        encoding="utf-8",      # 不让中文/特殊符号变成乱码
        timeout=60,            # du 会慢，给足时间；但绝不无限等
    )
    if result.returncode != 0:
        # 关键：命令失败必须炸出来，不能悄悄返回空字符串
        raise RuntimeError(f"adb 执行失败：{result.stderr.strip()}")
    return result.stdout


def report(raw: str, paths: list[str]) -> None:
    """把一次采集的原始输出，变成一份"命中情况"报告。"""
    rows = parse.parse_du(raw)
    hits, misses = parse.match(rows, paths)

    print(f"共 {len(rows)} 行原始数据，清单 {len(paths)} 条")
    print(f"命中 {len(hits)}/{len(paths)}")

    if misses:
        print("\n未命中（清单里有、数据里没找到）：")
        for path in misses:
            print("  -", path)
    else:
        print("全部命中。")


if __name__ == "__main__":
    if "--offline" in sys.argv:
        with open("samples/du-data.txt", encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = run_on_device("du /data")

    report(raw, parse.load_paths("paths.example.txt"))
