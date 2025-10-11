import socket
import threading
import time
import logging
import json
import struct
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RTKController:
    """RTK设备控制器类，用于管理多个RTK设备的连接和数据"""
    
    def __init__(self):
        """初始化RTK控制器"""
        # RTK设备列表
        self.devices = {}
        
        # 默认UDP监听端口
        self.udp_port = 60001  # 修改端口值
        
        # 数据存储
        self.device_data = {}
        self.device_records = {}
        
        # 连接状态和最后接收时间
        self.device_status = {}
        self.last_data_time = {}
        
        # 线程控制
        self.running = False
        self.listen_thread = None
        self.status_lock = threading.Lock()
        
        # 未注册设备数据临时存储（按IP地址索引）
        self.unregistered_ips = {}
        
        # 注意：移除了默认设备的注册
    
    def register_device(self, device_id: str, ip_address: str, name: str = None, device_info: str = None) -> Dict:
        """注册新的RTK设备"""
        if not name:
            name = f"RTK设备_{device_id}"
            
        # 解析额外的设备信息
        extra_info = {}
        if device_info:
            try:
                import json
                extra_info = json.loads(device_info)
            except Exception as e:
                logger.warning(f"解析设备信息时出错: {e}")
            
        with self.status_lock:
            self.devices[device_id] = {
                "id": device_id,
                "ip": ip_address,
                "name": name,
                "description": f"RTK定位设备 {name}",
                "recording": False,
                "isBaseStation": extra_info.get("isBaseStation", False),
                "deviceNumber": extra_info.get("deviceNumber", ""),
                "showIn3D": extra_info.get("showIn3D", True)
            }
            
            self.device_data[device_id] = {
                "timestamp": 0,
                "e": 0.0,
                "n": 0.0,
                "u": 0.0
            }
            
            self.device_status[device_id] = False
            self.last_data_time[device_id] = 0
            self.device_records[device_id] = []
            
            # 检查是否有来自该IP的未注册数据，如果有则更新状态并清理
            if ip_address in self.unregistered_ips:
                logger.info(f"发现IP {ip_address} 的未注册数据，更新设备 {device_id} 状态")
                data = self.unregistered_ips[ip_address]
                self.device_data[device_id] = data["data"]
                self.device_status[device_id] = True
                self.last_data_time[device_id] = data["time"]
                
                # 从未注册列表中移除（避免重复显示）
                del self.unregistered_ips[ip_address]
                logger.info(f"已从未注册列表中移除IP {ip_address}")
            
        return {"success": True, "message": f"已注册RTK设备: {name}"}
    
    def cleanup_device(self, device_id: str) -> Dict:
        """清理设备状态，为重新注册做准备"""
        try:
            with self.status_lock:
                if device_id in self.devices:
                    device_ip = self.devices[device_id]["ip"]
                    
                    # 将设备信息移回未注册列表，以便重新扫描
                    if device_id in self.device_data:
                        self.unregistered_ips[device_ip] = {
                            "time": self.last_data_time.get(device_id, time.time()),
                            "device_id": device_id,
                            "sender_ip": device_ip,
                            "data_packet_ip": device_ip,
                            "data": self.device_data[device_id]
                        }
                    
                    # 清理设备数据
                    del self.devices[device_id]
                    if device_id in self.device_data:
                        del self.device_data[device_id]
                    if device_id in self.device_status:
                        del self.device_status[device_id]
                    if device_id in self.last_data_time:
                        del self.last_data_time[device_id]
                    if device_id in self.device_records:
                        del self.device_records[device_id]
                    
                    logger.info(f"已清理设备 {device_id}，IP {device_ip} 已移回未注册列表")
                    return {"success": True, "message": f"已清理设备: {device_id}"}
                else:
                    return {"success": False, "message": f"设备 {device_id} 不存在"}
        except Exception as e:
            logger.error(f"清理设备失败: {e}")
            return {"success": False, "message": f"清理设备失败: {str(e)}"}

    def cleanup_all_devices(self) -> Dict:
        """清理所有设备状态，为重新注册做准备"""
        try:
            with self.status_lock:
                device_count = len(self.devices)
                if device_count == 0:
                    return {"success": True, "message": "没有需要清理的设备"}
                
                # 获取所有设备ID的副本，避免在迭代过程中修改字典
                device_ids = list(self.devices.keys())
                cleaned_count = 0
                
                for device_id in device_ids:
                    if device_id in self.devices:
                        device_ip = self.devices[device_id]["ip"]
                        
                        # 将设备信息移回未注册列表，以便重新扫描
                        if device_id in self.device_data:
                            self.unregistered_ips[device_ip] = {
                                "time": self.last_data_time.get(device_id, time.time()),
                                "device_id": device_id,
                                "sender_ip": device_ip,
                                "data_packet_ip": device_ip,
                                "data": self.device_data[device_id]
                            }
                        
                        # 清理设备数据
                        del self.devices[device_id]
                        if device_id in self.device_data:
                            del self.device_data[device_id]
                        if device_id in self.device_status:
                            del self.device_status[device_id]
                        if device_id in self.last_data_time:
                            del self.last_data_time[device_id]
                        if device_id in self.device_records:
                            del self.device_records[device_id]
                        
                        cleaned_count += 1
                        logger.info(f"已清理设备 {device_id}，IP {device_ip} 已移回未注册列表")
                
                logger.info(f"批量清理完成，共清理 {cleaned_count} 个设备")
                return {"success": True, "message": f"已清理 {cleaned_count} 个设备状态"}
                
        except Exception as e:
            logger.error(f"批量清理设备失败: {e}")
            return {"success": False, "message": f"批量清理设备失败: {str(e)}"}

    def unregister_device(self, device_id: str) -> Dict:
        """注销RTK设备"""
        if device_id not in self.devices:
            return {"error": "无效的设备ID"}
            
        with self.status_lock:
            del self.devices[device_id]
            del self.device_data[device_id]
            del self.device_status[device_id]
            del self.last_data_time[device_id]
            del self.device_records[device_id]
            
        return {"success": True, "message": f"已注销RTK设备: {device_id}"}
    
    def get_devices(self) -> Dict:
        """获取所有RTK设备信息"""
        with self.status_lock:
            result = {}
            for device_id, device in self.devices.items():
                device_info = device.copy()
                device_info["connected"] = self.device_status[device_id]
                device_info["last_update"] = self.last_data_time[device_id]
                device_info["data"] = self.device_data[device_id]
                result[device_id] = device_info
                
        return result
    
    def get_device_data(self, device_id: str) -> Dict:
        """获取指定RTK设备的数据"""
        if device_id not in self.devices:
            return {"error": "无效的设备ID"}
            
        with self.status_lock:
            device_info = self.devices[device_id].copy()
            device_info["connected"] = self.device_status[device_id]
            device_info["last_update"] = self.last_data_time[device_id]
            device_info["data"] = self.device_data[device_id]
            
        return device_info
    
    def start_recording(self, device_id: str) -> Dict:
        """开始记录RTK设备数据"""
        if device_id not in self.devices:
            return {"error": "无效的设备ID"}
            
        with self.status_lock:
            self.devices[device_id]["recording"] = True
            self.device_records[device_id] = []
            
        return {"success": True, "message": f"开始记录RTK设备数据: {self.devices[device_id]['name']}"}
    
    def stop_recording(self, device_id: str) -> Dict:
        """停止记录RTK设备数据"""
        if device_id not in self.devices:
            return {"error": "无效的设备ID"}
            
        with self.status_lock:
            self.devices[device_id]["recording"] = False
            
        return {
            "success": True, 
            "message": f"停止记录RTK设备数据: {self.devices[device_id]['name']}",
            "record_count": len(self.device_records[device_id])
        }
    
    def get_records(self, device_id: str) -> Dict:
        """获取RTK设备记录的数据"""
        if device_id not in self.devices:
            return {"error": "无效的设备ID"}
            
        with self.status_lock:
            records = self.device_records[device_id]
            
        return {
            "device_id": device_id,
            "device_name": self.devices[device_id]["name"],
            "records": records
        }
    
    def clear_records(self, device_id: str) -> Dict:
        """清除RTK设备记录的数据"""
        if device_id not in self.devices:
            return {"error": "无效的设备ID"}
            
        with self.status_lock:
            self.device_records[device_id] = []
            
        return {"success": True, "message": f"已清除RTK设备数据记录: {self.devices[device_id]['name']}"}
    
    def start_listening(self):
        """启动UDP监听线程"""
        if self.running:
            return {"message": "RTK UDP监听已经在运行"}
            
        self.running = True
        self.listen_thread = threading.Thread(target=self._udp_listener)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        return {"success": True, "message": f"已启动RTK UDP监听，端口: {self.udp_port}"}
    
    def stop_listening(self):
        """停止UDP监听线程"""
        if not self.running:
            return {"message": "RTK UDP监听未在运行"}
            
        self.running = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2.0)
            
        return {"success": True, "message": "已停止RTK UDP监听"}
    
    def scan_for_devices(self) -> Dict:
        """扫描网络上的RTK设备"""
        logger.info("开始扫描网络上的RTK设备...")
        
        detected_devices = []
        with self.status_lock:
            # 检查已接收到数据但尚未注册的IP地址
            current_time = time.time()
            registered_ips = {device["ip"] for device in self.devices.values()}
            
            # 添加详细的调试信息
            logger.info(f"扫描调试信息:")
            logger.info(f"- 当前时间: {current_time}")
            logger.info(f"- 已注册设备IP: {registered_ips}")
            logger.info(f"- 未注册IP数量: {len(self.unregistered_ips)}")
            
            for ip, data in self.unregistered_ips.items():
                time_diff = current_time - data["time"]
                logger.info(f"- 检查IP {ip}: 最后数据时间差 {time_diff:.1f}秒")
                
                # 延长时间窗口到60秒，并允许重新注册异常状态的设备
                if time_diff < 60:
                    # 检查是否已注册但可能需要重新注册
                    device_needs_registration = True
                    registration_reason = "未注册"
                    
                    if ip in registered_ips:
                        # 检查已注册设备的状态
                        for d_id, device in self.devices.items():
                            if device["ip"] == ip:
                                # 如果设备离线超过30秒，允许重新注册
                                if current_time - self.last_data_time.get(d_id, 0) > 30:
                                    registration_reason = "设备离线,需要重新注册"
                                    logger.info(f"设备 {ip} 已注册但离线超过30秒，允许重新注册")
                                else:
                                    device_needs_registration = False
                                    logger.info(f"设备 {ip} 已注册且在线，跳过")
                                break
                    
                    if device_needs_registration:
                        # 为未注册的IP生成一个推荐的设备ID
                        suggested_id = data.get("device_id", f"rtk_{len(detected_devices) + 1}")
                        if not suggested_id or suggested_id == "None":
                            suggested_id = f"rtk_{len(detected_devices) + 1}"
                        
                        detected_devices.append({
                            "id": suggested_id,
                            "ip": ip,
                            "last_seen": data["time"],
                            "name": f"RTK设备 ({ip})",
                            "reason": registration_reason,
                            "device_data": data.get("data", {})
                        })
                        logger.info(f"添加到扫描结果: {ip} - {registration_reason}")
        
        logger.info(f"扫描完成，发现 {len(detected_devices)} 个未注册的RTK设备")
        return {"success": True, "devices": detected_devices}
    

    
    def _udp_listener(self):
        """UDP监听线程函数"""
        logger.info(f"启动RTK UDP监听线程，端口: {self.udp_port}")
        
        # 创建UDP Socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", self.udp_port))
        sock.settimeout(1.0)  # 设置超时，以便定期检查running标志
        
        try:
            while self.running:
                try:
                    # 接收UDP数据包
                    data, addr = sock.recvfrom(1024)
                    sender_ip = addr[0]
                    
                    # 处理数据包
                    if len(data) >= 40:  # 新格式：8字节设备ID + 16字节IP + 16字节数据
                        try:
                            # 解析新格式数据包
                            device_id_bytes = data[:8]
                            device_ip_bytes = data[8:24]
                            data_part = data[24:40]  # 提取数据部分
                            
                            device_id = device_id_bytes.decode('utf-8').strip('\x00')
                            device_ip = device_ip_bytes.decode('utf-8').strip('\x00')
                            
                            # 解包格式: <Ifff （小端：uint32 + 3个float）
                            tCtrlMs, e, n, u = struct.unpack('<Ifff', data_part)
                            
                            # 检查有效性
                            if all(map(np.isfinite, [e, n, u])):
                                current_time = time.time()
                                
                                # 根据设备IP地址查找设备（优先使用数据包中的设备IP，支持模拟器多设备场景）
                                matched_device_id = None
                                logger.info(f"尝试匹配设备 - 发送方IP: {sender_ip}, 数据包IP: {device_ip}")
                                
                                for d_id, device in self.devices.items():
                                    logger.info(f"检查已注册设备 {d_id}: IP={device['ip']}")
                                    # 首先尝试通过设备ID匹配
                                    if d_id == device_id:
                                        matched_device_id = d_id
                                        logger.info(f"通过设备ID匹配成功! 设备ID: {d_id}")
                                        break
                                    # 然后尝试通过IP匹配（优先数据包IP，这样可以支持模拟器的多设备场景）
                                    elif device["ip"] == device_ip or device["ip"] == sender_ip:
                                        matched_device_id = d_id
                                        logger.info(f"通过IP匹配成功! 设备ID: {d_id}")
                                        break
                                
                                if not matched_device_id:
                                    logger.warning(f"未找到匹配的已注册设备! 发送方IP: {sender_ip}, 数据包IP: {device_ip}")
                                    logger.info(f"当前已注册设备: {[(d_id, device['ip']) for d_id, device in self.devices.items()]}")
                                
                                if matched_device_id:
                                    # 已注册设备，更新数据
                                    with self.status_lock:
                                        self.device_data[matched_device_id] = {
                                            "timestamp": tCtrlMs,
                                            "e": e,
                                            "n": n,
                                            "u": u
                                        }
                                        
                                        # 更新设备状态
                                        self.device_status[matched_device_id] = True
                                        self.last_data_time[matched_device_id] = current_time
                                        
                                        # 如果在记录，添加到记录中
                                        if self.devices[matched_device_id]["recording"]:
                                            self.device_records[matched_device_id].append({
                                                "timestamp": tCtrlMs,
                                                "e": e,
                                                "n": n,
                                                "u": u,
                                                "time": current_time
                                            })
                                    
                                    logger.debug(f"收到已注册RTK设备 {self.devices[matched_device_id]['name']} ({device_ip}) 数据: E={e:.3f}, N={n:.3f}, U={u:.3f}")
                                else:
                                    # 未注册设备，使用数据包中的设备IP作为键，这样可以正确区分多个模拟设备
                                    key_ip = device_ip if device_ip else sender_ip
                                    logger.info(f"收到来自未注册设备的RTK数据: {device_id} (发送方IP: {sender_ip}, 数据包IP: {device_ip}, 使用键: {key_ip})")
                                    self.unregistered_ips[key_ip] = {
                                        "time": current_time,
                                        "device_id": device_id,
                                        "sender_ip": sender_ip,
                                        "data_packet_ip": device_ip,
                                        "data": {
                                            "timestamp": tCtrlMs,
                                            "e": e,
                                            "n": n,
                                            "u": u
                                        }
                                    }
                            else:
                                logger.warning(f"收到无效RTK数据: {e}, {n}, {u}")
                                
                        except (struct.error, UnicodeDecodeError) as err:
                            logger.error(f"解包新格式RTK数据失败: {err}")
                            
                    elif len(data) >= 16:  # 兼容旧格式
                        try:
                            # 解包数据
                            # 数据格式可能有两种：旧格式直接是16字节数据，新格式前8字节是设备ID
                            device_id = None
                            data_part = data
                            
                            # 如果长度超过24字节，尝试提取设备ID
                            if len(data) >= 24:
                                try:
                                    device_id_bytes = data[:8]
                                    device_id = device_id_bytes.decode('utf-8').strip('\x00')
                                    data_part = data[8:24]  # 提取数据部分
                                except UnicodeDecodeError:
                                    # 如果解码失败，可能是旧格式
                                    data_part = data[:16]
                            else:
                                # 对于短数据包，只取前16字节
                                data_part = data[:16]
                                
                            # 解包格式: <Ifff （小端：uint32 + 3个float）
                            tCtrlMs, e, n, u = struct.unpack('<Ifff', data_part)
                            
                            # 检查有效性
                            if all(map(np.isfinite, [e, n, u])):
                                current_time = time.time()
                                
                                # 根据IP地址查找设备
                                matched_device_id = None
                                for d_id, device in self.devices.items():
                                    if device["ip"] == sender_ip:
                                        matched_device_id = d_id
                                        break
                                
                                if matched_device_id:
                                    # 已注册设备，更新数据
                                    with self.status_lock:
                                        self.device_data[matched_device_id] = {
                                            "timestamp": tCtrlMs,
                                            "e": e,
                                            "n": n,
                                            "u": u
                                        }
                                        
                                        # 更新设备状态
                                        self.device_status[matched_device_id] = True
                                        self.last_data_time[matched_device_id] = current_time
                                        
                                        # 如果在记录，添加到记录中
                                        if self.devices[matched_device_id]["recording"]:
                                            self.device_records[matched_device_id].append({
                                                "timestamp": tCtrlMs,
                                                "e": e,
                                                "n": n,
                                                "u": u,
                                                "time": current_time
                                            })
                                    
                                    logger.debug(f"收到已注册RTK设备 {self.devices[matched_device_id]['name']} 数据: E={e:.3f}, N={n:.3f}, U={u:.3f}")
                                else:
                                    # 未注册设备，记录IP和数据（兼容旧格式）
                                    logger.info(f"收到来自未注册IP的RTK数据: {sender_ip}, 设备ID: {device_id}")
                                    self.unregistered_ips[sender_ip] = {
                                        "time": current_time,
                                        "device_id": device_id,
                                        "sender_ip": sender_ip,
                                        "data_packet_ip": None,  # 旧格式没有数据包IP
                                        "data": {
                                            "timestamp": tCtrlMs,
                                            "e": e,
                                            "n": n,
                                            "u": u
                                        }
                                    }
                            else:
                                logger.warning(f"收到无效RTK数据: {e}, {n}, {u}")
                                
                        except (struct.error, UnicodeDecodeError) as err:
                            logger.error(f"解包RTK数据失败: {err}")
                    else:
                        logger.warning(f"收到非标准RTK数据包，长度: {len(data)}")
                        
                except socket.timeout:
                    # 超时，继续循环
                    pass
                except Exception as e:
                    logger.error(f"RTK UDP监听出错: {e}")
                    
                # 检查设备超时
                current_time = time.time()
                with self.status_lock:
                    for device_id in self.devices:
                        # 30秒没有数据认为设备离线
                        if current_time - self.last_data_time.get(device_id, 0) > 30:
                            self.device_status[device_id] = False
                            
        except Exception as e:
            logger.error(f"RTK UDP监听线程异常: {e}")
        finally:
            sock.close()
            logger.info("RTK UDP监听线程已停止")

# 创建全局RTK控制器实例
controller = RTKController() 