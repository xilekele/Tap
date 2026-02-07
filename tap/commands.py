"""命令模块"""

import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from .config import get_config
from .client import get_client
from .reader import get_reader

# 请求间隔配置（秒）
REQUEST_INTERVAL = 0.2  # 每次请求间隔0.2秒


class CheckCommand:
    """校验命令"""
    
    def __init__(self, file_path: str, frozen_zone: str, data_zone: str, table_id: str):
        self.file_path = Path(file_path)
        self.frozen_zone = frozen_zone
        self.data_zone = data_zone
        self.table_id = table_id
        
        self.config = get_config()
        self.client = get_client(self.config)
        self.reader = get_reader(file_path, frozen_zone, data_zone)
    
    def run(self) -> bool:
        """执行校验"""
        try:
            # 检查配置
            if not self.config.is_configured():
                raise Exception("请先配置APP_ID和APP_SECRET")
            
            if not self.config.app_token:
                raise Exception("请先配置app_token")
            
            # 读取文件表头
            file_headers = self.reader.read_headers()
            frozen_headers = self.reader.read_frozen_headers()
            
            # 获取飞书表格字段
            bitable_fields = self.client.get_fields(self.config.app_token, self.table_id)
            bitable_field_names = {f.get("field_name") for f in bitable_fields}
            
            # 校验数据区域字段
            errors = []
            for i, header in enumerate(file_headers):
                # 兼容ExcelReader和CSVReader
                data_start = getattr(self.reader, '_data_cols', getattr(self.reader, 'data_cols', (0, 0)))[0]
                col_letter = chr(ord('A') + i + data_start)
                if header and header not in bitable_field_names:
                    errors.append({
                        "type": "field_missing",
                        "location": f"{col_letter}1",
                        "field": header,
                        "message": f"字段 '{header}' 在数据表中不存在"
                    })
            
            # 校验冻结区域字段（用于数据ID）
            for header in frozen_headers:
                if header and header not in bitable_field_names:
                    errors.append({
                        "type": "field_missing",
                        "location": f"冻结区域",
                        "field": header,
                        "message": f"冻结区域字段 '{header}' 在数据表中不存在"
                    })
            
            if errors:
                print("❌ 校验失败，发现以下问题：\n")
                for error in errors:
                    print(f"  [{error['type']}] {error['location']}: {error['message']}")
                return False
            else:
                print("✅ 校验通过，所有字段都匹配")
                return True
                
        except Exception as e:
            print(f"❌ 校验失败: {e}")
            return False


class FlushCommand:
    """同步命令"""
    
    def __init__(self, file_path: str, frozen_zone: str, data_zone: str, 
                 table_id: str, mode: str = "record"):
        self.file_path = Path(file_path)
        self.frozen_zone = frozen_zone
        self.data_zone = data_zone
        self.table_id = table_id
        self.mode = mode  # "field" or "record"
        
        self.config = get_config()
        self.client = get_client(self.config)
        self.reader = get_reader(file_path, frozen_zone, data_zone)
    
    def _generate_data_id(self, frozen_data: Dict[str, Any]) -> str:
        """生成数据ID
        数据ID = 企业ID + _ + 数据集 + 会计期间 + 报表类型
        """
        def to_str(value):
            """安全转换为字符串"""
            if value is None:
                return ""
            if isinstance(value, list):
                return ",".join(str(v) for v in value)
            return str(value)
        
        enterprise_id = to_str(frozen_data.get("企业ID"))
        dataset = to_str(frozen_data.get("数据集"))
        period = to_str(frozen_data.get("会计期间"))
        report_type = to_str(frozen_data.get("报表类型"))
        
        return f"{enterprise_id}_{dataset}{period}{report_type}"
    
    def run(self) -> Tuple[bool, Dict]:
        """执行同步"""
        try:
            # 检查配置
            if not self.config.is_configured():
                raise Exception("请先配置APP_ID和APP_SECRET")
            
            if not self.config.app_token:
                raise Exception("请先配置app_token")
            
            # 读取文件数据
            frozen_headers = self.reader.read_frozen_headers()
            data_headers = self.reader.read_headers()
            frozen_data_list = self.reader.read_frozen_data()
            data_rows = self.reader.read_data()
            
            # 获取飞书表格字段
            bitable_fields = self.client.get_fields(self.config.app_token, self.table_id)
            bitable_field_map = {f.get("field_name"): f for f in bitable_fields}
            
            # field模式：检查并创建缺失的字段
            if self.mode == "field":
                # 获取飞书表格中所有关联字段
                link_fields = set()
                for field in bitable_fields:
                    if field.get("type") == 21:  # 关联类型
                        link_fields.add(field.get("field_name"))
                
                # 收集所有缺失的字段，批量创建
                missing_fields = []
                for header in data_headers:
                    if header and header not in bitable_field_map and header not in link_fields:
                        missing_fields.append({
                            "field_name": header,
                            "type": 1  # 文本类型
                        })
                    elif header and header in link_fields:
                        print(f"⚠️  字段 '{header}' 是关联字段，需要手动配置")
                
                # 批量创建缺失的字段
                if missing_fields:
                    print(f"⚠️  发现 {len(missing_fields)} 个新字段，批量创建中...")
                    self.client.create_fields(
                        self.config.app_token, 
                        self.table_id, 
                        missing_fields
                    )
                    print(f"✅ 成功创建 {len(missing_fields)} 个字段")
                
                # 刷新字段列表
                bitable_fields = self.client.get_fields(self.config.app_token, self.table_id)
                bitable_field_map = {f.get("field_name"): f for f in bitable_fields}
            
            # 获取飞书表格现有记录
            existing_records = self.client.get_records(self.config.app_token, self.table_id)
            time.sleep(REQUEST_INTERVAL)  # 请求间隔
            
            # 收集特殊类型字段信息
            # type=18: 日期时间, type=21: 关联, type=3: 单选, type=5: 多选等
            special_field_names = set()  # 需要跳过的字段（不传给API）
            single_link_fields = {}  # 单项关联字段: field_name -> {table_id, field_name}
            
            for field in bitable_fields:
                field_type = field.get("type")
                field_name = field.get("field_name")
                field_property = field.get("property") or {}
                
                # 如果有 table_id 属性，则是关联字段（飞书 API 有时 type 不准确）
                if field_property and field_property.get("table_id"):
                    if not field_property.get("multiple"):
                        # 单项关联 - 需要特殊处理
                        single_link_fields[field_name] = {
                            "table_id": field_property.get("table_id"),
                            "link_field_name": field_property.get("field_name")  # 关联表中的字段名
                        }
                    else:
                        # 多项关联 - 跳过
                        special_field_names.add(field_name)
                elif field_type == 21:  # 标准关联类型
                    if field_property and (field_property.get("relation_type") == "one" or not field_property.get("multiple")):
                        single_link_fields[field_name] = field_property
                    else:
                        special_field_names.add(field_name)
                # type=18（日期时间）不再默认跳过，飞书API可能返回不准确的类型
            
            # 构建数据ID到记录的映射
            # 数据ID存储在某个字段中，假设字段名为"数据ID"
            def to_str(value):
                """安全转换为字符串"""
                if value is None:
                    return ""
                if isinstance(value, list):
                    return ",".join(str(v) for v in value)
                return str(value)
            
            record_map = {}
            for record in existing_records:
                fields = record.get("fields", {})
                data_id = fields.get("数据ID")
                if data_id:
                    record_map[to_str(data_id)] = record
            
            # 构建关联表查找缓存 {table_id: {字段值: record_id}}
            link_cache = {}
            # CSV字段名 -> 关联表字段名 的映射
            field_name_mapping = {
                "企业简称": "企业",  # 企业简称 对应 关联表的"企业"字段
            }
            
            if single_link_fields:
                print(f"ℹ️  发现 {len(single_link_fields)} 个单项关联字段，开始构建查找缓存...")
                for field_name, link_info in single_link_fields.items():
                    link_table_id = link_info.get("table_id")
                    # 使用映射规则，否则使用原始字段名
                    link_field = field_name_mapping.get(field_name, field_name)
                    
                    if link_table_id and link_table_id not in link_cache:
                        # 获取关联表的所有记录
                        try:
                            link_records = self.client.get_records(self.config.app_token, link_table_id)
                            # 构建 {字段值: record_id} 映射
                            link_cache[link_table_id] = {}
                            for rec in link_records:
                                rec_fields = rec.get("fields", {})
                                link_value = rec_fields.get(link_field)
                                if link_value:
                                    link_cache[link_table_id][str(link_value)] = rec.get("record_id")
                            print(f"  ✓ 关联表 {link_table_id} ({link_field}): {len(link_cache[link_table_id])} 条记录")
                        except Exception as e:
                            print(f"  ✗ 获取关联表 {link_table_id} 失败: {e}")
            
            # 统计
            stats = {
                "total": len(data_rows),
                "created": 0,
                "updated": 0,
                "unchanged": 0,
                "errors": 0
            }
            
            # 收集需要批量处理的数据
            to_create = []  # 需要新建的记录 [{fields: {...}}, ...]
            to_update = []  # 需要更新的记录 [{record_id: ..., fields: {...}}, ...]
            to_create_ids = []  # 新建记录的数据ID，用于后续关联字段更新
            to_update_ids = []  # 更新记录的数据ID，用于后续关联字段更新
            
            # 第一遍：收集所有需要创建和更新的记录（不含关联字段）
            for i, (frozen_data, data_row) in enumerate(zip(frozen_data_list, data_rows)):
                try:
                    data_id = self._generate_data_id(frozen_data)
                    
                    # 合并冻结区域和数据区域的数据
                    merged_fields = {}
                    merged_fields.update(frozen_data)
                    merged_fields.update(data_row)
                    
                    # 添加数据ID
                    merged_fields["数据ID"] = data_id
                    
                    # 过滤掉特殊类型字段（日期时间等），保留关联字段尝试写入
                    filtered_fields = {k: v for k, v in merged_fields.items() if k not in special_field_names}
                    
                    # 转换数字类型字段
                    for field_name, field_info in bitable_field_map.items():
                        if field_name in filtered_fields and field_info.get("type") == 2:  # 数字类型
                            value = filtered_fields[field_name]
                            if value is not None and value != "":
                                try:
                                    filtered_fields[field_name] = float(value)
                                except (ValueError, TypeError):
                                    pass  # 转换失败保持原值
                    
                    # 处理单项关联字段 - 先记录下来
                    link_field_values = {}
                    for field_name, link_info in single_link_fields.items():
                        csv_field_name = field_name
                        if csv_field_name in merged_fields:
                            link_value = str(merged_fields[csv_field_name])
                        elif field_name in merged_fields:
                            link_value = str(merged_fields[field_name])
                        else:
                            continue
                        
                        link_table_id = link_info.get("table_id")
                        if link_table_id and link_value and link_table_id in link_cache:
                            record_id = link_cache[link_table_id].get(link_value)
                            if record_id:
                                link_field_values[field_name] = [record_id]
                    
                    # 过滤掉关联字段（不含在第一批创建/更新中）
                    create_fields = {k: v for k, v in filtered_fields.items() if k not in single_link_fields}
                    
                    if data_id in record_map:
                        # 记录已存在，检查是否需要更新
                        existing_record = record_map[data_id]
                        existing_fields = existing_record.get("fields", {})
                        
                        def value_to_str(v):
                            """安全转换为字符串"""
                            if v is None:
                                return ""
                            if isinstance(v, list):
                                return ",".join(str(x) for x in v)
                            return str(v)
                        
                        needs_update = False
                        for key, value in merged_fields.items():
                            if key in existing_fields and key not in single_link_fields:
                                existing_value = existing_fields[key]
                                if value_to_str(value) != value_to_str(existing_value):
                                    needs_update = True
                                    break
                        
                        if needs_update:
                            to_update.append({
                                "record_id": existing_record.get("record_id"),
                                "fields": create_fields
                            })
                            to_update_ids.append({
                                "data_id": data_id,
                                "link_field_values": link_field_values,
                                "record_id": existing_record.get("record_id")
                            })
                        else:
                            stats["unchanged"] += 1
                    else:
                        # 新记录
                        to_create.append({"fields": create_fields})
                        to_create_ids.append({
                            "data_id": data_id,
                            "link_field_values": link_field_values
                        })
                        
                except Exception as e:
                    stats["errors"] += 1
                    print(f"❌ 处理第 {i+1} 行失败: {e}")
            
            # 批量新建记录
            if to_create:
                # 批量创建，每次最多500条
                batch_size = 500
                for i in range(0, len(to_create), batch_size):
                    batch = to_create[i:i+batch_size]
                    batch_info = to_create_ids[i:i+batch_size]
                    
                    try:
                        result = self.client.create_records(
                            self.config.app_token,
                            self.table_id,
                            batch
                        )
                        # 获取批量创建返回的 record_id 列表
                        created_records = result.get("records", [])
                        created_count = len(created_records)
                        stats["created"] += created_count
                        print(f"➕ 批量新建 {created_count} 条记录")
                        
                        # 批量更新关联字段（使用批量创建返回的 record_id）
                        for j, info in enumerate(batch_info):
                            if j < len(created_records) and info["link_field_values"]:
                                record_id = created_records[j].get("record_id")
                                for field_name, link_id in info["link_field_values"].items():
                                    try:
                                        self.client.update_record(
                                            self.config.app_token,
                                            self.table_id,
                                            record_id,
                                            {field_name: link_id}
                                        )
                                    except Exception as e:
                                        print(f"  ⚠️  更新关联 '{field_name}' 失败: {e}")
                                        
                    except Exception as e:
                        print(f"❌ 批量创建失败: {e}")
                        # 回退到单条创建
                        for j, (record, info) in enumerate(zip(batch, batch_info)):
                            try:
                                new_record = self.client.create_record(
                                    self.config.app_token,
                                    self.table_id,
                                    record["fields"]
                                )
                                stats["created"] += 1
                                print(f"➕ 新建记录: {info['data_id']}")
                                
                                # 更新关联字段
                                for field_name, link_id in info["link_field_values"].items():
                                    try:
                                        self.client.update_record(
                                            self.config.app_token,
                                            self.table_id,
                                            new_record.get("record_id"),
                                            {field_name: link_id}
                                        )
                                    except Exception as e:
                                        print(f"  ⚠️  更新关联 '{field_name}' 失败: {e}")
                            except Exception as e:
                                print(f"❌ 创建记录 {info['data_id']} 失败: {e}")
            
            # 批量更新记录
            if to_update:
                # 批量更新，每次最多500条
                batch_size = 500
                for i in range(0, len(to_update), batch_size):
                    batch = to_update[i:i+batch_size]
                    batch_info = to_update_ids[i:i+batch_size]
                    
                    try:
                        self.client.update_records(
                            self.config.app_token,
                            self.table_id,
                            batch
                        )
                        updated_count = len(batch)
                        stats["updated"] += updated_count
                        print(f"🔄 批量更新 {updated_count} 条记录")
                        
                        # 批量更新关联字段
                        for info in batch_info:
                            if info["link_field_values"]:
                                for field_name, link_id in info["link_field_values"].items():
                                    try:
                                        self.client.update_record(
                                            self.config.app_token,
                                            self.table_id,
                                            info["record_id"],
                                            {field_name: link_id}
                                        )
                                    except Exception as e:
                                        print(f"  ⚠️  更新关联 '{field_name}' 失败: {e}")
                                        
                    except Exception as e:
                        print(f"❌ 批量更新失败: {e}")
                        # 回退到单条更新
                        for j, (record, info) in enumerate(zip(batch, batch_info)):
                            try:
                                self.client.update_record(
                                    self.config.app_token,
                                    self.table_id,
                                    record["record_id"],
                                    record["fields"]
                                )
                                stats["updated"] += 1
                                print(f"🔄 更新记录: {info['data_id']}")
                                
                                # 更新关联字段
                                for field_name, link_id in info["link_field_values"].items():
                                    try:
                                        self.client.update_record(
                                            self.config.app_token,
                                            self.table_id,
                                            info["record_id"],
                                            {field_name: link_id}
                                        )
                                    except Exception as e:
                                        print(f"  ⚠️  更新关联 '{field_name}' 失败: {e}")
                            except Exception as e:
                                print(f"❌ 更新记录 {info['data_id']} 失败: {e}")
            
            # 输出统计
            print(f"\n📊 同步完成:")
            print(f"   总记录数: {stats['total']}")
            print(f"   新建: {stats['created']}")
            print(f"   更新: {stats['updated']}")
            print(f"   跳过: {stats['unchanged']}")
            print(f"   错误: {stats['errors']}")
            
            return True, stats
            
        except Exception as e:
            import traceback
            print(f"❌ 同步失败: {e}")
            traceback.print_exc()
            return False, {}
