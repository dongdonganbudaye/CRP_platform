# RTK定位监控轨迹持久化修复方案

## 问题描述

在 RTK定位监控的3D可视化中，网页刷新会导致RTK设备的轨迹清除掉。希望轨迹在点击清除轨迹按钮前，即使刷新网页也不会被清除。

## 当前实现分析

### 轨迹数据存储方式
`javascript
// 当前轨迹数据存储在内存中（第748-749行）
const trajectoryLines = ref({});   // 3D轨迹线对象
const trajectoryPoints = ref({});  // 轨迹点坐标数组
`

### 问题根源
1. **内存存储**: 轨迹数据仅保存在响应式变量中，页面刷新后数据丢失
2. **无持久化**: 没有将轨迹数据保存到 localStorage 或后端
3. **清除机制**: 只有手动点击清除轨迹按钮才会清除

## 修复方案

### 方案概述
使用 localStorage 持久化存储轨迹数据，实现页面刷新后轨迹自动恢复。

### 修改内容

#### 1. 添加轨迹持久化功能函数

在 RtkMonitor.vue 的 <script setup> 部分添加以下函数（建议在第1557行 clearTrajectory 函数后添加）:

`javascript
// ==================== 轨迹持久化功能 ====================

// 保存轨迹数据到 localStorage
function saveTrajectoryToStorage() {
  try {
    const trajectoryData = {};
    
    // 遍历所有设备的轨迹点
    Object.keys(trajectoryPoints.value).forEach(deviceId => {
      const points = trajectoryPoints.value[deviceId];
      if (points && points.length > 0) {
        // 将 Three.js Vector3 对象转换为普通对象数组
        trajectoryData[deviceId] = points.map(point => ({
          x: point.x,
          y: point.y,
          z: point.z
        }));
      }
    });
    
    // 保存到 localStorage
    if (Object.keys(trajectoryData).length > 0) {
      localStorage.setItem('rtk_trajectory_data', JSON.stringify(trajectoryData));
      console.log('轨迹数据已保存到本地存储');
    }
  } catch (error) {
    console.error('保存轨迹数据失败:', error);
  }
}

// 从 localStorage 恢复轨迹数据
function restoreTrajectoryFromStorage() {
  try {
    const savedData = localStorage.getItem('rtk_trajectory_data');
    if (!savedData) {
      console.log('没有保存的轨迹数据');
      return;
    }
    
    const trajectoryData = JSON.parse(savedData);
    let restoredCount = 0;
    
    // 恢复轨迹点
    Object.keys(trajectoryData).forEach(deviceId => {
      const pointsData = trajectoryData[deviceId];
      if (pointsData && pointsData.length > 0) {
        // 将普通对象数组转换回 Three.js Vector3 对象
        trajectoryPoints.value[deviceId] = pointsData.map(p => 
          new THREE.Vector3(p.x, p.y, p.z)
        );
        
        // 重新绘制轨迹线
        const device = rtkDevices.value[deviceId];
        if (device && trajectoryPoints.value[deviceId].length >= 2) {
          updateTrajectoryLine(
            deviceId, 
            trajectoryPoints.value[deviceId], 
            device.isBaseStation
          );
          restoredCount++;
        }
      }
    });
    
    if (restoredCount > 0) {
      console.log(\已恢复 \ 个设备的轨迹数据\);
      ElMessage.success(\已恢复 \ 个设备的轨迹\);
    }
  } catch (error) {
    console.error('恢复轨迹数据失败:', error);
  }
}

// 清除 localStorage 中的轨迹数据
function clearTrajectoryFromStorage(deviceId = null) {
  try {
    if (deviceId) {
      // 清除单个设备的轨迹
      const savedData = localStorage.getItem('rtk_trajectory_data');
      if (savedData) {
        const trajectoryData = JSON.parse(savedData);
        delete trajectoryData[deviceId];
        
        if (Object.keys(trajectoryData).length > 0) {
          localStorage.setItem('rtk_trajectory_data', JSON.stringify(trajectoryData));
        } else {
          localStorage.removeItem('rtk_trajectory_data');
        }
        console.log(\已清除设备 \ 的轨迹存储\);
      }
    } else {
      // 清除所有轨迹
      localStorage.removeItem('rtk_trajectory_data');
      console.log('已清除所有轨迹存储');
    }
  } catch (error) {
    console.error('清除轨迹存储失败:', error);
  }
}
`

#### 2. 修改轨迹更新函数

修改 updateDeviceTrajectory 函数（第1184-1225行），在添加轨迹点后保存到 localStorage:

`javascript
// 更新设备轨迹
function updateDeviceTrajectory(device) {
  if (!device.connected || !device.data || !device.recording) return;
  
  const deviceId = device.id;
  
  // 优先使用转换后的世界坐标，如果没有则使用原始坐标
  const currentPosition = new THREE.Vector3();
  if (device.worldCoords) {
    currentPosition.set(
      device.worldCoords.x,
      device.worldCoords.y,
      -device.worldCoords.z
    );
  } else {
    currentPosition.set(
      device.data.e || 0,
      device.data.u || 0,
      -(device.data.n || 0)
    );
  }
  
  // 初始化轨迹点数组
  if (!trajectoryPoints.value[deviceId]) {
    trajectoryPoints.value[deviceId] = [];
  }
  
  // 添加新的轨迹点（避免重复添加相同位置）
  const points = trajectoryPoints.value[deviceId];
  const lastPoint = points.length > 0 ? points[points.length - 1] : null;
  
  if (!lastPoint || lastPoint.distanceTo(currentPosition) > 0.01) {
    points.push(currentPosition.clone());
    
    // 限制轨迹点数量，避免内存过多占用
    if (points.length > 1000) {
      points.shift();
    }
    
    // 更新轨迹线
    updateTrajectoryLine(deviceId, points, device.isBaseStation);
    
    // 【新增】保存轨迹数据到 localStorage
    saveTrajectoryToStorage();
  }
}
`

#### 3. 修改清除轨迹函数

修改 clearTrajectory 函数（第1528-1557行），清除时同时删除 localStorage 中的数据:

`javascript
async function clearTrajectory(deviceId) {
  try {
    await ElMessageBox.confirm('确定要清除此设备的轨迹记录吗？', '确认清除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    
    const response = await axios.delete(\\/api/rtk/devices/\/records\);
    
    if (response.data && response.data.success) {
      ElMessage.success('轨迹记录已清除');
      
      // 清除3D场景中的轨迹线
      if (trajectoryLines.value[deviceId]) {
        scene.value.remove(trajectoryLines.value[deviceId]);
        delete trajectoryLines.value[deviceId];
      }
      if (trajectoryPoints.value[deviceId]) {
        trajectoryPoints.value[deviceId] = [];
      }
      
      // 【新增】清除 localStorage 中的轨迹数据
      clearTrajectoryFromStorage(deviceId);
      
    } else {
      ElMessage.error('清除轨迹记录失败');
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清除轨迹记录失败:', error);
      ElMessage.error('清除轨迹记录失败');
    }
  }
}
`

#### 4. 在组件挂载时恢复轨迹

修改 onMounted 生命周期钩子（第3234-3274行），在初始化后恢复轨迹:

`javascript
onMounted(async () => {
  // 初始化3D场景
  await nextTick();
  init3DScene();
  
  // 尝试恢复配准状态（在加载模型前）
  const stateRestored = restoreAlignmentState();
  
  // 加载建筑模型（模型加载时会自动应用保存的变换）
  await loadBuildingModels();
  
  // 静默恢复配准状态（无提示消息）
  if (stateRestored) {
    console.log('配准状态已静默恢复');
    modelTransformApplied.value = true;
  }
  
  // 获取RTK设备数据
  await fetchRtkDevices();
  
  // 如果恢复了配准状态，重新应用坐标转换（静默）
  if (stateRestored && alignmentManager.value.rtkBasePoint) {
    updateAllRtkWorldCoords();
    console.log('RTK坐标系已静默恢复到配准状态');
  }
  
  // 【新增】恢复轨迹数据
  await nextTick(); // 等待3D场景和设备数据加载完成
  restoreTrajectoryFromStorage();
  
  // 设置数据刷新间隔，并在每次刷新后检查基准点
  refreshInterval.value = setInterval(() => {
    fetchRtkDevices().then(() => {
      checkRtkBasePointUpdate();
    });
  }, 2000);
  
  // 模拟WebSocket连接状态
  setTimeout(() => {
    wsConnected.value = true;
  }, 1000);
});
`

## 修改文件清单

- rontend/src/views/RtkMonitor.vue

## 实现效果

1. ✅ **轨迹持久化**: 轨迹数据自动保存到浏览器 localStorage
2. ✅ **页面刷新恢复**: 刷新页面后自动恢复所有设备的轨迹
3. ✅ **手动清除**: 点击清除轨迹按钮同时清除内存和存储
4. ✅ **性能优化**: 仅在轨迹点变化时保存，避免频繁写入
5. ✅ **数据限制**: 保持原有的1000点限制，防止存储溢出

## 注意事项

1. **localStorage 容量**: 浏览器 localStorage 通常有 5-10MB 限制，1000点轨迹约占用 50-100KB，多设备情况下需注意
2. **兼容性**: 现代浏览器均支持 localStorage，无需担心兼容性
3. **数据清理**: 建议定期清除不需要的轨迹数据
4. **隐私模式**: 浏览器隐私模式下 localStorage 可能在关闭窗口后清除

## 测试建议

1. 开始记录某设备轨迹  刷新页面  验证轨迹是否保留
2. 清除轨迹  刷新页面  验证轨迹是否已清除
3. 多设备同时记录  刷新页面  验证所有轨迹是否恢复
4. 长时间记录达到1000点  刷新页面  验证点数限制是否生效
