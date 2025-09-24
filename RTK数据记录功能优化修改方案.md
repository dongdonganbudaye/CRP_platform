# RTK数据记录功能优化修改方案

## 功能概述
优化RTK设备数据记录功能，实现开始记录时设置保存路径，每1000条数据自动导出，停止时自动导出剩余数据，无需用户再次确认保存路径。

## 主要变更

### 1. 功能流程调整

#### 1.1 开始记录流程（新）
1. 用户点击"开始记录数据"按钮
2. **立即弹出文件保存路径设置对话框**
3. 用户设置基础文件名和保存偏好
4. 确认后开始数据记录，按钮变为"停止记录数据"
5. 启动100ms间隔的定时器进行数据采集

#### 1.2 自动导出机制（新）
1. 每记录1000条数据时自动触发导出
2. 文件命名格式：`基础文件名_批次号.csv`
3. 导出过程不中断数据记录
4. 导出完成后清空已导出的数据，继续记录

#### 1.3 停止记录流程（新）
1. 用户点击"停止记录数据"按钮
2. 停止定时器，清除记录状态
3. **自动导出剩余数据（如果有）**
4. 无需用户确认，直接完成导出

### 2. 数据结构调整

#### 2.1 新增状态变量
```javascript
// 文件保存配置
const saveConfigDialogVisible = ref(false);
const baseSaveFileName = ref(''); // 基础文件名
const currentBatchNumber = ref({}); // 每个设备的批次号 {deviceId: number}
const saveDirectory = ref(''); // 保存目录（仅用于显示）

// 移除的状态变量
// saveDataDialogVisible - 不再需要停止时的确认对话框
// showFileNameInput - 不再需要
// currentSaveDevice - 不再需要
```

#### 2.2 文件命名规则
- **基础文件名**：用户设置的文件名前缀
- **批次文件名**：`基础文件名_batch_001.csv`, `基础文件名_batch_002.csv`
- **剩余数据文件名**：`基础文件名_batch_final.csv`（当停止时有剩余数据）

### 3. 界面调整

#### 3.1 保存配置对话框（新）
```vue
<!-- 保存配置对话框 -->
<el-dialog
  v-model="saveConfigDialogVisible"
  title="数据记录配置"
  width="450px"
  class="save-config-dialog"
  :close-on-click-modal="false"
>
  <div class="save-config-content">
    <p>配置数据文件保存设置：</p>
    
    <el-form label-width="100px">
      <el-form-item label="基础文件名">
        <el-input 
          v-model="baseSaveFileName" 
          placeholder="例如：RTK_测试数据"
        />
        <div class="filename-preview">
          预览：{{ baseSaveFileName || '文件名' }}_batch_001.csv
        </div>
      </el-form-item>
      
      <el-form-item label="导出说明">
        <div class="export-info">
          <p>• 每1000条数据自动导出一个文件</p>
          <p>• 停止记录时自动导出剩余数据</p>
          <p>• 文件将下载到浏览器默认下载文件夹</p>
        </div>
      </el-form-item>
    </el-form>
  </div>
  
  <template #footer>
    <span class="dialog-footer">
      <el-button @click="cancelSaveConfig">取消</el-button>
      <el-button @click="confirmSaveConfig" type="primary">
        开始记录
      </el-button>
    </span>
  </template>
</el-dialog>
```

#### 3.2 移除的界面元素
- 原有的数据保存确认对话框
- 文件名输入步骤
- 保存/不保存的选择按钮

### 4. 核心方法修改

#### 4.1 开始记录方法（重构）
```javascript
// 显示保存配置对话框
function showSaveConfigDialog(deviceId) {
  const device = rtkDevices.value[deviceId];
  if (!device) return;
  
  // 生成默认文件名
  baseSaveFileName.value = `RTK_${device.name || deviceId}_${new Date().toISOString().slice(0, 10)}`;
  currentRecordingDeviceId.value = deviceId;
  saveConfigDialogVisible.value = true;
}

// 确认配置并开始记录
function confirmSaveConfig() {
  if (!baseSaveFileName.value.trim()) {
    ElMessage.warning('请输入文件名');
    return;
  }
  
  const deviceId = currentRecordingDeviceId.value;
  saveConfigDialogVisible.value = false;
  
  // 初始化批次号
  currentBatchNumber.value[deviceId] = 1;
  
  // 开始实际的数据记录
  startDataRecording(deviceId);
}
```

#### 4.2 自动导出机制（新）
```javascript
// 检查是否需要自动导出
function checkAutoExport(deviceId) {
  const data = recordedData.value[deviceId];
  if (!data || data.length < 1000) return;
  
  // 提取前1000条数据
  const exportData = data.splice(0, 1000);
  const batchNumber = currentBatchNumber.value[deviceId] || 1;
  
  // 生成批次文件名
  const filename = `${baseSaveFileName.value}_batch_${String(batchNumber).padStart(3, '0')}`;
  
  // 自动导出
  exportDataToCSV(exportData, filename);
  
  // 更新批次号
  currentBatchNumber.value[deviceId]++;
  
  console.log(`设备 ${deviceId} 自动导出第 ${batchNumber} 批数据，${exportData.length} 条记录`);
}
```

#### 4.3 停止记录方法（重构）
```javascript
// 停止数据记录（自动导出剩余数据）
function stopDataRecording(deviceId) {
  const device = rtkDevices.value[deviceId];
  if (!device) return;
  
  try {
    // 清除定时器
    if (dataRecordIntervals.value[deviceId]) {
      clearInterval(dataRecordIntervals.value[deviceId]);
      delete dataRecordIntervals.value[deviceId];
    }
    
    // 更新设备状态
    dataRecordingDevices.value.delete(deviceId);
    device.dataRecording = false;
    
    const remainingData = recordedData.value[deviceId] || [];
    const totalRecorded = (currentBatchNumber.value[deviceId] - 1) * 1000 + remainingData.length;
    
    // 自动导出剩余数据
    if (remainingData.length > 0) {
      const filename = `${baseSaveFileName.value}_batch_final`;
      exportDataToCSV(remainingData, filename);
      ElMessage.success(`记录完成！共记录 ${totalRecorded} 条数据，剩余 ${remainingData.length} 条已导出`);
    } else {
      ElMessage.success(`记录完成！共记录 ${totalRecorded} 条数据`);
    }
    
    // 清理数据
    delete recordedData.value[deviceId];
    delete recordingStartTimes.value[deviceId];
    delete currentBatchNumber.value[deviceId];
    
  } catch (error) {
    console.error('停止数据记录失败:', error);
    ElMessage.error('停止数据记录失败');
  }
}
```

### 5. 用户体验优化

#### 5.1 进度指示
- 显示当前批次号
- 显示当前批次已记录条数
- 显示总记录条数

#### 5.2 导出反馈
- 自动导出时的轻量提示（不打断用户）
- 完成记录时的汇总信息
- 文件下载状态提示

#### 5.3 错误处理
- 文件名验证
- 导出失败重试机制
- 内存不足时的处理

### 6. 性能优化

#### 6.1 内存管理
- 每次导出后立即清空已导出数据
- 避免大量数据堆积在内存中
- 限制单批次最大数据量

#### 6.2 导出优化
- 异步导出，不阻塞数据记录
- 批量处理，提高导出效率
- 错误恢复机制

### 7. 兼容性说明

#### 7.1 向后兼容
- 保持现有轨迹记录功能不变
- 保持设备管理功能不变
- 保持3D可视化功能不变

#### 7.2 浏览器兼容
- 支持现代浏览器的文件下载API
- 自动处理文件名冲突
- 支持大文件下载

### 8. 具体修改内容

#### 8.1 需要修改的方法
1. `toggleDataRecording()` - 调整为显示配置对话框
2. `startDataRecording()` - 简化，移除对话框逻辑
3. `stopDataRecording()` - 重构为自动导出
4. `recordDeviceData()` - 添加自动导出检查
5. 移除相关方法：
   - `showSaveDataDialog()`
   - `confirmSaveData()`
   - `cancelSaveData()`
   - `discardData()`
   - `getCurrentRecordedDataCount()`
   - `getRecordingDuration()`

#### 8.2 需要添加的方法
1. `showSaveConfigDialog()` - 显示配置对话框
2. `confirmSaveConfig()` - 确认配置
3. `cancelSaveConfig()` - 取消配置
4. `checkAutoExport()` - 检查自动导出
5. `getBatchInfo()` - 获取批次信息

#### 8.3 需要修改的状态变量
- 移除：`saveDataDialogVisible`, `showFileNameInput`, `currentSaveDevice`, `currentSaveDeviceId`, `isExporting`
- 添加：`saveConfigDialogVisible`, `baseSaveFileName`, `currentBatchNumber`, `currentRecordingDeviceId`

### 9. 测试要点

#### 9.1 功能测试
- 验证1000条数据自动导出的准确性
- 测试多批次文件命名的正确性
- 验证剩余数据的正确导出

#### 9.2 性能测试
- 长时间记录的内存使用
- 大量设备同时记录
- 高频数据记录的稳定性

#### 9.3 边界测试
- 文件名冲突处理
- 网络中断时的数据保护
- 浏览器刷新时的状态恢复

---

**请确认以上修改方案是否符合您的需求，如有调整建议请告知，确认后我将开始实施代码修改。** 