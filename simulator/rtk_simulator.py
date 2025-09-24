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
            
            # 计算新位置
            self.position["e"] = self.base_coords[0] + self.radius * math.cos(self.angle)
            self.position["n"] = self.base_coords[1] + self.radius * math.sin(self.angle)
            # 高度不变
            self.position["u"] = self.base_coords[2]
        
        self.last_update = time.time()
    
    def _send_data(self, timestamp: int):
        """发送RTK数据"""
        if not self.socket:
            return
            
        try:
            # 数据包格式：设备ID(8字节) + IP地址(16字节) + 时间戳(4字节) + ENU坐标(12字节)
            # 总共40字节
            
            # 设备ID作为前缀（8字节）
            id_bytes = self.device_id.encode('utf-8').ljust(8, b'\x00')
            
            # 设备IP地址（16字节）
            ip_bytes = self.ip_address.encode('utf-8').ljust(16, b'\x00')
            
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
            
            logger.debug(f"RTK设备 {self.device_id} ({self.ip_address}) 发送数据: E={self.position['e']:.3f}, N={self.position['n']:.3f}, U={self.position['u']:.3f}")
            
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
        ttk.Combobox(device_add_frame, textvariable=self.movement_pattern_var, values=movement_patterns, width=10).grid(row=0, column=5, sticky=tk.W, padx=5, pady=5)
        
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
        # 清空列表
        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)
        
        # 添加设备
        for device_id, device in self.devices.items():
            status = "运行中" if device.running else "已停止"
            self.devices_tree.insert("", tk.END, values=(
                device.device_id,
                device.ip_address,
                device.pattern,
                f"{device.speed:.2f}",
                f"{device.radius:.2f}",
                status,
                device.packets_sent
            ))
    
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
            # 创建新设备
            device = RTKDevice(
                device_id=device_id,
                ip_address=ip_address,
                radius=self.noise_level_var.get(),
                speed=self.movement_speed_var.get(),
                base_coords=(0, 0, 0),  # 使用ENU坐标系统，基准点为原点
                pattern=movement_pattern,
                is_base_station=False,
                device_number=self.device_number_var.get()
            )
            
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