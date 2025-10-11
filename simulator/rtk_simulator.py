#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTK设备模拟器 - 模拟多个RTK设备发送UDP数据包
"""

import socket
import struct
import threading
import time
import random
import math
import argparse
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
import json

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# WGS-84常量
WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)
DEG_TO_RAD = math.pi / 180.0

# 参考点（默认与ESP32代码中相同）
DEFAULT_REF_LAT = 32.0806422
DEFAULT_REF_LON = 119.301785
DEFAULT_REF_ALT = 66.0

# 默认发送参数
DEFAULT_REMOTE_IP = "172.16.26.219"  # 修改为本机IP
DEFAULT_REMOTE_PORT = 60001  # 修改为与后端一致的端口
DEFAULT_SEND_INTERVAL = 0.1  # 10Hz

class RTKDevice:
    """模拟RTK设备类"""
    
    def __init__(self, device_id: str, ip_address: str, radius: float = 0.01, 
                 speed: float = 0.1, base_coords: Tuple[float, float, float] = (0, 0, 0),
                 pattern: str = "circular", is_base_station: bool = False, device_number: str = None):
        """
        初始化RTK设备
        
        参数:
            device_id: 设备ID，例如 "rtk1"
            ip_address: 设备IP地址
            radius: 运动半径（米）
            speed: 运动速度 (m/s)
            base_coords: 基准坐标 (e, n, u)，默认为原点
            pattern: 运动模式，"circular" 表示圆周运动，"static" 表示静止
            is_base_station: 是否为基站
            device_number: 设备编号
        """
        self.device_id = device_id
        self.ip_address = ip_address
        self.radius = radius
        self.speed = speed
        self.base_coords = base_coords
        self.pattern = pattern
        self.is_base_station = is_base_station
        self.device_number = device_number if device_number else "1"
        
        # 运动平面（用于圆周运动）
        self.motion_plane = "EN"  # 默认为EN平面
        
        # 直线运动的终点坐标
        self.end_coords = None
        
        # 直线运动的方向和进度
        self.linear_direction = 1  # 1表示从起点到终点，-1表示从终点到起点
        self.linear_progress = 0.0  # 0.0到1.0之间，表示在起点到终点路径上的进度
        
        # 随机运动的坐标范围
        self.random_ranges = None
        
        # 随机运动的下次更新时间（用于控制随机移动频率）
        self.next_random_update = 0.0
        
        # 当前角度（用于圆周运动）
        self.angle = 0.0
        
        # 当前状态
        self.running = False
        self.thread = None
        self.last_update = 0
        
        # 当前位置
        self.position = {
            "e": base_coords[0],
            "n": base_coords[1],
            "u": base_coords[2]
        }
        
        # 发送包计数
        self.packets_sent = 0
        
        # UDP socket 和目标地址
        self.socket = None
        self.target_address = None
        self.target_port = None
        
    def connect(self, target_address: str, target_port: int) -> bool:
        """连接到目标服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.target_address = target_address
            self.target_port = target_port
            return True
        except Exception as e:
            logger.error(f"RTK设备 {self.device_id} 创建Socket失败: {e}")
            return False
    
    def start(self) -> bool:
        """启动RTK设备模拟"""
        if self.running:
            logger.warning(f"RTK设备 {self.device_id} 已经在运行")
            return False
            
        if not self.socket:
            logger.error(f"RTK设备 {self.device_id} 尚未连接到服务器")
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"RTK设备 {self.device_id} 开始模拟运行")
        return True
    
    def stop(self) -> bool:
        """停止RTK设备模拟"""
        if not self.running:
            logger.warning(f"RTK设备 {self.device_id} 未在运行")
            return False
            
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            
        logger.info(f"RTK设备 {self.device_id} 已停止模拟运行")
        return True
    
    def _run(self):
        """设备运行线程"""
        try:
            start_time = time.time()
            
            while self.running:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # 更新位置
                self._update_position(elapsed)
                
                # 发送数据
                self._send_data(int(elapsed * 1000))  # 转换为毫秒
                
                # 等待下一个更新周期
                time.sleep(0.1)  # 10Hz更新频率
                
        except Exception as e:
            logger.error(f"RTK设备 {self.device_id} 运行出错: {e}")
        finally:
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def _update_position(self, elapsed: float):
        """更新设备位置"""
        if self.pattern == "static":
            # 静止模式，位置不变
            return
            
        elif self.pattern == "circular":
            # 圆周运动
            # 计算新角度：角速度 = 线速度/半径
            angular_velocity = self.speed / self.radius if self.radius > 0 else 0
            self.angle = (elapsed * angular_velocity) % (2 * math.pi)
            
            # 根据运动平面计算新位置
            if self.motion_plane == "EN":
                # EN平面（水平面）圆周运动
                self.position["e"] = self.base_coords[0] + self.radius * math.cos(self.angle)
                self.position["n"] = self.base_coords[1] + self.radius * math.sin(self.angle)
                self.position["u"] = self.base_coords[2]  # 高度不变
            elif self.motion_plane == "EU":
                # EU平面（东向-高程）圆周运动
                self.position["e"] = self.base_coords[0] + self.radius * math.cos(self.angle)
                self.position["n"] = self.base_coords[1]  # 北向不变
                self.position["u"] = self.base_coords[2] + self.radius * math.sin(self.angle)
            elif self.motion_plane == "NU":
                # NU平面（北向-高程）圆周运动
                self.position["e"] = self.base_coords[0]  # 东向不变
                self.position["n"] = self.base_coords[1] + self.radius * math.cos(self.angle)
                self.position["u"] = self.base_coords[2] + self.radius * math.sin(self.angle)
            else:
                # 默认为EN平面
                self.position["e"] = self.base_coords[0] + self.radius * math.cos(self.angle)
                self.position["n"] = self.base_coords[1] + self.radius * math.sin(self.angle)
                self.position["u"] = self.base_coords[2]
        
        elif self.pattern == "linear":
            # 直线往返运动
            if self.end_coords is None:
                # 如果没有设置终点，保持在起点
                return
            
            # 计算总距离
            total_distance = math.sqrt(
                (self.end_coords[0] - self.base_coords[0])**2 + 
                (self.end_coords[1] - self.base_coords[1])**2 + 
                (self.end_coords[2] - self.base_coords[2])**2
            )
            
            if total_distance == 0:
                # 起点和终点相同，保持静止
                return
            
            # 计算移动距离
            move_distance = elapsed * self.speed * self.linear_direction
            
            # 更新进度
            self.linear_progress += move_distance / total_distance
            
            # 检查是否到达端点，需要反向
            if self.linear_progress >= 1.0:
                self.linear_progress = 2.0 - self.linear_progress  # 反弹
                self.linear_direction = -1  # 反向
            elif self.linear_progress <= 0.0:
                self.linear_progress = -self.linear_progress  # 反弹
                self.linear_direction = 1  # 正向
            
            # 限制进度在0-1之间
            self.linear_progress = max(0.0, min(1.0, self.linear_progress))
            
            # 根据进度计算当前位置
            self.position["e"] = self.base_coords[0] + (self.end_coords[0] - self.base_coords[0]) * self.linear_progress
            self.position["n"] = self.base_coords[1] + (self.end_coords[1] - self.base_coords[1]) * self.linear_progress
            self.position["u"] = self.base_coords[2] + (self.end_coords[2] - self.base_coords[2]) * self.linear_progress
        
        elif self.pattern == "random":
            # 随机运动
            if self.random_ranges is None:
                # 如果没有设置范围，保持在基准位置
                return
            
            current_time = time.time()
            
            # 控制随机移动频率，使用设备自己的频率参数
            if current_time >= self.next_random_update:
                # 在指定范围内生成随机坐标
                self.position["e"] = random.uniform(self.random_ranges["min_e"], self.random_ranges["max_e"])
                self.position["n"] = random.uniform(self.random_ranges["min_n"], self.random_ranges["max_n"])
                self.position["u"] = random.uniform(self.random_ranges["min_u"], self.random_ranges["max_u"])
                
                # 设置下次更新时间（使用设备的频率范围）
                freq_min = self.random_ranges.get("frequency_min", 1.0)
                freq_max = self.random_ranges.get("frequency_max", 3.0)
                self.next_random_update = current_time + random.uniform(freq_min, freq_max)
        
        self.last_update = time.time()
    
    def _send_data(self, timestamp: int):
        """发送RTK数据"""
        if not self.socket:
            return
            
        try:
            # 数据包格式：设备ID(8字节) + IP地址(16字节) + 时间戳(4字节) + ENU坐标(12字节)
            # 总共40字节
            
            # 设备ID作为前缀（8字节）
            id_bytes = self.device_id.encode('utf-8')[:8].ljust(8, b'\x00')
            
            # 设备IP地址（16字节）- 改进处理
            ip_str = self.ip_address[:15]  # 限制IP字符串长度，为空字符预留空间
            ip_bytes = ip_str.encode('utf-8').ljust(16, b'\x00')
            
            # 打包数据：时间戳和ENU坐标（16字节）
            data = struct.pack('<Ifff', 
                             timestamp, 
                             self.position["e"], 
                             self.position["n"], 
                             self.position["u"])
            
            # 组合完整数据包：设备ID + 设备IP + 数据
            packet = id_bytes + ip_bytes + data
            self.socket.sendto(packet, (self.target_address, self.target_port))
            
            # 增加包计数
            self.packets_sent += 1
            
            # 添加调试日志
            logger.debug(f"RTK设备 {self.device_id} 发送数据包:")
            logger.debug(f"  设备ID: {self.device_id}")
            logger.debug(f"  IP地址: {self.ip_address}")
            logger.debug(f"  IP字节: {ip_bytes}")
            logger.debug(f"  坐标: E={self.position['e']:.3f}, N={self.position['n']:.3f}, U={self.position['u']:.3f}")
            
        except Exception as e:
            logger.error(f"RTK设备 {self.device_id} 发送数据失败: {e}")
    
    def get_status(self) -> Dict:
        """获取设备状态"""
        return {
            "id": self.device_id,
            "ip": self.ip_address,
            "running": self.running,
            "pattern": self.pattern,
            "position": self.position,
            "last_update": self.last_update,
            "isBaseStation": self.is_base_station,
            "deviceNumber": self.device_number
        }
    
    def set_pattern(self, pattern: str) -> bool:
        """设置运动模式"""
        if pattern not in ["circular", "static"]:
            return False
            
        self.pattern = pattern
        return True
    
    def set_parameters(self, radius: Optional[float] = None, speed: Optional[float] = None) -> bool:
        """设置运动参数"""
        if radius is not None:
            if radius < 0:
                return False
            self.radius = radius
            
        if speed is not None:
            if speed < 0:
                return False
            self.speed = speed
            
        return True

class RTKSimulator:
    """RTK设备模拟器，管理多个RTK设备"""
    
    def __init__(self):
        """初始化RTK设备模拟器"""
        self.devices = {}
        self.target_address = "127.0.0.1"
        self.target_port = 60001
        
    def set_target(self, address: str, port: int) -> bool:
        """设置目标服务器地址和端口"""
        try:
            self.target_address = address
            self.target_port = port
            
            # 更新所有设备的目标
            for device in self.devices.values():
                if device.socket:
                    device.socket.close()
                device.connect(self.target_address, self.target_port)
                
            return True
        except Exception as e:
            logger.error(f"设置目标地址失败: {e}")
            return False
    
    def add_device(self, device_id: str, ip_address: str = None, 
                  radius: float = 0.01, speed: float = 0.1,
                  base_coords: Tuple[float, float, float] = (0, 0, 0),
                  pattern: str = "circular", is_base_station: bool = False,
                  device_number: str = None) -> bool:
        """添加RTK设备"""
        try:
            # 如果未指定IP，使用设备ID和本地IP生成
            if not ip_address:
                # 获取本地IP地址
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                
                # 拆分IP并修改最后一段
                ip_parts = local_ip.split('.')
                # 使用设备ID中的数字作为最后一部分
                id_num = ''.join(filter(str.isdigit, device_id))
                if id_num:
                    ip_parts[-1] = str(60 + int(id_num))  # 从61开始
                else:
                    # 如果设备ID中没有数字，使用设备计数
                    ip_parts[-1] = str(61 + len(self.devices))
                
                ip_address = '.'.join(ip_parts)
            
            # 创建设备
            device = RTKDevice(
                device_id=device_id,
                ip_address=ip_address,
                radius=radius,
                speed=speed,
                base_coords=base_coords,
                pattern=pattern,
                is_base_station=is_base_station,
                device_number=device_number
            )
            
            # 连接到目标
            if not device.connect(self.target_address, self.target_port):
                return False
                
            # 添加到设备列表
            self.devices[device_id] = device
            logger.info(f"添加RTK设备: {device_id}, IP: {ip_address}")
            
            return True
        except Exception as e:
            logger.error(f"添加RTK设备失败: {e}")
            return False
    
    def remove_device(self, device_id: str) -> bool:
        """移除RTK设备"""
        if device_id not in self.devices:
            logger.warning(f"RTK设备不存在: {device_id}")
            return False
            
        # 停止设备
        device = self.devices[device_id]
        if device.running:
            device.stop()
            
        # 移除设备
        del self.devices[device_id]
        logger.info(f"移除RTK设备: {device_id}")
        
        return True
    
    def start_device(self, device_id: str) -> bool:
        """启动特定RTK设备"""
        if device_id not in self.devices:
            logger.warning(f"RTK设备不存在: {device_id}")
            return False
            
        return self.devices[device_id].start()
    
    def stop_device(self, device_id: str) -> bool:
        """停止特定RTK设备"""
        if device_id not in self.devices:
            logger.warning(f"RTK设备不存在: {device_id}")
            return False
            
        return self.devices[device_id].stop()
    
    def start_all(self) -> bool:
        """启动所有RTK设备"""
        success = True
        
        for device_id, device in self.devices.items():
            if not device.start():
                success = False
                
        return success
    
    def stop_all(self) -> bool:
        """停止所有RTK设备"""
        success = True
        
        for device_id, device in self.devices.items():
            if not device.stop():
                success = False
                
        return success
    
    def get_device_status(self, device_id: str) -> Dict:
        """获取特定RTK设备的状态"""
        if device_id not in self.devices:
            return {"error": f"RTK设备不存在: {device_id}"}
            
        return self.devices[device_id].get_status()
    
    def get_all_devices(self) -> Dict:
        """获取所有RTK设备的状态"""
        result = {}
        
        for device_id, device in self.devices.items():
            result[device_id] = device.get_status()
            
        return result
    
    def set_device_pattern(self, device_id: str, pattern: str) -> bool:
        """设置设备运动模式"""
        if device_id not in self.devices:
            logger.warning(f"RTK设备不存在: {device_id}")
            return False
            
        return self.devices[device_id].set_pattern(pattern)
    
    def set_device_parameters(self, device_id: str, radius: Optional[float] = None, 
                             speed: Optional[float] = None) -> bool:
        """设置设备运动参数"""
        if device_id not in self.devices:
            logger.warning(f"RTK设备不存在: {device_id}")
            return False
            
        return self.devices[device_id].set_parameters(radius, speed)

# 创建全局模拟器实例
simulator = RTKSimulator()

class RtkSimulatorGUI:
    """RTK模拟器GUI类"""
    
    def __init__(self, root):
        """初始化GUI"""
        self.root = root
        self.root.title("RTK设备模拟器")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 设备字典
        self.devices: Dict[str, RTKDevice] = {}
        
        # 静态模式的位置坐标
        self.static_position = {"e": 0.0, "n": 0.0, "u": 0.0}
        
        # 圆周运动模式的参数
        self.circular_params = {
            "center_e": 0.0,
            "center_n": 0.0, 
            "center_u": 0.0,
            "radius": 1.0,
            "plane": "EN"  # EN, EU, NU
        }
        
        # 直线运动模式的参数
        self.linear_params = {
            "start_e": 0.0,
            "start_n": 0.0,
            "start_u": 0.0,
            "end_e": 1.0,
            "end_n": 1.0,
            "end_u": 0.0
        }
        
        # 随机运动模式的参数
        self.random_params = {
            "min_e": -5.0,
            "max_e": 5.0,
            "min_n": -5.0,
            "max_n": 5.0,
            "min_u": -2.0,
            "max_u": 2.0,
            "frequency_min": 1.0,  # 最小移动间隔（秒）
            "frequency_max": 3.0   # 最大移动间隔（秒）
        }
        
        # 创建GUI组件
        self._create_widgets()
        
        # 设置默认值
        self._set_defaults()
        
        # 定时更新UI
        self._schedule_ui_update()
    
    def _create_widgets(self):
        """创建GUI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部控制区域
        control_frame = ttk.LabelFrame(main_frame, text="全局设置", padding="10")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 目标服务器设置
        ttk.Label(control_frame, text="目标服务器IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.remote_ip_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.remote_ip_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(control_frame, text="目标端口:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.remote_port_var = tk.IntVar()
        ttk.Entry(control_frame, textvariable=self.remote_port_var, width=8).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 参考点设置
        ttk.Label(control_frame, text="参考纬度:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.ref_lat_var = tk.DoubleVar()
        ttk.Entry(control_frame, textvariable=self.ref_lat_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(control_frame, text="参考经度:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.ref_lon_var = tk.DoubleVar()
        ttk.Entry(control_frame, textvariable=self.ref_lon_var, width=15).grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(control_frame, text="参考高度(m):").grid(row=1, column=4, sticky=tk.W, padx=5, pady=5)
        self.ref_alt_var = tk.DoubleVar()
        ttk.Entry(control_frame, textvariable=self.ref_alt_var, width=8).grid(row=1, column=5, sticky=tk.W, padx=5, pady=5)
        
        # 设备添加区域
        device_add_frame = ttk.LabelFrame(main_frame, text="添加设备", padding="10")
        device_add_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(device_add_frame, text="设备ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.device_id_var = tk.StringVar()
        ttk.Entry(device_add_frame, textvariable=self.device_id_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(device_add_frame, text="IP地址:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.device_ip_var = tk.StringVar()
        ttk.Entry(device_add_frame, textvariable=self.device_ip_var, width=15).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(device_add_frame, text="运动模式:").grid(row=0, column=4, sticky=tk.W, padx=5, pady=5)
        self.movement_pattern_var = tk.StringVar()
        movement_patterns = ["static", "circular", "linear", "random"]
        self.movement_pattern_combo = ttk.Combobox(device_add_frame, textvariable=self.movement_pattern_var, values=movement_patterns, width=10)
        self.movement_pattern_combo.grid(row=0, column=5, sticky=tk.W, padx=5, pady=5)
        self.movement_pattern_combo.bind("<<ComboboxSelected>>", self._on_pattern_selected)
        
        ttk.Label(device_add_frame, text="速度(m/s):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.movement_speed_var = tk.DoubleVar()
        ttk.Entry(device_add_frame, textvariable=self.movement_speed_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(device_add_frame, text="噪声(m):").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.noise_level_var = tk.DoubleVar()
        ttk.Entry(device_add_frame, textvariable=self.noise_level_var, width=8).grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(device_add_frame, text="设备号:").grid(row=1, column=4, sticky=tk.W, padx=5, pady=5)
        self.device_number_var = tk.StringVar()
        ttk.Entry(device_add_frame, textvariable=self.device_number_var, width=8).grid(row=1, column=5, sticky=tk.W, padx=5, pady=5)
        
        # 添加设备按钮
        ttk.Button(device_add_frame, text="添加设备", command=self._add_device).grid(row=1, column=6, sticky=tk.E, padx=5, pady=5)
        
        # 设备列表区域
        devices_frame = ttk.LabelFrame(main_frame, text="设备列表", padding="10")
        devices_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建Treeview用于显示设备列表
        columns = ("id", "ip", "pattern", "speed", "noise", "status", "packets")
        self.devices_tree = ttk.Treeview(devices_frame, columns=columns, show="headings")
        
        # 设置列标题
        self.devices_tree.heading("id", text="设备ID")
        self.devices_tree.heading("ip", text="IP地址")
        self.devices_tree.heading("pattern", text="运动模式")
        self.devices_tree.heading("speed", text="速度(m/s)")
        self.devices_tree.heading("noise", text="噪声(m)")
        self.devices_tree.heading("status", text="状态")
        self.devices_tree.heading("packets", text="已发送包数")
        
        # 设置列宽
        self.devices_tree.column("id", width=100)
        self.devices_tree.column("ip", width=120)
        self.devices_tree.column("pattern", width=100)
        self.devices_tree.column("speed", width=80)
        self.devices_tree.column("noise", width=80)
        self.devices_tree.column("status", width=80)
        self.devices_tree.column("packets", width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(devices_frame, orient=tk.VERTICAL, command=self.devices_tree.yview)
        self.devices_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.devices_tree.pack(fill=tk.BOTH, expand=True)
        
        # 添加双击和右键事件绑定
        self.devices_tree.bind("<Double-1>", self._on_tree_double_click)
        self.devices_tree.bind("<Button-3>", self._on_tree_right_click)
        
        # 设备控制按钮
        devices_button_frame = ttk.Frame(devices_frame)
        devices_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(devices_button_frame, text="启动所有", command=self._start_all_devices).pack(side=tk.LEFT, padx=5)
        ttk.Button(devices_button_frame, text="停止所有", command=self._stop_all_devices).pack(side=tk.LEFT, padx=5)
        ttk.Button(devices_button_frame, text="启动选中", command=self._start_selected_device).pack(side=tk.LEFT, padx=5)
        ttk.Button(devices_button_frame, text="停止选中", command=self._stop_selected_device).pack(side=tk.LEFT, padx=5)
        ttk.Button(devices_button_frame, text="删除选中", command=self._remove_selected_device).pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=5, pady=5)
    
    def _on_pattern_selected(self, event):
        """运动模式选择事件处理"""
        selected_pattern = self.movement_pattern_var.get()
        if selected_pattern == "static":
            self._show_static_position_dialog()
        elif selected_pattern == "circular":
            self._show_circular_motion_dialog()
        elif selected_pattern == "linear":
            self._show_linear_motion_dialog()
        elif selected_pattern == "random":
            self._show_random_motion_dialog()
    
    def _show_static_position_dialog(self):
        """显示静态位置设置对话框"""
        # 创建对话框
        position_window = tk.Toplevel(self.root)
        position_window.title("设置静态位置坐标")
        position_window.geometry("350x240")
        position_window.resizable(False, False)
        position_window.transient(self.root)
        position_window.grab_set()
        
        # 居中显示
        position_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 100,
            self.root.winfo_rooty() + 100
        ))
        
        # 创建表单
        frame = ttk.Frame(position_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="请输入静态设备的ENU坐标位置:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # E坐标
        ttk.Label(frame, text="E坐标(东向, 米):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        e_var = tk.DoubleVar(value=self.static_position["e"])
        ttk.Entry(frame, textvariable=e_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # N坐标
        ttk.Label(frame, text="N坐标(北向, 米):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        n_var = tk.DoubleVar(value=self.static_position["n"])
        ttk.Entry(frame, textvariable=n_var, width=15).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # U坐标
        ttk.Label(frame, text="U坐标(高程, 米):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        u_var = tk.DoubleVar(value=self.static_position["u"])
        ttk.Entry(frame, textvariable=u_var, width=15).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        def save_position():
            try:
                self.static_position["e"] = e_var.get()
                self.static_position["n"] = n_var.get()
                self.static_position["u"] = u_var.get()
                position_window.destroy()
                self.status_var.set(f"静态位置已设置: E={self.static_position['e']:.2f}, N={self.static_position['n']:.2f}, U={self.static_position['u']:.2f}")
                logger.info(f"静态位置设置: {self.static_position}")
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
        
        def reset_position():
            e_var.set(0.0)
            n_var.set(0.0)
            u_var.set(0.0)
        
        ttk.Button(button_frame, text="确定", command=save_position).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置", command=reset_position).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=position_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def _show_circular_motion_dialog(self):
        """显示圆周运动参数设置对话框"""
        # 创建对话框
        motion_window = tk.Toplevel(self.root)
        motion_window.title("设置圆周运动参数")
        motion_window.geometry("320x480")
        motion_window.resizable(False, False)
        motion_window.transient(self.root)
        motion_window.grab_set()
        

        # 居中显示
        motion_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 100,
            self.root.winfo_rooty() + 50
        ))
        
        # 创建表单
        frame = ttk.Frame(motion_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="请设置圆周运动参数:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # 圆心坐标
        ttk.Label(frame, text="圆心坐标", font=("Arial", 9, "bold")).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        # 圆心E坐标
        ttk.Label(frame, text="圆心E坐标(东向, 米):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        center_e_var = tk.DoubleVar(value=self.circular_params["center_e"])
        ttk.Entry(frame, textvariable=center_e_var, width=15).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 圆心N坐标
        ttk.Label(frame, text="圆心N坐标(北向, 米):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        center_n_var = tk.DoubleVar(value=self.circular_params["center_n"])
        ttk.Entry(frame, textvariable=center_n_var, width=15).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 圆心U坐标
        ttk.Label(frame, text="圆心U坐标(高程, 米):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        center_u_var = tk.DoubleVar(value=self.circular_params["center_u"])
        ttk.Entry(frame, textvariable=center_u_var, width=15).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 半径
        ttk.Label(frame, text="运动参数", font=("Arial", 9, "bold")).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        ttk.Label(frame, text="运动半径(米):").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        radius_var = tk.DoubleVar(value=self.circular_params["radius"])
        ttk.Entry(frame, textvariable=radius_var, width=15).grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 运动平面
        ttk.Label(frame, text="运动平面:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        plane_var = tk.StringVar(value=self.circular_params["plane"])
        plane_frame = ttk.Frame(frame)
        plane_frame.grid(row=7, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(plane_frame, text="EN平面(水平)", variable=plane_var, value="EN").pack(anchor=tk.W)
        ttk.Radiobutton(plane_frame, text="EU平面(东-高程)", variable=plane_var, value="EU").pack(anchor=tk.W)
        ttk.Radiobutton(plane_frame, text="NU平面(北-高程)", variable=plane_var, value="NU").pack(anchor=tk.W)
        
        # 说明文字
        info_label = ttk.Label(frame, text="• EN平面: 设备在水平面上做圆周运动\n• EU平面: 设备在东向-高程平面上做圆周运动\n• NU平面: 设备在北向-高程平面上做圆周运动", 
                              font=("Arial", 8), foreground="gray")
        info_label.grid(row=8, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(10, 5))
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=9, column=0, columnspan=2, pady=25)
        
        def save_circular_params():
            try:
                # 验证半径
                radius = radius_var.get()
                if radius <= 0:
                    messagebox.showerror("错误", "运动半径必须大于0")
                    return
                
                # 保存参数
                self.circular_params["center_e"] = center_e_var.get()
                self.circular_params["center_n"] = center_n_var.get()
                self.circular_params["center_u"] = center_u_var.get()
                self.circular_params["radius"] = radius
                self.circular_params["plane"] = plane_var.get()
                
                motion_window.destroy()
                
                plane_name = {"EN": "水平面", "EU": "东-高程平面", "NU": "北-高程平面"}[plane_var.get()]
                self.status_var.set(f"圆周运动参数已设置: 圆心({self.circular_params['center_e']:.1f}, {self.circular_params['center_n']:.1f}, {self.circular_params['center_u']:.1f}), 半径{radius:.1f}m, {plane_name}")
                logger.info(f"圆周运动参数设置: {self.circular_params}")
                
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
        
        def reset_circular_params():
            center_e_var.set(0.0)
            center_n_var.set(0.0)
            center_u_var.set(0.0)
            radius_var.set(1.0)
            plane_var.set("EN")
        
        ttk.Button(button_frame, text="保存", command=save_circular_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置", command=reset_circular_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=motion_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def _show_linear_motion_dialog(self):
        """显示直线运动参数设置对话框"""
        # 创建对话框
        motion_window = tk.Toplevel(self.root)
        motion_window.title("设置往返直线运动参数")
        motion_window.geometry("350x450")
        motion_window.resizable(False, False)
        motion_window.transient(self.root)
        motion_window.grab_set()
        
        # 居中显示
        motion_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 100,
            self.root.winfo_rooty() + 50
        ))
        
        # 创建表单
        frame = ttk.Frame(motion_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="请设置往返直线运动参数:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # 起点坐标
        ttk.Label(frame, text="起点坐标", font=("Arial", 9, "bold")).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        # 起点E坐标
        ttk.Label(frame, text="起点E坐标(东向, 米):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        start_e_var = tk.DoubleVar(value=self.linear_params["start_e"])
        ttk.Entry(frame, textvariable=start_e_var, width=15).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 起点N坐标
        ttk.Label(frame, text="起点N坐标(北向, 米):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        start_n_var = tk.DoubleVar(value=self.linear_params["start_n"])
        ttk.Entry(frame, textvariable=start_n_var, width=15).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 起点U坐标
        ttk.Label(frame, text="起点U坐标(高程, 米):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        start_u_var = tk.DoubleVar(value=self.linear_params["start_u"])
        ttk.Entry(frame, textvariable=start_u_var, width=15).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 终点坐标
        ttk.Label(frame, text="终点坐标", font=("Arial", 9, "bold")).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        # 终点E坐标
        ttk.Label(frame, text="终点E坐标(东向, 米):").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        end_e_var = tk.DoubleVar(value=self.linear_params["end_e"])
        ttk.Entry(frame, textvariable=end_e_var, width=15).grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 终点N坐标
        ttk.Label(frame, text="终点N坐标(北向, 米):").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        end_n_var = tk.DoubleVar(value=self.linear_params["end_n"])
        ttk.Entry(frame, textvariable=end_n_var, width=15).grid(row=7, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 终点U坐标
        ttk.Label(frame, text="终点U坐标(高程, 米):").grid(row=8, column=0, sticky=tk.W, padx=5, pady=5)
        end_u_var = tk.DoubleVar(value=self.linear_params["end_u"])
        ttk.Entry(frame, textvariable=end_u_var, width=15).grid(row=8, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 说明文字
        info_label = ttk.Label(frame, text="• 设备将在起点和终点之间做往返直线运动\n• 起点和终点不能相同\n• 运动速度由主界面的速度参数控制", 
                              font=("Arial", 8), foreground="gray")
        info_label.grid(row=9, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(10, 5))
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=25)
        
        def save_linear_params():
            try:
                # 获取坐标值
                start_coords = (start_e_var.get(), start_n_var.get(), start_u_var.get())
                end_coords = (end_e_var.get(), end_n_var.get(), end_u_var.get())
                
                # 验证起点和终点不能相同
                if start_coords == end_coords:
                    messagebox.showerror("错误", "起点和终点坐标不能相同")
                    return
                
                # 保存参数
                self.linear_params["start_e"] = start_coords[0]
                self.linear_params["start_n"] = start_coords[1]
                self.linear_params["start_u"] = start_coords[2]
                self.linear_params["end_e"] = end_coords[0]
                self.linear_params["end_n"] = end_coords[1]
                self.linear_params["end_u"] = end_coords[2]
                
                motion_window.destroy()
                
                # 计算直线距离
                distance = math.sqrt(
                    (end_coords[0] - start_coords[0])**2 + 
                    (end_coords[1] - start_coords[1])**2 + 
                    (end_coords[2] - start_coords[2])**2
                )
                
                self.status_var.set(f"往返直线运动参数已设置: 起点({start_coords[0]:.1f}, {start_coords[1]:.1f}, {start_coords[2]:.1f}) -> 终点({end_coords[0]:.1f}, {end_coords[1]:.1f}, {end_coords[2]:.1f}), 距离{distance:.1f}m")
                logger.info(f"往返直线运动参数设置: {self.linear_params}")
                
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
        
        def reset_linear_params():
            start_e_var.set(0.0)
            start_n_var.set(0.0)
            start_u_var.set(0.0)
            end_e_var.set(1.0)
            end_n_var.set(1.0)
            end_u_var.set(0.0)
        
        ttk.Button(button_frame, text="保存", command=save_linear_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置", command=reset_linear_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=motion_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def _show_random_motion_dialog(self):
        """显示随机运动参数设置对话框"""
        # 创建对话框
        motion_window = tk.Toplevel(self.root)
        motion_window.title("设置随机运动参数")
        motion_window.geometry("420x420")
        motion_window.resizable(False, False)
        motion_window.transient(self.root)
        motion_window.grab_set()
        
        # 居中显示
        motion_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 100,
            self.root.winfo_rooty() + 50
        ))
        
        # 创建表单
        frame = ttk.Frame(motion_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="请设置随机运动参数:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=4, pady=(0, 15))
        
        # 左列：E坐标和N坐标范围
        # E坐标范围
        ttk.Label(frame, text="E坐标(东向)范围", font=("Arial", 9, "bold")).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        # E坐标最小值
        ttk.Label(frame, text="最小值(米):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        min_e_var = tk.DoubleVar(value=self.random_params["min_e"])
        ttk.Entry(frame, textvariable=min_e_var, width=12).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # E坐标最大值
        ttk.Label(frame, text="最大值(米):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        max_e_var = tk.DoubleVar(value=self.random_params["max_e"])
        ttk.Entry(frame, textvariable=max_e_var, width=12).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # N坐标范围
        ttk.Label(frame, text="N坐标(北向)范围", font=("Arial", 9, "bold")).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        # N坐标最小值
        ttk.Label(frame, text="最小值(米):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        min_n_var = tk.DoubleVar(value=self.random_params["min_n"])
        ttk.Entry(frame, textvariable=min_n_var, width=12).grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # N坐标最大值
        ttk.Label(frame, text="最大值(米):").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        max_n_var = tk.DoubleVar(value=self.random_params["max_n"])
        ttk.Entry(frame, textvariable=max_n_var, width=12).grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 右列：U坐标范围和随机移动频率
        # U坐标范围
        ttk.Label(frame, text="U坐标(高程)范围", font=("Arial", 9, "bold")).grid(row=1, column=2, columnspan=2, sticky=tk.W, pady=(10, 5), padx=(20, 0))
        
        # U坐标最小值
        ttk.Label(frame, text="最小值(米):").grid(row=2, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        min_u_var = tk.DoubleVar(value=self.random_params["min_u"])
        ttk.Entry(frame, textvariable=min_u_var, width=12).grid(row=2, column=3, sticky=tk.W, padx=5, pady=5)
        
        # U坐标最大值
        ttk.Label(frame, text="最大值(米):").grid(row=3, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        max_u_var = tk.DoubleVar(value=self.random_params["max_u"])
        ttk.Entry(frame, textvariable=max_u_var, width=12).grid(row=3, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 随机移动频率
        ttk.Label(frame, text="随机移动频率", font=("Arial", 9, "bold")).grid(row=4, column=2, columnspan=2, sticky=tk.W, pady=(15, 5), padx=(20, 0))
        
        # 最小移动间隔
        ttk.Label(frame, text="最小间隔(秒):").grid(row=5, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        freq_min_var = tk.DoubleVar(value=self.random_params["frequency_min"])
        ttk.Entry(frame, textvariable=freq_min_var, width=12).grid(row=5, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 最大移动间隔
        ttk.Label(frame, text="最大间隔(秒):").grid(row=6, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        freq_max_var = tk.DoubleVar(value=self.random_params["frequency_max"])
        ttk.Entry(frame, textvariable=freq_max_var, width=12).grid(row=6, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 说明文字
        info_label = ttk.Label(frame, text="• 设备将在指定的坐标范围内随机移动\n• 支持正数、负数和0\n• 最小值必须小于最大值\n• 移动间隔：每次随机移动后等待的时间范围", 
                              font=("Arial", 8), foreground="gray")
        info_label.grid(row=7, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(20, 5))
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=8, column=0, columnspan=4, pady=25)
        
        def save_random_params():
            try:
                # 获取范围值
                min_e = min_e_var.get()
                max_e = max_e_var.get()
                min_n = min_n_var.get()
                max_n = max_n_var.get()
                min_u = min_u_var.get()
                max_u = max_u_var.get()
                freq_min = freq_min_var.get()
                freq_max = freq_max_var.get()
                
                # 验证范围
                if min_e >= max_e:
                    messagebox.showerror("错误", "E坐标最小值必须小于最大值")
                    return
                if min_n >= max_n:
                    messagebox.showerror("错误", "N坐标最小值必须小于最大值")
                    return
                if min_u >= max_u:
                    messagebox.showerror("错误", "U坐标最小值必须小于最大值")
                    return
                if freq_min <= 0:
                    messagebox.showerror("错误", "最小移动间隔必须大于0")
                    return
                if freq_max <= 0:
                    messagebox.showerror("错误", "最大移动间隔必须大于0")
                    return
                if freq_min >= freq_max:
                    messagebox.showerror("错误", "最小移动间隔必须小于最大移动间隔")
                    return
                
                # 保存参数
                self.random_params["min_e"] = min_e
                self.random_params["max_e"] = max_e
                self.random_params["min_n"] = min_n
                self.random_params["max_n"] = max_n
                self.random_params["min_u"] = min_u
                self.random_params["max_u"] = max_u
                self.random_params["frequency_min"] = freq_min
                self.random_params["frequency_max"] = freq_max
                
                motion_window.destroy()
                
                # 计算范围大小
                range_e = max_e - min_e
                range_n = max_n - min_n
                range_u = max_u - min_u
                
                self.status_var.set(f"随机运动参数已设置: E({min_e:.1f}~{max_e:.1f}), N({min_n:.1f}~{max_n:.1f}), U({min_u:.1f}~{max_u:.1f}), 间隔({freq_min:.1f}~{freq_max:.1f}秒)")
                logger.info(f"随机运动参数设置: {self.random_params}")
                
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
        
        def reset_random_params():
            min_e_var.set(-5.0)
            max_e_var.set(5.0)
            min_n_var.set(-5.0)
            max_n_var.set(5.0)
            min_u_var.set(-2.0)
            max_u_var.set(2.0)
            freq_min_var.set(1.0)
            freq_max_var.set(3.0)
        
        ttk.Button(button_frame, text="保存", command=save_random_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置", command=reset_random_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=motion_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def _set_defaults(self):
        """设置默认值"""
        self.remote_ip_var.set(DEFAULT_REMOTE_IP)
        self.remote_port_var.set(DEFAULT_REMOTE_PORT)
        self.ref_lat_var.set(DEFAULT_REF_LAT)
        self.ref_lon_var.set(DEFAULT_REF_LON)
        self.ref_alt_var.set(DEFAULT_REF_ALT)
        
        self.device_id_var.set("rtk1")
        self.device_ip_var.set("192.168.3.62")
        self.movement_pattern_var.set("circular")
        self.movement_speed_var.set(0.1)
        self.noise_level_var.set(0.01)
        self.device_number_var.set("1")
    
    def _schedule_ui_update(self):
        """定时更新UI"""
        self._update_devices_tree()
        self.root.after(1000, self._schedule_ui_update)
    
    def _update_devices_tree(self):
        """更新设备列表"""
        # 保存当前选中的设备ID
        selected_items = self.devices_tree.selection()
        selected_device_ids = []
        for item in selected_items:
            try:
                device_id = self.devices_tree.item(item)["values"][0]
                selected_device_ids.append(device_id)
            except (IndexError, tk.TclError):
                pass
        
        # 添加调试日志
        if selected_device_ids:
            logger.debug(f"保存的选中设备ID: {selected_device_ids}")
        
        # 清空列表
        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)
        
        # 添加设备
        item_map = {}  # 存储设备ID到item_id的映射
        for device_id, device in self.devices.items():
            status = "运行中" if device.running else "已停止"
            item_id = self.devices_tree.insert("", tk.END, values=(
                device.device_id,
                device.ip_address,
                device.pattern,
                f"{device.speed:.2f}",
                f"{device.radius:.2f}",
                status,
                device.packets_sent
            ))
            item_map[device.device_id] = item_id
        
        # 延迟恢复选中状态，确保Treeview完全更新
        if selected_device_ids:
            self.root.after(10, lambda: self._restore_selection(selected_device_ids, item_map))
    
    def _restore_selection(self, selected_device_ids, item_map):
        """恢复选中状态"""
        try:
            restored_count = 0
            for device_id in selected_device_ids:
                if device_id in item_map:
                    item_id = item_map[device_id]
                    self.devices_tree.selection_add(item_id)
                    restored_count += 1
                    logger.debug(f"恢复选中状态: {device_id}")
            
            # 验证选中状态是否恢复成功
            current_selection = self.devices_tree.selection()
            if selected_device_ids and not current_selection:
                logger.warning(f"选中状态恢复失败，原选中设备: {selected_device_ids}")
            elif current_selection:
                restored_ids = []
                for item in current_selection:
                    try:
                        restored_id = self.devices_tree.item(item)["values"][0]
                        restored_ids.append(restored_id)
                    except (IndexError, tk.TclError):
                        pass
                logger.debug(f"成功恢复选中状态: {restored_ids} (共{restored_count}个)")
        except Exception as e:
            logger.error(f"恢复选中状态失败: {e}")
    
    def _add_device(self):
        """添加新设备"""
        device_id = self.device_id_var.get().strip()
        ip_address = self.device_ip_var.get().strip()
        movement_pattern = self.movement_pattern_var.get()
        
        # 验证输入
        if not device_id:
            messagebox.showerror("错误", "设备ID不能为空")
            return
        
        if not ip_address or not self._validate_ip(ip_address):
            messagebox.showerror("错误", "IP地址格式不正确")
            return
        
        if device_id in self.devices:
            messagebox.showerror("错误", f"设备ID '{device_id}' 已存在")
            return
        
        try:
            # 确定基准坐标和运动参数
            if movement_pattern == "static":
                # 静态模式使用设置的静态位置
                base_coords = (self.static_position["e"], self.static_position["n"], self.static_position["u"])
                radius = 0.0  # 静态模式不需要半径
            elif movement_pattern == "circular":
                # 圆周运动模式使用设置的圆心位置和半径
                base_coords = (self.circular_params["center_e"], self.circular_params["center_n"], self.circular_params["center_u"])
                radius = self.circular_params["radius"]
            elif movement_pattern == "linear":
                # 直线运动模式使用起点作为基准坐标
                base_coords = (self.linear_params["start_e"], self.linear_params["start_n"], self.linear_params["start_u"])
                # 计算起点到终点的距离作为运动范围
                radius = math.sqrt(
                    (self.linear_params["end_e"] - self.linear_params["start_e"])**2 + 
                    (self.linear_params["end_n"] - self.linear_params["start_n"])**2 + 
                    (self.linear_params["end_u"] - self.linear_params["start_u"])**2
                )
            elif movement_pattern == "random":
                # 随机运动模式使用范围中心作为基准坐标
                base_coords = (
                    (self.random_params["min_e"] + self.random_params["max_e"]) / 2,
                    (self.random_params["min_n"] + self.random_params["max_n"]) / 2,
                    (self.random_params["min_u"] + self.random_params["max_u"]) / 2
                )
                # 计算最大范围作为运动半径
                radius = max(
                    (self.random_params["max_e"] - self.random_params["min_e"]) / 2,
                    (self.random_params["max_n"] - self.random_params["min_n"]) / 2,
                    (self.random_params["max_u"] - self.random_params["min_u"]) / 2
                )
            else:
                # 其他模式使用默认的原点坐标
                base_coords = (0, 0, 0)
                radius = self.noise_level_var.get()
            
            # 创建新设备
            device = RTKDevice(
                device_id=device_id,
                ip_address=ip_address,
                radius=radius,
                speed=self.movement_speed_var.get(),
                base_coords=base_coords,
                pattern=movement_pattern,
                is_base_station=False,
                device_number=self.device_number_var.get()
            )
            
            # 如果是圆周运动，设置运动平面信息
            if movement_pattern == "circular":
                device.motion_plane = self.circular_params["plane"]
            # 如果是直线运动，设置终点坐标信息
            elif movement_pattern == "linear":
                device.end_coords = (self.linear_params["end_e"], self.linear_params["end_n"], self.linear_params["end_u"])
            # 如果是随机运动，设置坐标范围信息
            elif movement_pattern == "random":
                device.random_ranges = {
                    "min_e": self.random_params["min_e"],
                    "max_e": self.random_params["max_e"],
                    "min_n": self.random_params["min_n"],
                    "max_n": self.random_params["max_n"],
                    "min_u": self.random_params["min_u"],
                    "max_u": self.random_params["max_u"],
                    "frequency_min": self.random_params["frequency_min"],
                    "frequency_max": self.random_params["frequency_max"]
                }
            
            # 连接到目标服务器
            if not device.connect(self.remote_ip_var.get(), self.remote_port_var.get()):
                messagebox.showerror("错误", f"无法连接到目标服务器 {self.remote_ip_var.get()}:{self.remote_port_var.get()}")
                return
            
            # 添加到设备字典
            self.devices[device_id] = device
            
            # 更新UI
            self._update_devices_tree()
            
            # 更新状态栏
            self.status_var.set(f"已添加设备: {device_id}")
            
            # 自动增加设备ID和IP地址
            if device_id.endswith(tuple('0123456789')):
                # 如果ID以数字结尾，增加数字
                base = ''.join([c for c in device_id if not c.isdigit()])
                num = int(''.join([c for c in device_id if c.isdigit()])) + 1
                next_id = f"{base}{num}"
            else:
                # 否则添加数字2
                next_id = f"{device_id}2"
            
            # 更新下一个IP地址
            ip_parts = ip_address.split('.')
            current_last = int(ip_parts[-1])
            ip_parts[-1] = str(current_last + 1)
            next_ip = '.'.join(ip_parts)
            
            self.device_id_var.set(next_id)
            self.device_ip_var.set(next_ip)
            
            # 更新设备编号
            current_device_num = int(self.device_number_var.get())
            self.device_number_var.set(str(current_device_num + 1))
            
        except Exception as e:
            messagebox.showerror("错误", f"添加设备失败: {str(e)}")
    
    def _validate_ip(self, ip_address):
        """验证IP地址格式"""
        try:
            socket.inet_aton(ip_address)
            return True
        except:
            return False
    
    def _start_all_devices(self):
        """启动所有设备"""
        for device in self.devices.values():
            device.start()
        self.status_var.set(f"已启动所有设备 ({len(self.devices)}个)")
    
    def _stop_all_devices(self):
        """停止所有设备"""
        for device in self.devices.values():
            device.stop()
        self.status_var.set(f"已停止所有设备 ({len(self.devices)}个)")
    
    def _start_selected_device(self):
        """启动选中设备"""
        selected = self.devices_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择设备")
            return
        
        device_id = self.devices_tree.item(selected[0])["values"][0]
        if device_id in self.devices:
            self.devices[device_id].start()
            self.status_var.set(f"已启动设备: {device_id}")
    
    def _stop_selected_device(self):
        """停止选中设备"""
        selected = self.devices_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择设备")
            return
        
        device_id = self.devices_tree.item(selected[0])["values"][0]
        if device_id in self.devices:
            self.devices[device_id].stop()
            self.status_var.set(f"已停止设备: {device_id}")
    
    def _remove_selected_device(self):
        """删除选中设备"""
        selected = self.devices_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择设备")
            return
        
        device_id = self.devices_tree.item(selected[0])["values"][0]
        if device_id in self.devices:
            # 先停止设备
            self.devices[device_id].stop()
            
            # 从字典中删除
            del self.devices[device_id]
            
            # 更新UI
            self._update_devices_tree()
            
            self.status_var.set(f"已删除设备: {device_id}")
    
    def _on_tree_double_click(self, event):
        """双击编辑设备"""
        item = self.devices_tree.selection()[0] if self.devices_tree.selection() else None
        if item:
            self._edit_device(item)
    
    def _on_tree_right_click(self, event):
        """右键菜单"""
        item = self.devices_tree.identify_row(event.y)
        if item:
            self.devices_tree.selection_set(item)
            
            # 创建右键菜单
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="编辑设备", command=lambda: self._edit_device(item))
            context_menu.add_separator()
            context_menu.add_command(label="启动设备", command=self._start_selected_device)
            context_menu.add_command(label="停止设备", command=self._stop_selected_device)
            context_menu.add_separator()
            context_menu.add_command(label="删除设备", command=self._remove_selected_device)
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
    
    def _edit_device(self, item):
        """编辑设备对话框"""
        # 获取当前设备信息
        values = self.devices_tree.item(item)["values"]
        device_id = values[0]
        
        if device_id not in self.devices:
            messagebox.showerror("错误", "设备不存在")
            return
        
        device = self.devices[device_id]
        
        # 创建编辑对话框
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"编辑设备 - {device_id}")
        edit_window.geometry("400x300")
        edit_window.resizable(False, False)
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # 居中显示
        edit_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))
        
        # 创建编辑表单
        self._create_edit_form(edit_window, device, item)
    
    def _create_edit_form(self, parent, device, tree_item):
        """创建设备编辑表单"""
        frame = ttk.Frame(parent, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 设备ID
        ttk.Label(frame, text="设备ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        device_id_var = tk.StringVar(value=device.device_id)
        ttk.Entry(frame, textvariable=device_id_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # IP地址
        ttk.Label(frame, text="IP地址:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ip_var = tk.StringVar(value=device.ip_address)
        ttk.Entry(frame, textvariable=ip_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 运动模式
        ttk.Label(frame, text="运动模式:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        pattern_var = tk.StringVar(value=device.pattern)
        pattern_combo = ttk.Combobox(frame, textvariable=pattern_var, values=["static", "circular", "linear", "random"], 
                                    state="readonly", width=17)
        pattern_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 绑定运动模式选择事件
        def on_edit_pattern_selected(event):
            if pattern_var.get() == "static":
                self._show_edit_static_position_dialog(device)
            elif pattern_var.get() == "circular":
                self._show_edit_circular_motion_dialog(device)
            elif pattern_var.get() == "linear":
                self._show_edit_linear_motion_dialog(device)
            elif pattern_var.get() == "random":
                self._show_edit_random_motion_dialog(device)
        
        pattern_combo.bind("<<ComboboxSelected>>", on_edit_pattern_selected)
        
        # 速度
        ttk.Label(frame, text="速度(m/s):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        speed_var = tk.DoubleVar(value=device.speed)
        ttk.Entry(frame, textvariable=speed_var, width=20).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 噪声
        ttk.Label(frame, text="噪声(m):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        noise_var = tk.DoubleVar(value=device.radius)  # 注意：当前代码中噪声存储在radius字段
        ttk.Entry(frame, textvariable=noise_var, width=20).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        # 保存按钮
        def save_changes():
            try:
                new_device_id = device_id_var.get().strip()
                new_ip = ip_var.get().strip()
                new_pattern = pattern_var.get()
                new_speed = speed_var.get()
                new_noise = noise_var.get()
                
                # 验证输入
                if not new_device_id or not new_ip:
                    messagebox.showerror("错误", "设备ID和IP地址不能为空")
                    return
                
                if not self._validate_ip(new_ip):
                    messagebox.showerror("错误", "IP地址格式不正确")
                    return
                
                if new_speed < 0 or new_noise < 0:
                    messagebox.showerror("错误", "速度和噪声不能为负数")
                    return
                
                # 如果设备ID改变，需要检查是否重复
                if new_device_id != device.device_id and new_device_id in self.devices:
                    messagebox.showerror("错误", f"设备ID '{new_device_id}' 已存在")
                    return
                
                # 保存更改
                self._apply_device_changes(device, new_device_id, new_ip, new_pattern, new_speed, new_noise, tree_item)
                parent.destroy()
                
            except ValueError as e:
                messagebox.showerror("错误", f"输入值无效: {e}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
        
        ttk.Button(button_frame, text="保存", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=parent.destroy).pack(side=tk.LEFT, padx=5)
    
    def _apply_device_changes(self, device, new_device_id, new_ip, new_pattern, new_speed, new_noise, tree_item):
        """应用设备更改"""
        old_device_id = device.device_id
        was_running = device.running
        
        # 如果设备正在运行，先停止
        if was_running:
            device.stop()
        
        # 更新设备属性
        device.device_id = new_device_id
        device.ip_address = new_ip
        device.pattern = new_pattern
        device.speed = new_speed
        device.radius = new_noise  # 注意：当前代码中噪声存储在radius字段
        
        # 如果设备ID改变，需要更新字典键
        if old_device_id != new_device_id:
            del self.devices[old_device_id]
            self.devices[new_device_id] = device
        
        # 重新连接（IP可能已改变）
        if device.socket:
            device.socket.close()
            device.socket = None
        device.connect(self.remote_ip_var.get(), self.remote_port_var.get())
        
        # 如果之前在运行，重新启动
        if was_running:
            device.start()
        
        # 更新UI
        self._update_devices_tree()
        
        self.status_var.set(f"已更新设备: {new_device_id}")
        logger.info(f"设备更新成功: {old_device_id} -> {new_device_id}")
    
    def _validate_ip(self, ip_address):
        """验证IP地址格式"""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip_address):
            return False
        
        try:
            # 验证每个段是否在0-255范围内
            parts = ip_address.split('.')
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False
    
    def _show_edit_static_position_dialog(self, device):
        """显示编辑时的静态位置设置对话框"""
        # 创建对话框
        position_window = tk.Toplevel(self.root)
        position_window.title(f"设置设备 {device.device_id} 的静态位置")
        position_window.geometry("350x240")
        position_window.resizable(False, False)
        position_window.transient(self.root)
        position_window.grab_set()
        
        # 居中显示
        position_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 120,
            self.root.winfo_rooty() + 120
        ))
        
        # 创建表单
        frame = ttk.Frame(position_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"设置设备 {device.device_id} 的ENU坐标位置:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # E坐标
        ttk.Label(frame, text="E坐标(东向, 米):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        e_var = tk.DoubleVar(value=device.base_coords[0])
        ttk.Entry(frame, textvariable=e_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # N坐标
        ttk.Label(frame, text="N坐标(北向, 米):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        n_var = tk.DoubleVar(value=device.base_coords[1])
        ttk.Entry(frame, textvariable=n_var, width=15).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # U坐标
        ttk.Label(frame, text="U坐标(高程, 米):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        u_var = tk.DoubleVar(value=device.base_coords[2])
        ttk.Entry(frame, textvariable=u_var, width=15).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        def save_device_position():
            try:
                new_coords = (e_var.get(), n_var.get(), u_var.get())
                device.base_coords = new_coords
                # 如果设备是静态的，立即更新位置
                if device.pattern == "static":
                    device.position["e"] = new_coords[0]
                    device.position["n"] = new_coords[1]
                    device.position["u"] = new_coords[2]
                position_window.destroy()
                self.status_var.set(f"设备 {device.device_id} 静态位置已更新: E={new_coords[0]:.2f}, N={new_coords[1]:.2f}, U={new_coords[2]:.2f}")
                logger.info(f"设备 {device.device_id} 静态位置更新: {new_coords}")
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
        
        def reset_device_position():
            e_var.set(0.0)
            n_var.set(0.0)
            u_var.set(0.0)
        
        ttk.Button(button_frame, text="确定", command=save_device_position).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置", command=reset_device_position).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=position_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def _show_edit_circular_motion_dialog(self, device):
        """显示编辑时的圆周运动参数设置对话框"""
        # 创建对话框
        motion_window = tk.Toplevel(self.root)
        motion_window.title(f"设置设备 {device.device_id} 的圆周运动参数")
        motion_window.geometry("320x480")
        motion_window.resizable(False, False)
        motion_window.transient(self.root)
        motion_window.grab_set()
        
        # 居中显示
        motion_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 80,
            self.root.winfo_rooty() + 70
        ))
        
        # 创建表单
        frame = ttk.Frame(motion_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"设置设备 {device.device_id} 的圆周运动参数:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # 圆心坐标
        ttk.Label(frame, text="圆心坐标", font=("Arial", 9, "bold")).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        # 圆心E坐标
        ttk.Label(frame, text="圆心E坐标(东向, 米):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        center_e_var = tk.DoubleVar(value=device.base_coords[0])
        ttk.Entry(frame, textvariable=center_e_var, width=15).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 圆心N坐标
        ttk.Label(frame, text="圆心N坐标(北向, 米):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        center_n_var = tk.DoubleVar(value=device.base_coords[1])
        ttk.Entry(frame, textvariable=center_n_var, width=15).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 圆心U坐标
        ttk.Label(frame, text="圆心U坐标(高程, 米):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        center_u_var = tk.DoubleVar(value=device.base_coords[2])
        ttk.Entry(frame, textvariable=center_u_var, width=15).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 半径
        ttk.Label(frame, text="运动参数", font=("Arial", 9, "bold")).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        ttk.Label(frame, text="运动半径(米):").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        radius_var = tk.DoubleVar(value=device.radius)
        ttk.Entry(frame, textvariable=radius_var, width=15).grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 运动平面
        ttk.Label(frame, text="运动平面:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        current_plane = getattr(device, 'motion_plane', 'EN')
        plane_var = tk.StringVar(value=current_plane)
        plane_frame = ttk.Frame(frame)
        plane_frame.grid(row=7, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(plane_frame, text="EN平面(水平)", variable=plane_var, value="EN").pack(anchor=tk.W)
        ttk.Radiobutton(plane_frame, text="EU平面(东-高程)", variable=plane_var, value="EU").pack(anchor=tk.W)
        ttk.Radiobutton(plane_frame, text="NU平面(北-高程)", variable=plane_var, value="NU").pack(anchor=tk.W)
        
        # 说明文字
        info_label = ttk.Label(frame, text="• EN平面: 设备在水平面上做圆周运动\n• EU平面: 设备在东向-高程平面上做圆周运动\n• NU平面: 设备在北向-高程平面上做圆周运动", 
                              font=("Arial", 8), foreground="gray")
        info_label.grid(row=8, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(10, 5))
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=9, column=0, columnspan=2, pady=25)
        
        def save_device_circular_params():
            try:
                # 验证半径
                radius = radius_var.get()
                if radius <= 0:
                    messagebox.showerror("错误", "运动半径必须大于0")
                    return
                
                # 更新设备参数
                new_coords = (center_e_var.get(), center_n_var.get(), center_u_var.get())
                device.base_coords = new_coords
                device.radius = radius
                device.motion_plane = plane_var.get()
                
                motion_window.destroy()
                
                plane_name = {"EN": "水平面", "EU": "东-高程平面", "NU": "北-高程平面"}[plane_var.get()]
                self.status_var.set(f"设备 {device.device_id} 圆周运动参数已更新: 圆心({new_coords[0]:.1f}, {new_coords[1]:.1f}, {new_coords[2]:.1f}), 半径{radius:.1f}m, {plane_name}")
                logger.info(f"设备 {device.device_id} 圆周运动参数更新: 圆心{new_coords}, 半径{radius}, 平面{plane_var.get()}")
                
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
        
        def reset_device_circular_params():
            center_e_var.set(0.0)
            center_n_var.set(0.0)
            center_u_var.set(0.0)
            radius_var.set(1.0)
            plane_var.set("EN")
        
        ttk.Button(button_frame, text="保存", command=save_device_circular_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置", command=reset_device_circular_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=motion_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def _show_edit_linear_motion_dialog(self, device):
        """显示编辑时的直线运动参数设置对话框"""
        # 创建对话框
        motion_window = tk.Toplevel(self.root)
        motion_window.title(f"设置设备 {device.device_id} 的往返直线运动参数")
        motion_window.geometry("350x450")
        motion_window.resizable(False, False)
        motion_window.transient(self.root)
        motion_window.grab_set()
        
        # 居中显示
        motion_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 80,
            self.root.winfo_rooty() + 70
        ))
        
        # 创建表单
        frame = ttk.Frame(motion_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"设置设备 {device.device_id} 的往返直线运动参数:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # 起点坐标（当前设备的基准坐标）
        ttk.Label(frame, text="起点坐标", font=("Arial", 9, "bold")).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        # 起点E坐标
        ttk.Label(frame, text="起点E坐标(东向, 米):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        start_e_var = tk.DoubleVar(value=device.base_coords[0])
        ttk.Entry(frame, textvariable=start_e_var, width=15).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 起点N坐标
        ttk.Label(frame, text="起点N坐标(北向, 米):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        start_n_var = tk.DoubleVar(value=device.base_coords[1])
        ttk.Entry(frame, textvariable=start_n_var, width=15).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 起点U坐标
        ttk.Label(frame, text="起点U坐标(高程, 米):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        start_u_var = tk.DoubleVar(value=device.base_coords[2])
        ttk.Entry(frame, textvariable=start_u_var, width=15).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 终点坐标
        ttk.Label(frame, text="终点坐标", font=("Arial", 9, "bold")).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        # 获取当前设备的终点坐标，如果没有则使用默认值
        current_end = getattr(device, 'end_coords', (device.base_coords[0] + 1, device.base_coords[1] + 1, device.base_coords[2]))
        
        # 终点E坐标
        ttk.Label(frame, text="终点E坐标(东向, 米):").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        end_e_var = tk.DoubleVar(value=current_end[0])
        ttk.Entry(frame, textvariable=end_e_var, width=15).grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 终点N坐标
        ttk.Label(frame, text="终点N坐标(北向, 米):").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        end_n_var = tk.DoubleVar(value=current_end[1])
        ttk.Entry(frame, textvariable=end_n_var, width=15).grid(row=7, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 终点U坐标
        ttk.Label(frame, text="终点U坐标(高程, 米):").grid(row=8, column=0, sticky=tk.W, padx=5, pady=5)
        end_u_var = tk.DoubleVar(value=current_end[2])
        ttk.Entry(frame, textvariable=end_u_var, width=15).grid(row=8, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 说明文字
        info_label = ttk.Label(frame, text="• 设备将在起点和终点之间做往返直线运动\n• 起点和终点不能相同\n• 运动速度由设备的速度参数控制", 
                              font=("Arial", 8), foreground="gray")
        info_label.grid(row=9, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(10, 5))
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=25)
        
        def save_device_linear_params():
            try:
                # 获取坐标值
                start_coords = (start_e_var.get(), start_n_var.get(), start_u_var.get())
                end_coords = (end_e_var.get(), end_n_var.get(), end_u_var.get())
                
                # 验证起点和终点不能相同
                if start_coords == end_coords:
                    messagebox.showerror("错误", "起点和终点坐标不能相同")
                    return
                
                # 更新设备参数
                device.base_coords = start_coords
                device.end_coords = end_coords
                
                # 重置直线运动状态
                device.linear_direction = 1
                device.linear_progress = 0.0
                
                motion_window.destroy()
                
                # 计算直线距离
                distance = math.sqrt(
                    (end_coords[0] - start_coords[0])**2 + 
                    (end_coords[1] - start_coords[1])**2 + 
                    (end_coords[2] - start_coords[2])**2
                )
                
                self.status_var.set(f"设备 {device.device_id} 往返直线运动参数已更新: 起点({start_coords[0]:.1f}, {start_coords[1]:.1f}, {start_coords[2]:.1f}) -> 终点({end_coords[0]:.1f}, {end_coords[1]:.1f}, {end_coords[2]:.1f}), 距离{distance:.1f}m")
                logger.info(f"设备 {device.device_id} 往返直线运动参数更新: 起点{start_coords}, 终点{end_coords}")
                
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
        
        def reset_device_linear_params():
            start_e_var.set(0.0)
            start_n_var.set(0.0)
            start_u_var.set(0.0)
            end_e_var.set(1.0)
            end_n_var.set(1.0)
            end_u_var.set(0.0)
        
        ttk.Button(button_frame, text="保存", command=save_device_linear_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置", command=reset_device_linear_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=motion_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def _show_edit_random_motion_dialog(self, device):
        """显示编辑时的随机运动参数设置对话框"""
        # 创建对话框
        motion_window = tk.Toplevel(self.root)
        motion_window.title(f"设置设备 {device.device_id} 的随机运动参数")
        motion_window.geometry("420x420")
        motion_window.resizable(False, False)
        motion_window.transient(self.root)
        motion_window.grab_set()
        
        # 居中显示
        motion_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 80,
            self.root.winfo_rooty() + 70
        ))
        
        # 创建表单
        frame = ttk.Frame(motion_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"设置设备 {device.device_id} 的随机运动参数:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=4, pady=(0, 15))
        
        # 获取当前设备的随机范围，如果没有则使用默认值
        current_ranges = getattr(device, 'random_ranges', {
            "min_e": -5.0, "max_e": 5.0,
            "min_n": -5.0, "max_n": 5.0,
            "min_u": -2.0, "max_u": 2.0,
            "frequency_min": 1.0, "frequency_max": 3.0
        })
        
        # 左列：E坐标和N坐标范围
        # E坐标范围
        ttk.Label(frame, text="E坐标(东向)范围", font=("Arial", 9, "bold")).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        # E坐标最小值
        ttk.Label(frame, text="最小值(米):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        min_e_var = tk.DoubleVar(value=current_ranges["min_e"])
        ttk.Entry(frame, textvariable=min_e_var, width=12).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # E坐标最大值
        ttk.Label(frame, text="最大值(米):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        max_e_var = tk.DoubleVar(value=current_ranges["max_e"])
        ttk.Entry(frame, textvariable=max_e_var, width=12).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # N坐标范围
        ttk.Label(frame, text="N坐标(北向)范围", font=("Arial", 9, "bold")).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        # N坐标最小值
        ttk.Label(frame, text="最小值(米):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        min_n_var = tk.DoubleVar(value=current_ranges["min_n"])
        ttk.Entry(frame, textvariable=min_n_var, width=12).grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # N坐标最大值
        ttk.Label(frame, text="最大值(米):").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        max_n_var = tk.DoubleVar(value=current_ranges["max_n"])
        ttk.Entry(frame, textvariable=max_n_var, width=12).grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 右列：U坐标范围和随机移动频率
        # U坐标范围
        ttk.Label(frame, text="U坐标(高程)范围", font=("Arial", 9, "bold")).grid(row=1, column=2, columnspan=2, sticky=tk.W, pady=(10, 5), padx=(20, 0))
        
        # U坐标最小值
        ttk.Label(frame, text="最小值(米):").grid(row=2, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        min_u_var = tk.DoubleVar(value=current_ranges["min_u"])
        ttk.Entry(frame, textvariable=min_u_var, width=12).grid(row=2, column=3, sticky=tk.W, padx=5, pady=5)
        
        # U坐标最大值
        ttk.Label(frame, text="最大值(米):").grid(row=3, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        max_u_var = tk.DoubleVar(value=current_ranges["max_u"])
        ttk.Entry(frame, textvariable=max_u_var, width=12).grid(row=3, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 随机移动频率
        ttk.Label(frame, text="随机移动频率", font=("Arial", 9, "bold")).grid(row=4, column=2, columnspan=2, sticky=tk.W, pady=(15, 5), padx=(20, 0))
        
        # 最小移动间隔
        ttk.Label(frame, text="最小间隔(秒):").grid(row=5, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        freq_min_var = tk.DoubleVar(value=current_ranges.get("frequency_min", 1.0))
        ttk.Entry(frame, textvariable=freq_min_var, width=12).grid(row=5, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 最大移动间隔
        ttk.Label(frame, text="最大间隔(秒):").grid(row=6, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        freq_max_var = tk.DoubleVar(value=current_ranges.get("frequency_max", 3.0))
        ttk.Entry(frame, textvariable=freq_max_var, width=12).grid(row=6, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 说明文字
        info_label = ttk.Label(frame, text="• 设备将在指定的坐标范围内随机移动\n• 支持正数、负数和0\n• 最小值必须小于最大值\n• 移动间隔：每次随机移动后等待的时间范围", 
                              font=("Arial", 8), foreground="gray")
        info_label.grid(row=7, column=0, columnspan=4, sticky=tk.W, padx=5, pady=(20, 5))
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=8, column=0, columnspan=4, pady=25)
        
        def save_device_random_params():
            try:
                # 获取范围值
                min_e = min_e_var.get()
                max_e = max_e_var.get()
                min_n = min_n_var.get()
                max_n = max_n_var.get()
                min_u = min_u_var.get()
                max_u = max_u_var.get()
                freq_min = freq_min_var.get()
                freq_max = freq_max_var.get()
                
                # 验证范围
                if min_e >= max_e:
                    messagebox.showerror("错误", "E坐标最小值必须小于最大值")
                    return
                if min_n >= max_n:
                    messagebox.showerror("错误", "N坐标最小值必须小于最大值")
                    return
                if min_u >= max_u:
                    messagebox.showerror("错误", "U坐标最小值必须小于最大值")
                    return
                if freq_min <= 0:
                    messagebox.showerror("错误", "最小移动间隔必须大于0")
                    return
                if freq_max <= 0:
                    messagebox.showerror("错误", "最大移动间隔必须大于0")
                    return
                if freq_min >= freq_max:
                    messagebox.showerror("错误", "最小移动间隔必须小于最大移动间隔")
                    return
                
                # 更新设备参数
                device.random_ranges = {
                    "min_e": min_e, "max_e": max_e,
                    "min_n": min_n, "max_n": max_n,
                    "min_u": min_u, "max_u": max_u,
                    "frequency_min": freq_min, "frequency_max": freq_max
                }
                
                # 重置随机运动状态
                device.next_random_update = 0.0
                
                motion_window.destroy()
                
                self.status_var.set(f"设备 {device.device_id} 随机运动参数已更新: E({min_e:.1f}~{max_e:.1f}), N({min_n:.1f}~{max_n:.1f}), U({min_u:.1f}~{max_u:.1f}), 间隔({freq_min:.1f}~{freq_max:.1f}秒)")
                logger.info(f"设备 {device.device_id} 随机运动参数更新: {device.random_ranges}")
                
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
        
        def reset_device_random_params():
            min_e_var.set(-5.0)
            max_e_var.set(5.0)
            min_n_var.set(-5.0)
            max_n_var.set(5.0)
            min_u_var.set(-2.0)
            max_u_var.set(2.0)
            freq_min_var.set(1.0)
            freq_max_var.set(3.0)
        
        ttk.Button(button_frame, text="保存", command=save_device_random_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置", command=reset_device_random_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=motion_window.destroy).pack(side=tk.LEFT, padx=5)

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='RTK设备模拟器')
    parser.add_argument('--remote-ip', type=str, default=DEFAULT_REMOTE_IP,
                        help=f'目标服务器IP地址 (默认: {DEFAULT_REMOTE_IP})')
    parser.add_argument('--remote-port', type=int, default=DEFAULT_REMOTE_PORT,
                        help=f'目标服务器端口 (默认: {DEFAULT_REMOTE_PORT})')
    parser.add_argument('--ref-lat', type=float, default=DEFAULT_REF_LAT,
                        help=f'参考纬度 (默认: {DEFAULT_REF_LAT})')
    parser.add_argument('--ref-lon', type=float, default=DEFAULT_REF_LON,
                        help=f'参考经度 (默认: {DEFAULT_REF_LON})')
    parser.add_argument('--ref-alt', type=float, default=DEFAULT_REF_ALT,
                        help=f'参考高度 (默认: {DEFAULT_REF_ALT})')
    
    args = parser.parse_args()
    
    # 创建GUI
    root = tk.Tk()
    app = RtkSimulatorGUI(root)
    
    # 启动主循环
    root.mainloop()

if __name__ == "__main__":
    main() 