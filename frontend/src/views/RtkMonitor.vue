<template>
  <div class="rtk-monitor-dashboard">
    <!-- 顶部状态栏 -->
    <div class="status-bar">
      <div class="status-item">
        <div class="status-icon online"></div>
        <span>系统在线</span>
      </div>
      <div class="status-item">
        <div class="status-icon" :class="wsConnected ? 'online' : 'offline'"></div>
        <span>{{ wsConnected ? 'WebSocket已连接' : 'WebSocket未连接' }}</span>
      </div>
      <div class="status-item">
        <div class="status-value">{{ Object.keys(rtkDevices).length }}</div>
        <span>在线设备</span>
      </div>
      <div class="status-item">
        <div class="status-value">{{ Object.values(rtkDevices).filter(d => d.isBaseStation).length }}</div>
        <span>基站数量</span>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 左侧控制面板 -->
      <div class="control-panel">
        <div class="panel-section">
          <h3 class="section-title">设备管理</h3>
          <div class="scan-controls">
            <el-button 
              type="primary" 
              class="scan-btn"
              @click="scanRtkDevices" 
              :loading="isScanning"
              :disabled="isScanning"
            >
              <i class="el-icon-search"></i>
              {{ isScanning ? '扫描中...' : '扫描RTK设备' }}
            </el-button>
            <el-button 
              type="success" 
              class="manual-add-btn"
              @click="showManualAddDialog"
              :disabled="isScanning"
            >
              <i class="el-icon-plus"></i>
              手动添加设备
            </el-button>
          </div>
          
          <!-- 扫描结果 -->
          <div v-if="scanResults.length > 0" class="scan-results">
            <h4>发现的设备</h4>
            <div class="device-grid">
              <div v-for="device in scanResults" :key="device.id" class="device-card" @click="showConfigDialog(device)">
                <div class="device-icon">
                  <i class="el-icon-position"></i>
                </div>
                <div class="device-info">
                  <div class="device-id">{{ device.id }}</div>
                  <div class="device-ip">{{ device.ip }}</div>
                </div>
                <div class="device-signal">
                  <div class="signal-bars">
                    <div class="bar active"></div>
                    <div class="bar active"></div>
                    <div class="bar active"></div>
                    <div class="bar"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 已注册设备 -->
        <div class="panel-section">
          <h3 class="section-title">已注册设备</h3>
          <div class="registered-devices">
            <div v-for="device in Object.values(rtkDevices)" :key="device.id" 
                 class="registered-device" 
                 :class="{ 
                   active: device.connected,
                   'rtk-selectable': addingPointPair && addPointPairStep === 2
                 }"
                 @click="handleDeviceClick(device)">
              <div class="device-header">
                <div class="device-name">
                  <!-- 颜色指示器 -->
                  <div class="device-color-indicator" 
                       :style="{ backgroundColor: getDeviceColor(device.id, device.isBaseStation).css }"
                       :title="`设备颜色: ${getDeviceColor(device.id, device.isBaseStation).name}`">
                  </div>
                  {{ device.name || device.id }}
                </div>
                <div class="device-status" :class="device.connected ? 'online' : 'offline'">
                  {{ device.connected ? '在线' : '离线' }}
                </div>
              </div>
              <div class="device-details">
                <div class="detail-item">
                  <span class="label">IP:</span>
                  <span class="value">{{ device.ip }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">类型:</span>
                  <span class="value" :class="device.isBaseStation ? 'base-station' : 'mobile-station'">
                    {{ device.isBaseStation ? '基站' : '移动站' }}
                  </span>
                </div>
                <div class="detail-item">
                  <span class="label">编号:</span>
                  <span class="value">{{ device.deviceNumber || '-' }}</span>
                </div>
              </div>
              <div v-if="device.connected && device.data" class="position-data">
                <div class="coordinate">
                  <span class="coord-label">E:</span>
                  <span class="coord-value">{{ getDisplayCoordinate(device, 'e')?.toFixed(3) }}m</span>
                </div>
                <div class="coordinate">
                  <span class="coord-label">N:</span>
                  <span class="coord-value">{{ getDisplayCoordinate(device, 'n')?.toFixed(3) }}m</span>
                </div>
                <div class="coordinate">
                  <span class="coord-label">U:</span>
                  <span class="coord-value">{{ getDisplayCoordinate(device, 'u')?.toFixed(3) }}m</span>
                </div>
              </div>
              <!-- 可视化控制 -->
              <div class="visualization-control">
                <el-switch 
                  v-model="device.showIn3D" 
                  size="small"
                  active-text="3D显示" 
                  inactive-text="隐藏"
                  :active-value="true"
                  :inactive-value="false"
                  @change="(value) => toggleVisualization(device.id, value)"
                  @click.stop
                />
              </div>
              <!-- 轨迹控制按钮 -->
              <div v-if="device.connected" class="trajectory-controls">
                <!-- 数据记录控制按钮 -->
                <el-button 
                  size="small" 
                  :type="device.dataRecording ? 'danger' : 'primary'"
                  @click="toggleDataRecording(device.id)"
                  class="data-record-btn"
                >
                  {{ device.dataRecording ? '停止记录数据' : '开始记录数据' }}
                </el-button>
                <el-button 
                  size="small" 
                  :type="device.recording ? 'danger' : 'success'"
                  @click="toggleRecording(device.id)"
                  class="trajectory-btn"
                >
                  {{ device.recording ? '停止记录轨迹' : '开始记录轨迹' }}
                </el-button>
                <el-button 
                  size="small" 
                  type="info"
                  @click="clearTrajectory(device.id)"
                  class="trajectory-btn"
                >
                  清除轨迹
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- 建筑模型管理 -->
        <div class="panel-section">
          <h3 class="section-title">建筑模型管理</h3>
          
          <!-- 模型上传 -->
          <div class="model-upload-section">
            <el-upload
              action="#"
              :before-upload="handleModelUpload"
              :show-file-list="false"
              accept=".gltf,.glb,.obj,.stl"
              :disabled="isUploadingModel"
            >
              <el-button type="primary" :loading="isUploadingModel">
                <i class="el-icon-upload"></i>
                {{ isUploadingModel ? '上传中...' : '上传模型' }}
              </el-button>
            </el-upload>
            <div class="upload-tip">
              支持格式：GLTF, GLB, OBJ, STL
            </div>
          </div>
          
          <!-- 模型显示控制 -->
          <div class="model-controls">
            <div class="control-item">
              <el-switch 
                v-model="showModels" 
                active-text="显示模型" 
                inactive-text="隐藏模型"
                @change="updateModelVisibility"
              />
            </div>
            
            <div class="control-item">
              <span class="control-label">透明度:</span>
              <el-slider 
                v-model="modelOpacity" 
                :min="0" 
                :max="1" 
                :step="0.1"
                @change="updateModelOpacity"
              />
            </div>
            
            <div class="control-item">
              <span class="control-label">显示模式:</span>
              <el-radio-group v-model="modelLayerMode" size="small" @change="updateModelLayerMode">
                <el-radio-button value="overlay">叠加</el-radio-button>
                <el-radio-button value="design">仅设计</el-radio-button>
                <el-radio-button value="actual">仅实际</el-radio-button>
              </el-radio-group>
            </div>
          </div>
          
          <!-- 已加载的模型列表 -->
          <div class="loaded-models-list" v-if="buildingModels.length > 0">
            <h4>已加载模型</h4>
            <div v-for="model in buildingModels" :key="model.id" class="model-item">
              <div class="model-info">
                <span class="model-name">{{ model.name }}</span>
                <span class="model-size">{{ model.format }}</span>
              </div>
              <div class="model-actions">
                <!-- 新增：单独显示/隐藏按钮 -->
                <el-button 
                  size="small" 
                  :type="model.visible !== false ? 'success' : 'warning'"
                  circle
                  @click="toggleModelVisibility(model.id)"
                  :title="model.visible !== false ? '隐藏模型' : '显示模型'"
                >
                  <i :class="model.visible !== false ? 'el-icon-view' : 'el-icon-hide'"></i>
                </el-button>
                
                <!-- 现有的编辑按钮 -->
                <el-button 
                  size="small" 
                  type="info"
                  circle
                  @click="editModel(model)"
                >
                  <i class="el-icon-edit"></i>
                </el-button>
                
                <!-- 现有的删除按钮 -->
                <el-button 
                  size="small" 
                  type="danger"
                  circle
                  @click="deleteModel(model.id)"
                >
                  <i class="el-icon-delete"></i>
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- 两阶段配准控制面板 -->
        <div class="panel-section">
          <h3 class="section-title">模型配准</h3>
          
          <!-- 阶段1：基准点配准 -->
          <div class="alignment-stage">
            <h4 class="stage-title">
              <i class="el-icon-location"></i>
              阶段1: 基准点配准
              <span v-if="alignmentManager.stage1Complete" class="status-badge success">✓</span>
            </h4>
            
            <!-- BIM基准点设置 -->
            <div class="base-point-section">
              <div class="section-header">
                <span class="section-label">BIM基准点</span>
                <el-switch 
                  v-model="vertexSelectionMode" 
                  size="small"
                  active-text="顶点选择" 
                  @change="toggleVertexSelection"
                />
              </div>
              
              <div v-if="vertexSelectionMode" class="vertex-controls">
                <div class="control-item">
                  <span class="control-label">顶点密度:</span>
                  <el-radio-group v-model="vertexDensity" size="small" @change="updateVertexDisplay">
                    <el-radio-button value="low">低</el-radio-button>
                    <el-radio-button value="medium">中</el-radio-button>
                    <el-radio-button value="high">高</el-radio-button>
                  </el-radio-group>
                </div>
              </div>
              
              <div v-if="alignmentManager.bimBasePoint" class="base-point-info">
                <div class="info-item">
                  <span class="info-label">基准点坐标:</span>
                  <span class="info-value">
                    ({{ alignmentManager.bimBasePoint.x.toFixed(3) }}, 
                     {{ alignmentManager.bimBasePoint.y.toFixed(3) }}, 
                     {{ alignmentManager.bimBasePoint.z.toFixed(3) }})
                  </span>
                </div>
                <div class="info-item">
                  <span class="info-label">状态:</span>
                  <span class="info-value success">已对齐到原点</span>
                </div>
              </div>
            </div>
            
            <!-- RTK基准点设置 -->
            <div class="base-point-section">
              <div class="section-header">
                <span class="section-label">RTK基准点</span>
              </div>
              
              <div class="rtk-base-controls">
                <el-select 
                  v-model="selectedRtkBaseDevice" 
                  placeholder="选择RTK基准设备"
                  size="small"
                  @change="setRtkBasePoint"
                >
                  <el-option
                    v-for="device in availableRtkDevices"
                    :key="device.id"
                    :label="device.name || device.id"
                    :value="device.id"
                  >
                    <span>{{ device.name || device.id }}</span>
                    <span style="float: right; color: #8492a6; font-size: 13px">
                      {{ device.connected ? '在线' : '离线' }}
                    </span>
                  </el-option>
                </el-select>
              </div>
              
              <div v-if="alignmentManager.rtkBasePoint" class="base-point-info">
                <div class="info-item">
                  <span class="info-label">基准设备:</span>
                  <span class="info-value">{{ alignmentManager.rtkBasePoint.deviceId }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">原始坐标:</span>
                  <span class="info-value">
                    E:{{ alignmentManager.rtkBasePoint.originalCoords.e.toFixed(3) }}
                    N:{{ alignmentManager.rtkBasePoint.originalCoords.n.toFixed(3) }}
                    U:{{ alignmentManager.rtkBasePoint.originalCoords.u.toFixed(3) }}
                  </span>
                </div>
                <div class="info-item">
                  <span class="info-label">状态:</span>
                  <span class="info-value success">坐标系已重置</span>
                </div>
              </div>
            </div>
            
            <div class="stage-actions">
              <el-button 
                type="primary" 
                size="small"
                @click="completeStage1"
                :disabled="!canCompleteStage1"
              >
                完成基准点配准
              </el-button>
              <el-button 
                size="small"
                @click="resetStage1"
                :disabled="!alignmentManager.stage1Complete"
              >
                重置
              </el-button>
            </div>
          </div>
          
          <!-- 阶段2：精确配准 -->
          <div class="alignment-stage" :class="{ disabled: !alignmentManager.stage1Complete }">
            <h4 class="stage-title">
              <i class="el-icon-s-grid"></i>
              阶段2: 精确配准 (Kabsch算法)
              <span v-if="alignmentManager.stage2Complete" class="status-badge success">✓</span>
              <span v-else-if="!alignmentManager.stage1Complete" class="status-badge disabled">需要完成阶段1</span>
            </h4>
            
            <!-- 特征点管理 -->
            <div class="feature-points-section">
              <div class="section-header">
                <span class="section-label">特征点对 ({{ pointPairs.length }}/{{ minPointPairs }})</span>
                <el-button 
                  size="small" 
                  type="success"
                  @click="startAddingPointPair"
                  :disabled="!alignmentManager.stage1Complete || addingPointPair"
                >
                  <i class="el-icon-plus"></i>
                  添加点对
                </el-button>
              </div>
              
              <div v-if="addingPointPair" class="adding-point-pair">
                <div class="add-point-step">
                  <span class="step-label">步骤 {{ addPointPairStep }}/2:</span>
                  <span class="step-desc">
                    {{ addPointPairStep === 1 ? '点击BIM模型上的特征点' : '选择对应的RTK点' }}
                  </span>
                </div>
                <el-button size="small" @click="cancelAddingPointPair">取消</el-button>
              </div>
              
              <!-- 点对列表 -->
              <div class="point-pairs-list">
                <div v-for="(pair, index) in pointPairs" :key="pair.id" class="point-pair-item">
                  <div class="pair-header">
                    <span class="pair-name">{{ pair.name || `点对${index + 1}` }}</span>
                    <div class="pair-actions">
                      <el-button size="mini" type="text" @click="editPointPair(pair)">
                        <i class="el-icon-edit"></i>
                      </el-button>
                      <el-button size="mini" type="text" @click="deletePointPair(pair.id)">
                        <i class="el-icon-delete"></i>
                      </el-button>
                    </div>
                  </div>
                  <div class="pair-coords">
                    <div class="coord-item">
                      <span class="coord-label">BIM:</span>
                      <span class="coord-value">
                        ({{ pair.bimPoint.x.toFixed(2) }}, {{ pair.bimPoint.y.toFixed(2) }}, {{ pair.bimPoint.z.toFixed(2) }})
                      </span>
                    </div>
                    <div class="coord-item">
                      <span class="coord-label">RTK:</span>
                      <span class="coord-value">
                        ({{ pair.rtkPoint.x.toFixed(2) }}, {{ pair.rtkPoint.y.toFixed(2) }}, {{ pair.rtkPoint.z.toFixed(2) }})
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div v-if="pointPairs.length < minPointPairs" class="point-pairs-hint">
                <i class="el-icon-info"></i>
                至少需要 {{ minPointPairs }} 个点对进行精确配准
              </div>
            </div>
            
            <!-- 配准控制 -->
            <div class="alignment-controls">
              <el-button 
                type="primary" 
                size="small"
                @click="performKabschAlignment"
                :disabled="!canPerformKabsch"
                :loading="performingAlignment"
              >
                {{ performingAlignment ? '配准中...' : '执行精确配准' }}
              </el-button>
              <el-button 
                size="small"
                @click="previewAlignment"
                :disabled="!canPerformKabsch"
              >
                预览配准
              </el-button>
              <el-button 
                size="small"
                @click="resetStage2"
                :disabled="!alignmentManager.stage2Complete"
              >
                重置配准
              </el-button>
            </div>
            
            <!-- 配准结果 -->
            <div v-if="alignmentManager.alignmentError !== null" class="alignment-results">
              <div class="result-item">
                <span class="result-label">RMS误差:</span>
                <span class="result-value" :class="getErrorClass(alignmentManager.alignmentError.rms)">
                  {{ alignmentManager.alignmentError.rms.toFixed(4) }}m
                </span>
              </div>
              <div class="result-item">
                <span class="result-label">最大误差:</span>
                <span class="result-value" :class="getErrorClass(alignmentManager.alignmentError.max)">
                  {{ alignmentManager.alignmentError.max.toFixed(4) }}m
                </span>
              </div>
              <div class="result-item">
                <span class="result-label">平均误差:</span>
                <span class="result-value" :class="getErrorClass(alignmentManager.alignmentError.mean)">
                  {{ alignmentManager.alignmentError.mean.toFixed(4) }}m
                </span>
              </div>
              <div class="result-item">
                <span class="result-label">标准差:</span>
                <span class="result-value">{{ alignmentManager.alignmentError.std.toFixed(4) }}m</span>
              </div>
              <div class="result-item">
                <span class="result-label">旋转角度:</span>
                <span class="result-value">{{ alignmentManager.alignmentError.rotation.toFixed(2) }}°</span>
              </div>
              
              <!-- 质量评估 -->
              <div v-if="alignmentManager.qualityAssessment" class="quality-assessment">
                <div class="quality-score">
                  <span class="score-label">配准质量评分:</span>
                  <span class="score-value" :class="getQualityScoreClass(alignmentManager.qualityAssessment.score)">
                    {{ alignmentManager.qualityAssessment.score }}/100
                  </span>
                </div>
                <div v-if="alignmentManager.qualityAssessment.recommendations.length > 0" class="recommendations">
                  <div class="recommendations-title">改进建议:</div>
                  <ul class="recommendations-list">
                    <li v-for="(rec, index) in alignmentManager.qualityAssessment.recommendations" :key="index">
                      {{ rec }}
                    </li>
                  </ul>
                </div>
              </div>
              
              <div class="result-actions">
                <el-button size="small" type="info" @click="showDetailedReport">
                  详细报告
                </el-button>
                <el-button size="small" type="success" @click="showErrorDistribution">
                  误差分布
                </el-button>
              </div>
            </div>
          </div>
          
          <!-- 配准状态总览 -->
          <div class="alignment-overview">
            <div class="overview-item">
              <span class="overview-label">阶段1:</span>
              <span class="overview-status" :class="{ success: alignmentManager.stage1Complete }">
                {{ alignmentManager.stage1Complete ? '✓ 基准点已对齐' : '○ 待完成' }}
              </span>
            </div>
            <div class="overview-item">
              <span class="overview-label">阶段2:</span>
              <span class="overview-status" :class="{ success: alignmentManager.stage2Complete }">
                {{ alignmentManager.stage2Complete ? '✓ 精配准完成' : '○ 待完成' }}
              </span>
            </div>
            <div v-if="alignmentManager.stage2Complete" class="overview-item">
              <span class="overview-label">总体精度:</span>
              <span class="overview-status" :class="getAccuracyClass()">
                {{ getAccuracyText() }}
              </span>
            </div>
            <el-button 
              v-if="alignmentManager.stage2Complete"
              size="small" 
              type="success"
              @click="exportAlignmentReport"
            >
              导出配准报告
            </el-button>
          </div>
        </div>
      </div>

      <!-- 右侧3D可视化 -->
      <div class="visualization-panel">
        <div class="panel-header">
          <h2>3D可视化</h2>
        </div>
                 <div ref="container3d" class="three-container"></div>
      </div>
    </div>

    <!-- 数据记录配置对话框 -->
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

    <!-- 设备配置对话框 -->
    <el-dialog
      v-model="configDialogVisible"
      title="RTK设备配置"
      width="500px"
      class="config-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="configForm" :rules="configRules" ref="configFormRef" label-width="100px">
        <el-form-item label="设备ID" prop="deviceId">
          <el-input v-model="configForm.deviceId" :disabled="isEditing" />
        </el-form-item>
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="configForm.name" placeholder="请输入设备名称" />
        </el-form-item>
        <el-form-item label="IP地址" prop="ip">
          <el-input v-model="configForm.ip" :disabled="isEditing" />
        </el-form-item>
        <el-form-item label="设备编号" prop="deviceNumber">
          <el-input v-model="configForm.deviceNumber" placeholder="请输入设备编号" />
        </el-form-item>
        <el-form-item label="设备类型">
          <el-radio-group v-model="configForm.isBaseStation">
            <el-radio :value="false">移动站</el-radio>
            <el-radio :value="true">基站</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="3D可视化">
          <el-switch 
            v-model="configForm.showIn3D" 
            active-text="显示" 
            inactive-text="隐藏"
            :active-value="true"
            :inactive-value="false"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="configDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveDeviceConfig" :loading="isSaving">
            {{ isEditing ? '保存' : '添加' }}
          </el-button>
          <el-button 
            v-if="isEditing" 
            type="warning" 
            @click="cleanupDevice"
          >
            清理状态
          </el-button>
          <el-button 
            v-if="isEditing" 
            type="danger" 
            @click="deleteDevice"
          >
            删除设备
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, nextTick, markRaw } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import axios from 'axios';
import { apiBaseUrl } from '@/config';
import { calculateKabschAlignment, assessAlignmentQuality } from '@/utils/kabsch';

// 数据状态
const rtkDevices = ref({});
const scanResults = ref([]);
const isScanning = ref(false);

const wsConnected = ref(false);
const is3dViewReady = ref(false);
const container3d = ref(null);
const showGrid = ref(true);

// 建筑模型状态
const buildingModels = ref([]);
const loadedModels = ref({});
const gltfLoader = new GLTFLoader();
const stlLoader = new STLLoader();
const isUploadingModel = ref(false);
const modelOpacity = ref(0.7);
const showModels = ref(true);
const modelLayerMode = ref('overlay'); // 'overlay', 'design', 'actual'

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

// 场景状态
const scene = ref(null);
const camera = ref(null);
const renderer = ref(null);
const controls = ref(null);
const deviceMeshes = ref({});
const baseMeshes = ref([]);
const gridHelper = ref(null);
const trajectoryLines = ref({});
const trajectoryPoints = ref({});

// 配置对话框状态
const configDialogVisible = ref(false);
const isEditing = ref(false);
const isSaving = ref(false);
const configFormRef = ref(null);
const configForm = ref({
  deviceId: '',
  name: '',
  ip: '',
  deviceNumber: '',
  isBaseStation: false,
  showIn3D: true
});

const configRules = {
  deviceId: [
    { required: true, message: '请输入设备ID', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入设备名称', trigger: 'blur' }
  ],
  ip: [
    { required: true, message: '请输入IP地址', trigger: 'blur' },
    { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: 'IP地址格式不正确', trigger: 'blur' }
  ],
  deviceNumber: [
    { required: true, message: '请输入设备编号', trigger: 'blur' }
  ]
};

// 刷新间隔
const refreshInterval = ref(null);

// 两阶段配准系统
const alignmentManager = ref({
  stage1Complete: false,
  stage2Complete: false,
  bimBasePoint: null,
  rtkBasePoint: null,
  stage1Transform: new THREE.Matrix4(),
  kabschTransform: new THREE.Matrix4(),
  finalTransform: new THREE.Matrix4(),
  alignmentError: null,
  qualityAssessment: null
});

// 顶点选择相关
const vertexSelectionMode = ref(false);
const vertexDensity = ref('medium');
const modelVertices = ref([]);
const vertexMeshes = ref([]);
const highlightedVertex = ref(null);

// RTK基准点选择
const selectedRtkBaseDevice = ref(null);
const availableRtkDevices = computed(() => {
  return Object.values(rtkDevices.value).filter(device => !device.isBaseStation);
});

// 阶段2：特征点对管理
const pointPairs = ref([]);
const minPointPairs = ref(3);
const addingPointPair = ref(false);
const addPointPairStep = ref(1);
const currentPointPair = ref(null);
const performingAlignment = ref(false);

// 模型变换状态追踪
const modelTransformApplied = ref(false); // 追踪模型是否已应用配准变换

// 数据记录功能状态
const dataRecordingDevices = ref(new Set()); // 正在记录数据的设备集合
const dataRecordIntervals = ref({}); // 存储各设备的定时器
const recordedData = ref({}); // 存储记录的数据 {deviceId: [dataArray]}
const recordingStartTimes = ref({}); // 存储开始记录的时间

// 数据记录配置状态
const saveConfigDialogVisible = ref(false);
const baseSaveFileName = ref(''); // 基础文件名
const currentBatchNumber = ref({}); // 每个设备的批次号 {deviceId: number}
const currentRecordingDeviceId = ref(''); // 当前正在配置的设备ID

// 计算属性
const canCompleteStage1 = computed(() => {
  return alignmentManager.value.bimBasePoint && alignmentManager.value.rtkBasePoint;
});

const canPerformKabsch = computed(() => {
  return alignmentManager.value.stage1Complete && pointPairs.value.length >= minPointPairs.value;
});

// 初始化3D场景
function init3DScene() {
  if (!container3d.value) return;
  
  // 创建场景
  scene.value = markRaw(new THREE.Scene());
  scene.value.background = new THREE.Color(0xe0e0e0);
  
  // 创建相机
  camera.value = markRaw(new THREE.PerspectiveCamera(
    75, 
    container3d.value.clientWidth / container3d.value.clientHeight, 
    0.1, 
    1000
  ));
  camera.value.position.set(15, 15, 15);
  camera.value.lookAt(0, 0, 0);
  
  // 创建渲染器
  renderer.value = markRaw(new THREE.WebGLRenderer({ antialias: true }));
  renderer.value.setSize(container3d.value.clientWidth, container3d.value.clientHeight);
  renderer.value.shadowMap.enabled = true;
  renderer.value.shadowMap.type = THREE.PCFSoftShadowMap;
  container3d.value.appendChild(renderer.value.domElement);
  
  // 创建轨道控制器
  controls.value = markRaw(new OrbitControls(camera.value, renderer.value.domElement));
  controls.value.enableDamping = true;
  controls.value.dampingFactor = 0.05;
  controls.value.target.set(0, 0, 0);
  controls.value.minDistance = 5;
  controls.value.maxDistance = 100;
  
  // 添加网格
  gridHelper.value = markRaw(new THREE.GridHelper(20, 20, 0xffffff, 0x333333));
  gridHelper.value.material.transparent = true;
  gridHelper.value.material.opacity = 0.3;
  scene.value.add(gridHelper.value);
  
  // 添加自定义坐标轴 - E轴方向调整
  // E轴 (红色) - 指向X正方向
  const eAxisGeometry = markRaw(new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(2, 0, 0)  // E轴指向X正方向
  ]));
  const eAxisMaterial = markRaw(new THREE.LineBasicMaterial({ color: 0xff0000 }));
  const eAxis = markRaw(new THREE.Line(eAxisGeometry, eAxisMaterial));
  scene.value.add(eAxis);
  
  // E轴箭头
  const eArrowGeometry = markRaw(new THREE.ConeGeometry(0.05, 0.2, 8));
  const eArrowMaterial = markRaw(new THREE.MeshBasicMaterial({ color: 0xff0000 }));
  const eArrow = markRaw(new THREE.Mesh(eArrowGeometry, eArrowMaterial));
  eArrow.position.set(2, 0, 0);
  eArrow.rotateZ(-Math.PI / 2); // 旋转箭头指向正确方向
  scene.value.add(eArrow);
  
  // N轴 (绿色) - 指向Z负方向
  const nAxisGeometry = markRaw(new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(0, 0, -2)
  ]));
  const nAxisMaterial = markRaw(new THREE.LineBasicMaterial({ color: 0x00ff00 }));
  const nAxis = markRaw(new THREE.Line(nAxisGeometry, nAxisMaterial));
  scene.value.add(nAxis);
  
  // N轴箭头
  const nArrowGeometry = markRaw(new THREE.ConeGeometry(0.05, 0.2, 8));
  const nArrowMaterial = markRaw(new THREE.MeshBasicMaterial({ color: 0x00ff00 }));
  const nArrow = markRaw(new THREE.Mesh(nArrowGeometry, nArrowMaterial));
  nArrow.position.set(0, 0, -2);
  nArrow.rotateX(-Math.PI / 2); // 旋转箭头指向正确方向
  scene.value.add(nArrow);
  
  // U轴 (蓝色) - 指向Y正方向
  const uAxisGeometry = markRaw(new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(0, 2, 0)
  ]));
  const uAxisMaterial = markRaw(new THREE.LineBasicMaterial({ color: 0x0000ff }));
  const uAxis = markRaw(new THREE.Line(uAxisGeometry, uAxisMaterial));
  scene.value.add(uAxis);
  
  // U轴箭头
  const uArrowGeometry = markRaw(new THREE.ConeGeometry(0.05, 0.2, 8));
  const uArrowMaterial = markRaw(new THREE.MeshBasicMaterial({ color: 0x0000ff }));
  const uArrow = markRaw(new THREE.Mesh(uArrowGeometry, uArrowMaterial));
  uArrow.position.set(0, 2, 0);
  // U轴箭头默认向上，不需要旋转
  scene.value.add(uArrow);
  
  // 添加坐标轴标签 (E, N, U)
  // 创建文本几何体的函数
  function createAxisLabel(text, position, color) {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 32;
    const ctx = canvas.getContext('2d');
    
    // 清除画布，设置透明背景
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    ctx.fillStyle = color;
    ctx.font = 'bold 20px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 32, 16);
    
    const texture = markRaw(new THREE.CanvasTexture(canvas));
    const spriteMaterial = markRaw(new THREE.SpriteMaterial({ 
      map: texture,
      transparent: true,
      alphaTest: 0.1
    }));
    const sprite = markRaw(new THREE.Sprite(spriteMaterial));
    sprite.scale.set(0.5, 0.25, 1);
    sprite.position.copy(position);
    
    return sprite;
  }
  
  // 添加E、N、U标签
  const eLabel = createAxisLabel('E', new THREE.Vector3(2.5, 0, 0), '#ff0000');
  const nLabel = createAxisLabel('N', new THREE.Vector3(0, 0, -2.5), '#00ff00');
  const uLabel = createAxisLabel('U', new THREE.Vector3(0, 2.5, 0), '#0000ff');
  
  scene.value.add(eLabel);
  scene.value.add(nLabel);
  scene.value.add(uLabel);
  
  // 添加光源（全局日光 + 环境光）
  const hemiLight = markRaw(new THREE.HemisphereLight(0xffffff, 0x444444, 1.2)); // sky, ground, intensity
  scene.value.add(hemiLight);

  const ambientLight = markRaw(new THREE.AmbientLight(0xffffff, 0.6));
  scene.value.add(ambientLight);

  const directionalLight = markRaw(new THREE.DirectionalLight(0xffffff, 1.2));
  directionalLight.position.set(50, 80, 50); // simulate sun position
  directionalLight.castShadow = true;
  directionalLight.shadow.mapSize.width = 2048;
  directionalLight.shadow.mapSize.height = 2048;
  scene.value.add(directionalLight);
  
  // 动画循环
  function animate() {
    requestAnimationFrame(animate);
    controls.value.update();
    renderer.value.render(scene.value, camera.value);
  }
  
  animate();
  is3dViewReady.value = true;
  
  // 窗口大小变化处理
  function handleResize() {
    if (!container3d.value) return;
    camera.value.aspect = container3d.value.clientWidth / container3d.value.clientHeight;
    camera.value.updateProjectionMatrix();
    renderer.value.setSize(container3d.value.clientWidth, container3d.value.clientHeight);
  }
  
  window.addEventListener('resize', handleResize);
  
  onBeforeUnmount(() => {
    window.removeEventListener('resize', handleResize);
    if (renderer.value) {
      renderer.value.dispose();
      container3d.value.removeChild(renderer.value.domElement);
    }
  });
}

// 更新3D场景中的设备
function updateDevicesIn3D() {
  if (!scene.value) {
    console.log('3D场景未初始化');
    return;
  }
  
  console.log('开始更新3D场景，设备数量:', Object.keys(rtkDevices.value).length);
  
  // 清除旧的设备模型
  Object.values(deviceMeshes.value).forEach(mesh => {
    scene.value.remove(mesh);
  });
  baseMeshes.value.forEach(mesh => {
    scene.value.remove(mesh);
  });
  
  deviceMeshes.value = {};
  baseMeshes.value = [];
  
  // 不清除轨迹线，保持轨迹显示
  
  let visibleDeviceCount = 0;
  
  // 创建新的设备模型
  Object.values(rtkDevices.value).forEach(device => {
    console.log(`检查设备 ${device.id}:`, {
      connected: device.connected,
      hasData: !!device.data,
      showIn3D: device.showIn3D,
      data: device.data
    });
    
    // 只显示已连接、有数据且启用3D可视化的设备
    if (!device.connected || !device.data || !device.showIn3D) {
      console.log(`设备 ${device.id} 被跳过`);
      return;
    }
    
    visibleDeviceCount++;
    
    // 优先使用转换后的世界坐标，如果没有则使用原始坐标
    const position = markRaw(new THREE.Vector3());
    
    if (device.worldCoords) {
      // 使用已转换的世界坐标（相对于RTK基准点）
      position.set(
        device.worldCoords.x, // E轴直接映射到X轴
        device.worldCoords.y, // U轴直接映射到Y轴
        -device.worldCoords.z // N轴取反映射到Z轴
      );
    } else {
      // 回退到原始ENU坐标（配准前）
      position.set(
        device.data.e || 0, // E轴直接映射到X轴
        device.data.u || 0, // U轴直接映射到Y轴
        -(device.data.n || 0) // N轴取反映射到Z轴
      );
    }
    
    let geometry, material;
    const deviceColor = getDeviceColor(device.id, device.isBaseStation);
    
    if (device.isBaseStation) {
       // 基站：白色球体（缩小一半）
       geometry = markRaw(new THREE.SphereGeometry(0.15, 16, 16));
       material = markRaw(new THREE.MeshLambertMaterial({ 
         color: deviceColor.hex,
         emissive: 0x222222
       }));
       
       // 基站覆盖范围
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
       // 移动站：使用分配的颜色（缩小一半）
       geometry = markRaw(new THREE.SphereGeometry(0.1, 16, 16));
       material = markRaw(new THREE.MeshLambertMaterial({ 
         color: deviceColor.hex,
         emissive: 0x111111  // 使用固定的暗灰色发光，避免颜色干扰
       }));
     }
    
    const mesh = markRaw(new THREE.Mesh(geometry, material));
    mesh.position.copy(position);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    
    // 添加设备标签
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    
    // 绘制背景
    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
         // 绘制边框 - 使用设备分配的颜色
     ctx.strokeStyle = deviceColor.css;
     ctx.lineWidth = 2;
     ctx.strokeRect(2, 2, canvas.width - 4, canvas.height - 4);
    
    // 绘制文字
    ctx.fillStyle = 'white';
    ctx.font = 'bold 18px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(device.name || device.id, canvas.width / 2, canvas.height / 2);
    
    const texture = markRaw(new THREE.CanvasTexture(canvas));
    const spriteMaterial = markRaw(new THREE.SpriteMaterial({ map: texture }));
    const sprite = markRaw(new THREE.Sprite(spriteMaterial));
    sprite.scale.set(2, 0.5, 1);
    sprite.position.set(0, 0.8, 0);
    mesh.add(sprite);
    
    scene.value.add(mesh);
    deviceMeshes.value[device.id] = mesh;
    
    // 如果是RTK基准点，添加特殊标识（红色外框）
    if (alignmentManager.value.rtkBasePoint && 
        device.id === alignmentManager.value.rtkBasePoint.deviceId) {
      const ringGeometry = markRaw(new THREE.RingGeometry(0.25, 0.35, 16));
      const ringMaterial = markRaw(new THREE.MeshBasicMaterial({ 
        color: 0xff0000,
        transparent: true, 
        opacity: 0.8,
        side: THREE.DoubleSide
      }));
      const ringMesh = markRaw(new THREE.Mesh(ringGeometry, ringMaterial));
      ringMesh.position.copy(position);
      ringMesh.position.y += 0.05; // 稍微提升避免重叠
      ringMesh.rotation.x = -Math.PI / 2;
      scene.value.add(ringMesh);
      baseMeshes.value.push(ringMesh);
      
      // 验证基准点是否在原点
      if (device.worldCoords && 
          (Math.abs(device.worldCoords.x) > 0.001 || 
           Math.abs(device.worldCoords.y) > 0.001 || 
           Math.abs(device.worldCoords.z) > 0.001)) {
        console.warn(`RTK基准点不在原点! 位置: (${device.worldCoords.x.toFixed(3)}, ${device.worldCoords.y.toFixed(3)}, ${device.worldCoords.z.toFixed(3)})`);
      } else {
        console.log('RTK基准点验证: 已正确位于原点');
      }
    }
    
    console.log(`已添加设备 ${device.id} 到3D场景，位置:`, position);
    
    // 更新轨迹
    updateDeviceTrajectory(device);
  });
  
  console.log(`3D场景更新完成，可见设备数量: ${visibleDeviceCount}`);
}

// 更新设备轨迹
function updateDeviceTrajectory(device) {
  if (!device.connected || !device.data || !device.recording) return;
  
  const deviceId = device.id;
  
  // 优先使用转换后的世界坐标，如果没有则使用原始坐标
  const currentPosition = new THREE.Vector3();
  if (device.worldCoords) {
    currentPosition.set(
      device.worldCoords.x, // E轴直接映射到X轴
      device.worldCoords.y, // U轴直接映射到Y轴
      -device.worldCoords.z // N轴取反映射到Z轴
    );
  } else {
    currentPosition.set(
      device.data.e || 0, // E轴直接映射到X轴
      device.data.u || 0, // U轴直接映射到Y轴
      -(device.data.n || 0) // N轴取反映射到Z轴
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
  }
}

// 更新轨迹线
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

// 获取所有RTK设备
async function fetchRtkDevices() {
  try {
    const response = await axios.get(`${apiBaseUrl}/api/rtk/devices`);
    if (response.data) {
      // 检测断开连接的设备，释放颜色分配
      const previousDeviceIds = Object.keys(rtkDevices.value);
      const currentDeviceIds = Object.keys(response.data);
      
      // 找出已断开连接的设备
      const disconnectedDevices = previousDeviceIds.filter(deviceId => 
        !currentDeviceIds.includes(deviceId) || 
        (rtkDevices.value[deviceId]?.connected && !response.data[deviceId]?.connected)
      );
      
      // 释放断开连接设备的颜色分配
      disconnectedDevices.forEach(deviceId => {
        console.log(`设备 ${deviceId} 已断开连接，释放颜色分配`);
        releaseDeviceColor(deviceId);
      });
      
      // 保存当前的worldCoords和其他本地状态
      const currentWorldCoords = {};
      const currentShowIn3D = {};
      
      // 备份现有的worldCoords和showIn3D状态
      Object.values(rtkDevices.value).forEach(device => {
        if (device.worldCoords) {
          currentWorldCoords[device.id] = device.worldCoords;
        }
        if (device.showIn3D !== undefined) {
          currentShowIn3D[device.id] = device.showIn3D;
        }
      });
      
      // 更新设备数据，但保护本地计算的字段
      Object.values(response.data).forEach(device => {
        // 恢复worldCoords
        if (currentWorldCoords[device.id]) {
          device.worldCoords = currentWorldCoords[device.id];
        }
        
        // 恢复showIn3D状态
        if (currentShowIn3D[device.id] !== undefined) {
          device.showIn3D = currentShowIn3D[device.id];
        } else if (device.showIn3D === undefined) {
          device.showIn3D = true; // 默认显示
        }
        
        // 恢复数据记录状态
        device.dataRecording = dataRecordingDevices.value.has(device.id);
      });
      
      rtkDevices.value = response.data;
      
      // 如果有RTK基准点设置，重新应用坐标转换
      if (alignmentManager.value.rtkBasePoint) {
        updateAllRtkWorldCoords();
      }
      
      console.log('已获取RTK设备:', Object.keys(rtkDevices.value));
      console.log('设备详情:', rtkDevices.value);
      
      if (is3dViewReady.value) {
        updateDevicesIn3D();
      }
    }
  } catch (error) {
    console.error('获取RTK设备失败:', error);
  }
}

// 扫描RTK设备
async function scanRtkDevices() {
  if (isScanning.value) return;
  
  isScanning.value = true;
  ElMessage.info('开始扫描RTK设备...');
  
  try {
    const response = await axios.post(`${apiBaseUrl}/api/rtk/scan`);
    
    if (response.data && response.data.success) {
      scanResults.value = response.data.devices || [];
      console.log('扫描到的设备:', scanResults.value);
      
      if (scanResults.value.length === 0) {
        ElMessage.info('未发现新的RTK设备');
      } else {
        ElMessage.success(`发现 ${scanResults.value.length} 个RTK设备`);
      }
    }
  } catch (error) {
    console.error('扫描RTK设备失败:', error);
    ElMessage.error('扫描RTK设备失败');
  } finally {
    isScanning.value = false;
  }
}



// 显示配置对话框
function showConfigDialog(device) {
  console.log('显示配置对话框，设备:', device);
  configForm.value = {
    deviceId: device.id,
    name: device.name || device.id,
    ip: device.ip,
    deviceNumber: '1',
    isBaseStation: false,
    showIn3D: true
  };
  isEditing.value = false;
  configDialogVisible.value = true;
}

// 显示手动添加设备对话框
function showManualAddDialog() {
  console.log('显示手动添加设备对话框');
  configForm.value = {
    deviceId: '',
    name: '',
    ip: '',
    deviceNumber: '1',
    isBaseStation: false,
    showIn3D: true
  };
  isEditing.value = false;
  configDialogVisible.value = true;
}

// 编辑设备
function editDevice(device) {
  configForm.value = {
    deviceId: device.id,
    name: device.name || device.id,
    ip: device.ip,
    deviceNumber: device.deviceNumber || '1',
    isBaseStation: device.isBaseStation || false,
    showIn3D: device.showIn3D !== undefined ? device.showIn3D : true
  };
  isEditing.value = true;
  configDialogVisible.value = true;
}

// 保存设备配置
async function saveDeviceConfig() {
  if (!configFormRef.value) return;
  
  try {
    await configFormRef.value.validate();
    isSaving.value = true;
    
    const url = isEditing.value 
      ? `${apiBaseUrl}/api/rtk/devices/${configForm.value.deviceId}`
      : `${apiBaseUrl}/api/rtk/devices`;
    
    const method = isEditing.value ? 'put' : 'post';
    
    const requestData = {
      device_id: configForm.value.deviceId,
      ip_address: configForm.value.ip,
      name: configForm.value.name,
      device_number: configForm.value.deviceNumber,
      is_base_station: configForm.value.isBaseStation,
      show_in_3d: configForm.value.showIn3D
    };
    
    console.log('发送设备配置请求:', method, url, requestData);
    const response = await axios[method](url, requestData);
    
    if (response.data && response.data.success) {
      ElMessage.success(isEditing.value ? '设备更新成功' : '设备添加成功');
      configDialogVisible.value = false;
      
      // 从扫描结果中移除
      if (!isEditing.value) {
        scanResults.value = scanResults.value.filter(d => d.id !== configForm.value.deviceId);
      }
      
      await fetchRtkDevices();
    } else {
      ElMessage.error(isEditing.value ? '设备更新失败' : '设备添加失败');
    }
  } catch (error) {
    if (error !== 'validation failed') {
      console.error('保存设备配置失败:', error);
      ElMessage.error('操作失败');
    }
  } finally {
    isSaving.value = false;
  }
}

// 删除设备
async function deleteDevice() {
  try {
    await ElMessageBox.confirm('确定要删除此设备吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    
    const response = await axios.delete(`${apiBaseUrl}/api/rtk/devices/${configForm.value.deviceId}`);
    
    if (response.data && response.data.success) {
      ElMessage.success('设备删除成功');
      configDialogVisible.value = false;
      await fetchRtkDevices();
    } else {
      ElMessage.error('设备删除失败');
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除设备失败:', error);
      ElMessage.error('删除设备失败');
    }
  }
}

// 清理设备状态（为重新注册做准备）
async function cleanupDevice() {
  try {
    await ElMessageBox.confirm(
      '此操作将清理设备状态并将其移回未注册列表，以便重新扫描和注册。确定要继续吗？', 
      '清理设备状态', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    );
    
    const response = await axios.post(`${apiBaseUrl}/api/rtk/device/${configForm.value.deviceId}/cleanup`);
    
    if (response.data && response.data.success) {
      ElMessage.success('设备状态已清理，可重新扫描');
      configDialogVisible.value = false;
      await fetchRtkDevices();
      // 自动触发一次扫描
      setTimeout(() => {
        scanRtkDevices();
      }, 1000);
    } else {
      ElMessage.error('设备状态清理失败: ' + (response.data.message || '未知错误'));
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清理设备状态失败:', error);
      ElMessage.error('清理设备状态失败');
    }
  }
}

// 轨迹记录相关功能
async function toggleRecording(deviceId) {
  try {
    const device = rtkDevices.value[deviceId];
    if (!device) return;
    
    const action = device.recording ? 'stop' : 'start';
    const response = await axios.post(`${apiBaseUrl}/api/rtk/devices/${deviceId}/recording/${action}`);
    
    if (response.data && response.data.success) {
      ElMessage.success(device.recording ? '停止记录轨迹' : '开始记录轨迹');
      await fetchRtkDevices();
    } else {
      ElMessage.error('轨迹记录操作失败');
    }
  } catch (error) {
    console.error('轨迹记录操作失败:', error);
    ElMessage.error('轨迹记录操作失败');
  }
}

async function clearTrajectory(deviceId) {
  try {
    await ElMessageBox.confirm('确定要清除此设备的轨迹记录吗？', '确认清除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    
    const response = await axios.delete(`${apiBaseUrl}/api/rtk/devices/${deviceId}/records`);
    
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

// 切换设备3D可视化
async function toggleVisualization(deviceId, showIn3D) {
  try {
    const device = rtkDevices.value[deviceId];
    if (!device) return;
    
    console.log(`切换设备 ${deviceId} 的3D可视化为: ${showIn3D}`);
    
    // 先更新本地状态
    device.showIn3D = showIn3D;
    
    // 立即更新3D场景
    if (is3dViewReady.value) {
      updateDevicesIn3D();
    }
    
    // 然后更新后端
    const response = await axios.put(`${apiBaseUrl}/api/rtk/devices/${deviceId}`, {
      device_id: deviceId,
      ip_address: device.ip,
      name: device.name,
      device_number: device.deviceNumber,
      is_base_station: device.isBaseStation,
      show_in_3d: showIn3D
    });
    
    if (response.data && response.data.success) {
      ElMessage.success(showIn3D ? '已启用3D显示' : '已隐藏3D显示');
    } else {
      ElMessage.error('更新可视化设置失败，但本地显示已更新');
    }
  } catch (error) {
    console.error('切换可视化失败:', error);
    ElMessage.error('更新服务器失败，但本地显示已更新');
  }
}

// 建筑模型相关函数
async function loadBuildingModels() {
  try {
    const response = await axios.get(`${apiBaseUrl}/api/models`);
    buildingModels.value = response.data;
    
    // 加载每个模型到3D场景
    for (const model of buildingModels.value) {
      if (model.visible !== false) {
        await loadModelToScene(model);
      }
    }
  } catch (error) {
    console.error('加载建筑模型列表失败:', error);
  }
}

async function handleModelUpload(file) {
  isUploadingModel.value = true;
  
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    // 添加默认元数据
    const metadata = {
      name: file.name.replace(/\.(gltf|glb|obj|stl)$/i, ''),
      position: { x: 0, y: 0, z: 0 },
      rotation: { x: 0, y: 0, z: 0 },
      scale: { x: 1, y: 1, z: 1 },
      opacity: modelOpacity.value,
      visible: true
    };
    formData.append('metadata', JSON.stringify(metadata));
    
    const response = await axios.post(`${apiBaseUrl}/api/models/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    
    if (response.data.success) {
      ElMessage.success('模型上传成功');
      
      // 添加到模型列表
      buildingModels.value.push(response.data.model_info);
      
      // 加载模型到3D场景
      await loadModelToScene(response.data.model_info);
    }
  } catch (error) {
    console.error('上传模型失败:', error);
    ElMessage.error('上传模型失败');
  } finally {
    isUploadingModel.value = false;
  }
  
  return false; // 阻止默认上传行为
}

async function loadModelToScene(modelInfo) {
  if (!scene.value) return;
  
  try {
    const modelUrl = `${apiBaseUrl}/api/models/${modelInfo.id}/file`;
    const format = modelInfo.format.toLowerCase();
    
    if (format === '.stl') {
      // 使用STL加载器
      stlLoader.load(
        modelUrl,
        (geometry) => {
          // STL文件只包含几何信息，需要创建材质
          const material = new THREE.MeshPhongMaterial({
            color: 0x00ff88,
            specular: 0x111111,
            shininess: 200,
            transparent: true,
            opacity: modelInfo.opacity || modelOpacity.value,
            side: THREE.DoubleSide
          });
          
          const mesh = new THREE.Mesh(geometry, material);
          
          // 设置位置
          mesh.position.set(
            modelInfo.position.x,
            modelInfo.position.y,
            modelInfo.position.z
          );
          
          // 设置旋转
          mesh.rotation.set(
            modelInfo.rotation.x,
            modelInfo.rotation.y,
            modelInfo.rotation.z
          );
          
          // 设置缩放
          mesh.scale.set(
            modelInfo.scale.x,
            modelInfo.scale.y,
            modelInfo.scale.z
          );
          
          // 启用阴影
          mesh.castShadow = true;
          mesh.receiveShadow = true;
          
          // 计算边界框并居中（STL文件可能不在原点）
          geometry.computeBoundingBox();
          const boundingBox = geometry.boundingBox;
          const center = new THREE.Vector3();
          boundingBox.getCenter(center);
          geometry.translate(-center.x, -center.y, -center.z);
          
          // 添加到场景
          scene.value.add(mesh);
          loadedModels.value[modelInfo.id] = mesh;
          
          console.log(`STL模型 ${modelInfo.name} 加载成功`);
          
          // 直接应用已保存的配准变换（如果存在）
          applySavedTransformToModel(mesh);
        },
        (progress) => {
          console.log(`加载进度: ${(progress.loaded / progress.total * 100).toFixed(2)}%`);
        },
        (error) => {
          console.error(`加载STL模型失败: ${modelInfo.name}`, error);
          ElMessage.error(`加载模型 ${modelInfo.name} 失败`);
        }
      );
    } else {
      // 使用GLTF加载器（支持.gltf, .glb, .obj）
      gltfLoader.load(
        modelUrl,
        (gltf) => {
          const model = gltf.scene;
          
          // 设置位置
          model.position.set(
            modelInfo.position.x,
            modelInfo.position.y,
            modelInfo.position.z
          );
          
          // 设置旋转
          model.rotation.set(
            modelInfo.rotation.x,
            modelInfo.rotation.y,
            modelInfo.rotation.z
          );
          
          // 设置缩放
          model.scale.set(
            modelInfo.scale.x,
            modelInfo.scale.y,
            modelInfo.scale.z
          );
          
          // 设置透明度
          model.traverse((child) => {
            if (child.isMesh) {
              child.material.transparent = true;
              child.material.opacity = modelInfo.opacity || modelOpacity.value;
              child.castShadow = true;
              child.receiveShadow = true;
            }
          });
          
          // 添加到场景
          scene.value.add(model);
          loadedModels.value[modelInfo.id] = model;
          
          console.log(`模型 ${modelInfo.name} 加载成功`);
          
          // 直接应用已保存的配准变换（如果存在）
          applySavedTransformToModel(model);
        },
        (progress) => {
          console.log(`加载进度: ${(progress.loaded / progress.total * 100).toFixed(2)}%`);
        },
        (error) => {
          console.error(`加载模型失败: ${modelInfo.name}`, error);
          ElMessage.error(`加载模型 ${modelInfo.name} 失败`);
        }
      );
    }
  } catch (error) {
    console.error('加载模型到场景失败:', error);
  }
}

async function deleteModel(modelId) {
  try {
    await ElMessageBox.confirm('确定要删除此模型吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    
    const response = await axios.delete(`${apiBaseUrl}/api/models/${modelId}`);
    
    if (response.data.success) {
      // 从场景中移除模型
      if (loadedModels.value[modelId]) {
        scene.value.remove(loadedModels.value[modelId]);
        delete loadedModels.value[modelId];
      }
      
      // 从列表中移除
      buildingModels.value = buildingModels.value.filter(m => m.id !== modelId);
      
      ElMessage.success('模型删除成功');
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除模型失败:', error);
      ElMessage.error('删除模型失败');
    }
  }
}

function updateModelVisibility(visible) {
  // 只对当前可见状态为true的模型应用全局设置
  Object.entries(loadedModels.value).forEach(([modelId, model]) => {
    const modelInfo = buildingModels.value.find(m => m.id === modelId);
    if (modelInfo && modelInfo.visible !== false) {
      model.visible = visible;
    }
  });
}

function updateModelOpacity(opacity) {
  Object.values(loadedModels.value).forEach(model => {
    if (model.isMesh) {
      // STL模型是直接的Mesh对象
      if (model.material) {
        model.material.opacity = opacity;
      }
    } else {
      // GLTF模型需要遍历子对象
      model.traverse((child) => {
        if (child.isMesh && child.material) {
          child.material.opacity = opacity;
        }
      });
    }
  });
}

function updateModelLayerMode(mode) {
  // 根据模式控制设备和模型的显示
  if (mode === 'design') {
    // 只显示设计模型
    updateModelVisibility(true);
    Object.values(deviceMeshes.value).forEach(mesh => {
      mesh.visible = false;
    });
  } else if (mode === 'actual') {
    // 只显示实际位置（RTK设备）
    updateModelVisibility(false);
    Object.values(deviceMeshes.value).forEach(mesh => {
      mesh.visible = true;
    });
  } else {
    // 叠加显示
    updateModelVisibility(true);
    Object.values(deviceMeshes.value).forEach(mesh => {
      mesh.visible = true;
    });
  }
}

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

// 获取设备显示坐标（优先使用配准后的世界坐标）
function getDisplayCoordinate(device, axis) {
  if (!device || !device.data) return 0;
  
  if (device.worldCoords) {
    // 使用配准后的世界坐标
    switch (axis) {
      case 'e':
        return device.worldCoords.x; // E轴直接映射
      case 'n':
        return -device.worldCoords.z; // N轴取反映射（因为N轴指向Z负方向）
      case 'u':
        return device.worldCoords.y; // U轴直接映射
      default:
        return 0;
    }
  } else {
    // 回退到原始ENU坐标
    switch (axis) {
      case 'e':
        return device.data.e || 0; // E轴直接映射
      case 'n':
        return -(device.data.n || 0); // N轴取反映射（因为N轴指向Z负方向）
      case 'u':
        return device.data.u || 0; // U轴直接映射
      default:
        return 0;
    }
  }
}

// 切换单个模型的显示/隐藏状态
async function toggleModelVisibility(modelId) {
  try {
    // 找到对应的模型
    const model = buildingModels.value.find(m => m.id === modelId);
    if (!model) return;
    
    // 切换可见状态
    const newVisibility = model.visible !== false ? false : true;
    model.visible = newVisibility;
    
    // 更新3D场景中的模型显示
    if (loadedModels.value[modelId]) {
      loadedModels.value[modelId].visible = newVisibility;
    }
    
    // 如果当前处于顶点选择模式，更新顶点显示
    if (vertexSelectionMode.value) {
      console.log(`模型 ${modelId} 可见性已改变，更新顶点显示`);
      updateVertexDisplay();
    }
    
    // 同步到后端
    try {
      const response = await axios.put(`${apiBaseUrl}/api/models/${modelId}`, {
        ...model,
        visible: newVisibility
      });
      
      if (response.data && response.data.success) {
        ElMessage.success(newVisibility ? '模型已显示' : '模型已隐藏');
      } else {
        ElMessage.error('更新模型状态失败，但本地显示已更新');
      }
    } catch (apiError) {
      console.warn('后端API调用失败，仅更新本地状态:', apiError);
      ElMessage.success(newVisibility ? '模型已显示' : '模型已隐藏');
    }
  } catch (error) {
    console.error('切换模型可见性失败:', error);
    ElMessage.error('操作失败');
  }
}

function editModel(model) {
  // TODO: 实现模型编辑功能
  ElMessage.info('模型编辑功能开发中...');
}

// ==================== 两阶段配准系统 ====================

// 阶段1：基准点配准功能

// 切换顶点选择模式
function toggleVertexSelection(enabled) {
  if (enabled) {
    extractModelVertices();
    showVertices();
    // 添加鼠标移动监听器用于顶点高亮
    renderer.value.domElement.addEventListener('mousemove', onVertexHover);
    renderer.value.domElement.addEventListener('click', onVertexClick);
  } else {
    hideVertices();
    // 移除监听器
    renderer.value.domElement.removeEventListener('mousemove', onVertexHover);
    renderer.value.domElement.removeEventListener('click', onVertexClick);
  }
}

// 从模型中提取顶点
function extractModelVertices() {
  modelVertices.value = [];
  
  Object.entries(loadedModels.value).forEach(([modelId, model]) => {
    // 检查模型是否可见
    const modelInfo = buildingModels.value.find(m => m.id === modelId);
    if (!modelInfo || modelInfo.visible === false) {
      console.log(`跳过隐藏模型 ${modelId} 的顶点提取`);
      return;
    }
    
    // 同时检查3D场景中模型的可见性
    if (!model.visible) {
      console.log(`跳过3D场景中隐藏的模型 ${modelId}`);
      return;
    }
    
    const vertices = [];
    
    model.traverse((child) => {
      if (child.isMesh && child.geometry) {
        const positions = child.geometry.attributes.position;
        if (positions) {
          // 根据密度设置采样间隔
          const densityMap = { low: 10, medium: 5, high: 2 };
          const step = densityMap[vertexDensity.value] || 5;
          
          for (let i = 0; i < positions.count; i += step) {
            const vertex = new THREE.Vector3();
            vertex.fromBufferAttribute(positions, i);
            
            // 转换到世界坐标
            child.localToWorld(vertex);
            vertices.push(vertex);
          }
        }
      }
    });
    
    modelVertices.value.push(...vertices);
  });
  
  console.log(`从可见模型中提取了 ${modelVertices.value.length} 个顶点`);
}

// 显示顶点
function showVertices() {
  hideVertices(); // 先清除之前的顶点
  
  const geometry = new THREE.SphereGeometry(0.05, 8, 8);
  const material = new THREE.MeshBasicMaterial({ color: 0x00ff00, transparent: true, opacity: 0.6 });
  
  modelVertices.value.forEach(vertex => {
    const mesh = markRaw(new THREE.Mesh(geometry, material));
    mesh.position.copy(vertex);
    mesh.userData.isVertex = true;
    mesh.userData.originalPosition = vertex.clone();
    scene.value.add(mesh);
    vertexMeshes.value.push(mesh);
  });
}

// 隐藏顶点
function hideVertices() {
  vertexMeshes.value.forEach(mesh => {
    scene.value.remove(mesh);
  });
  vertexMeshes.value = [];
  
  if (highlightedVertex.value) {
    scene.value.remove(highlightedVertex.value);
    highlightedVertex.value = null;
  }
}

// 更新顶点显示密度
function updateVertexDisplay() {
  if (vertexSelectionMode.value) {
    extractModelVertices();
    showVertices();
  }
}

// 顶点悬停高亮
function onVertexHover(event) {
  if (!vertexSelectionMode.value) return;
  
  const rect = renderer.value.domElement.getBoundingClientRect();
  const mouse = new THREE.Vector2();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(mouse, camera.value);
  
  const intersects = raycaster.intersectObjects(vertexMeshes.value);
  
  // 移除之前的高亮
  if (highlightedVertex.value) {
    scene.value.remove(highlightedVertex.value);
    highlightedVertex.value = null;
  }
  
  if (intersects.length > 0) {
    const vertex = intersects[0].object;
    
    // 创建高亮显示
    const highlightGeometry = new THREE.SphereGeometry(0.08, 8, 8);
    const highlightMaterial = new THREE.MeshBasicMaterial({ color: 0xffff00 });
    highlightedVertex.value = markRaw(new THREE.Mesh(highlightGeometry, highlightMaterial));
    highlightedVertex.value.position.copy(vertex.position);
    scene.value.add(highlightedVertex.value);
    
    // 改变鼠标样式
    renderer.value.domElement.style.cursor = 'pointer';
  } else {
    renderer.value.domElement.style.cursor = 'default';
  }
}

// 顶点点击选择
function onVertexClick(event) {
  if (!vertexSelectionMode.value) return;
  
  const rect = renderer.value.domElement.getBoundingClientRect();
  const mouse = new THREE.Vector2();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(mouse, camera.value);
  
  const intersects = raycaster.intersectObjects(vertexMeshes.value);
  
  if (intersects.length > 0) {
    const selectedVertex = intersects[0].object.userData.originalPosition;
    
    if (addingPointPair.value && addPointPairStep.value === 1) {
      // 阶段2：添加特征点对的第一步
      currentPointPair.value = {
        bimPoint: selectedVertex.clone(),
        rtkPoint: null
      };
      addPointPairStep.value = 2;
      ElMessage.success('BIM点已选择，请选择对应的RTK点');
    } else {
      // 阶段1：设置BIM基准点
      setBimBasePoint(selectedVertex);
    }
  }
}

// 设置BIM基准点
function setBimBasePoint(vertex) {
  alignmentManager.value.bimBasePoint = vertex.clone();
  
  // 计算平移向量（将基准点移动到原点）
  const translation = new THREE.Vector3().subVectors(new THREE.Vector3(0, 0, 0), vertex);
  alignmentManager.value.stage1Transform.makeTranslation(translation.x, translation.y, translation.z);
  
  // 应用变换到所有BIM模型
  Object.values(loadedModels.value).forEach(model => {
    model.applyMatrix4(alignmentManager.value.stage1Transform);
  });
  
  // 更新顶点位置
  if (vertexSelectionMode.value) {
    updateVertexDisplay();
  }
  
  // 标记模型已应用变换（新增）
  modelTransformApplied.value = true;
  
  // 保存状态
  saveAlignmentState();
  
  ElMessage.success('BIM基准点已设置并对齐到原点');
  console.log('BIM基准点已设置:', vertex);
}

// 设置RTK基准点
function setRtkBasePoint(deviceId) {
  const device = rtkDevices.value[deviceId];
  if (!device || !device.data) {
    ElMessage.error('选择的设备无数据');
    return;
  }
  
  alignmentManager.value.rtkBasePoint = {
    deviceId: deviceId,
    originalCoords: {
      e: device.data.e,
      n: device.data.n,
      u: device.data.u
    },
    timestamp: Date.now()
  };
  
  // 重新计算所有RTK点的世界坐标
  updateAllRtkWorldCoords();
  
  // 保存状态
  saveAlignmentState();
  
  ElMessage.success('RTK基准点已设置');
  console.log('RTK基准点已设置:', alignmentManager.value.rtkBasePoint);
}

// 更新所有RTK点的世界坐标
function updateAllRtkWorldCoords() {
  if (!alignmentManager.value.rtkBasePoint) {
    console.warn('没有RTK基准点，跳过世界坐标更新');
    return;
  }
  
  console.log('更新RTK世界坐标, 基准点:', alignmentManager.value.rtkBasePoint);
  
  // 检查基准点设备是否仍然存在
  const baseDevice = rtkDevices.value[alignmentManager.value.rtkBasePoint.deviceId];
  if (!baseDevice || !baseDevice.data) {
    console.warn(`RTK基准点设备 ${alignmentManager.value.rtkBasePoint.deviceId} 不存在或无数据`);
    return;
  }
  
  Object.values(rtkDevices.value).forEach(device => {
    if (device.data) {
      // 计算相对于基准点的偏移
      const offset = {
        e: device.data.e - alignmentManager.value.rtkBasePoint.originalCoords.e,
        n: device.data.n - alignmentManager.value.rtkBasePoint.originalCoords.n,
        u: device.data.u - alignmentManager.value.rtkBasePoint.originalCoords.u
      };
      
      // 转换为世界坐标（RTK基准点对应世界原点）
      device.worldCoords = {
        x: offset.e,
        y: offset.u,
        z: offset.n
      };
      
      // 添加调试信息
      console.log(`设备 ${device.id}:`, {
        原始坐标: { e: device.data.e, n: device.data.n, u: device.data.u },
        偏移量: offset,
        世界坐标: device.worldCoords,
        是否为基准点: device.id === alignmentManager.value.rtkBasePoint.deviceId
      });
    }
  });
  
  // 更新3D显示
  updateDevicesIn3D();
}

// 检查RTK基准点坐标是否发生变化
function checkRtkBasePointUpdate() {
  if (!alignmentManager.value.rtkBasePoint) return;
  
  const baseDevice = rtkDevices.value[alignmentManager.value.rtkBasePoint.deviceId];
  if (!baseDevice || !baseDevice.data) return;
  
  const currentCoords = {
    e: baseDevice.data.e,
    n: baseDevice.data.n,
    u: baseDevice.data.u
  };
  
  const originalCoords = alignmentManager.value.rtkBasePoint.originalCoords;
  
  // 检查基准点坐标是否发生显著变化（>1cm）
  const deltaE = Math.abs(currentCoords.e - originalCoords.e);
  const deltaN = Math.abs(currentCoords.n - originalCoords.n);
  const deltaU = Math.abs(currentCoords.u - originalCoords.u);
  
  if (deltaE > 0.01 || deltaN > 0.01 || deltaU > 0.01) {
    console.warn('RTK基准点坐标发生变化:', {
      原始坐标: originalCoords,
      当前坐标: currentCoords,
      变化量: { deltaE, deltaN, deltaU }
    });
    
    // 可选：自动更新基准点坐标或提示用户
    // updateRtkBasePointCoords(currentCoords);
  }
}

// 保存对齐状态到localStorage
function saveAlignmentState() {
  if (alignmentManager.value.rtkBasePoint && alignmentManager.value.bimBasePoint) {
    const alignmentState = {
      rtkBasePoint: alignmentManager.value.rtkBasePoint,
      bimBasePoint: {
        x: alignmentManager.value.bimBasePoint.x,
        y: alignmentManager.value.bimBasePoint.y,
        z: alignmentManager.value.bimBasePoint.z
      },
      stage1Complete: alignmentManager.value.stage1Complete,
      stage2Complete: alignmentManager.value.stage2Complete,
      // 保存变换矩阵
      stage1Transform: {
        elements: Array.from(alignmentManager.value.stage1Transform.elements)
      },
      kabschTransform: alignmentManager.value.kabschTransform ? {
        elements: Array.from(alignmentManager.value.kabschTransform.elements)
      } : null,
      finalTransform: alignmentManager.value.finalTransform ? {
        elements: Array.from(alignmentManager.value.finalTransform.elements)
      } : null,
      // 保存特征点对数据
      pointPairs: pointPairs.value.map(pair => ({
        id: pair.id,
        bimPoint: {
          x: pair.bimPoint.x,
          y: pair.bimPoint.y,
          z: pair.bimPoint.z
        },
        rtkPoint: {
          x: pair.rtkPoint.x,
          y: pair.rtkPoint.y,
          z: pair.rtkPoint.z
        }
      })),
      // 新增：保存模型变换应用状态
      modelTransformApplied: modelTransformApplied.value,
      timestamp: Date.now()
    };
    
    localStorage.setItem('rtk_alignment_state', JSON.stringify(alignmentState));
    console.log('配准状态已保存:', alignmentState);
  }
}

// 从localStorage恢复对齐状态
function restoreAlignmentState() {
  try {
    const savedState = localStorage.getItem('rtk_alignment_state');
    if (savedState) {
      const alignmentState = JSON.parse(savedState);
      
      // 检查状态是否过期（24小时）
      const isExpired = Date.now() - alignmentState.timestamp > 24 * 60 * 60 * 1000;
      if (isExpired) {
        localStorage.removeItem('rtk_alignment_state');
        return false;
      }
      
      // 恢复基本状态
      alignmentManager.value.rtkBasePoint = alignmentState.rtkBasePoint;
      alignmentManager.value.bimBasePoint = new THREE.Vector3(
        alignmentState.bimBasePoint.x,
        alignmentState.bimBasePoint.y,
        alignmentState.bimBasePoint.z
      );
      alignmentManager.value.stage1Complete = alignmentState.stage1Complete;
      alignmentManager.value.stage2Complete = alignmentState.stage2Complete || false;
      
      // 恢复变换矩阵
      if (alignmentState.stage1Transform) {
        alignmentManager.value.stage1Transform.fromArray(alignmentState.stage1Transform.elements);
      }
      
      if (alignmentState.kabschTransform) {
        alignmentManager.value.kabschTransform = new THREE.Matrix4();
        alignmentManager.value.kabschTransform.fromArray(alignmentState.kabschTransform.elements);
      }
      
      if (alignmentState.finalTransform) {
        alignmentManager.value.finalTransform = new THREE.Matrix4();
        alignmentManager.value.finalTransform.fromArray(alignmentState.finalTransform.elements);
      }
      
      // 恢复特征点对
      if (alignmentState.pointPairs) {
        pointPairs.value = alignmentState.pointPairs.map(pair => ({
          id: pair.id,
          bimPoint: new THREE.Vector3(pair.bimPoint.x, pair.bimPoint.y, pair.bimPoint.z),
          rtkPoint: new THREE.Vector3(pair.rtkPoint.x, pair.rtkPoint.y, pair.rtkPoint.z)
        }));
      }
      
      // 恢复模型变换应用状态
      modelTransformApplied.value = alignmentState.modelTransformApplied || false;
      
      console.log('配准状态已恢复:', alignmentState);
      console.log('模型变换应用状态:', modelTransformApplied.value);
      
      // 重新应用坐标转换
      if (alignmentManager.value.rtkBasePoint) {
        updateAllRtkWorldCoords();
      }
      
      return true;
    }
  } catch (error) {
    console.error('恢复配准状态失败:', error);
    localStorage.removeItem('rtk_alignment_state');
  }
  
  return false;
}

// 应用保存的变换到所有BIM模型
function applyAlignmentToModels() {
  if (!loadedModels.value || Object.keys(loadedModels.value).length === 0) {
    console.warn('没有已加载的模型，跳过变换应用');
    return;
  }
  
  console.log('开始应用配准变换到BIM模型...');
  
  // 应用阶段1变换（BIM基准点对齐）
  if (alignmentManager.value.stage1Complete && alignmentManager.value.stage1Transform) {
    console.log('应用阶段1变换（基准点对齐）');
    Object.values(loadedModels.value).forEach(model => {
      model.applyMatrix4(alignmentManager.value.stage1Transform);
    });
  }
  
  // 应用阶段2变换（Kabsch精确配准）
  if (alignmentManager.value.stage2Complete && alignmentManager.value.kabschTransform) {
    console.log('应用阶段2变换（Kabsch配准）');
    Object.values(loadedModels.value).forEach(model => {
      model.applyMatrix4(alignmentManager.value.kabschTransform);
    });
  }
  
  // 更新顶点显示（如果处于顶点选择模式）
  if (vertexSelectionMode.value) {
    updateVertexDisplay();
  }
  
  console.log('BIM模型变换应用完成');
}

// 检查并应用配准状态到模型（仅用于手动恢复）
function applyRestoredAlignment(showMessage = true) {
  // 检查是否有恢复的配准状态需要应用
  if (alignmentManager.value.stage1Complete || alignmentManager.value.stage2Complete) {
    console.log('检测到已恢复的配准状态');
    
    // 只在模型未应用变换时才应用变换
    if (!modelTransformApplied.value) {
      console.log('模型未应用变换，开始应用配准变换到模型');
      applyAlignmentToModels();
      modelTransformApplied.value = true;
    } else {
      console.log('模型已应用变换，跳过重复应用');
    }
    
    // 只在需要时显示恢复信息
    if (showMessage) {
      let message = '';
      if (alignmentManager.value.stage1Complete) {
        message += '阶段1配准已恢复';
      }
      if (alignmentManager.value.stage2Complete) {
        message += alignmentManager.value.stage1Complete ? '，阶段2配准已恢复' : '阶段2配准已恢复';
      }
      
      ElMessage.success(message);
    }
  }
}

// 对单个加载的模型应用配准变换
function applyAlignmentToLoadedModel(model) {
  // 只在配准状态已恢复时应用变换
  if (alignmentManager.value.stage1Complete && alignmentManager.value.stage1Transform) {
    console.log('对新加载的模型应用阶段1变换');
    model.applyMatrix4(alignmentManager.value.stage1Transform);
  }
  
  if (alignmentManager.value.stage2Complete && alignmentManager.value.kabschTransform) {
    console.log('对新加载的模型应用阶段2变换');
    model.applyMatrix4(alignmentManager.value.kabschTransform);
  }
}

// 对单个模型应用已保存的配准变换（无提示）
function applySavedTransformToModel(model) {
  // 从localStorage检查是否有保存的配准状态
  try {
    const savedState = localStorage.getItem('rtk_alignment_state');
    if (savedState) {
      const alignmentState = JSON.parse(savedState);
      
      // 检查状态是否过期（24小时）
      const isExpired = Date.now() - alignmentState.timestamp > 24 * 60 * 60 * 1000;
      if (isExpired) {
        return; // 过期则不应用
      }
      
      // 应用阶段1变换（如果存在）
      if (alignmentState.stage1Complete && alignmentState.stage1Transform) {
        const stage1Matrix = new THREE.Matrix4();
        stage1Matrix.fromArray(alignmentState.stage1Transform.elements);
        model.applyMatrix4(stage1Matrix);
        console.log('对模型应用已保存的阶段1变换');
      }
      
      // 应用阶段2变换（如果存在）
      if (alignmentState.stage2Complete && alignmentState.kabschTransform) {
        const kabschMatrix = new THREE.Matrix4();
        kabschMatrix.fromArray(alignmentState.kabschTransform.elements);
        model.applyMatrix4(kabschMatrix);
        console.log('对模型应用已保存的阶段2变换');
      }
    }
  } catch (error) {
    console.error('应用保存的变换失败:', error);
  }
}

// 完成阶段1配准
function completeStage1() {
  if (!canCompleteStage1.value) {
    ElMessage.warning('请先设置BIM基准点和RTK基准点');
    return;
  }
  
  // 验证坐标系对齐
  const rtkBaseDevice = rtkDevices.value[alignmentManager.value.rtkBasePoint.deviceId];
  if (rtkBaseDevice && rtkBaseDevice.worldCoords) {
    const distance = Math.sqrt(
      Math.pow(rtkBaseDevice.worldCoords.x, 2) + 
      Math.pow(rtkBaseDevice.worldCoords.y, 2) + 
      Math.pow(rtkBaseDevice.worldCoords.z, 2)
    );
    
    if (distance > 0.001) {
      console.warn(`坐标系对齐验证失败: RTK基准点距离原点 ${distance.toFixed(4)}m`);
    } else {
      console.log('坐标系对齐验证成功: RTK基准点已位于原点');
    }
  }
  
  alignmentManager.value.stage1Complete = true;
  
  // 保存配准状态
  saveAlignmentState();
  
  // 关闭顶点选择模式
  vertexSelectionMode.value = false;
  toggleVertexSelection(false);
  
  ElMessage.success('阶段1配准完成！BIM基准点和RTK基准点已对齐到原点');
}

// 重置阶段1
function resetStage1() {
  // 恢复模型原始位置
  if (alignmentManager.value.stage1Transform) {
    const inverseTransform = alignmentManager.value.stage1Transform.clone().invert();
    Object.values(loadedModels.value).forEach(model => {
      model.applyMatrix4(inverseTransform);
    });
  }
  
  alignmentManager.value.stage1Complete = false;
  alignmentManager.value.bimBasePoint = null;
  alignmentManager.value.rtkBasePoint = null;
  alignmentManager.value.stage1Transform.identity();
  selectedRtkBaseDevice.value = null;
  
  // 重置RTK坐标
  Object.values(rtkDevices.value).forEach(device => {
    delete device.worldCoords;
  });
  
  // 重置模型变换应用状态（新增）
  modelTransformApplied.value = false;
  
  // 清除保存的配准状态（新增）
  localStorage.removeItem('rtk_alignment_state');
  console.log('配准状态已清除');
  
  updateDevicesIn3D();
  ElMessage.info('阶段1已重置');
}

// 阶段2：精确配准功能

// 开始添加点对
function startAddingPointPair() {
  addingPointPair.value = true;
  addPointPairStep.value = 1;
  currentPointPair.value = null;
  
  // 启用顶点选择模式
  if (!vertexSelectionMode.value) {
    vertexSelectionMode.value = true;
    toggleVertexSelection(true);
  }
  
  ElMessage.info('请点击BIM模型上的特征点');
}

// 取消添加点对
function cancelAddingPointPair() {
  addingPointPair.value = false;
  addPointPairStep.value = 1;
  currentPointPair.value = null;
  ElMessage.info('已取消添加点对');
}

// 选择RTK点（用于点对的第二步）
function selectRtkPointForPair(deviceId) {
  if (!addingPointPair.value || addPointPairStep.value !== 2) return;
  
  const device = rtkDevices.value[deviceId];
  if (!device || !device.worldCoords) {
    ElMessage.error('选择的RTK设备无世界坐标数据');
    return;
  }
  
  currentPointPair.value.rtkPoint = new THREE.Vector3(
    device.worldCoords.x,
    device.worldCoords.y,
    device.worldCoords.z
  );
  
  // 添加到点对列表
  const pointPair = {
    id: Date.now(),
    name: `点对${pointPairs.value.length + 1}`,
    bimPoint: currentPointPair.value.bimPoint,
    rtkPoint: currentPointPair.value.rtkPoint,
    deviceId: deviceId
  };
  
  pointPairs.value.push(pointPair);
  
  // 重置状态
  addingPointPair.value = false;
  addPointPairStep.value = 1;
  currentPointPair.value = null;
  
  ElMessage.success(`点对已添加 (${pointPairs.value.length}/${minPointPairs.value})`);
}

// 删除点对
function deletePointPair(pairId) {
  pointPairs.value = pointPairs.value.filter(pair => pair.id !== pairId);
  ElMessage.info('点对已删除');
}

// 编辑点对
function editPointPair(pair) {
  ElMessage.info('点对编辑功能开发中...');
}

// 执行Kabsch配准
async function performKabschAlignment() {
  if (!canPerformKabsch.value) {
    ElMessage.warning('需要至少3个点对才能进行精确配准');
    return;
  }
  
  performingAlignment.value = true;
  
  try {
    // 提取BIM和RTK点坐标
    const bimPoints = pointPairs.value.map(pair => pair.bimPoint);
    const rtkPoints = pointPairs.value.map(pair => pair.rtkPoint);
    
    console.log('开始Kabsch配准...');
    console.log('BIM点数:', bimPoints.length);
    console.log('RTK点数:', rtkPoints.length);
    
    // 执行Kabsch算法
    const kabschResult = calculateKabschAlignment(bimPoints, rtkPoints);
    
    console.log('Kabsch配准结果:', kabschResult);
    
    // 保存变换矩阵和误差统计
    alignmentManager.value.kabschTransform = kabschResult.transformMatrix;
    alignmentManager.value.alignmentError = kabschResult.errorStats;
    
    // 计算最终变换矩阵
    alignmentManager.value.finalTransform.multiplyMatrices(
      alignmentManager.value.kabschTransform,
      alignmentManager.value.stage1Transform
    );
    
    // 应用变换到所有BIM模型
    Object.values(loadedModels.value).forEach(model => {
      model.applyMatrix4(alignmentManager.value.kabschTransform);
    });
    
    // 更新顶点位置
    if (vertexSelectionMode.value) {
      updateVertexDisplay();
    }
    
    // 评估配准质量
    const qualityAssessment = assessAlignmentQuality(kabschResult.errorStats);
    console.log('配准质量评估:', qualityAssessment);
    
    alignmentManager.value.stage2Complete = true;
    alignmentManager.value.qualityAssessment = qualityAssessment;
    
    // 更新模型变换状态（如果还没有标记为已应用）
    if (!modelTransformApplied.value) {
      modelTransformApplied.value = true;
    }
    
    // 保存配准状态（新增）
    saveAlignmentState();
    
    // 显示成功消息
    const rms = kabschResult.errorStats.rms;
    const qualityText = qualityAssessment.summary;
    
    ElMessage.success({
      message: `精确配准完成！${qualityText}`,
      duration: 5000
    });
    
    // 如果质量较差，显示建议
    if (qualityAssessment.recommendations.length > 0) {
      setTimeout(() => {
        ElMessage.warning({
          message: `建议: ${qualityAssessment.recommendations.join('; ')}`,
          duration: 8000
        });
      }, 2000);
    }
    
  } catch (error) {
    console.error('Kabsch配准失败:', error);
    ElMessage.error('配准失败: ' + error.message);
  } finally {
    performingAlignment.value = false;
  }
}

// 预览配准
function previewAlignment() {
  ElMessage.info('配准预览功能开发中...');
}

// 重置阶段2
function resetStage2() {
  // 恢复到阶段1完成后的状态
  if (alignmentManager.value.kabschTransform) {
    const inverseTransform = alignmentManager.value.kabschTransform.clone().invert();
    Object.values(loadedModels.value).forEach(model => {
      model.applyMatrix4(inverseTransform);
    });
  }
  
  alignmentManager.value.stage2Complete = false;
  alignmentManager.value.kabschTransform.identity();
  alignmentManager.value.finalTransform.copy(alignmentManager.value.stage1Transform);
  alignmentManager.value.alignmentError = null;
  alignmentManager.value.qualityAssessment = null;
  
  pointPairs.value = [];
  addingPointPair.value = false;
  addPointPairStep.value = 1;
  currentPointPair.value = null;
  
  // 更新顶点位置
  if (vertexSelectionMode.value) {
    updateVertexDisplay();
  }
  
  // 保存配准状态（新增）
  saveAlignmentState();
  
  ElMessage.info('阶段2已重置');
}

// UI辅助函数

// 获取误差等级样式类
function getErrorClass(error) {
  if (error < 0.02) return 'excellent';
  if (error < 0.05) return 'good';
  if (error < 0.1) return 'warning';
  return 'error';
}

// 获取精度等级样式类
function getAccuracyClass() {
  if (!alignmentManager.value.alignmentError) return '';
  const rms = alignmentManager.value.alignmentError.rms;
  if (rms < 0.02) return 'excellent';
  if (rms < 0.05) return 'good';
  if (rms < 0.1) return 'warning';
  return 'error';
}

// 获取精度描述文本
function getAccuracyText() {
  if (!alignmentManager.value.alignmentError) return '';
  const rms = alignmentManager.value.alignmentError.rms;
  if (rms < 0.02) return '优秀 (< 2cm)';
  if (rms < 0.05) return '良好 (< 5cm)';
  if (rms < 0.1) return '一般 (< 10cm)';
  return '需要改进 (> 10cm)';
}

// 获取质量评分样式类
function getQualityScoreClass(score) {
  if (score >= 80) return 'excellent';
  if (score >= 60) return 'good';
  if (score >= 40) return 'warning';
  return 'error';
}

// 显示误差分布
function showErrorDistribution() {
  if (!alignmentManager.value.alignmentError || !alignmentManager.value.alignmentError.individual) {
    ElMessage.warning('没有误差数据');
    return;
  }
  
  const errors = alignmentManager.value.alignmentError.individual;
  const errorStats = alignmentManager.value.alignmentError;
  
  let message = `误差分布统计:\n`;
  message += `• 点对数量: ${errors.length}\n`;
  message += `• RMS误差: ${errorStats.rms.toFixed(4)}m\n`;
  message += `• 平均误差: ${errorStats.mean.toFixed(4)}m\n`;
  message += `• 最大误差: ${errorStats.max.toFixed(4)}m\n`;
  message += `• 最小误差: ${errorStats.min.toFixed(4)}m\n`;
  message += `• 标准差: ${errorStats.std.toFixed(4)}m\n\n`;
  
  message += `各点对误差:\n`;
  errors.forEach((error, index) => {
    const pair = pointPairs.value[index];
    const pairName = pair ? pair.name : `点对${index + 1}`;
    message += `• ${pairName}: ${error.toFixed(4)}m\n`;
  });
  
  ElMessageBox.alert(message, '误差分布详情', {
    confirmButtonText: '确定',
    type: 'info'
  });
}

// 显示详细报告
function showDetailedReport() {
  if (!alignmentManager.value.alignmentError || !alignmentManager.value.qualityAssessment) {
    ElMessage.warning('没有配准数据');
    return;
  }
  
  const errorStats = alignmentManager.value.alignmentError;
  const quality = alignmentManager.value.qualityAssessment;
  
  let report = `配准详细报告\n`;
  report += `==================\n\n`;
  
  report += `配准概况:\n`;
  report += `• 配准方法: 两阶段Kabsch算法\n`;
  report += `• 特征点对数量: ${pointPairs.value.length}\n`;
  report += `• 配准时间: ${new Date().toLocaleString()}\n\n`;
  
  report += `误差统计:\n`;
  report += `• RMS误差: ${errorStats.rms.toFixed(6)}m\n`;
  report += `• 平均误差: ${errorStats.mean.toFixed(6)}m\n`;
  report += `• 最大误差: ${errorStats.max.toFixed(6)}m\n`;
  report += `• 最小误差: ${errorStats.min.toFixed(6)}m\n`;
  report += `• 标准差: ${errorStats.std.toFixed(6)}m\n`;
  report += `• 旋转角度: ${errorStats.rotation.toFixed(3)}°\n\n`;
  
  report += `质量评估:\n`;
  report += `• 质量等级: ${quality.quality}\n`;
  report += `• 质量评分: ${quality.score}/100\n`;
  report += `• 质量摘要: ${quality.summary}\n\n`;
  
  if (quality.recommendations.length > 0) {
    report += `改进建议:\n`;
    quality.recommendations.forEach((rec, index) => {
      report += `${index + 1}. ${rec}\n`;
    });
    report += `\n`;
  }
  
  report += `特征点对详情:\n`;
  pointPairs.value.forEach((pair, index) => {
    const error = errorStats.individual[index];
    report += `${pair.name}:\n`;
    report += `  BIM点: (${pair.bimPoint.x.toFixed(3)}, ${pair.bimPoint.y.toFixed(3)}, ${pair.bimPoint.z.toFixed(3)})\n`;
    report += `  RTK点: (${pair.rtkPoint.x.toFixed(3)}, ${pair.rtkPoint.y.toFixed(3)}, ${pair.rtkPoint.z.toFixed(3)})\n`;
    report += `  误差: ${error.toFixed(6)}m\n\n`;
  });
  
  ElMessageBox.alert(report, '配准详细报告', {
    confirmButtonText: '确定',
    type: 'info'
  });
}

// 导出配准报告
function exportAlignmentReport() {
  if (!alignmentManager.value.alignmentError || !alignmentManager.value.qualityAssessment) {
    ElMessage.warning('没有配准数据可导出');
    return;
  }
  
  // 生成报告内容
  const errorStats = alignmentManager.value.alignmentError;
  const quality = alignmentManager.value.qualityAssessment;
  
  const reportData = {
    timestamp: new Date().toISOString(),
    method: '两阶段Kabsch算法配准',
    pointPairsCount: pointPairs.value.length,
    stage1: {
      bimBasePoint: alignmentManager.value.bimBasePoint,
      rtkBasePoint: alignmentManager.value.rtkBasePoint,
      completed: alignmentManager.value.stage1Complete
    },
    stage2: {
      completed: alignmentManager.value.stage2Complete,
      pointPairs: pointPairs.value.map((pair, index) => ({
        name: pair.name,
        bimPoint: pair.bimPoint,
        rtkPoint: pair.rtkPoint,
        error: errorStats.individual[index]
      }))
    },
    errorStatistics: errorStats,
    qualityAssessment: quality
  };
  
  // 创建下载链接
  const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `配准报告_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  
  ElMessage.success('配准报告已导出');
}

// 处理设备点击事件
function handleDeviceClick(device) {
  if (addingPointPair.value && addPointPairStep.value === 2) {
    // 阶段2：选择RTK点
    selectRtkPointForPair(device.id);
  } else {
    // 正常编辑设备
    editDevice(device);
  }
}

// ==================== 数据记录功能 ====================

// 切换数据记录状态
function toggleDataRecording(deviceId) {
  const device = rtkDevices.value[deviceId];
  if (!device) {
    ElMessage.error('设备不存在');
    return;
  }
  
  if (!device.connected || !device.data) {
    ElMessage.warning('设备未连接或无数据，无法开始记录');
    return;
  }
  
  if (device.dataRecording) {
    stopDataRecording(deviceId);
  } else {
    showSaveConfigDialog(deviceId);
  }
}

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

// 取消配置
function cancelSaveConfig() {
  saveConfigDialogVisible.value = false;
  currentRecordingDeviceId.value = '';
  baseSaveFileName.value = '';
}

// 开始数据记录
function startDataRecording(deviceId) {
  const device = rtkDevices.value[deviceId];
  if (!device) return;
  
  try {
    // 初始化数据存储
    recordedData.value[deviceId] = [];
    recordingStartTimes.value[deviceId] = Date.now();
    
    // 标记设备为记录状态
    dataRecordingDevices.value.add(deviceId);
    device.dataRecording = true;
    
    // 启动100ms间隔的定时器
    const interval = setInterval(() => {
      recordDeviceData(deviceId);
    }, 100);
    
    dataRecordIntervals.value[deviceId] = interval;
    
    ElMessage.success(`设备 ${device.name || deviceId} 开始记录数据`);
    console.log(`开始记录设备 ${deviceId} 的数据，基础文件名: ${baseSaveFileName.value}`);
    
  } catch (error) {
    console.error('开始数据记录失败:', error);
    ElMessage.error('开始数据记录失败');
  }
}

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
    const batchNumber = currentBatchNumber.value[deviceId] || 1;
    const totalRecorded = (batchNumber - 1) * 1000 + remainingData.length;
    
    console.log(`停止记录设备 ${deviceId} 的数据，共记录 ${totalRecorded} 条`);
    
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

// 记录设备数据
function recordDeviceData(deviceId) {
  const device = rtkDevices.value[deviceId];
  if (!device || !device.connected || !device.data) {
    console.warn(`设备 ${deviceId} 连接状态或数据异常，跳过本次记录`);
    return;
  }
  
  try {
    // 获取当前时间戳
    const timestamp = new Date().toISOString();
    
    // 获取坐标数据（优先使用世界坐标）
    let eCoord, nCoord, uCoord;
    
    if (device.worldCoords) {
      // 使用转换后的世界坐标
      eCoord = device.worldCoords.x; // E轴直接映射
      nCoord = -device.worldCoords.z; // N轴取反映射（因为N轴指向Z负方向）
      uCoord = device.worldCoords.y; // U轴直接映射
    } else {
      // 回退到原始ENU坐标
      eCoord = device.data.e || 0; // E轴直接映射
      nCoord = -(device.data.n || 0); // N轴取反映射（因为N轴指向Z负方向）
      uCoord = device.data.u || 0; // U轴直接映射
    }
    
    // 构建记录数据
    const dataRecord = {
      timestamp: timestamp,
      deviceId: device.id,
      deviceName: device.name || device.id,
      ipAddress: device.ip || '',
      deviceNumber: device.deviceNumber || '',
      deviceType: device.isBaseStation ? '基站' : '移动站',
      e: eCoord,
      n: nCoord,
      u: uCoord
    };
    
    // 添加到记录数据中
    if (!recordedData.value[deviceId]) {
      recordedData.value[deviceId] = [];
    }
    
    recordedData.value[deviceId].push(dataRecord);
    
    // 检查是否需要自动导出
    checkAutoExport(deviceId);
    
  } catch (error) {
    console.error(`记录设备 ${deviceId} 数据失败:`, error);
  }
}

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
  
  // 轻量提示，不干扰用户
  console.log(`设备 ${deviceId} 自动导出第 ${batchNumber} 批数据，${exportData.length} 条记录`);
  
  // 可选：显示简短通知
  ElMessage({
    message: `已自动导出第 ${batchNumber} 批数据 (1000条)`,
    type: 'success',
    duration: 2000,
    showClose: false
  });
}



// 导出CSV文件
function exportDataToCSV(data, filename) {
  return new Promise((resolve, reject) => {
    try {
      // CSV表头
      const headers = [
        '世界时间',
        '设备ID', 
        '设备名称',
        'IP地址',
        '设备编号',
        '设备类型',
        'E坐标',
        'N坐标', 
        'U坐标'
      ];
      
      // 构建CSV内容
      let csvContent = headers.join(',') + '\n';
      
      data.forEach(record => {
        const row = [
          record.timestamp,
          record.deviceId,
          `"${record.deviceName}"`, // 用引号包围，防止名称中有逗号
          record.ipAddress,
          record.deviceNumber,
          record.deviceType,
          record.e.toFixed(6),
          record.n.toFixed(6),
          record.u.toFixed(6)
        ];
        csvContent += row.join(',') + '\n';
      });
      
      // 创建下载链接
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      
      link.href = url;
      link.download = filename.endsWith('.csv') ? filename : filename + '.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      resolve();
      
    } catch (error) {
      reject(error);
    }
  });
}



// 生命周期钩子
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
    // 不调用applyRestoredAlignment，避免显示恢复消息
    // 更新模型变换状态
    modelTransformApplied.value = true;
  }
  
  // 获取RTK设备数据
  await fetchRtkDevices();
  
  // 如果恢复了配准状态，重新应用坐标转换（静默）
  if (stateRestored && alignmentManager.value.rtkBasePoint) {
    updateAllRtkWorldCoords();
    console.log('RTK坐标系已静默恢复到配准状态');
  }
  
  // 设置数据刷新间隔，并在每次刷新后检查基准点
  refreshInterval.value = setInterval(() => {
    fetchRtkDevices().then(() => {
      // 检查基准点坐标更新
      checkRtkBasePointUpdate();
    });
  }, 2000);
  
  // 模拟WebSocket连接状态
  setTimeout(() => {
    wsConnected.value = true;
  }, 1000);
});

onBeforeUnmount(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value);
  }
  
  // 清理所有数据记录定时器和状态
  Object.values(dataRecordIntervals.value).forEach(interval => {
    clearInterval(interval);
  });
  dataRecordIntervals.value = {};
  dataRecordingDevices.value.clear();
  currentBatchNumber.value = {};
});
</script>

<style scoped>
.rtk-monitor-dashboard {
  min-height: 100vh;
  background: #000000;
  color: #ffffff;
  font-family: 'Roboto', sans-serif;
}

.status-bar {
  display: flex;
  justify-content: space-around;
  padding: 15px 30px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 2px 20px rgba(255, 255, 255, 0.1);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.status-icon {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  box-shadow: 0 0 10px currentColor;
}

.status-icon.online {
  background: #00ff88;
  color: #00ff88;
}

.status-icon.offline {
  background: #ff4444;
  color: #ff4444;
}

.status-value {
  font-size: 24px;
  font-weight: bold;
  color: #ffffff;
}

.main-content {
  display: flex;
  gap: 20px;
  padding: 20px;
  height: calc(100vh - 80px);
}

.control-panel {
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-height: calc(100vh - 140px); /* 减去顶部状态栏和一些边距 */
  overflow-y: auto; /* 添加垂直滚动条 */
  padding-right: 10px; /* 为滚动条留出空间 */
}

/* 自定义滚动条样式 */
.control-panel::-webkit-scrollbar {
  width: 8px;
}

.control-panel::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.control-panel::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  transition: background 0.3s ease;
}

.control-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

.panel-section {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 8px 32px rgba(255, 255, 255, 0.1);
}

.section-title {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #ffffff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  padding-bottom: 10px;
}

.scan-btn {
  width: 100%;
  height: 50px;
  background: linear-gradient(45deg, #444444, #666666);
  border: 1px solid #ffffff;
  border-radius: 8px;
  font-size: 16px;
  font-weight: bold;
  color: #ffffff;
  box-shadow: 0 4px 20px rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
}

.scan-btn:hover {
  background: linear-gradient(45deg, #666666, #888888);
  box-shadow: 0 6px 30px rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

.device-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.device-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.device-card:hover {
  background: rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 20px rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.device-card:active {
  transform: translateY(0px);
  background: rgba(255, 255, 255, 0.3);
}

.device-icon {
  font-size: 24px;
  color: #ffffff;
}

.device-info {
  flex: 1;
}

.device-id {
  font-weight: bold;
  color: #ffffff;
}

.device-ip {
  font-size: 12px;
  color: #888;
}

.signal-bars {
  display: flex;
  gap: 2px;
  align-items: end;
}

.bar {
  width: 4px;
  height: 8px;
  background: #333;
  border-radius: 2px;
}

.bar.active {
  background: #00ff88;
  box-shadow: 0 0 5px #00ff88;
}

.registered-devices {
  display: flex;
  flex-direction: column;
  gap: 15px;
  max-height: 400px;
  overflow-y: auto;
}

.registered-device {
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.registered-device:hover {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 20px rgba(255, 255, 255, 0.1);
}

.registered-device:active {
  transform: scale(0.98);
  background: rgba(255, 255, 255, 0.15);
}

.registered-device.active {
  border-color: rgba(0, 255, 136, 0.5);
  box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
}

.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.device-name {
  font-weight: bold;
  color: #ffffff;
  display: flex;
  align-items: center;
}

.device-color-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 8px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 0 4px rgba(0, 0, 0, 0.3);
  flex-shrink: 0;
}

.device-status {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
}

.device-status.online {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.device-status.offline {
  background: rgba(255, 68, 68, 0.2);
  color: #ff4444;
}

.device-details {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 10px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.label {
  color: #888;
}

.value {
  color: #ffffff;
}

.value.base-station {
  color: #ff6666;
}

.value.mobile-station {
  color: #66aaff;
}

.position-data {
  display: flex;
  gap: 15px;
  font-size: 11px;
}

.coordinate {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.coord-label {
  color: #888;
}

.coord-value {
  color: #ffffff;
  font-weight: bold;
}

.visualization-control {
  display: flex;
  justify-content: center;
  margin-top: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.trajectory-controls {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  justify-content: center;
  flex-wrap: wrap;
}

.data-record-btn {
  font-size: 11px;
  padding: 4px 8px;
  height: auto;
  min-height: 24px;
  margin-right: 4px;
}

.trajectory-btn {
  font-size: 11px;
  padding: 4px 8px;
  height: auto;
  min-height: 24px;
}

.visualization-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.panel-header h2 {
  margin: 0;
  color: #ffffff;
}

.three-container {
  flex: 1;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(255, 255, 255, 0.1);
}

:deep(.config-dialog) {
  background: rgba(240, 240, 240, 0.98);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(200, 200, 200, 0.5);
  border-radius: 15px;
}

:deep(.config-dialog .el-dialog__header) {
  background: linear-gradient(45deg, rgba(255, 255, 255, 0.9), rgba(240, 240, 240, 0.9));
  border-bottom: 1px solid rgba(200, 200, 200, 0.5);
}

:deep(.config-dialog .el-dialog__title) {
  color: #333333;
  font-weight: bold;
}

:deep(.config-dialog .el-form-item__label) {
  color: #333333;
  font-weight: 500;
}

:deep(.config-dialog .el-input__wrapper) {
  background: #ffffff;
  border: 1px solid #d1d5db;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

:deep(.config-dialog .el-input__inner) {
  background: transparent;
  border: none;
  color: #333333;
}

:deep(.config-dialog .el-input__inner::placeholder) {
  color: #9ca3af;
}

:deep(.config-dialog .el-radio__label) {
  color: #333333;
}

:deep(.config-dialog .el-radio__input.is-checked .el-radio__inner) {
  background-color: #409eff;
  border-color: #409eff;
}

:deep(.config-dialog .el-button--primary) {
  background-color: #409eff;
  border-color: #409eff;
}

:deep(.config-dialog .el-button--danger) {
  background-color: #f56565;
  border-color: #f56565;
}

/* 滚动条样式 */
.registered-devices::-webkit-scrollbar {
  width: 6px;
}

.registered-devices::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.registered-devices::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.registered-devices::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

/* 建筑模型管理样式 */
.model-upload-section {
  margin-bottom: 1rem;
  text-align: center;
}

.model-upload-section .upload-tip {
  margin-top: 0.5rem;
  font-size: 12px;
  color: #888;
}

.model-controls {
  margin: 1rem 0;
}

.model-controls .control-item {
  margin-bottom: 1rem;
}

.model-controls .control-item .control-label {
  display: inline-block;
  width: 80px;
  color: #888;
  font-size: 14px;
  margin-right: 0.5rem;
}

.model-controls .control-item .el-slider {
  width: calc(100% - 100px);
  display: inline-block;
  vertical-align: middle;
}

.loaded-models-list {
  margin-top: 1rem;
}

.loaded-models-list h4 {
  color: #e0e0e0;
  margin-bottom: 0.5rem;
  font-size: 14px;
}

.loaded-models-list .model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  margin-bottom: 0.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s;
}

.loaded-models-list .model-item:hover {
  background: rgba(0, 0, 0, 0.5);
  border-color: rgba(255, 255, 255, 0.2);
}

.loaded-models-list .model-item .model-info .model-name {
  color: #e0e0e0;
  font-size: 14px;
  margin-right: 0.5rem;
}

.loaded-models-list .model-item .model-info .model-size {
  color: #888;
  font-size: 12px;
  text-transform: uppercase;
}

.loaded-models-list .model-item .model-actions {
  display: flex;
  gap: 0.5rem;
}

.loaded-models-list .model-item .model-actions .el-button {
  padding: 4px;
  font-size: 12px;
}

/* 修改Element Plus组件在暗色主题下的样式 */
:deep(.el-radio-button__inner) {
  background: rgba(0, 0, 0, 0.3);
  border-color: rgba(255, 255, 255, 0.2);
  color: #e0e0e0;
}

:deep(.el-radio-button__inner:hover) {
  color: #00ff88;
}

:deep(.el-radio-button__orig-radio:checked + .el-radio-button__inner) {
  background: rgba(0, 255, 136, 0.2);
  border-color: #00ff88;
  color: #00ff88;
}

/* 手动添加设备按钮样式 */
.manual-add-btn {
  background: linear-gradient(135deg, #00d4aa, #00ff88) !important;
  border: none !important;
  color: white !important;
}

.manual-add-btn:hover {
  background: linear-gradient(135deg, #00a87a, #00cc6a) !important;
  transform: translateY(-1px);
}

.scan-controls {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

:deep(.el-slider__runway) {
  background: rgba(255, 255, 255, 0.1);
}

:deep(.el-slider__bar) {
  background: #00ff88;
}

:deep(.el-slider__button) {
  border-color: #00ff88;
}

/* ==================== 配准系统样式 ==================== */

.alignment-stage {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.alignment-stage.disabled {
  opacity: 0.6;
  pointer-events: none;
}

.stage-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 15px 0;
  font-size: 16px;
  font-weight: 600;
  color: #e0e0e0;
}

.stage-title i {
  color: #00ff88;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  margin-left: auto;
}

.status-badge.success {
  background-color: rgba(0, 255, 136, 0.2);
  color: #00ff88;
  border: 1px solid #00ff88;
}

.status-badge.disabled {
  background-color: rgba(255, 255, 255, 0.1);
  color: #888;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.base-point-section {
  margin-bottom: 15px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.section-label {
  font-weight: 500;
  color: #e0e0e0;
}

.vertex-controls {
  margin-bottom: 10px;
}

.control-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.control-label {
  font-size: 14px;
  color: #ccc;
  min-width: 80px;
}

.base-point-info {
  background: rgba(0, 255, 136, 0.1);
  padding: 10px;
  border-radius: 4px;
  border-left: 3px solid #00ff88;
}

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-label {
  font-size: 13px;
  color: #888;
}

.info-value {
  font-size: 13px;
  color: #e0e0e0;
  font-weight: 500;
}

.info-value.success {
  color: #00ff88;
}

.rtk-base-controls {
  margin-bottom: 10px;
}

.stage-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.feature-points-section {
  margin-bottom: 15px;
}

.adding-point-pair {
  background: rgba(255, 193, 7, 0.1);
  padding: 10px;
  border-radius: 4px;
  border: 1px solid rgba(255, 193, 7, 0.3);
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.add-point-step {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-label {
  font-weight: 500;
  color: #ffc107;
}

.step-desc {
  font-size: 13px;
  color: #ccc;
}

.point-pairs-list {
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 10px;
}

.point-pair-item {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 10px;
  margin-bottom: 8px;
}

.pair-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.pair-name {
  font-weight: 500;
  color: #e0e0e0;
}

.pair-actions {
  display: flex;
  gap: 4px;
}

.pair-coords {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.coord-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.coord-label {
  font-size: 12px;
  color: #888;
  min-width: 35px;
}

.coord-value {
  font-size: 12px;
  color: #ccc;
  font-family: monospace;
}

.point-pairs-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 4px;
  color: #409eff;
  font-size: 13px;
}

.alignment-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.alignment-results {
  background: rgba(0, 0, 0, 0.4);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 15px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.result-item:last-child {
  margin-bottom: 0;
}

.result-label {
  font-size: 13px;
  color: #ccc;
}

.result-value {
  font-size: 13px;
  font-weight: 500;
  font-family: monospace;
}

.result-value.excellent {
  color: #00ff88;
}

.result-value.good {
  color: #ffc107;
}

.result-value.warning {
  color: #ff6b6b;
}

.result-value.error {
  color: #ff4757;
  font-weight: 600;
}

.alignment-overview {
  background: rgba(64, 158, 255, 0.1);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid rgba(64, 158, 255, 0.3);
}

.overview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.overview-item:last-child {
  margin-bottom: 0;
}

.overview-label {
  font-size: 14px;
  color: #e0e0e0;
  font-weight: 500;
}

.overview-status {
  font-size: 13px;
  color: #888;
}

.overview-status.success {
  color: #00ff88;
  font-weight: 500;
}

.overview-status.excellent {
  color: #00ff88;
  font-weight: 600;
}

.overview-status.good {
  color: #ffc107;
  font-weight: 500;
}

.overview-status.warning {
  color: #ff6b6b;
  font-weight: 500;
}

.overview-status.error {
  color: #ff4757;
  font-weight: 600;
}

/* 滚动条样式 - 配准面板 */
.point-pairs-list::-webkit-scrollbar {
  width: 6px;
}

.point-pairs-list::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.point-pairs-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.point-pairs-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

/* Element Plus 组件在配准面板中的样式调整 */
:deep(.alignment-stage .el-switch__core) {
  background: rgba(255, 255, 255, 0.2);
}

:deep(.alignment-stage .el-switch.is-checked .el-switch__core) {
  background: #00ff88;
}

:deep(.alignment-stage .el-radio-button__inner) {
  background: rgba(0, 0, 0, 0.4);
  border-color: rgba(255, 255, 255, 0.2);
  color: #e0e0e0;
}

:deep(.alignment-stage .el-radio-button__orig-radio:checked + .el-radio-button__inner) {
  background: rgba(0, 255, 136, 0.2);
  border-color: #00ff88;
  color: #00ff88;
}

:deep(.alignment-stage .el-select .el-input__wrapper) {
  background: rgba(0, 0, 0, 0.4);
  border-color: rgba(255, 255, 255, 0.2);
}

:deep(.alignment-stage .el-select .el-input__inner) {
  color: #e0e0e0;
}

:deep(.alignment-stage .el-button--mini) {
  padding: 2px 6px;
  font-size: 11px;
}

/* 质量评估样式 */
.quality-assessment {
  margin-top: 15px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.quality-score {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.score-label {
  font-size: 14px;
  color: #e0e0e0;
  font-weight: 500;
}

.score-value {
  font-size: 16px;
  font-weight: 600;
  font-family: monospace;
}

.score-value.excellent {
  color: #00ff88;
}

.score-value.good {
  color: #ffc107;
}

.score-value.warning {
  color: #ff6b6b;
}

.score-value.error {
  color: #ff4757;
}

.recommendations {
  margin-top: 10px;
}

.recommendations-title {
  font-size: 13px;
  color: #ffc107;
  font-weight: 500;
  margin-bottom: 8px;
}

.recommendations-list {
  margin: 0;
  padding-left: 16px;
  color: #ccc;
  font-size: 12px;
}

.recommendations-list li {
  margin-bottom: 4px;
  line-height: 1.4;
}

.result-actions {
  margin-top: 15px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* RTK设备选择状态样式 */
.registered-device.rtk-selectable {
  border: 2px solid #ffc107 !important;
  background: rgba(255, 193, 7, 0.1) !important;
  cursor: pointer;
  animation: pulse 2s infinite;
}

.registered-device.rtk-selectable:hover {
  background: rgba(255, 193, 7, 0.2) !important;
  transform: scale(1.02);
}

.registered-device.rtk-selectable::after {
  content: "点击选择";
  position: absolute;
  top: -8px;
  right: -8px;
  background: #ffc107;
  color: #000;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: bold;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(255, 193, 7, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(255, 193, 7, 0);
  }
}

/* 数据记录配置对话框样式 */
:deep(.save-config-dialog) {
  background: rgba(240, 240, 240, 0.98);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(200, 200, 200, 0.5);
  border-radius: 15px;
}

:deep(.save-config-dialog .el-dialog__header) {
  background: linear-gradient(45deg, rgba(255, 255, 255, 0.9), rgba(240, 240, 240, 0.9));
  border-bottom: 1px solid rgba(200, 200, 200, 0.5);
}

:deep(.save-config-dialog .el-dialog__title) {
  color: #333333;
  font-weight: bold;
}

.save-config-content {
  color: #333333;
  line-height: 1.6;
}

.save-config-content p {
  margin: 0 0 15px 0;
  font-size: 15px;
}

.filename-preview {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 4px;
  font-size: 13px;
  color: #666;
  font-family: monospace;
}

.export-info {
  background: rgba(255, 193, 7, 0.1);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 193, 7, 0.3);
}

.export-info p {
  margin: 5px 0;
  font-size: 13px;
  color: #856404;
}

:deep(.save-config-dialog .el-form-item__label) {
  color: #333333;
  font-weight: 500;
}

:deep(.save-config-dialog .el-input__wrapper) {
  background: #ffffff;
  border: 1px solid #d1d5db;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

:deep(.save-config-dialog .el-input__inner) {
  background: transparent;
  border: none;
  color: #333333;
}

:deep(.save-config-dialog .el-button--primary) {
  background-color: #409eff;
  border-color: #409eff;
}
</style>
