<template>
  <div class="webrtc-stream">
    <!-- WebRTC Video Stream via iframe -->
    <iframe
      v-if="isStreamActive"
      :src="iframeUrl"
      ref="webrtcFrame"
      class="webrtc-iframe"
      frameborder="0"
      allow="microphone; camera; autoplay; fullscreen"
      allowfullscreen
      @load="onIframeLoad"
      @error="onIframeError"
    ></iframe>
    
    <!-- Loading State -->
    <div v-if="isConnecting" class="connecting-overlay">
      <div class="loader"></div>
      <div class="connecting-text">正在连接 WebRTC 视频流...</div>
    </div>
    
    <!-- Offline State -->
    <div v-if="!isStreamActive && !isConnecting" class="offline-overlay">
      <div class="offline-message">VIDEO SIGNAL OFFLINE</div>
      <div class="offline-details">{{ lastError || '等待WebRTC视频流连接' }}</div>
    </div>
    
    <!-- Debug Panel -->
    <div v-if="debugMode" class="debug-panel">
      <div class="debug-title">WebRTC调试信息</div>
      <div class="debug-item">协议类型: WebRTC</div>
      <div class="debug-item">当前状态: {{ currentStatus }}</div>
      <div class="debug-item">流地址: {{ streamUrl }}</div>
      <div class="debug-item">音频支持: {{ audioEnabled ? '启用' : '禁用' }}</div>
      <div class="debug-item">重连次数: {{ reconnectAttempts }}/{{ maxReconnectAttempts }}</div>
      <div class="debug-item" v-if="lastError">错误信息: {{ lastError }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'WebRtcStream',
  emits: ['stream-status-change'],
  props: {
    autoConnect: {
      type: Boolean,
      default: true
    },
    streamUrl: {
      type: String,
      required: true
    },
    debugMode: {
      type: Boolean,
      default: false
    },
    audioEnabled: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      isStreamActive: false,
      isConnecting: false,
      reconnectAttempts: 0,
      maxReconnectAttempts: 3,
      reconnectTimer: null,
      statusCheckTimer: null,
      lastError: '',
      currentStatus: '未初始化',
      _hasInitialized: false
    }
  },
  computed: {
    iframeUrl() {
      return this.streamUrl;
    }
  },
  watch: {
    isStreamActive(newValue) {
      this.$emit('stream-status-change', newValue);
    }
  },
  methods: {
    startStream() {
      // 防止重复连接
      if (this.isConnecting || this.isStreamActive) {
        console.log('WebRTC流已连接或正在连接中，不重复连接');
        return;
      }
      
      this.isConnecting = true;
      this.currentStatus = '正在连接';
      this.lastError = '';
      
      if (this.debugMode) {
        console.log('WebRTC连接信息:', {
          streamUrl: this.streamUrl,
          audioEnabled: this.audioEnabled
        });
      }
      
      // iframe会自动加载，但我们需要更准确地检测流状态
      // 设置一个更短的初始检查时间
      setTimeout(() => {
        if (this.isConnecting) {
          // 检查iframe是否真的有内容
          const iframe = this.$refs.webrtcFrame;
          if (iframe) {
            try {
              // 尝试检查iframe的内容状态
              // 注意：由于跨域限制，我们无法直接访问iframe内容
              // 所以我们采用保守的方法，假设连接失败直到有明确的成功信号
              this.isStreamActive = false;
              this.isConnecting = false;
              this.currentStatus = '连接超时';
              this.lastError = '视频流连接超时，请检查设备状态';
              
              if (this.debugMode) {
                console.log('WebRTC流连接超时');
              }
              
              // 尝试重连
              this.handleConnectionFailure();
            } catch (error) {
              console.error('检查iframe状态时出错:', error);
              this.handleConnectionFailure();
            }
          }
        }
      }, 8000); // 延长到8秒，给更多时间加载
    },
    
    stopStream() {
      console.log('停止WebRTC视频流');
      
      const iframe = this.$refs.webrtcFrame;
      if (iframe) {
        // 清空iframe src来停止流
        iframe.src = 'about:blank';
      }
      
      this.isStreamActive = false;
      this.isConnecting = false;
      this.currentStatus = '已停止';
      this.clearTimers();
    },
    
    onIframeLoad() {
      if (this.debugMode) {
        console.log('WebRTC iframe loaded');
      }
      
      // iframe加载完成，但需要进一步验证是否真的有视频流
      // 由于跨域限制，我们采用保守策略
      setTimeout(() => {
        if (this.isConnecting) {
          // 如果iframe能够加载，我们假设连接可能成功
          // 但仍然需要用户或其他机制来确认实际的视频流状态
          this.isStreamActive = false; // 保持保守态度
          this.isConnecting = false;
          this.currentStatus = '等待视频流';
          this.lastError = '设备可能离线或视频流不可用';
          
          if (this.debugMode) {
            console.log('WebRTC iframe加载完成，但视频流状态未知');
          }
        }
      }, 2000);
    },
    
    onIframeError() {
      const error = 'WebRTC iframe加载失败';
      console.error(error);
      this.lastError = error;
      this.currentStatus = '加载失败';
      this.handleConnectionFailure();
    },
    
    handleConnectionFailure() {
      this.isStreamActive = false;
      this.isConnecting = false;
      this.currentStatus = '连接失败';
      
      // 自动重连逻辑
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.attemptReconnect();
      } else {
        this.currentStatus = '重连次数已达上限';
        this.lastError = '已达到最大重连次数，请检查网络连接和流地址';
        console.log('Maximum reconnect attempts reached for WebRTC');
      }
    },
    
    attemptReconnect() {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        
        this.clearTimers();
        this.reconnectTimer = setTimeout(() => {
          console.log(`Attempting WebRTC reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
          this.startStream();
        }, Math.min(3000 * this.reconnectAttempts, 10000)); // 指数退避，最大10秒
      }
    },
    
    clearTimers() {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      if (this.statusCheckTimer) {
        clearInterval(this.statusCheckTimer);
        this.statusCheckTimer = null;
      }
    },
    
    // 检查流状态（简化版本，主要依赖iframe加载状态）
    checkStreamStatus() {
      // 对于iframe方式，我们主要依赖加载状态
      // 可以通过检查iframe的contentWindow来判断是否正常
      try {
        const iframe = this.$refs.webrtcFrame;
        if (iframe && iframe.contentWindow) {
          // iframe正常加载
          if (!this.isStreamActive && !this.isConnecting) {
            // 如果当前显示为离线，但iframe存在，可能需要重新激活
            this.currentStatus = '检测到流活动';
          }
        }
      } catch (error) {
        // 跨域限制，无法访问contentWindow，这是正常的
        if (this.debugMode) {
          console.log('无法检查iframe状态（跨域限制）');
        }
      }
    },
    
    // 确保在组件失活时停止流
    deactivateComponent() {
      console.log('WebRtcStream组件被缓存，停止连接');
      this.stopStream();
    },
    
    // 组件重新激活时
    activateComponent() {
      console.log('WebRtcStream组件被激活，重新检查连接状态');
      if (this.autoConnect) {
        this.startStream();
      }
    }
  },
  mounted() {
    console.log('WebRtcStream component mounted');
    
    // 如果autoConnect为true，延迟启动流
    if (this.autoConnect && !this._hasInitialized) {
      setTimeout(() => {
        this.startStream();
      }, 500);
      
      this._hasInitialized = true;
    }
    
    // 定期检查流状态
    this.statusCheckTimer = setInterval(() => {
      this.checkStreamStatus();
    }, 10000); // 每10秒检查一次
  },
  beforeUnmount() {
    console.log('WebRtcStream component unmounting, cleaning up');
    this.stopStream();
  },
  activated() {
    console.log('WebRtcStream component activated');
    this.activateComponent();
  },
  deactivated() {
    console.log('WebRtcStream component deactivated');
    this.deactivateComponent();
  }
}
</script>

<style scoped>
.webrtc-stream {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  background: #000;
}

.webrtc-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: #000;
}

.connecting-overlay, .offline-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: #000;
}

.loader {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255,255,255,0.1);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 1s ease-in-out infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.connecting-text {
  color: rgba(255,255,255,0.7);
  font-size: 14px;
  text-align: center;
}

.offline-message {
  font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
  color: rgba(255,255,255,0.7);
  font-size: 16px;
  letter-spacing: 1px;
  margin-bottom: 10px;
}

.offline-details {
  font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
  color: rgba(255,255,255,0.5);
  font-size: 12px;
  text-align: center;
}

.debug-panel {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(0, 0, 0, 0.8);
  padding: 15px;
  border-radius: 8px;
  font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 12px;
  color: #fff;
  max-width: 300px;
  z-index: 10;
}

.debug-title {
  font-weight: bold;
  margin-bottom: 10px;
  color: #4cd964;
  border-bottom: 1px solid rgba(255,255,255,0.2);
  padding-bottom: 5px;
}

.debug-item {
  margin-bottom: 5px;
  word-break: break-all;
}
</style> 