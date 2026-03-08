"""
Sport Vision — CV 处理流水线
串联姿态分析、动作识别、可视化的核心流水线
"""

import cv2
import base64
import numpy as np
import time
from pathlib import Path
from typing import Optional, AsyncGenerator

from backend.pose_analyzer import PoseAnalyzer
from backend.action_recognizer import ActionRecognizer
from backend.visualizer import Visualizer


class Pipeline:
    """视频分析流水线"""

    def __init__(self):
        self.pose_analyzer = PoseAnalyzer()
        self.action_recognizer = ActionRecognizer()
        self.visualizer = Visualizer()
        self.is_running = False

    async def process_video(self, video_path: str,
                            target_fps: int = 24,
                            skip_frames: int = 1) -> AsyncGenerator[dict, None]:
        """
        处理视频并逐帧 yield 分析结果（异步生成器）

        Yields:
            {
                "frame_base64": str,       # 渲染后的帧（JPEG base64）
                "frame_number": int,
                "total_frames": int,
                "fps": float,
                "pose": {...} or None,     # 姿态分析结果
                "action": {...} or None,   # 动作识别结果
                "progress": float,         # 0.0 ~ 1.0
                "heatmap_data": [...],     # 热力图数据点
            }
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            yield {"error": f"Cannot open video: {video_path}"}
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 限制输出尺寸（保持比例，最大宽度 960）
        max_width = 960
        if frame_width > max_width:
            scale = max_width / frame_width
            target_w = max_width
            target_h = int(frame_height * scale)
        else:
            target_w = frame_width
            target_h = frame_height

        self.is_running = True
        self.pose_analyzer.reset()
        self.action_recognizer.reset()
        self.visualizer.reset()

        frame_count = 0
        # 帧间隔控制
        frame_interval = 1.0 / target_fps

        try:
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                if frame_count % skip_frames != 0:
                    continue

                start_time = time.time()

                # 缩放
                if frame.shape[1] != target_w:
                    frame = cv2.resize(frame, (target_w, target_h))

                # RGB 转换（MediaPipe 需要 RGB）
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # 1. 姿态分析
                pose_result = self.pose_analyzer.process_frame(frame_rgb)

                # 2. 动作识别
                action_result = None
                if pose_result:
                    action_result = self.action_recognizer.update(
                        pose_result["keypoints"],
                        pose_result["joint_angles"]
                    )

                # 3. 可视化渲染
                rendered = self.visualizer.render_frame(frame, pose_result, action_result)

                # 编码为 JPEG base64
                _, buffer = cv2.imencode(".jpg", rendered, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_base64 = base64.b64encode(buffer).decode("utf-8")

                # 构建输出
                progress = frame_count / total_frames if total_frames > 0 else 0

                yield {
                    "frame_base64": frame_base64,
                    "frame_number": frame_count,
                    "total_frames": total_frames,
                    "fps": round(video_fps, 1),
                    "width": target_w,
                    "height": target_h,
                    "pose": self._sanitize_pose(pose_result),
                    "action": action_result,
                    "progress": round(min(progress, 1.0), 3),
                    "heatmap_data": self.pose_analyzer.get_trajectory(),
                }

                # 控制帧率
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    import asyncio
                    await asyncio.sleep(sleep_time)

        finally:
            cap.release()
            self.is_running = False

    def _sanitize_pose(self, pose_result: Optional[dict]) -> Optional[dict]:
        """清理姿态数据以便 JSON 序列化"""
        if not pose_result:
            return None
        # 移除大体积的骨骼连接信息（前端已有）
        return {
            "keypoints": pose_result["keypoints"],
            "joint_angles": pose_result["joint_angles"],
            "biomechanics": pose_result["biomechanics"],
            "center_of_mass": pose_result["center_of_mass"],
            "confidence": pose_result["confidence"],
        }

    def stop(self):
        """停止处理"""
        self.is_running = False

    def close(self):
        """释放所有资源"""
        self.stop()
        self.pose_analyzer.close()
