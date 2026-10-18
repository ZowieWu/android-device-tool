"""第二格：把 df -h 的输出拆成一条条记录。

今天不需要模拟器：samples/ 里存着真实输出，离线就能开发。
两个空要你填——填对了，说明你真读懂了那份数据。
"""


def parse_df(output: str) -> list[list[str]]:
    """把 df -h 的输出拆开。

    返回：[['tmpfs', '2.9G', '1.3M', '2.9G', '1%', '/dev'], ...]
    每条记录必须是 6 个字段：Filesystem / Size / Used / Avail / Use% / Mounted on
    """
    lines = output.strip().splitlines()
    data = lines[1:]          # 空 A：表头那一行要不要算进数据？

    rows = []
    for line in data:
        parts = line.split(None, 5)   # 空 B：表头有几个词？数据行切几段才对？
        rows.append(parts)
    return rows


if __name__ == "__main__":
    # 离线模式：直接拿仓库里那份真实输出当输入
    with open("samples/df-h-ldplayer14.txt", encoding="utf-8") as f:
        text = f.read()

    rows = parse_df(text)
    print(f"一共 {len(rows)} 条记录")
    for row in rows:
        print(f"{len(row)} 段 | {row}")
