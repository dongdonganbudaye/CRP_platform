# BIM基准点配准状态持久化修复方案

## 问题分析

### 当前问题
完成"BIM基准点"配准后刷新页面，模型会重新回到"BIM基准点"配准前的位置，配准状态丢失。

### 根本原因
1. **配准状态未持久化**：`alignmentManager`对象存储在Vue的响应式数据中，页面刷新后丢失
2. **变换矩阵未保存**：`stage1Transform`、`kabschTransform`等变换矩阵信息未持久化
3. **模型重新加载**：页面刷新时模型重新从服务器加载，应用的是原始位置，未应用已完成的配准变换

## 修复方案

### 方案一：本地存储持久化（推荐）

#### 1. 添加配准状态序列化/反序列化函数

**文件**：`frontend/src/views/RtkMonitor.vue`

**在现有代码中添加以下函数**：


```javascript
// 在script setup中添加以下函数

// 序列化配准状态到本地存储
function saveAlignmentState() {
  const stateToSave = {
    stage1Complete: alignmentManager.value.stage1Complete,
    stage2Complete: alignmentManager.value.stage2Complete,
    bimBasePoint: alignmentManager.value.bimBasePoint ? {
      x: alignmentManager.value.bimBasePoint.x,
      y: alignmentManager.value.bimBasePoint.y,
      z: alignmentManager.value.bimBasePoint.z
    } : null,
    rtkBasePoint: alignmentManager.value.rtkBasePoint,
    stage1Transform: alignmentManager.value.stage1Transform.elements,
    kabschTransform: alignmentManager.value.kabschTransform.elements,
    finalTransform: alignmentManager.value.finalTransform.elements,
    alignmentError: alignmentManager.value.alignmentError,
    qualityAssessment: alignmentManager.value.qualityAssessment,
    pointPairs: pointPairs.value.map(pair => ({
      bimPoint: { x: pair.bimPoint.x, y: pair.bimPoint.y, z: pair.bimPoint.z },
      rtkPoint: { x: pair.rtkPoint.x, y: pair.rtkPoint.y, z: pair.rtkPoint.z }
    })),
    timestamp: Date.now()
  };
  
  localStorage.setItem('rtk_alignment_state', JSON.stringify(stateToSave));
  console.log('配准状态已保存到本地存储');
}

// 从本地存储恢复配准状态
function loadAlignmentState() {
  try {
    const savedState = localStorage.getItem('rtk_alignment_state');
    if (!savedState) return false;
    
    const state = JSON.parse(savedState);
    
    // 检查数据是否过期（可选：7天过期）
    const daysPassed = (Date.now() - state.timestamp) / (1000 * 60 * 60 * 24);
    if (daysPassed > 7) {
      console.log('配准状态已过期，清除本地存储');
      localStorage.removeItem('rtk_alignment_state');
      return false;
    }
    
    // 恢复配准状态
    alignmentManager.value.stage1Complete = state.stage1Complete;
    alignmentManager.value.stage2Complete = state.stage2Complete;
    
    // 恢复BIM基准点
    if (state.bimBasePoint) {
      alignmentManager.value.bimBasePoint = new THREE.Vector3(
        state.bimBasePoint.x,
        state.bimBasePoint.y,
        state.bimBasePoint.z
      );
    }
    
    // 恢复RTK基准点
    alignmentManager.value.rtkBasePoint = state.rtkBasePoint;
    
    // 恢复变换矩阵
    alignmentManager.value.stage1Transform.fromArray(state.stage1Transform);
    alignmentManager.value.kabschTransform.fromArray(state.kabschTransform);
    alignmentManager.value.finalTransform.fromArray(state.finalTransform);
    
    // 恢复误差信息
    alignmentManager.value.alignmentError = state.alignmentError;
    alignmentManager.value.qualityAssessment = state.qualityAssessment;
    
    // 恢复点对信息
    if (state.pointPairs) {
      pointPairs.value = state.pointPairs.map(pair => ({
        bimPoint: new THREE.Vector3(pair.bimPoint.x, pair.bimPoint.y, pair.bimPoint.z),
        rtkPoint: new THREE.Vector3(pair.rtkPoint.x, pair.rtkPoint.y, pair.rtkPoint.z)
      }));
    }
    
    console.log('配准状态已从本地存储恢复');
    return true;
  } catch (error) {
    console.error('恢复配准状态失败:', error);
    localStorage.removeItem('rtk_alignment_state');
    return false;
  }
}

// 清除保存的配准状态
function clearAlignmentState() {
  localStorage.removeItem('rtk_alignment_state');
  console.log('配准状态已清除');
}
```

#### 2. 修改模型加载函数以应用保存的变换

**修改 `loadModelToScene` 函数**：

```javascript
// 在loadModelToScene函数中，在模型添加到场景后添加以下代码

async function loadModelToScene(modelInfo) {
  // ... 现有的模型加载代码 ...
  
  // 在模型添加到场景后，应用保存的变换（如果存在）
  if (format === '.stl') {
    // STL加载完成后的回调中添加
    stlLoader.load(
      modelUrl,
      (geometry) => {
        // ... 现有的STL处理代码 ...
        
        // 添加到场景
        scene.value.add(mesh);
        loadedModels.value[modelInfo.id] = mesh;
        
        // 应用保存的变换
        applyAlignmentToModel(mesh);
        
        console.log(`STL模型 ${modelInfo.name} 加载成功`);
      },
      // ... 其他回调 ...
    );
  } else {
    // GLTF加载完成后的回调中添加
    gltfLoader.load(
      modelUrl,
      (gltf) => {
        // ... 现有的GLTF处理代码 ...
        
        // 添加到场景
        scene.value.add(model);
        loadedModels.value[modelInfo.id] = model;
        
        // 应用保存的变换
        applyAlignmentToModel(model);
        
        console.log(`模型 ${modelInfo.name} 加载成功`);
      },
      // ... 其他回调 ...
    );
  }
}

// 应用配准变换到单个模型
function applyAlignmentToModel(model) {
  // 如果阶段1完成，应用stage1变换
  if (alignmentManager.value.stage1Complete && alignmentManager.value.stage1Transform) {
    model.applyMatrix4(alignmentManager.value.stage1Transform);
  }
  
  // 如果阶段2完成，应用kabsch变换
  if (alignmentManager.value.stage2Complete && alignmentManager.value.kabschTransform) {
    model.applyMatrix4(alignmentManager.value.kabschTransform);
  }
}
```

#### 3. 修改配准相关函数以自动保存状态

**修改 `setBimBasePoint` 函数**：

```javascript
// 在setBimBasePoint函数末尾添加保存调用
function setBimBasePoint(vertex) {
  // ... 现有代码 ...
  
  ElMessage.success('BIM基准点已设置并对齐到原点');
  console.log('BIM基准点已设置:', vertex);
  
  // 保存配准状态
  saveAlignmentState();
}
```

**修改 `setRtkBasePoint` 函数**：

```javascript
// 在setRtkBasePoint函数末尾添加保存调用
function setRtkBasePoint(deviceId) {
  // ... 现有代码 ...
  
  ElMessage.success('RTK基准点已设置');
  console.log('RTK基准点已设置:', alignmentManager.value.rtkBasePoint);
  
  // 保存配准状态
  saveAlignmentState();
}
```

**修改 `completeStage1` 函数**：

```javascript
// 在completeStage1函数末尾添加保存调用
function completeStage1() {
  // ... 现有代码 ...
  
  ElMessage.success('阶段1配准完成！可以开始精确配准');
  
  // 保存配准状态
  saveAlignmentState();
}
```

**修改 `performKabschAlignment` 函数**：

```javascript
// 在performKabschAlignment函数末尾添加保存调用
async function performKabschAlignment() {
  // ... 现有代码 ...
  
  ElMessage.success({
    message: `精确配准完成！${qualityText}`,
    duration: 5000
  });
  
  // 保存配准状态
  saveAlignmentState();
  
  // ... 其余代码 ...
}
```

**修改 `resetStage1` 和重置相关函数**：

```javascript
// 在重置函数中清除保存的状态
function resetStage1() {
  // ... 现有重置代码 ...
  
  // 清除保存的配准状态
  clearAlignmentState();
}

// 添加完全重置配准的函数
function resetAllAlignment() {
  // 重置所有配准状态
  alignmentManager.value.stage1Complete = false;
  alignmentManager.value.stage2Complete = false;
  alignmentManager.value.bimBasePoint = null;
  alignmentManager.value.rtkBasePoint = null;
  alignmentManager.value.stage1Transform = new THREE.Matrix4();
  alignmentManager.value.kabschTransform = new THREE.Matrix4();
  alignmentManager.value.finalTransform = new THREE.Matrix4();
  alignmentManager.value.alignmentError = null;
  alignmentManager.value.qualityAssessment = null;
  pointPairs.value = [];
  
  // 清除保存的状态
  clearAlignmentState();
  
  // 重新加载所有模型到原始位置
  Object.values(loadedModels.value).forEach(model => {
    scene.value.remove(model);
  });
  loadedModels.value = {};
  loadBuildingModels();
  
  ElMessage.success('配准状态已完全重置');
}
```

#### 4. 修改mounted生命周期以恢复状态

**修改 onMounted 函数**：

```javascript
// 修改现有的onMounted函数
onMounted(async () => {
  // 初始化3D场景
  await nextTick();
  init3DScene();
  
  // 尝试恢复配准状态
  const stateRestored = loadAlignmentState();
  
  // 加载建筑模型（如果状态已恢复，模型加载时会自动应用变换）
  await loadBuildingModels();
  
  // 如果状态已恢复，显示提示信息
  if (stateRestored) {
    ElMessage.info({
      message: '已恢复上次的配准状态',
      duration: 3000
    });
  }
  
  // 连接WebSocket
  await fetchRtkDevices();
  
  refreshInterval.value = setInterval(fetchRtkDevices, 2000);
  
  // 模拟WebSocket连接状态
  setTimeout(() => {
    wsConnected.value = true;
  }, 1000);
});
```

#### 5. 添加手动清除配准状态的按钮（可选）

**在模板中添加清除按钮**：

```vue
<!-- 在配准状态总览部分添加清除按钮 -->
<div class="alignment-overview">
  <!-- 现有的状态显示代码 -->
  
  <!-- 添加清除配准状态的按钮 -->
  <el-button 
    v-if="alignmentManager.stage1Complete || alignmentManager.stage2Complete"
    size="small" 
    type="warning"
    @click="resetAllAlignment"
  >
    重置所有配准
  </el-button>
</div>
```

## 修改效果

### 优势
1. **状态持久化**：配准状态在页面刷新后不会丢失
2. **自动恢复**：页面重新加载时自动应用之前的配准变换
3. **数据完整性**：保存所有关键的配准信息，包括变换矩阵、点对数据等
4. **用户体验**：避免重复配准工作，提高效率

### 注意事项
1. **存储限制**：localStorage有大小限制（通常5-10MB），但配准数据很小不会有问题
2. **数据过期**：设置7天过期时间，避免长期存储过时数据
3. **错误处理**：包含完整的错误处理和数据验证
4. **兼容性**：支持现有的重置功能

## 确认修改

**请您确认是否同意按照此方案进行BIM基准点配准状态持久化修复？**

此方案将彻底解决刷新页面后配准状态丢失的问题，确保用户的配准工作成果得到保留。 