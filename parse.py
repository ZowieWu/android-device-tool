"""第二格：把 df -h 的输出拆成一条条记录。

今天不需要模拟器：samples/ 里存着真实输出，离线就能开发。
"""


def parse_df(output: str) -> list[list[str]]:
    """把 df -h 的输出拆开。

    返回：[['tmpfs', '2.9G', '1.3M', '2.9G', '1%', '/dev'], ...]
    每条记录必须是 6 个字段：Filesystem / Size / Used / Avail / Use% / Mounted on
    """
    lines = output.strip().splitlines()
    data = lines[1:]  # 跳过表头

    rows = []
    for line in data:
        parts = line.split(None, 5)  # 最多切 5 刀 → 6 段
        rows.append(parts)
    return rows


# ---------------------------------------------------------------
# 第三格：白名单——哪些行有资格进表
# ---------------------------------------------------------------

KEEP = {"/data"}  # 空 A：有资格进表的挂载点。


# 提示：你的工具要回答"这台设备哪个地方的存储要满了"。
#      看一遍那 14 行的 Mounted on，哪个才是设备自己的存储？


def pick(rows: list[list[str]], keep=None) -> tuple[list, list]:
    """按白名单筛行，返回 (留下的行, [(被丢掉的行, 原因), ...])。

    被丢掉的行必须带原因：静默丢弃 = 三个月后没人知道表里为什么少了 13 行。
    """
    keep = KEEP if keep is None else keep
    kept, dropped = [], []
    for row in rows:
        mount = row[-1]
        if mount in keep:  # 空 B：怎么判断它在不在白名单里？
            kept.append(row)
        else:
            dropped.append((row, "不在白名单"))
    return kept, dropped


def parse_du(output: str) -> list[list[str]]:
    """把 du 的输出拆开。

    每行形如：`37908<TAB>/data/local/file-cache`
    返回：[['37908', '/data/local/file-cache'], ...]

    提示：这是"2 个字段"——和 parse_df 那个 6 字段是**同一个形状**，只是数字不一样。
    """
    lines = output.strip().splitlines()
    data = lines[:]

    rows = []
    for line in data:
        parts = line.split(None, 1)  # 最多切 1 刀 → 2 段
        rows.append(parts)
    return rows


def humanize(k: int) -> str:
    """把 K 变成人能读的单位：2048 → '2.0M'，1048576 → '1.0G'。

    判断的对象必须和显示的对象是同一个：
    1048570K 的"原始值"不到 1G，但它四舍五入后会显示成 1024.0M ——
    所以要先换算再判断，否则用户会看到"1024.0M"这种不存在的单位写法。
    """
    m = round(k / 1024, 1)  # 先算：它有多少 M（按将要显示的精度）
    if m >= 1024:  # 再判：这个显示值是不是已经够 1G 了
        return f"{k / 1024 ** 2:.1f}G"
    if k >= 1024:
        return f"{m:.1f}M"
    return f"{k}K"


def _key(path: str) -> str:
    """比较用的键：只剥前导 /，其余原样，做归一化处理。"""
    return path.lstrip("/")


def match(rows: list[list[str]], paths: list[str]) -> tuple[list, list]:
    """按清单匹配 df / du 的行。

    返回 (命中, 未命中)：
      命中   = [(path, row), ...]  —— 按 paths 里的顺序，方便和清单逐行对齐
      未命中 = [path, ...]         —— 清单里有、但数据里没找到的

    rows 每一条的"最后一列"就是路径。
    这一步的用途：它把"漏了哪几条"变成一个看得见的数字，而不是让人以为填满了。
    """
    hits, misses = [], []
    for path in paths:  # ① 按清单顺序走（顺序由需求决定）
        found = None
        for row in rows:  # ② 每条数据看一眼
            if _key(row[-1]) == _key(path):  # ③ 路径对上了
                found = row
                break  # ④ 找到就停，别重复计数
        if found is None:  # ⑤ 没找到
            misses.append(path)  # 空 A：这个 path 应该去哪个列表？
        else:
            hits.append((path, found))  # 空 B：hits 里每一项要长成什么形状？（看文档注释）
    return hits, misses


if __name__ == "__main__":
    # 离线模式：直接拿仓库里那份真实输出当输入
    with open("samples/df-h-ldplayer14.txt", encoding="utf-8") as f:
        text = f.read()

    rows = parse_df(text)
    print(f"一共 {len(rows)} 条记录\n")

    kept, dropped = pick(rows)
    print(f"进表 {len(kept)} 行：")
    for row in kept:
        print("  ", row)

    print(f"\n排除 {len(dropped)} 行（示例）：")
    for row, reason in dropped[:3]:
        print("  ", row[-1], "→", reason)
    print(f"  ……共 {len(dropped)} 行")
