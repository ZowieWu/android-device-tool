"""第一版：调 adb 执行一条命令，把结果打印出来。

对应 README 第二节的第 2 个勾选项。
这一版只做一件事：把设备上的命令输出，原样搬到屏幕上。
"""

import subprocess

# 两个硬编码：这是第一版故意的妥协，后面要改成"自动发现"（见 README 第三节）。
ADB = r"D:\leidian\LDPlayer14\adb.exe"
SERIAL = "emulator-5554"


def run_on_device(command: str) -> str:
    """在设备上执行一条命令，返回它的标准输出。"""
    result = subprocess.run(
        [ADB, "-s", SERIAL, "shell", command],
        capture_output=True,   # 把输出接住，而不是漏到屏幕上
        text=True,             # 按文本解码，不是一堆字节
        encoding="utf-8",      # 不让中文/特殊符号变成乱码
        timeout=15,            # adb 卡住时不要无限等
    )
    if result.returncode != 0:
        # 关键：命令失败必须炸出来，不能悄悄返回空字符串
        raise RuntimeError(f"adb 执行失败：{result.stderr.strip()}")
    return result.stdout


if __name__ == "__main__":
    print(run_on_device("df -h"))
