# HLS切换为WebRTC修改方案

## 概述
将机械臂监控页面的HLS协议切换为WebRTC协议，提供更低延迟的视频流体验。

## 修改内容

### 1. 修改机械臂监控页面 - `frontend/src/views/ArmMonitor.vue`

**目标**：将HlsStream组件替换为WebRtcStream组件，更新相关配置和显示信息。

**具体修改**：

#### 1.1 更新模板部分
```vue
<!-- 原代码（第20-27行） -->
<div class="video-section">
  <HlsStream 
    @stream-status-change="updateStreamStatus" 
    :debugMode="debugMode"
    :streamUrl="streamUrl"
    ref="hlsStream" 
  />
</div>

<!-- 新代码 -->
<div class="video-section">
  <WebRtcStream 
    @stream-status-change="updateStreamStatus" 
    :debugMode="debugMode"
    :streamUrl="webrtcUrl"
    :audioEnabled="false"
    ref="webrtcStream" 
  />
</div>
```

#### 1.2 更新协议信息显示（第58-65行）
```vue
<!-- 原代码 -->
<div class="info-item">
  <span class="info-label">协议类型:</span>
  <span class="info-value">HLS (HTTP Live Streaming)</span>
</div>
<div class="info-item">
  <span class="info-label">延迟优化:</span>
  <span class="info-value">{{ isStreamActive ? '已启用' : '无数据' }}</span>
</div>

<!-- 新代码 -->
<div class="info-item">
  <span class="info-label">协议类型:</span>
  <span class="info-value">WebRTC (Web Real-Time Communication)</span>
</div>
<div class="info-item">
  <span class="info-label">音频支持:</span>
  <span class="info-value">禁用</span>
</div>
<div class="info-item">
  <span class="info-label">实时延迟:</span>
  <span class="info-value">{{ isStreamActive ? '< 1秒' : '无数据' }}</span>
</div>
```

#### 1.3 更新流地址显示（第54-57行）
```vue
<!-- 原代码 -->
<div class="info-item">
  <span class="info-label">流地址:</span>
  <span class="info-value">{{ streamUrl }}</span>
</div>

<!-- 新代码 -->
<div class="info-item">
  <span class="info-label">流地址:</span>
  <span class="info-value">{{ webrtcUrl }}</span>
</div>
```

#### 1.4 更新脚本部分
```javascript
// 原代码（第74行）
import HlsStream from '../components/video/HlsStream.vue';

// 新代码
import WebRtcStream from '../components/video/WebRtcStream.vue';
```

```javascript
// 原代码（第78-80行）
components: {
  HlsStream
},

// 新代码
components: {
  WebRtcStream
},
```

```javascript
// 原代码（第82-89行）
data() {
  return {
    isStreamActive: false,
    isBackendConnected: false,
    isArmCameraConnected: false,
    checkBackendTimer: null,
    streamUrl: '/hlsram/live0/index.m3u8',  // 使用代理路径
    debugMode: false
  }
},

// 新代码
data() {
  return {
    isStreamActive: false,
    isBackendConnected: false,
    isArmCameraConnected: false,
    checkBackendTimer: null,
    webrtcUrl: 'http://192.168.0.51/player/webrtc?streamPath=hlsram/live0&isMute=0&auto=1&aspect=1&hasAudio=0&username=admin&auth=f6fdffe48c908deb0f4c3bd36c032e72',
    debugMode: false
  }
},
```

### 2. 更新后端流服务 - `backend/app/arm_streaming.py`

**目标**：更新后端服务以支持WebRTC流状态检查。

**具体修改**：

#### 2.1 更新流URL和协议信息
```python
# 原代码（第11行）
def __init__(self, stream_url: str = "http://192.168.0.51:80/hlsram/live0/index.m3u8"):

# 新代码
def __init__(self, stream_url: str = "http://192.168.0.51/player/webrtc?streamPath=hlsram/live0&isMute=0&auto=1&aspect=1&hasAudio=0&username=admin&auth=f6fdffe48c908deb0f4c3bd36c032e72"):
```

#### 2.2 更新流信息返回（get_stream_info方法）
```python
# 原代码
return {
    "camera_connected": camera_connected,
    "stream_url": self.stream_url,
    "stream_type": "HLS",
    "protocol": "HTTP Live Streaming",
    "audio_enabled": False,
    "last_check": self.last_check_time,
    "check_interval": self.check_interval,
    "low_latency_enabled": True,
    "timestamp": time.time()
}

# 新代码
return {
    "camera_connected": camera_connected,
    "stream_url": self.stream_url,
    "stream_type": "WebRTC",
    "protocol": "Web Real-Time Communication",
    "audio_enabled": False,
    "last_check": self.last_check_time,
    "check_interval": self.check_interval,
    "low_latency_enabled": True,
    "real_time_latency": "< 1 second",
    "timestamp": time.time()
}
```

#### 2.3 更新连接检查方法
```python
# 在check_camera_connection方法中，将检查逻辑调整为检查WebRTC播放器页面
# 原代码检查 .m3u8 文件
# 新代码检查 WebRTC 播放器页面的可访问性

def check_camera_connection(self) -> bool:
    """检查机械臂WebRTC流连接状态"""
    current_time = time.time()
    
    # 避免频繁检查
    if current_time - self.last_check_time < self.check_interval:
        return self.is_connected
    
    self.last_check_time = current_time
    
    try:
        # 检查WebRTC播放器页面是否可访问
        response = requests.get(
            self.stream_url,
            timeout=self.connection_timeout,
            allow_redirects=True
        )
        
        # 检查响应状态
        if response.status_code == 200:
            if not self.is_connected:
                logger.info(f"机械臂WebRTC流连接恢复正常: {self.stream_url}")
            self.is_connected = True
        else:
            if self.is_connected:
                logger.warning(f"机械臂WebRTC流响应异常: {response.status_code}")
            self.is_connected = False
            
    except requests.exceptions.RequestException as e:
        logger.debug(f"机械臂WebRTC流连接检查异常: {e}")
    except Exception as e:
        logger.debug(f"机械臂WebRTC流状态检查出错: {e}")
    
    return self.is_connected
```

### 3. 更新Vite代理配置 - `frontend/vite.config.js`

**目标**：添加对WebRTC播放器的代理支持（如需要）。

**具体修改**：
```javascript
// 在proxy配置中添加（如果需要本地开发时的代理）
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path
  },
  '/ws': {
    target: 'ws://localhost:8000',
    ws: true,
    changeOrigin: true
  },
  // 保留HLS代理以备其他组件使用
  '/hlsram': {
    target: 'http://192.168.0.51:80',
    changeOrigin: true,
    secure: false,
    rewrite: (path) => path
  },
  // 新增：WebRTC播放器代理（如果需要）
  '/player': {
    target: 'http://192.168.0.51',
    changeOrigin: true,
    secure: false,
    rewrite: (path) => path
  }
}
```

## 修改效果

### 优势
1. **超低延迟**：WebRTC协议延迟通常 < 1秒，比HLS的3-7秒显著降低
2. **实时交互**：支持真正的实时视频流
3. **更好的用户体验**：几乎无感知的延迟

### 注意事项
1. **网络要求**：WebRTC对网络稳定性要求较高
2. **浏览器兼容性**：现代浏览器都支持，但可能需要HTTPS环境
3. **防火墙配置**：可能需要特定的网络端口配置

## 确认修改

**请您确认是否同意按照此方案进行WebRTC协议切换？**

如果同意，我将按照以上计划进行修改。如有任何调整需求，请告知我。 