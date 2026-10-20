# 样本说明

**这里的文件是"原始采集输出"，一个字节都不许改。**它们是解析器的靶子，也是以后 pytest 的数据源。

| 文件 | 来源 | 采集时间 | 采集身份 | 状态 |
|---|---|---|---|---|
| `df-h-ldplayer14.txt` | 雷电模拟器 14 | 2026-10-18 00:33 | `shell`（uid 2000） | 14 行数据；含宿主机的 C 盘挂载行 |
| `du-data.txt` | 雷电模拟器 14 | 2026-10-20 15:55 | **`root`（uid 0）** | 1732 行；**stderr 为空**（无 `Permission denied`） |

## 采集方式

```bat
adb -s emulator-5554 shell "df -h" > samples\df-h-ldplayer14.txt
adb -s emulator-5554 shell "du /data" > samples\du-data.txt 2> samples\du-data.err
```

**stdout 和 stderr 分开存**：stderr 非空就说明这批数字不可信。

## 已知事实

- `du /data` **默认输出的单位就是 K**（第一列是纯数字，没有 `G`/`M`/`K` 字符），所以不需要 `-k`、更不需要 `-h`。
- `du` 输出的路径**带前导 `/`**（`/data/fonts`），而内部表格的清单**不带**（`data/fonts`）→ 匹配前要归一化。
- `du /data` 会有 **1700+ 行**，而实际需要的清单只有几十条 → **白名单是必需的，不是优化**。

## 注意

- **权限差异**：`du` 样本是 `adb root` 之后采的。真实 release 设备没有 root，需要先完成内部授权（见 `NOTES.md` 第二节）——**这份样本能验证"格式"，不能验证"真实权限路径"。**
- `*.err` 文件是采集时的 stderr 快照，属于临时产物，不入库。
