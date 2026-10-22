"""一条命令完成一次采集；两次采集之间能自动算增长%。

用法：

    python main.py --stage before    # 跑机前采一次，存快照
    python main.py --stage after     # 跑机后采一次，自动和今天的 before 对比
    python main.py --offline         # 不连设备，用 samples/du-data.txt

快照位置：out/<串号>/<日期>-<阶段>.json（out/ 不进仓库）
"""

import datetime
import json
import os
import subprocess
import sys

import parse

# 两个硬编码：第一版故意的妥协，以后要改成"自动发现"（见 README）。
ADB = r"D:\leidian\LDPlayer14\adb.exe"
SERIAL = "emulator-5554"
OUT_DIR = "out"


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


def check_device() -> tuple[bool, str]:
    """开跑前自检：返回 (能不能跑, 人话原因)。

    查两件事，按"最常出错的顺序"排：
      1) 设备在不在
      2) 内部存储读不读得到（release 设备的常见坑）

    为什么要有它：没有自检时，读不到 /data 只会得到一个 Permission denied 的异常，
    人还得自己猜"是设备没连、还是权限不够、还是我命令写错了"。
    """
    try:
        run_on_device("echo ok")
    except Exception as e:
        return False, (
            "设备不可用。\n"
            f"  原始报错：{e}\n"
            "  处理：确认模拟器已启动；真机请确认数据线已连上、adb 授权已确认。"
        )

    try:
        run_on_device("ls /data")
    except Exception as e:
        return False, (
            "读不到设备内部存储（release 版本最常见的坑）。\n"
            f"  原始报错：{e}\n"
            "  处理：确认该设备已完成内部授权；模拟器请先执行 adb root。"
        )

    return True, "ok"


# ---------------------------------------------------------------
# 快照：把一次采集的结果落到磁盘，第二次采集才能和它对比
# ---------------------------------------------------------------

def to_growth_rows(hits: list) -> list:
    """[(清单路径, 原始行), ...] → [[大小K, 路径], ...]（growth() 的输入形状）。

    用"清单里的路径"当键（不是原始输出里的路径），这样两次采集才对得上。
    """
    return [[int(row[0]), path] for path, row in hits]


def snapshot_path(stage: str) -> str:
    """out/<串号>/<日期>-<阶段>.json —— 同一天、同一台设备的两次采集放在一起。"""
    today = datetime.date.today().isoformat()
    folder = os.path.join(OUT_DIR, SERIAL)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{today}-{stage}.json")


def save_snapshot(stage: str, hits: list) -> str:
    data = {
        "stage": stage,
        "serial": SERIAL,
        "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "rows": to_growth_rows(hits),
    }
    path = snapshot_path(stage)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def latest_before() -> dict | None:
    """找**最近一次** before 快照（不管哪天）。

    为什么不用"今天"：跑机常常跨夜——晚上采 before、第二天早上采 after，
    用"日期"当键会让它们永远配不上对。业务主键是"这一轮跑机"，不是"某一天"。
    """
    folder = os.path.join(OUT_DIR, SERIAL)
    if not os.path.isdir(folder):
        return None

    candidates = [
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if name.endswith("-before.json")
    ]
    if not candidates:
        return None

    newest = max(candidates, key=os.path.getmtime)
    with open(newest, encoding="utf-8") as f:
        return json.load(f)


def load_snapshot(stage: str) -> dict | None:
    path = snapshot_path(stage)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------
# 输出
# ---------------------------------------------------------------

def report(rows: list, paths: list, hits: list, misses: list) -> None:
    print(f"共 {len(rows)} 行原始数据，清单 {len(paths)} 条")
    print(f"命中 {len(hits)}/{len(paths)}")
    if misses:
        print("\n未命中（清单里有、数据里没找到）：")
        for path in misses:
            print("  -", path)
    else:
        print("全部命中。")


def write_excel(growth_rows: list, path: str) -> str:
    """把 growth() 的结果写成一张 xlsx。

    表头：路径 / 前(K) / 后(K) / 增长%
    规则：None 写成**空单元格**——不用 0 冒充，也不写 "None" 字符串。

    `import openpyxl` 放在函数里：没装这个库时，其它功能照常能用，只有调用它才会报错。
    """
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "跑机数据"
    ws.append(["路径", "前(K)", "后(K)", "增长%"])

    for p, b, a, pct in growth_rows:
        ws.append([p, b, a, None if pct is None else round(pct, 1)])

    wb.save(path)
    return path


def report_growth(before_rows: list, after_rows: list) -> None:
    print("\n增长（跑机前 → 跑机后）：")
    print(f"  {'路径':32s} {'前':>9s} {'后':>9s} {'增长':>8s}")
    for path, b, a, pct in parse.growth(before_rows, after_rows):
        b_str = parse.humanize(b) if b is not None else "—"
        a_str = parse.humanize(a) if a is not None else "—"
        p_str = f"{pct:+.1f}%" if pct is not None else "—"
        print(f"  {path:32s} {b_str:>9s} {a_str:>9s} {p_str:>8s}")


# ---------------------------------------------------------------
# 入口
# ---------------------------------------------------------------

if __name__ == "__main__":
    offline = "--offline" in sys.argv

    stage = None
    if "--stage" in sys.argv:
        stage = sys.argv[sys.argv.index("--stage") + 1]
        if stage not in ("before", "after"):
            print(f"[错误] --stage 只能是 before 或 after，你给的是 {stage!r}")
            sys.exit(2)

    if offline:
        with open("samples/du-data.txt", encoding="utf-8") as f:
            raw = f.read()
    else:
        # 先自检，再采。不通过就带着人话退出，绝不交一张空表。
        ok, reason = check_device()
        if not ok:
            print(f"[错误] {reason}")
            print("\n已停止，未采集任何数据。")
            sys.exit(1)
        raw = run_on_device("du /data")

    paths = parse.load_paths("paths.example.txt")
    rows = parse.parse_du(raw)
    hits, misses = parse.match(rows, paths)
    report(rows, paths, hits, misses)

    if stage:
        saved = save_snapshot(stage, hits)
        print(f"\n已存快照（{stage}）：{saved}")

    if stage == "after":
        before = latest_before()
        if before is None:
            print("\n[提示] 还没采过 before，没法对比。先跑：python main.py --stage before")
        else:
            print(f"\n对比对象：{before['saved_at']} 的 before 快照")
            report_growth(before["rows"], to_growth_rows(hits))

            # 落地：把这张增长表写成 xlsx（同一台设备、同一天，和快照放在一起）
            today = datetime.date.today().isoformat()
            xlsx = os.path.join(OUT_DIR, SERIAL, f"{today}.xlsx")
            try:
                write_excel(parse.growth(before["rows"], to_growth_rows(hits)), xlsx)
                print(f"\n已写出表格：{xlsx}")
            except ImportError:
                print("\n[提示] 没装 openpyxl，表格没写出来。装一下：")
                print("  python -m pip install openpyxl -i https://pypi.tuna.tsinghua.edu.cn/simple")
