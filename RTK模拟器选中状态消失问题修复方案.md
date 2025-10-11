# RTK模拟器设备列表选中条消失问题分析与修复方案

## 问题描述
在"rtk_simulator.py"的"设备列表"中，对某个设备的选中条点击后会立即消失。

## 问题原因分析

### 根本原因
在`simulator/rtk_simulator.py`的第569-586行，`_update_devices_tree()`方法存在问题：

```python
def _update_devices_tree(self):
    """更新设备列表"""
    # 清空列表
    for item in self.devices_tree.get_children():
        self.devices_tree.delete(item)  # 这里会删除所有项目，包括选中的项目
    
    # 添加设备
    for device_id, device in self.devices.items():
        status = "运行中" if device.running else "已停止"
        self.devices_tree.insert("", tk.END, values=(...))
```

### 问题流程
1. **用户点击选择设备**：Treeview中的某一行被选中
2. **定时更新触发**：`_schedule_ui_update()`每1000ms调用一次（第567行）
3. **清空并重建列表**：`_update_devices_tree()`删除所有项目并重新插入
4. **选中状态丢失**：由于整个列表被重建，之前的选中状态完全丢失

### 定时更新机制
```python
def _schedule_ui_update(self):
    """定时更新UI"""
    self._update_devices_tree()  # 每秒都会重建整个列表
    self.root.after(1000, self._schedule_ui_update)
```

## 修复方案

### 方案一：保存和恢复选中状态（推荐）
修改`_update_devices_tree()`方法，在清空列表前保存选中状态，重建后恢复：

```python
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
    
    # 清空列表
    for item in self.devices_tree.get_children():
        self.devices_tree.delete(item)
    
    # 添加设备并恢复选中状态
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
        
        # 如果这个设备之前被选中，恢复选中状态
        if device.device_id in selected_device_ids:
            self.devices_tree.selection_add(item_id)
```

### 方案二：智能更新（更高效）
只更新变化的项目，而不是重建整个列表：

```python
def _update_devices_tree(self):
    """更新设备列表（智能更新）"""
    # 获取现有项目
    existing_items = {}
    for item in self.devices_tree.get_children():
        try:
            device_id = self.devices_tree.item(item)["values"][0]
            existing_items[device_id] = item
        except (IndexError, tk.TclError):
            pass
    
    # 更新现有设备或添加新设备
    for device_id, device in self.devices.items():
        status = "运行中" if device.running else "已停止"
        new_values = (
            device.device_id,
            device.ip_address,
            device.pattern,
            f"{device.speed:.2f}",
            f"{device.radius:.2f}",
            status,
            device.packets_sent
        )
        
        if device_id in existing_items:
            # 更新现有项目
            self.devices_tree.item(existing_items[device_id], values=new_values)
            existing_items.pop(device_id)  # 标记为已处理
        else:
            # 添加新项目
            self.devices_tree.insert("", tk.END, values=new_values)
    
    # 删除不存在的设备
    for item in existing_items.values():
        self.devices_tree.delete(item)
```

### 方案三：减少更新频率
将更新频率从1秒改为3-5秒，减少用户操作被打断的概率：

```python
def _schedule_ui_update(self):
    """定时更新UI"""
    self._update_devices_tree()
    self.root.after(3000, self._schedule_ui_update)  # 改为3秒更新一次
```

## 推荐修复步骤

1. **第一步**：实施方案一，保存和恢复选中状态
2. **第二步**：可选择实施方案三，减少更新频率以改善用户体验
3. **第三步**：测试确认选中状态能够正确保持

## 修复位置
- 文件：`simulator/rtk_simulator.py`
- 方法：`_update_devices_tree()` (第569-586行)
- 可选：`_schedule_ui_update()` (第564-567行)

## 影响范围
- 改善用户体验，选中状态不会丢失
- 不影响设备模拟功能
- 兼容现有的设备操作功能

请确认是否按**方案一**进行修复？
