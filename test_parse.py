"""第一个测试文件：拿真实数据 + 一条人造边界数据，验证 parse.py 的规矩。

跑：python -m pytest test_parse.py -v
"""

import parse

SAMPLE = open("samples/df-h-ldplayer14.txt", encoding="utf-8").read()


def test_row_count():
    """真实输出里有 14 条数据行（表头不算）。"""
    assert len(parse.parse_df(SAMPLE)) == 14


def test_each_row_has_six_fields():
    """每条记录都必须是 6 个字段，一个例外都不能有。"""
    assert {len(row) for row in parse.parse_df(SAMPLE)} == {6}


def test_whitelist_keeps_only_data():
    """白名单只留设备自己的存储：跑完筛完，只剩 /data 这一行。"""
    kept, _ = parse.pick(parse.parse_df(SAMPLE))
    assert [row[-1] for row in kept] == ["/data"]


def test_dropped_rows_have_reason():
    """被排除的行必须带原因，不能静默消失。"""
    _, dropped = parse.pick(parse.parse_df(SAMPLE))
    assert len(dropped) == 13
    assert all(reason for _, reason in dropped)


def test_mount_point_with_space():
    """人造边界：挂载点里带空格时，最后一列不能被切碎。

    模拟器的挂载点都没有空格，所以这条是唯一能测出 maxsplit 是否写对的用例。
    """
    fake = "Filesystem Size Used Avail Use% Mounted on\n"
    fake += "/dev/block/sdb2  23G  154M  22G  1%  /mnt/media_rw/My Disk"
    rows = parse.parse_df(fake)
    assert len(rows) == 1
    assert rows[0][-1] == "/mnt/media_rw/My Disk"


def test_humanize_basic():
    """常规值：单位换对了就行。"""
    assert parse.humanize(512) == "512K"
    assert parse.humanize(2048) == "2.0M"
    assert parse.humanize(1048576) == "1.0G"


def test_humanize_at_boundary():
    """边界值：1048570K = 1023.99M，四舍五入会显示成 1024.0M —— 必须进位成 G。

    这个用例是回归测试：它锁定"判断的对象必须等于显示的对象"这条规则。
    """
    assert parse.humanize(1048570) == "1.0G"
    # 差一点点、但四舍五入后仍然够进位的那个点
    assert parse.humanize(1048525) == "1.0G"
    # 再差一点就不该进位了（1023.9M）
    assert parse.humanize(1048524) == "1023.9M"


# ---------------------------------------------------------------
# 下面两条是"规格"，等你把 parse.match() 写出来让它们变绿
# ---------------------------------------------------------------

def test_match_counts_hits_and_misses():
    """清单 3 条、数据里只存在 2 条 → 命中 2，未命中 1（且名字对得上）。"""
    rows = parse.parse_df(SAMPLE)
    hits, misses = parse.match(rows, ["/data", "/dev", "/nope"])
    assert len(hits) == 2
    assert misses == ["/nope"]


def test_match_keeps_whole_row():
    """命中时要把整行原样带出来，不是只给路径。"""
    rows = parse.parse_df(SAMPLE)
    hits, misses = parse.match(rows, ["/data"])
    assert misses == []
    path, row = hits[0]
    assert path == "/data"
    assert len(row) == 6

# ---------------------------------------------------------------
# 第四格的规格：parse_du()（du 的输出 = 数值 + 路径，两段）
# ---------------------------------------------------------------

DU_SAMPLE = open("samples/du-data.txt", encoding="utf-8").read()


def test_parse_du_two_fields():
    """du 的每一行都必须拆成 2 段：数值 + 路径。"""
    rows = parse.parse_du(DU_SAMPLE)
    assert len(rows) > 1000
    assert {len(r) for r in rows} == {2}


def test_parse_du_value_is_digits():
    """第一段是纯数字（单位 K），不允许出现单位字符。"""
    rows = parse.parse_du(DU_SAMPLE)
    assert all(r[0].isdigit() for r in rows)


def test_parse_du_keeps_path_intact():
    """第二段是完整路径，保留前导 /（归一化是下一步的事，不是解析的事）。"""
    rows = parse.parse_du("37908\t/data/local/file-cache")
    assert rows[0] == ["37908", "/data/local/file-cache"]


# ---------------------------------------------------------------
# 第五格的规格：归一化（清单不带前导 /，du 输出带前导 /）
# ---------------------------------------------------------------

def test_match_normalizes_leading_slash():
    """清单写 `data/fonts`，数据里是 `/data/fonts` —— 也必须匹配上。

    注意：返回的 path 应该保持清单里的原样（data/fonts），不要偷偷改数据。
    """
    rows = parse.parse_du("100\t/data/fonts")
    hits, misses = parse.match(rows, ["data/fonts"])
    assert misses == []
    assert hits[0][0] == "data/fonts"


def test_match_still_exact_on_other_parts():
    """归一化只剥前导 /，不能把 `data/fonts` 和 `data/fonts/files` 混为一谈。"""
    rows = parse.parse_du("100\t/data/fonts/files")
    hits, misses = parse.match(rows, ["data/fonts"])
    assert hits == []
    assert misses == ["data/fonts"]

def test_key_strips_only_leading_slash():
    assert parse._key("/data/fonts") == "data/fonts"
    assert parse._key("data/fonts") == "data/fonts"
    assert parse._key("/data/log/") == "data/log/"     # 尾斜杠不动,归一化