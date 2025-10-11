import os
import cv2
import time
import asyncio
import datetime
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import threading
import numpy as np
from . import zed_server
from app.esp32_controller import controller as esp32_controller
from app.rtk_controller import controller as rtk_controller
from app.model_manager import model_manager
import logging
import atexit
import signal
import json
from fastapi.responses import StreamingResponse, FileResponse
from app.video_streaming import VideoCamera
from app.lift_controller import lift_car_controller
from app.arm_streaming import arm_streaming_service

# Initialize FastAPI app
app = FastAPI(title="Smart Construction Platform")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directory for storing video frames if it doesn't exist
os.makedirs("data/video_frames", exist_ok=True)

# Global variables for video streaming
frame_buffer = None
frame_lock = threading.Lock()
is_streaming = False
stream_info = {
    "fps": 0,
    "frame_count": 0,
    "start_time": None,
    "source_address": None,
    "resolution": "Unknown"
}

# 用于优雅关闭的事件标志
shutdown_event = threading.Event()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_app")

# 初始化视频相机
camera = None
try:
    camera = VideoCamera()
    logger.info("Camera initialized successfully")
except Exception as e:
    logger.error(f"Error initializing camera: {e}")

def receive_rtp_stream():
    """Receive RTP stream and update the global frame buffer"""
    global frame_buffer, is_streaming, stream_info
    
    print("开始接收RTP视频流...")
    # 初始化OpenCV的VideoCapture以接收RTP流
    # 使用udpsrc作为GStreamer管道
    gst_str = (
        "udpsrc port=5000 ! "
        "application/x-rtp,media=video,payload=96,clock-rate=90000,encoding-name=H264 ! "
        "rtph264depay ! h264parse ! avdec_h264 ! "
        "videoconvert ! appsink"
    )
    cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
    
    # 初始化时间和FPS计算
    stream_info["start_time"] = time.time()
    frame_time = time.time()
    fps_update_time = time.time()
    
    try:
        while not shutdown_event.is_set():  # 检查关闭事件
            ret, frame = cap.read()
            
            if not ret:
                # 如果无法获取帧，等待一段时间然后继续尝试
                time.sleep(0.1)
                continue
            
            # 成功接收到帧，设置流状态为活跃
            is_streaming = True
            
            # 计算FPS
            current_time = time.time()
            if current_time - frame_time > 0:
                instantaneous_fps = 1.0 / (current_time - frame_time)
                
                # 平滑FPS计算，每秒更新一次
                if current_time - fps_update_time >= 1.0:
                    stream_info["fps"] = round(instantaneous_fps, 1)
                    fps_update_time = current_time
                    
                    # 打印流信息
                    if not shutdown_event.is_set():  # 只在非关闭状态下记录日志
                        logger.info(f"视频流信息 - FPS: {stream_info['fps']}, 帧数: {stream_info['frame_count']}")
            
            frame_time = current_time
            stream_info["frame_count"] += 1
            
            # 获取分辨率信息（只在第一帧时获取）
            if stream_info["resolution"] == "Unknown" and frame is not None:
                height, width = frame.shape[:2]
                stream_info["resolution"] = f"{width}x{height}"
            
            # 添加时间戳和信息到帧上
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, f"时间: {timestamp}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f"FPS: {stream_info['fps']}", (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # 更新全局帧缓冲区
            with frame_lock:
                frame_buffer = frame
            
    except Exception as e:
        if not shutdown_event.is_set():  # 只在非关闭状态下记录错误
            logger.error(f"视频流接收错误: {e}")
        is_streaming = False
    finally:
        cap.release()
        if not shutdown_event.is_set():  # 只在非关闭状态下记录日志
            logger.info("RTP流接收已停止")
        is_streaming = False

def generate_frames():
    """Generate frames for HTTP streaming"""
    global frame_buffer
    
    while True:
        with frame_lock:
            if frame_buffer is not None:
                # Encode the frame as JPEG
                _, buffer = cv2.imencode('.jpg', frame_buffer)
                frame_bytes = buffer.tobytes()
                
                # Yield the frame for the HTTP response
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # If no frame is available, send a blank frame or error message
                blank_frame = create_blank_frame("等待视频流...")
                _, buffer = cv2.imencode('.jpg', blank_frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Control the frame rate
        time.sleep(0.033)  # ~30 FPS

def create_blank_frame(message="No video signal"):
    """Create a blank frame with error message when no video is available"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add a grid pattern for visual effect
    for i in range(0, 480, 40):
        cv2.line(frame, (0, i), (640, i), (0, 0, 80), 1)
    
    for i in range(0, 640, 40):
        cv2.line(frame, (i, 0), (i, 480), (0, 0, 80), 1)
    
    # Add text message
    cv2.putText(frame, message, (int(640/2) - 100, int(480/2)), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    
    # Add timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, timestamp, (20, 460), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    
    return frame

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.client_connections = {}  # 用于跟踪每个客户端IP的连接数
        self.max_connections_per_client = 4  # 每个客户端最多允许4个WebSocket连接
        self.max_total_connections = 20  # 系统总共最多允许20个WebSocket连接

    async def connect(self, websocket: WebSocket):
        # 检查是否处于关闭状态
        if shutdown_event.is_set():
            await websocket.close(code=1001, reason="Server shutting down")
            return False
            
        # 获取客户端IP
        client_host = websocket.client.host
        
        # 检查总连接数是否超过限制
        if len(self.active_connections) >= self.max_total_connections:
            logger.warning(f"总连接数已达到上限 ({self.max_total_connections})，拒绝新连接")
            await websocket.close(code=1013, reason="Maximum connections reached")
            return False
        
        # 检查该客户端的连接数是否超过限制
        if client_host in self.client_connections and self.client_connections[client_host] >= self.max_connections_per_client:
            logger.warning(f"客户端 {client_host} 的连接数已达到上限 ({self.max_connections_per_client})，拒绝新连接")
            await websocket.close(code=1013, reason="Too many connections from this client")
            return False
            
        # 接受连接
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # 更新客户端连接计数
        if client_host not in self.client_connections:
            self.client_connections[client_host] = 1
        else:
            self.client_connections[client_host] += 1
            
        logger.info(f"新的WebSocket连接，客户端IP: {client_host}，该客户端连接数: {self.client_connections[client_host]}，总连接数: {len(self.active_connections)}")
        return True

    def disconnect(self, websocket: WebSocket):
        # 获取客户端IP
        client_host = websocket.client.host if hasattr(websocket, 'client') else "unknown"
        
        # 从活跃连接列表中移除
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
            # 更新客户端连接计数
            if client_host in self.client_connections:
                self.client_connections[client_host] -= 1
                if self.client_connections[client_host] <= 0:
                    del self.client_connections[client_host]
                    
            logger.info(f"WebSocket连接关闭，客户端IP: {client_host}，该客户端剩余连接数: {self.client_connections.get(client_host, 0)}，总连接数: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
    
    async def close_all_connections(self):
        """关闭所有活跃的WebSocket连接"""
        logger.info(f"正在关闭所有WebSocket连接，当前共有 {len(self.active_connections)} 个连接")
        for websocket in self.active_connections[:]:  # 使用副本进行迭代，避免在迭代时修改列表
            try:
                await websocket.close(code=1001, reason="Server shutting down")
                self.active_connections.remove(websocket)
            except Exception as e:
                logger.error(f"关闭WebSocket连接时出错: {e}")
        
        # 清空连接计数
        self.client_connections.clear()
        logger.info("所有WebSocket连接已关闭")

manager = ConnectionManager()

# 启动ZED服务器
zed_server.init_zed_server()

# Start the RTP stream receiver in a separate thread
stream_thread = threading.Thread(target=receive_rtp_stream, daemon=True)
stream_thread.start()

@app.get("/")
async def get_index():
    return {"message": "Smart Construction Platform API is running"}

@app.get("/api/video_feed")
async def video_feed_api():
    """API Endpoint for HTTP video streaming"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/stream_status")
async def stream_status_api():
    """获取流状态API"""
    global stream_info
    
    # Calculate the stream duration if applicable
    duration = None
    if stream_info["start_time"] is not None and is_streaming:
        duration = time.time() - stream_info["start_time"]
        duration = round(duration, 1)
    
    # 获取ZED相机连接状态
    zed_connected = zed_server.is_zed_connected()
    
    return {
        "streaming": is_streaming,
        "fps": stream_info["fps"],
        "frame_count": stream_info["frame_count"],
        "duration": duration,
        "resolution": stream_info["resolution"],
        "source": stream_info["source_address"],
        "zed_connected": zed_connected,  # 添加ZED相机连接状态
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.websocket("/ws/video")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for video streaming"""
    # 尝试连接，如果达到限制则会返回False
    if not await manager.connect(websocket):
        return  # 连接被拒绝，直接返回
        
    try:
        while not shutdown_event.is_set():  # 检查关闭事件
            with frame_lock:
                if frame_buffer is not None and is_streaming:
                    # Encode the frame as JPEG with quality setting to control bandwidth
                    _, buffer = cv2.imencode('.jpg', frame_buffer, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame_bytes = buffer.tobytes()
                    
                    # Send the frame through WebSocket
                    await websocket.send_bytes(frame_bytes)
                else:
                    # 不发送模拟帧，让前端显示离线状态
                    # 发送一个空的1x1像素的透明图片，这样前端会触发错误处理
                    empty_frame = np.zeros((1, 1, 3), dtype=np.uint8)
                    _, buffer = cv2.imencode('.jpg', empty_frame)
                    frame_bytes = buffer.tobytes()
                    await websocket.send_bytes(frame_bytes)
            
            # Control the frame rate - adjust for network performance
            await asyncio.sleep(0.05)  # 20 FPS for WebSocket to reduce bandwidth
    except WebSocketDisconnect:
        pass
    except Exception as e:
        if not shutdown_event.is_set():  # 只在非关闭状态下记录错误
            logger.error(f"WebSocket错误: {e}")
    finally:
        manager.disconnect(websocket)

# 添加另一个路径以支持API前缀
@app.websocket("/api/ws/video")
async def websocket_endpoint_api(websocket: WebSocket):
    """WebSocket API endpoint for video streaming"""
    await websocket_endpoint(websocket)

@app.websocket("/ws/zed")
async def zed_websocket_endpoint(websocket: WebSocket):
    """ZED相机统一WebSocket端点 - 处理RGB和深度数据并支持模式切换"""
    await zed_server.handle_websocket(websocket)

# 保留旧的端点以向后兼容，但使用新的统一处理
@app.websocket("/ws/zed/rgb")
async def zed_rgb_endpoint(websocket: WebSocket):
    """ZED RGB视频流WebSocket端点 (向后兼容)"""
    await zed_websocket_endpoint(websocket)

@app.websocket("/ws/zed/depth")
async def zed_depth_endpoint(websocket: WebSocket):
    """ZED 深度图WebSocket端点 (向后兼容)"""
    await zed_websocket_endpoint(websocket)

# 修改清理资源函数，添加关闭WebSocket连接
async def async_cleanup_resources():
    """异步清理资源函数"""
    logger.info("正在异步清理资源...")
    await manager.close_all_connections()
    logger.info("异步资源清理完成")

def cleanup_resources():
    """同步清理资源函数，在程序退出时调用"""
    logger.info("正在清理主应用资源...")
    # 设置关闭事件，通知所有线程退出
    shutdown_event.set()
    
    # 创建一个新的事件循环来运行异步清理
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_cleanup_resources())
        loop.close()
    except Exception as e:
        logger.error(f"异步清理资源时出错: {e}")
    
    # 给线程一些时间来退出
    time.sleep(0.5)
    logger.info("主应用资源清理完成")

# 信号处理函数
def signal_handler(sig, frame):
    logger.info(f"主应用收到信号 {sig}，正在优雅关闭...")
    shutdown_event.set()
    # 执行清理操作
    cleanup_resources()
    # 强制退出程序
    sys.exit(0)

# 注册信号处理和退出处理
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup_resources)

# 添加ESP32控制API路由
@app.get("/api/esp32/status")
async def get_esp32_status():
    """获取所有ESP32控制板的状态"""
    return esp32_controller.get_all_status()

@app.get("/api/esp32/{board_id}")
async def get_esp32_board_status(board_id: str):
    """获取指定ESP32控制板的状态"""
    result = esp32_controller.get_board_status(board_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.post("/api/esp32/{board_id}/button/{button_id}")
async def send_esp32_command(board_id: str, button_id: int):
    """发送命令到ESP32控制板"""
    result = await esp32_controller.send_command(board_id, button_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/api/debug/buttons")
async def get_debug_buttons():
    """调试端点：返回ESP32控制器的按钮配置"""
    return {
        "board1": esp32_controller.boards["board1"]["buttons"],
        "board2": esp32_controller.boards["board2"]["buttons"]
    }

@app.get("/api/lift/status")
async def get_lift_status():
    """获取登高车状态"""
    return lift_car_controller.get_info()

@app.post("/api/lift/button/{button_id}")
async def send_lift_command(button_id: int):
    """发送提升小车控制命令"""
    return await lift_car_controller.send_command(button_id)

# RTK设备API路由
@app.get("/api/rtk/devices")
async def get_rtk_devices():
    """获取所有RTK设备信息"""
    return rtk_controller.get_devices()

@app.get("/api/rtk/device/{device_id}")
async def get_rtk_device(device_id: str):
    """获取指定RTK设备信息"""
    return rtk_controller.get_device_data(device_id)

@app.post("/api/rtk/device/register")
async def register_rtk_device(device_id: str, ip_address: str, name: str = None, device_info: str = None):
    """注册新的RTK设备"""
    return rtk_controller.register_device(device_id, ip_address, name, device_info)

@app.post("/api/rtk/devices")
async def create_rtk_device(request: Request):
    """创建新的RTK设备（支持JSON body）"""
    try:
        data = await request.json()
        
        # 提取参数
        device_id = data.get("device_id")
        ip_address = data.get("ip_address")
        name = data.get("name")
        device_number = data.get("device_number")
        is_base_station = data.get("is_base_station", False)
        
        # 验证必要参数
        if not device_id or not ip_address:
            raise HTTPException(status_code=400, detail="device_id and ip_address are required")
        
        # 构建设备信息
        device_info = {
            "deviceNumber": device_number,
            "isBaseStation": is_base_station,
            "showIn3D": data.get("show_in_3d", True)
        }
        device_info_str = json.dumps(device_info)
        
        # 调用控制器注册设备
        result = rtk_controller.register_device(device_id, ip_address, name, device_info_str)
        
        if result.get("success"):
            return {"success": True, "message": result.get("message", "设备注册成功")}
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "设备注册失败"))
        
    except Exception as e:
        logger.error(f"注册RTK设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rtk/scan")
async def scan_rtk_devices():
    """扫描网络上的RTK设备"""
    return rtk_controller.scan_for_devices()

@app.post("/api/rtk/devices/cleanup-all")
async def cleanup_all_rtk_devices():
    """清理所有RTK设备状态，为重新注册做准备"""
    try:
        logger.info("收到批量清理所有RTK设备的请求")
        result = rtk_controller.cleanup_all_devices()
        logger.info(f"批量清理结果: {result}")
        
        if result.get("success"):
            return {"success": True, "message": result.get("message", "所有设备清理成功")}
        else:
            return {"success": False, "message": result.get("message", "设备清理失败")}
        
    except Exception as e:
        logger.error(f"批量清理RTK设备失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@app.put("/api/rtk/devices/{device_id}")
async def update_rtk_device(device_id: str, request: Request):
    """更新RTK设备（支持JSON body）"""
    try:
        data = await request.json()
        
        # 提取参数
        ip_address = data.get("ip_address")
        name = data.get("name")
        device_number = data.get("device_number")
        is_base_station = data.get("is_base_station", False)
        
        # 验证必要参数
        if not ip_address:
            raise HTTPException(status_code=400, detail="ip_address is required")
        
        # 先删除旧设备
        rtk_controller.unregister_device(device_id)
        
        # 构建设备信息
        device_info = {
            "deviceNumber": device_number,
            "isBaseStation": is_base_station,
            "showIn3D": data.get("show_in_3d", True)
        }
        device_info_str = json.dumps(device_info)
        
        # 重新注册设备
        result = rtk_controller.register_device(device_id, ip_address, name, device_info_str)
        
        if result.get("success"):
            return {"success": True, "message": result.get("message", "设备更新成功")}
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "设备更新失败"))
        
    except Exception as e:
        logger.error(f"更新RTK设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/rtk/devices/{device_id}")
async def delete_rtk_device(device_id: str):
    """删除RTK设备"""
    try:
        result = rtk_controller.unregister_device(device_id)
        
        if result.get("success"):
            return {"success": True, "message": result.get("message", "设备删除成功")}
        else:
            return {"success": False, "message": result.get("error", "设备删除失败")}
        
    except Exception as e:
        logger.error(f"删除RTK设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/rtk/device/{device_id}")
async def unregister_rtk_device(device_id: str):
    """注销RTK设备"""
    return rtk_controller.unregister_device(device_id)

@app.post("/api/rtk/device/{device_id}/cleanup")
async def cleanup_rtk_device(device_id: str):
    """清理RTK设备状态，为重新注册做准备"""
    try:
        result = rtk_controller.cleanup_device(device_id)
        
        if result.get("success"):
            return {"success": True, "message": result.get("message", "设备清理成功")}
        else:
            return {"success": False, "message": result.get("message", "设备清理失败")}
        
    except Exception as e:
        logger.error(f"清理RTK设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rtk/device/{device_id}/record/start")
async def start_rtk_recording(device_id: str):
    """开始记录RTK设备数据"""
    return rtk_controller.start_recording(device_id)

@app.post("/api/rtk/device/{device_id}/record/stop")
async def stop_rtk_recording(device_id: str):
    """停止记录RTK设备数据"""
    return rtk_controller.stop_recording(device_id)

@app.get("/api/rtk/device/{device_id}/records")
async def get_rtk_records(device_id: str):
    """获取RTK设备记录的数据"""
    return rtk_controller.get_records(device_id)

@app.delete("/api/rtk/device/{device_id}/records")
async def clear_rtk_records(device_id: str):
    """清除RTK设备记录的数据"""
    return rtk_controller.clear_records(device_id)

# 添加兼容性路由，匹配前端调用的路径
@app.post("/api/rtk/devices/{device_id}/recording/{action}")
async def toggle_rtk_recording(device_id: str, action: str):
    """切换RTK设备记录状态（兼容性路由）"""
    if action == "start":
        return rtk_controller.start_recording(device_id)
    elif action == "stop":
        return rtk_controller.stop_recording(device_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'start' or 'stop'")

@app.delete("/api/rtk/devices/{device_id}/records")
async def clear_rtk_records_compat(device_id: str):
    """清除RTK设备记录的数据（兼容性路由）"""
    return rtk_controller.clear_records(device_id)

# 启动和停止RTK监听的API
@app.post("/api/rtk/listen/start")
async def start_rtk_listening():
    """启动RTK UDP监听"""
    return rtk_controller.start_listening()

@app.post("/api/rtk/listen/stop")
async def stop_rtk_listening():
    """停止RTK UDP监听"""
    return rtk_controller.stop_listening()

# RTK WebSocket路由，用于实时推送RTK数据
@app.websocket("/ws/rtk")
async def rtk_websocket_endpoint(websocket: WebSocket):
    """RTK数据WebSocket连接"""
    await websocket.accept()
    
    # 启动RTK监听（如果尚未启动）
    if not rtk_controller.running:
        rtk_controller.start_listening()
    
    try:
        # 开始发送数据
        while True:
            # 获取所有设备的最新数据
            devices_data = rtk_controller.get_devices()
            
            # 发送数据到客户端
            await websocket.send_json(devices_data)
            
            # 每100毫秒发送一次数据
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("RTK WebSocket客户端断开连接")
    except Exception as e:
        logger.error(f"RTK WebSocket错误: {e}")

# 启动应用时自动启动一些服务
@app.on_event("startup")
async def startup_event():
    # 启动RTK监听服务
    rtk_controller.start_listening()
    logger.info("RTK监听服务已启动")
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# 建筑模型管理API
@app.post("/api/models/upload")
async def upload_model(file: UploadFile, request: Request):
    """上传建筑模型文件"""
    # 从表单数据或JSON中获取元数据
    metadata = {}
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        form_data = await request.form()
        if "metadata" in form_data:
            import json
            metadata = json.loads(form_data["metadata"])
    
    return await model_manager.upload_model(file, metadata)

@app.get("/api/models")
async def get_models():
    """获取所有建筑模型列表"""
    return model_manager.get_models()

@app.get("/api/models/{model_id}")
async def get_model(model_id: str):
    """获取指定建筑模型信息"""
    model = model_manager.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return model

@app.put("/api/models/{model_id}")
async def update_model(model_id: str, request: Request):
    """更新建筑模型信息"""
    updates = await request.json()
    return model_manager.update_model(model_id, updates)

@app.delete("/api/models/{model_id}")
async def delete_model(model_id: str):
    """删除建筑模型"""
    return model_manager.delete_model(model_id)

@app.get("/api/models/{model_id}/file")
async def get_model_file(model_id: str):
    """获取建筑模型文件"""
    from fastapi.responses import FileResponse
    file_path = model_manager.get_model_file_path(model_id)
    return FileResponse(file_path)

# 机械臂相关API
@app.get("/api/arm/status")
async def get_arm_status():
    """获取机械臂摄像头状态"""
    return arm_streaming_service.get_status()

@app.get("/api/arm/stream_info")
async def get_arm_stream_info():
    """获取机械臂视频流信息"""
    return arm_streaming_service.get_stream_info() 