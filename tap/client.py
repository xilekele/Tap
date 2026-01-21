"""飞书API客户端模块"""

import time
import requests
from typing import Optional, Dict, Any, List
from .config import get_config

# API基础地址
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

class FeishuClient:
    """飞书API客户端"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def _get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        # 检查是否已有有效的token
        if self.config.tenant_access_token and self.config.tenant_access_token_expires_at:
            if time.time() < self.config.tenant_access_token_expires_at:
                return self.config.tenant_access_token
        
        # 获取新的token
        url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.config.app_id,
            "app_secret": self.config.app_secret
        }
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"获取token失败: {data.get('msg')}")
        
        # 保存token和过期时间
        self.config.tenant_access_token = data.get("tenant_access_token")
        self.config.tenant_access_token_expires_at = int(time.time()) + data.get("expire", 7200) - 60
        self.config.save()
        
        return self.config.tenant_access_token
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送API请求"""
        token = self._get_tenant_access_token()
        url = f"{FEISHU_API_BASE}{endpoint}"
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        
        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                raise Exception(f"API路径不存在: {endpoint}\n可能原因: 1)应用缺少多维表格权限 2)应用未在企业内安装 3)app_token不正确")
            raise Exception(f"HTTP错误: {e}")
        except Exception as e:
            raise Exception(f"请求错误: {e}")
        
        if data.get("code") != 0:
            raise Exception(f"API请求失败: {data.get('msg')}")
        
        return data.get("data", {})
    
    # ==================== 应用级API ====================
    
    def get_app_info(self) -> Dict[str, Any]:
        """获取应用信息"""
        return self._request("GET", "/app/v1/info")
    
    # ==================== 多维表格基础API ====================
    
    def get_bitable_list(self, page_size: int = 50) -> List[Dict]:
        """获取多维表格列表"""
        items = []
        page_token = None
        
        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            
            data = self._request("GET", "/bitable/v1/apps", params=params)
            
            # 安全获取items
            page_items = data.get("items")
            if page_items is not None:
                items.extend(page_items)
            
            # 检查是否还有更多数据
            has_more = data.get("has_more", False)
            if not has_more:
                break
            
            page_token = data.get("page_token")
            if not page_token:
                break
        
        return items
    
    def get_bitable(self, app_token: str) -> Dict[str, Any]:
        """获取多维表格信息"""
        return self._request("GET", f"/bitable/v1/apps/{app_token}")
    
    # ==================== 表API ====================
    
    def get_tables(self, app_token: str) -> List[Dict]:
        """获取数据表列表"""
        data = self._request("GET", f"/bitable/v1/apps/{app_token}/tables")
        return data.get("items", [])
    
    def get_table(self, app_token: str, table_id: str) -> Dict[str, Any]:
        """获取数据表信息"""
        return self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}")
    
    # ==================== 字段API ====================
    
    def get_fields(self, app_token: str, table_id: str) -> List[Dict]:
        """获取字段列表"""
        items = []
        page_token = None
        
        while True:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token
            
            data = self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields", params=params)
            
            # 安全获取items，处理可能为null的情况
            page_items = data.get("items")
            if page_items is not None:
                items.extend(page_items)
            
            # 检查是否还有更多数据
            has_more = data.get("has_more", False)
            if not has_more:
                break
            
            page_token = data.get("page_token")
            if not page_token:
                break
        
        return items
    
    def get_field(self, app_token: str, table_id: str, field_id: str) -> Dict[str, Any]:
        """获取字段详情"""
        return self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}")
    
    def create_field(self, app_token: str, table_id: str, field_name: str, field_type: str, 
                     options: Optional[Dict] = None) -> Dict[str, Any]:
        """创建字段"""
        payload = {
            "field_name": field_name,
            "type": int(field_type),
        }
        if options:
            payload["property"] = options

        return self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields", json=payload)
    
    def update_field(self, app_token: str, table_id: str, field_id: str, 
                     field_name: Optional[str] = None, options: Optional[Dict] = None) -> Dict[str, Any]:
        """更新字段"""
        payload = {}
        if field_name:
            payload["field_name"] = field_name
        if options:
            payload["property"] = options
        
        return self._request("PUT", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}", json=payload)
    
    def delete_field(self, app_token: str, table_id: str, field_id: str) -> Dict[str, Any]:
        """删除字段"""
        return self._request("DELETE", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}")
    
    # ==================== 记录API ====================
    
    def get_records(self, app_token: str, table_id: str, 
                    field_names: Optional[List[str]] = None,
                    page_size: int = 500) -> List[Dict]:
        """获取记录列表"""
        items = []
        page_token = None
        
        while True:
            params = {"page_size": min(page_size, 500)}
            if page_token:
                params["page_token"] = page_token
            if field_names:
                params["field_names"] = ",".join(field_names)
            
            data = self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records", params=params)
            
            # 安全获取items
            page_items = data.get("items")
            if page_items is not None:
                items.extend(page_items)
            
            # 检查是否还有更多数据
            has_more = data.get("has_more", False)
            if not has_more:
                break
            
            page_token = data.get("page_token")
            if not page_token:
                break
        
        return items
    
    def get_record(self, app_token: str, table_id: str, record_id: str) -> Dict[str, Any]:
        """获取单条记录"""
        return self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}")
    
    def create_record(self, app_token: str, table_id: str, fields: Dict[str, Any],
                      uuid: Optional[str] = None) -> Dict[str, Any]:
        """创建记录"""
        payload = {"fields": fields}
        if uuid:
            payload["uuid"] = uuid
        
        result = self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records", json=payload)
        # 返回 record_id 而不是完整对象
        if result and "record" in result:
            return result["record"]
        return result
    
    def create_records(self, app_token: str, table_id: str, records: List[Dict],
                       uuid_key: Optional[str] = None) -> Dict[str, Any]:
        """批量创建记录"""
        payload = {"records": records}
        if uuid_key:
            payload["uuid_key"] = uuid_key
        
        return self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create", json=payload)
    
    def update_record(self, app_token: str, table_id: str, record_id: str, 
                      fields: Dict[str, Any]) -> Dict[str, Any]:
        """更新记录"""
        payload = {"fields": fields}

        return self._request("PUT", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}", json=payload)
    
    def update_records(self, app_token: str, table_id: str, records: List[Dict]) -> Dict[str, Any]:
        """批量更新记录"""
        payload = {"records": records}
        return self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update", json=payload)
    
    def delete_record(self, app_token: str, table_id: str, record_id: str) -> Dict[str, Any]:
        """删除记录"""
        return self._request("DELETE", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}")
    
    def delete_records(self, app_token: str, table_id: str, record_ids: List[str]) -> Dict[str, Any]:
        """批量删除记录"""
        payload = {"records": [{"record_id": rid} for rid in record_ids]}
        return self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete", json=payload)
    
    def batch_get_records(self, app_token: str, table_id: str, 
                          record_ids: List[str]) -> Dict[str, Any]:
        """批量获取记录"""
        params = {"record_ids": ",".join(record_ids)}
        return self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_get", params=params)

# 全局客户端实例
_client: Optional[FeishuClient] = None
_client_config_id: Optional[int] = None

def get_client(config=None) -> FeishuClient:
    """获取全局客户端实例"""
    global _client, _client_config_id
    config_id = id(config) if config else None
    
    # 如果没有传入config或者config id不匹配，创建新实例
    if _client is None or _client_config_id != config_id:
        _client = FeishuClient(config)
        _client_config_id = config_id
    return _client

def reset_client():
    """重置客户端"""
    global _client
    _client = None
