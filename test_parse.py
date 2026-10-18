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
