# Tap - 飞书多维表格CLI工具

Tap 是一个用于操作飞书多维表格的命令行工具。

## 功能特性

- **配置管理**: 支持配置 `APP_ID`、`APP_SECRET`、`app_token`
- **自动授权**: 配置后自动获取和刷新 `tenant_access_token`
- **字段校验**: `tap check` 命令校验文件字段与数据表字段是否匹配
- **数据同步**: `tap flush` 命令同步数据到飞书多维表格
- **双模式支持**: `field` 模式自动创建新字段，`record` 模式只处理记录

## 安装

```bash
pip install -e .
```

## 配置

在使用前需要配置飞书应用凭证：

```bash
tap config set APP_ID your_app_id
tap config set APP_SECRET your_app_secret
tap config set app_token your_app_token
```

查看当前配置：

```bash
tap config show
```

检查配置是否完整：

```bash
tap config check
```

## 使用方法

### 校验字段

校验文件中的字段是否与数据表中的字段相匹配：

```bash
tap check /path/to/file.xlsx --frozen-zone "A:F" --data-zone "G:Z" --table-id "tblxxx"
```

参数说明：
- `file_path`: Excel/CSV 文件路径
- `--frozen-zone`: 冻结区域列范围（默认: A:F）
- `--data-zone`: 数据区域列范围（默认: G:Z）
- `--table-id`: 数据表ID

### 同步数据

将数据同步到飞书多维表格：

```bash
# record模式（默认）：只处理记录的匹配、更新、创建
tap flush /path/to/file.xlsx --table-id "tblxxx"

# field模式：字段不存在先创建，再处理记录
flush "Tap/.trash/1-JTCBB_CBB04矿山企业产品综合成本构成表_merged.csv" --frozen-zone "A:F" --data-zone "G:Z" --table-id tbl3aVf0vW7hMZfi --mode recor
```

参数说明：
- `file_path`: Excel/CSV 文件路径
- `--frozen-zone`: 冻结区域列范围（默认: A:F）
- `--data-zone`: 数据区域列范围（默认: G:Z）
- `--table-id`: 数据表ID
- `--mode`: 同步模式（默认: record）
  - `field`: 字段不存在先创建
  - `record`: 只处理记录

### 数据ID规则

数据ID用于唯一标识一条记录，格式为：

```
数据ID = 企业ID + "_" + 数据集 + 会计期间 + 报表类型
```

## 项目结构

```
tap/
├── __init__.py       # 包初始化
├── cli.py            # CLI入口
├── config.py         # 配置管理
├── client.py         # 飞书API客户端
├── commands.py       # 命令实现
└── reader.py         # Excel/CSV文件读取
```

## API封装

本项目封装了飞书多维表格的核心API：

### 字段API
- `get_fields()`: 获取字段列表
- `get_field()`: 获取字段详情
- `create_field()`: 创建字段
- `update_field()`: 更新字段
- `delete_field()`: 删除字段

### 记录API
- `get_records()`: 获取记录列表
- `get_record()`: 获取单条记录
- `create_record()`: 创建记录
- `create_records()`: 批量创建记录
- `update_record()`: 更新记录
- `update_records()`: 批量更新记录
- `delete_record()`: 删除记录
- `delete_records()`: 批量删除记录

实际例子
```bash
tap flush ".trash/1-JTCBB_CBB04矿山企业产品综合成本构成表_merged.csv" --frozen-zone "0:4" --data-zone "5:184" --table-id tbl3aVf0vW7hMZfi --mode field
tap flush ".trash/1-JTCBB_CBB04矿山企业产品综合成本构成表_merged.csv" --frozen-zone "0:4" --data-zone "185:364" --table-id tblzO8gbUedihy45 --mode field
tap flush ".trash/2-JTCBB_CBB02矿山作业成本项目构成表_merged.csv" --frozen-zone "0:4" --data-zone "5:220" --table-id tble0lofFXXNBv8d --mode field        # 同名问题
tap flush ".trash/2-JTCBB_CBB02矿山作业成本项目构成表_merged.csv" --frozen-zone "0:4" --data-zone "221:364" --table-id tblKjkqskINE6Byp --mode field      # 同名问题
tap flush ".trash/2-JTCBB_CBB02矿山作业成本项目构成表_merged.csv" --frozen-zone "0:4" --data-zone "365:604" --table-id tblUhWnY49ubqMYg --mode field
tap flush ".trash/2-JTCBB_CBB02矿山作业成本项目构成表_merged.csv" --frozen-zone "0:4" --data-zone "605:796" --table-id tblxUjM9HNsX94Cg --mode field
tap flush ".trash/2-JTCBB_CBB02矿山作业成本项目构成表_merged.csv" --frozen-zone "0:4" --data-zone "797:940" --table-id tblCNvFgxa12SKWM --mode field
tap flush ".trash/2-JTCBB_CBB02矿山作业成本项目构成表_merged.csv" --frozen-zone "0:4" --data-zone "941:1228" --table-id tblZEX7HaZCtiuvd --mode field
tap flush ".trash/2-JTCBB_CBB02矿山作业成本项目构成表_merged.csv" --frozen-zone "0:4" --data-zone "1229:1348" --table-id tbl4PEjGgITNRmB9 --mode field
tap flush ".trash/3-JTCBB_CBB03矿山成本要素表_merged.csv" --frozen-zone "0:4" --data-zone "5:256" --table-id tbl9rMAai8vmd2M0 --mode field
tap flush ".trash/3-JTCBB_CBB03矿山成本要素表_merged.csv" --frozen-zone "0:4" --data-zone "257:466" --table-id tblUnCVXrJnZLt0A --mode field
tap flush ".trash/3-JTCBB_CBB03矿山成本要素表_merged.csv" --frozen-zone "0:4" --data-zone "467:746" --table-id tblJPzGYdjCGIGMM --mode field
tap flush ".trash/4-JTCBB_CBB05矿山企业制造费用明细表_merged.csv" --frozen-zone "0:4" --data-zone "5:276" --table-id tblA2DvdA5e9bTdS --mode field
tap flush ".trash/4-JTCBB_CBB05矿山企业制造费用明细表_merged.csv" --frozen-zone "0:4" --data-zone "277:452" --table-id tblA4hCXmqf0Zcu0 --mode field
tap flush ".trash/4-JTCBB_CBB05矿山企业制造费用明细表_merged.csv" --frozen-zone "0:4" --data-zone "453:708" --table-id tbl6xtJP63orQPSF --mode field
tap flush ".trash/4-JTCBB_CBB05矿山企业制造费用明细表_merged.csv" --frozen-zone "0:4" --data-zone "709:932" --table-id tblmzGZLnPAl6kzX --mode field      # 同名问题
tap flush ".trash/5-JTCBB_CBB07定额材料、动力消耗统计表_merged.csv" --frozen-zone "0:4" --data-zone "5:244" --table-id tblqacZcc0ehXI2C --mode field
tap flush ".trash/5-JTCBB_CBB07定额材料、动力消耗统计表_merged.csv" --frozen-zone "0:4" --data-zone "245:340" --table-id tbl32l0sTJoTYg9Y --mode field
tap flush ".trash/5-JTCBB_CBB07定额材料、动力消耗统计表_merged.csv" --frozen-zone "0:4" --data-zone "341:652" --table-id tblGE1A2E6ZvsH6W --mode field    # 同名问题
tap flush ".trash/5-JTCBB_CBB07定额材料、动力消耗统计表_merged.csv" --frozen-zone "0:4" --data-zone "653:748" --table-id tblMG0xm33aVMMaF --mode field
tap flush ".trash/5-JTCBB_CBB07定额材料、动力消耗统计表_merged.csv" --frozen-zone "0:4" --data-zone "749:988" --table-id tblASzmARuavuWSO --mode field    # 同名问题
tap flush ".trash/5-JTCBB_CBB07定额材料、动力消耗统计表_merged.csv" --frozen-zone "0:4" --data-zone "989:1132" --table-id tbl9KhZ7VlSe5rGG --mode field
```

## License

MIT
