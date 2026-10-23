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


def load_paths(file: str = "paths.example.txt") -> list[str]:
    """读路径清单：跳过注释行（以 # 开头）和空行，其余按原样返回，顺序不变。

    提示：这是"遍历 + 判断 + 放进列表"——你已经写过三次的形状。
    """
    paths = []
    with open(file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                paths.append(line)
    return paths


def growth(before_rows: list, after_rows: list) -> list:
    """按路径对齐"跑机前 / 跑机后"两次采集，算增长。

    参数是两次的命中行：`[[大小K, 路径], ...]`（可能只包含本阶段命中的行）。
    返回 `[(path, before_k, after_k, pct), ...]`，按 path 排序，方便和清单逐行对齐：

      两次都有    → pct = (after - before) / before * 100
                    **before == 0 时 pct = None**（不可计算，绝不出现 #DIV/0!）
      只有 before → after_k = None, pct = None（跑机后消失了）
      只有 after  → before_k = None, pct = None（跑机后新出现）

    提示：这是"两次数据按同一个键对齐"——你写过的 match() 是它的小号版本。
    ① 把 before 变成字典：{路径: 大小}
    ② 把 after  变成字典：{路径: 大小}
    ③ 路径全集 = 两边的键合起来（去重）
    ④ 按路径排序，逐条算：
     两边都有 → pct = (a - b) / b * 100；b == 0 时 pct = None
     只有 before → (path, b, None, None)
     只有 after  → (path, None, a, None)
    """
    # 1. 建字典
    before_dict = {}
    for row in before_rows:
        path = row[1]  # 取出路径
        size = int(row[0])  # 取出大小并转为整数
        before_dict[path] = size

    after_dict = {}
    for row in after_rows:
        path = row[1]
        size = int(row[0])
        after_dict[path] = size

    # 2. 取合集并排序
    all_paths = set(before_dict.keys()) | set(after_dict.keys())
    sorted_paths = sorted(all_paths)

    # 3. 核心计算逻辑
    result = []  # ① 准备一个空列表

    for path in sorted_paths:  # ② 你算好的排序路径，现在用上
        bk = before_dict.get(path)  # ③ 取两边的值（可能是 None）
        ak = after_dict.get(path)

        if bk is not None and ak is not None:
            if bk == 0:  # 两边都有
                result.append((path, bk, ak, None))
            else:
                pct = (ak - bk) / bk * 100
                result.append((path, bk, ak, pct))
        elif bk is not None:  # 只有 before：跑机后消失了
            result.append((path, bk, None, None))
        else:  # 只有 after：跑机后新出现
            result.append((path, None, ak, None))

    return result                      # ④ 最后返回
def usage(row: list[str]) -> tuple[int, int, float]:
    """从 `df -k` 的一行里算**真实**使用率。

    row 形如：['/dev/block/sdb2', '24170284', '182100', '23988184', '1%', '/system/...']
                                    total K      used K      avail K

    两条铁律（都是踩出来的）：
      1. **不要用 row[4] 的 Use%**——它是取整的（显示 1%，真实是 0.75%）。
      2. **不要用 row[-1] 判断这是哪个路径**——同一设备有多个挂载点时，df 可能
         返回另一条（/data 会显示成 /system/vendor/lib/arm/cpuinfo）。
    """
    total = int(row[1])
    used = int(row[2])
    pct = (used / total * 100) if total else 0.0
    return total, used, round(pct, 2)


def judge(pct: float, rated: float) -> str:
    """把使用率和"项目额定百分比"比，返回一句人话结论。

    ⚠️ 边界由你定：pct == rated 时算不算超标？定了就写进注释，别留模糊。
    """
    if pct > rated:
        return f"超额定（{pct:.2f}% > 额定 {rated:g}%）"
    return f"未超额定（{pct:.2f}% ≤ 额定 {rated:g}%）"


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


def top_n(rows: list[list[str]], n: int = 5) -> list[tuple[int, str]]:
    """按占用从大到小取前 n 条，返回 [(大小K, 路径), ...]。

    给调试用：一眼看出这台设备上哪个目录最占地方。

    三个新东西：
      int(row[0])        —— 字符串 "37908" 变数字 37908。不转的话，排序会按"字典序"：
                            "9" 比 "10" 大，因为它逐位比较字符。
      pairs.sort(key=..) —— key 是个函数，告诉它"拿每一项的哪一部分来比大小"。
      lambda p: p[0]     —— 一个没名字的小函数，等价于"给我 p，我还你 p[0]"。
    """
    pairs = []
    for row in rows:
        pairs.append((int(row[0]), row[1]))
    pairs.sort(key=lambda p: p[0], reverse=True)   # reverse=True = 从大到小
    return pairs[:n]


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
