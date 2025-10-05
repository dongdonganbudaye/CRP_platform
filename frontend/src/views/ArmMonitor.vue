<template>
  <div class="arm-monitor-page">
    <div class="page-content">
      <div class="main-title">
        机械臂监控
        <div class="title-controls">
          <v-btn
            size="small"
            :color="debugMode ? 'primary' : 'secondary'"
            variant="tonal"
            class="debug-btn"
            @click="toggleDebugMode"
          >
            <v-icon size="small" class="mr-1">mdi-bug</v-icon>
            调试模式
          </v-btn>
        </div>
      </div>
      
      <div class="video-section">
        <div class="triple-video-container">
          <div class="video-panel">
            <div class="video-title">
              <v-icon color="primary" class="mr-1">mdi-robot</v-icon>
              机械臂1 (192.168.0.10)
            </div>
            <WebRtcStream 
              @stream-status-change="updateStreamStatus1" 
              :debugMode="debugMode"
              :streamUrl="webrtcUrl1"
              :audioEnabled="true"
              ref="webrtcStream1"
              class="rotated-stream"
            />
          </div>
          <div class="video-panel">
            <div class="video-title">
              <v-icon color="primary" class="mr-1">mdi-robot</v-icon>
              机械臂2 (192.168.0.12)
            </div>
            <WebRtcStream 
              @stream-status-change="updateStreamStatus2" 
              :debugMode="debugMode"
              :streamUrl="webrtcUrl2"
              :audioEnabled="true"
              ref="webrtcStream2"
              class="rotated-stream"
            />
          </div>
          <div class="video-panel">
            <div class="video-title">
              <v-icon color="primary" class="mr-1">mdi-robot</v-icon>
              机械臂3 (192.168.0.22)
            </div>
            <WebRtcStream 
              @stream-status-change="updateStreamStatus3" 
              :debugMode="debugMode"
              :streamUrl="webrtcUrl3"
              :audioEnabled="true"
              ref="webrtcStream3"
              class="rotated-stream"
            />
          </div>
        </div>
      </div>
      
      <div class="info-section">
        <div class="info-card">
          <div class="card-title">
            <v-icon color="primary" class="mr-2">mdi-information-outline</v-icon>
            机械臂1 (192.168.0.10)
          </div>
          <div class="info-content">
            <div class="info-item">
              <span class="info-label">摄像头状态:</span>
              <span class="info-value" :class="{ 'online': isArm1CameraConnected, 'offline': !isArm1CameraConnected }">
                {{ isArm1CameraConnected ? '已连接' : '未连接' }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">视频流状态:</span>
              <span class="info-value" :class="{ 'online': isStream1Active, 'offline': !isStream1Active }">
                {{ isStream1Active ? '活跃' : '非活跃' }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">音频支持:</span>
              <span class="info-value">{{ isStream1Active ? '已启用' : '无数据' }}</span>
            </div>
          </div>
        </div>
        
        <div class="info-card">
          <div class="card-title">
            <v-icon color="primary" class="mr-2">mdi-information-outline</v-icon>
            机械臂2 (192.168.0.12)
          </div>
          <div class="info-content">
            <div class="info-item">
              <span class="info-label">摄像头状态:</span>
              <span class="info-value" :class="{ 'online': isArm2CameraConnected, 'offline': !isArm2CameraConnected }">
                {{ isArm2CameraConnected ? '已连接' : '未连接' }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">视频流状态:</span>
              <span class="info-value" :class="{ 'online': isStream2Active, 'offline': !isStream2Active }">
                {{ isStream2Active ? '活跃' : '非活跃' }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">音频支持:</span>
              <span class="info-value">{{ isStream2Active ? '已启用' : '无数据' }}</span>
            </div>
          </div>
        </div>
        
        <div class="info-card">
          <div class="card-title">
            <v-icon color="primary" class="mr-2">mdi-information-outline</v-icon>
            机械臂3 (192.168.0.22)
          </div>
          <div class="info-content">
            <div class="info-item">
              <span class="info-label">摄像头状态:</span>
              <span class="info-value" :class="{ 'online': isArm3CameraConnected, 'offline': !isArm3CameraConnected }">
                {{ isArm3CameraConnected ? '已连接' : '未连接' }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">视频流状态:</span>
              <span class="info-value" :class="{ 'online': isStream3Active, 'offline': !isStream3Active }">
                {{ isStream3Active ? '活跃' : '非活跃' }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">音频支持:</span>
              <span class="info-value">{{ isStream3Active ? '已启用' : '无数据' }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="system-info">
        <div class="info-card">
          <div class="card-title">
            <v-icon color="primary" class="mr-2">mdi-server</v-icon>
            系统信息
          </div>
          <div class="info-content">
            <div class="info-item">
              <span class="info-label">后端API服务:</span>
              <span class="info-value" :class="{ 'online': isBackendConnected, 'offline': !isBackendConnected }">
                {{ isBackendConnected ? '在线' : '离线' }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">协议类型:</span>
              <span class="info-value">WebRTC</span>
            </div>
            <div class="info-item">
              <span class="info-label">延迟优化:</span>
              <span class="info-value">{{ (isStream1Active || isStream2Active || isStream3Active) ? '已启用' : '无数据' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">总连接数:</span>
              <span class="info-value">{{ (isStream1Active ? 1 : 0) + (isStream2Active ? 1 : 0) + (isStream3Active ? 1 : 0) }}/3</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import WebRtcStream from '../components/video/WebRtcStream.vue';

export default {
  name: 'ArmMonitor',
  components: {
    WebRtcStream
  },
  data() {
    return {
      // 机械臂1状态 (192.168.0.10)
      isStream1Active: false,
      isArm1CameraConnected: false,
      webrtcUrl1: 'http://192.168.0.10/player/webrtc?streamPath=hlsram/live0&isMute=1&auto=1&aspect=0&hasAudio=1&username=admin&auth=f6fdffe48c908deb0f4c3bd36c032e72',
      
      // 机械臂2状态 (192.168.0.12)
      isStream2Active: false,
      isArm2CameraConnected: false,
      webrtcUrl2: 'http://192.168.0.12/player/webrtc?streamPath=hlsram/live0&isMute=1&auto=1&aspect=0&hasAudio=1&username=admin&auth=f6fdffe48c908deb0f4c3bd36c032e72',
      
      // 机械臂3状态 (192.168.0.22)
      isStream3Active: false,
      isArm3CameraConnected: false,
      webrtcUrl3: 'http://192.168.0.22/player/webrtc?streamPath=hlsram/live0&isMute=1&auto=1&aspect=0&hasAudio=1&username=admin&auth=f6fdffe48c908deb0f4c3bd36c032e72',
      
      // 系统状态
      isBackendConnected: false,
      checkBackendTimer: null,
      checkCameraTimer: null,
      debugMode: false
    }
  },
  methods: {
    updateStreamStatus1(status) {
      this.isStream1Active = status;
      // 摄像头状态应该独立检测，不直接等于视频流状态
      if (!status) {
        this.isArm1CameraConnected = false;
      }
    },
    updateStreamStatus2(status) {
      this.isStream2Active = status;
      // 摄像头状态应该独立检测，不直接等于视频流状态
      if (!status) {
        this.isArm2CameraConnected = false;
      }
    },
    updateStreamStatus3(status) {
      this.isStream3Active = status;
      // 摄像头状态应该独立检测，不直接等于视频流状态
      if (!status) {
        this.isArm3CameraConnected = false;
      }
    },
    checkBackendConnection() {
      // 检查后端API服务是否可用（使用机械臂专用API）
      fetch('/api/arm/status')
        .then(response => {
          if (response.ok) {
            this.isBackendConnected = true;
            return response.json();
          } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
        })
        .then(data => {
          console.log('Backend API status:', data);
        })
        .catch(error => {
          console.error('Backend API connection error:', error);
          this.isBackendConnected = false;
          
          // 如果机械臂API不可用，尝试检查基础API服务
          fetch('/api/')
            .then(response => {
              if (response.ok) {
                this.isBackendConnected = true;
                console.log('Backend base API is available');
              }
            })
            .catch(baseError => {
              console.error('Backend base API also failed:', baseError);
              this.isBackendConnected = false;
            });
        });
    },
    checkArmCameraStatus() {
      // 检查机械臂摄像头状态 - 通过ping或HTTP请求测试设备连通性
      const armIPs = ['192.168.0.10', '192.168.0.12', '192.168.0.22'];
      const cameraStatusPromises = armIPs.map((ip, index) => {
        return new Promise((resolve) => {
          // 尝试访问摄像头的基础页面来检测连通性
          const testUrl = `http://${ip}/`;
          const timeout = 3000; // 3秒超时
          
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), timeout);
          
          fetch(testUrl, { 
            method: 'HEAD',
            mode: 'no-cors', // 允许跨域请求
            signal: controller.signal 
          })
          .then(() => {
            clearTimeout(timeoutId);
            resolve({ index, connected: true });
          })
          .catch(() => {
            clearTimeout(timeoutId);
            resolve({ index, connected: false });
          });
        });
      });
      
      Promise.all(cameraStatusPromises).then(results => {
        results.forEach(result => {
          switch(result.index) {
            case 0:
              this.isArm1CameraConnected = result.connected;
              break;
            case 1:
              this.isArm2CameraConnected = result.connected;
              break;
            case 2:
              this.isArm3CameraConnected = result.connected;
              break;
          }
        });
        
        if (this.debugMode) {
          console.log('Camera status check results:', results);
        }
      });
    },
    toggleDebugMode() {
      this.debugMode = !this.debugMode;
      console.log('调试模式:', this.debugMode ? '开启' : '关闭');
    }
  },
  created() {
    console.log('ArmMonitor component created');
  },
  mounted() {
    console.log('ArmMonitor component mounted');
    // 初始检查
    this.checkBackendConnection();
    this.checkArmCameraStatus();
    
    // 定期检查后端连接 (每30秒)
    this.checkBackendTimer = setInterval(() => {
      this.checkBackendConnection();
    }, 30000);
    
    // 定期检查摄像头状态 (每10秒)
    this.checkCameraTimer = setInterval(() => {
      this.checkArmCameraStatus();
    }, 10000);
  },
  beforeUnmount() {
    console.log('ArmMonitor component unmounting, cleaning up');
    // 清除定时器
    if (this.checkBackendTimer) {
      clearInterval(this.checkBackendTimer);
      this.checkBackendTimer = null;
    }
    if (this.checkCameraTimer) {
      clearInterval(this.checkCameraTimer);
      this.checkCameraTimer = null;
    }
  }
}
</script>

<style scoped>
.arm-monitor-page {
  padding: 80px 20px 20px 20px;
  min-height: 100vh;
  background: #000;
  display: flex;
  flex-direction: column;
}

.page-content {
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
}

.main-title {
  font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 28px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 30px;
  letter-spacing: 1px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-controls {
  display: flex;
  gap: 10px;
}

.debug-btn {
  min-width: 90px;
  font-size: 12px;
}

.video-section {
  width: 100%;
  height: 75vh; /* 增加高度从65vh到75vh */
  margin-bottom: 20px;
  border-radius: 10px;
  overflow: hidden;
}

.triple-video-container {
  display: flex;
  gap: 12px;
  height: 100%;
}

.video-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(18, 18, 18, 0.3);
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  /* 为旋转后的视频提供合适的容器 */
  min-height: 0;
  /* 调整宽高比以适应旋转后的内容 */
  aspect-ratio: 3/4; /* 适应旋转90度后的画面比例 */
}

.video-title {
  background: rgba(18, 18, 18, 0.8);
  color: #fff;
  padding: 10px 14px;
  font-size: 15px;
  font-weight: 500;
  display: flex;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.video-panel .webrtc-stream {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  /* 确保视频容器占满可用空间 */
  width: 100%;
  height: 100%;
}

.rotated-stream {
  transform: rotate(90deg);
  transform-origin: center center;
  /* 让旋转后的画面填满整个容器 */
  width: 140%; /* 增加宽度补偿旋转后的尺寸变化 */
  height: 140%; /* 增加高度补偿旋转后的尺寸变化 */
  max-width: none;
  max-height: none;
}

/* 为旋转后的iframe添加特殊样式 */
.rotated-stream .webrtc-iframe {
  width: 100%;
  height: 100%;
  object-fit: cover; /* 改为cover让画面填满容器 */
}

.info-section {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
}

.system-info {
  display: flex;
  gap: 15px;
}

.info-card {
  flex: 1;
  background: rgba(18, 18, 18, 0.7);
  border-radius: 10px;
  padding: 18px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.system-info .info-card {
  max-width: 100%;
}

.card-title {
  font-size: 17px;
  font-weight: 500;
  color: #fff;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
}

.info-content {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
}

.info-value {
  color: #fff;
  font-size: 15px;
  font-weight: 500;
  word-break: break-all;
}

.info-value.online {
  color: #4cd964;
}

.info-value.offline {
  color: #ff3b30;
}

@media (max-width: 1400px) {
  .info-section {
    flex-wrap: wrap;
  }
  
  .info-card {
    min-width: calc(50% - 10px);
  }
}

@media (max-width: 1024px) {
  .triple-video-container {
    flex-direction: column;
    gap: 10px;
  }
  
  .video-section {
    height: auto;
  }
  
  .video-panel {
    height: 50vh; /* 增加移动端高度从40vh到50vh */
    aspect-ratio: auto; /* 移动端移除宽高比限制 */
  }
  
  .info-section {
    flex-direction: column;
  }
  
  .info-card {
    min-width: 100%;
  }
}

@media (max-width: 768px) {
  .video-panel {
    height: 45vh; /* 增加小屏幕高度从35vh到45vh */
  }
  
  .info-content {
    grid-template-columns: 1fr;
  }
  
  .video-title {
    font-size: 13px;
    padding: 8px 10px;
  }
  
  .page-content {
    max-width: 100%;
  }
}
</style>