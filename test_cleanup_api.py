#!/usr/bin/env python3
"""
测试RTK设备批量清理API的脚本
"""

import requests
import json

# 配置
API_BASE_URL = "http://localhost:8000"

def test_cleanup_all_api():
    """测试批量清理API"""
    print("测试RTK设备批量清理API...")
    
    try:
        # 首先获取当前设备列表
        print("1. 获取当前设备列表...")
        response = requests.get(f"{API_BASE_URL}/api/rtk/devices")
        if response.status_code == 200:
            devices = response.json()
            print(f"   当前设备数量: {len(devices)}")
            for device_id, device in devices.items():
                print(f"   - {device_id}: {device.get('name', 'N/A')} ({device.get('ip', 'N/A')})")
        else:
            print(f"   获取设备列表失败: {response.status_code}")
            return
        
        # 测试批量清理API
        print("\n2. 测试批量清理API...")
        response = requests.post(f"{API_BASE_URL}/api/rtk/devices/cleanup-all")
        
        print(f"   HTTP状态码: {response.status_code}")
        print(f"   响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get("success"):
                print("   ✅ 批量清理成功!")
            else:
                print(f"   ❌ 批量清理失败: {result.get('message', '未知错误')}")
        else:
            print(f"   ❌ API调用失败: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"   错误文本: {response.text}")
        
        # 再次获取设备列表验证清理结果
        print("\n3. 验证清理结果...")
        response = requests.get(f"{API_BASE_URL}/api/rtk/devices")
        if response.status_code == 200:
            devices_after = response.json()
            print(f"   清理后设备数量: {len(devices_after)}")
            if len(devices_after) == 0:
                print("   ✅ 所有设备已成功清理!")
            else:
                print("   ⚠️  仍有设备存在:")
                for device_id, device in devices_after.items():
                    print(f"     - {device_id}: {device.get('name', 'N/A')}")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确保后端服务在 http://localhost:8000 运行")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cleanup_all_api()
