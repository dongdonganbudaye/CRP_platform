# RTK设备颜色区分显示修改方案

## 修改概述
为不同的RTK设备分配不同的颜色，使每个RTK设备的小球（位置标记）和轨迹线都显示为独特的颜色，便于在3D场景中区分和识别，最多支持8个RTK设备同时在线。

## 当前状态分析
- **现有颜色方案**: 
  - 基站：白色球体 (0xffffff) + 白色轨迹
  - 移动站：绿色球体 (0x00ff88) + 绿色轨迹
- **现有实现位置**: `frontend/src/views/RtkMonitor.vue`
  - 小球颜色：第1003-1028行
  - 轨迹颜色：第1160-1165行
  - 标签边框：第1047行

## 修改详情

### 1. 颜色方案设计

#### 1.1 预定义颜色列表
为8个RTK设备预定义8种不同的颜色，颜色选择考虑：
- 在3D场景中具有良好的对比度和可识别性
- 颜色之间差异明显
- 适合深色背景显示

```javascript
// 8种不同的RTK设备颜色
const RTK_DEVICE_COLORS = [
  { name: '蓝色', hex: 0x3498db, css: '#3498db' },     // 设备1
  { name: '绿色', hex: 0x2ecc71, css: '#2ecc71' },     // 设备2  
  { name: '橙色', hex: 0xe67e22, css: '#e67e22' },     // 设备3
  { name: '紫色', hex: 0x9b59b6, css: '#9b59b6' },     // 设备4
  { name: '红色', hex: 0xe74c3c, css: '#e74c3c' },     // 设备5
  { name: '青色', hex: 0x1abc9c, css: '#1abc9c' },     // 设备6
  { name: '黄色', hex: 0xf1c40f, css: '#f1c40f' },     // 设备7
  { name: '粉色', hex: 0xe91e63, css: '#e91e63' }      // 设备8
];
```

#### 1.2 基站颜色保持特殊性
- **基站**: 保持白色 (0xffffff)，作为基准参考点
- **移动站**: 根据设备分配不同颜色

### 2. 前端代码修改 (`frontend/src/views/RtkMonitor.vue`)

#### 2.1 添加颜色管理函数
在JavaScript部分添加颜色相关的函数：

```javascript
// RTK设备颜色配置
const RTK_DEVICE_COLORS = [
  { name: '蓝色', hex: 0x3498db, css: '#3498db' },
  { name: '绿色', hex: 0x2ecc71, css: '#2ecc71' },
  { name: '橙色', hex: 0xe67e22, css: '#e67e22' },
  { name: '紫色', hex: 0x9b59b6, css: '#9b59b6' },
  { name: '红色', hex: 0xe74c3c, css: '#e74c3c' },
  { name: '青色', hex: 0x1abc9c, css: '#1abc9c' },
  { name: '黄色', hex: 0xf1c40f, css: '#f1c40f' },
  { name: '粉色', hex: 0xe91e63, css: '#e91e63' }
];

// 设备颜色分配管理
const deviceColorAssignments = ref({});

// 获取设备颜色
function getDeviceColor(deviceId, isBaseStation = false) {
  // 基站始终使用白色
  if (isBaseStation) {
    return { hex: 0xffffff, css: '#ffffff', name: '白色' };
  }
  
  // 检查是否已分配颜色
  if (deviceColorAssignments.value[deviceId]) {
    return deviceColorAssignments.value[deviceId];
  }
  
  // 为新设备分配颜色
  const assignedColors = Object.values(deviceColorAssignments.value);
  const availableColors = RTK_DEVICE_COLORS.filter(color => 
    !assignedColors.some(assigned => assigned.hex === color.hex)
  );
  
  if (availableColors.length > 0) {
    deviceColorAssignments.value[deviceId] = availableColors[0];
    return availableColors[0];
  }
  
  // 如果所有颜色都已分配，循环使用
  const colorIndex = Object.keys(deviceColorAssignments.value).length % RTK_DEVICE_COLORS.length;
  deviceColorAssignments.value[deviceId] = RTK_DEVICE_COLORS[colorIndex];
  return RTK_DEVICE_COLORS[colorIndex];
}

// 释放设备颜色分配
function releaseDeviceColor(deviceId) {
  delete deviceColorAssignments.value[deviceId];
}
```

#### 2.2 修改设备3D显示函数 (第1000-1029行)
```javascript
// 在 updateDevicesIn3D 函数中修改颜色部分
let geometry, material;
const deviceColor = getDeviceColor(device.id, device.isBaseStation);

if (device.isBaseStation) {
  // 基站：白色球体
  geometry = markRaw(new THREE.SphereGeometry(0.3, 16, 16));
  material = markRaw(new THREE.MeshLambertMaterial({ 
    color: deviceColor.hex,
    emissive: 0x222222
  }));
  
  // 基站覆盖范围（保持白色）
  const rangeGeometry = markRaw(new THREE.RingGeometry(4.5, 5, 32));
  const rangeMaterial = markRaw(new THREE.MeshBasicMaterial({ 
    color: deviceColor.hex, 
    transparent: true, 
    opacity: 0.1,
    side: THREE.DoubleSide
  }));
  const rangeMesh = markRaw(new THREE.Mesh(rangeGeometry, rangeMaterial));
  rangeMesh.rotation.x = -Math.PI / 2;
  rangeMesh.position.copy(position);
  rangeMesh.position.y = 0.01;
  scene.value.add(rangeMesh);
  baseMeshes.value.push(rangeMesh);
} else {
  // 移动站：使用分配的颜色
  geometry = markRaw(new THREE.SphereGeometry(0.2, 16, 16));
  material = markRaw(new THREE.MeshLambertMaterial({ 
    color: deviceColor.hex,
    emissive: deviceColor.hex * 0.1  // 微弱的自发光效果
  }));
}
```

#### 2.3 修改标签边框颜色 (第1047行)
```javascript
// 绘制边框 - 使用设备分配的颜色
const deviceColor = getDeviceColor(device.id, device.isBaseStation);
ctx.strokeStyle = deviceColor.css;
ctx.lineWidth = 2;
ctx.strokeRect(2, 2, canvas.width - 4, canvas.height - 4);
```

#### 2.4 修改轨迹线颜色 (第1160-1165行)
```javascript
// 更新轨迹线函数中的颜色处理
function updateTrajectoryLine(deviceId, points, isBaseStation) {
  if (points.length < 2) return;
  
  // 移除旧的轨迹线
  if (trajectoryLines.value[deviceId]) {
    scene.value.remove(trajectoryLines.value[deviceId]);
  }
  
  // 获取设备颜色
  const deviceColor = getDeviceColor(deviceId, isBaseStation);
  
  // 创建新的轨迹线
  const geometry = markRaw(new THREE.BufferGeometry().setFromPoints(points));
  const material = markRaw(new THREE.LineBasicMaterial({
    color: deviceColor.hex,
    linewidth: 2,
    transparent: true,
    opacity: 0.8
  }));
  
  const line = markRaw(new THREE.Line(geometry, material));
  scene.value.add(line);
  trajectoryLines.value[deviceId] = line;
}
```

#### 2.5 添加设备颜色显示功能
在RTK设备列表UI中显示每个设备的分配颜色：

```vue
<!-- 在设备信息显示中添加颜色指示器 -->
<div class="device-color-indicator" 
     :style="{ backgroundColor: getDeviceColor(device.id, device.isBaseStation).css }"
     :title="`设备颜色: ${getDeviceColor(device.id, device.isBaseStation).name}`">
</div>
```

#### 2.6 设备断开连接时的清理
修改设备连接状态处理，在设备断开时释放颜色分配：

```javascript
// 在设备断开连接处理中添加
function handleDeviceDisconnect(deviceId) {
  // 现有的断开连接处理...
  
  // 释放颜色分配
  releaseDeviceColor(deviceId);
}
```

### 3. CSS样式添加

#### 3.1 设备颜色指示器样式
```css
.device-color-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 8px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 0 4px rgba(0, 0, 0, 0.3);
}
```

### 4. 功能特性

#### 4.1 颜色分配规则
- **基站**: 始终使用白色，便于识别基准点
- **移动站**: 按连接顺序依次分配8种预定义颜色
- **颜色复用**: 超过8个设备时循环使用颜色
- **颜色释放**: 设备断开时释放颜色，可供新设备使用

#### 4.2 视觉效果
- **小球颜色**: 每个设备使用独特颜色的球体
- **轨迹颜色**: 轨迹线与对应设备球体颜色一致
- **标签边框**: 设备标签边框使用相同颜色
- **颜色指示**: 在设备列表中显示颜色指示器

#### 4.3 用户体验
- **快速识别**: 通过颜色快速区分不同设备
- **颜色提示**: 鼠标悬停显示颜色名称
- **视觉一致性**: 小球、轨迹、标签使用统一颜色

### 5. 预期效果

修改完成后：
```
设备1: 蓝色球体 + 蓝色轨迹 + 蓝色边框
设备2: 绿色球体 + 绿色轨迹 + 绿色边框
设备3: 橙色球体 + 橙色轨迹 + 橙色边框
...
基站: 白色球体 + 白色轨迹 + 白色边框 (保持特殊性)
```

### 6. 修改文件列表
- `frontend/src/views/RtkMonitor.vue` (主要修改)

### 7. 风险评估
- **低风险**: 主要是颜色修改，不影响核心功能逻辑
- **向后兼容**: 保持基站的白色显示，确保现有配准功能不受影响
- **性能影响**: 最小，仅增加颜色计算逻辑

### 8. 扩展性考虑
- **颜色配置**: 可以轻松调整预定义颜色
- **动态颜色**: 未来可支持用户自定义设备颜色
- **颜色持久化**: 可以将颜色分配保存到后端

## 是否确认进行此修改？
请确认是否按照以上方案进行修改。如有调整需求，请告知具体要求。 