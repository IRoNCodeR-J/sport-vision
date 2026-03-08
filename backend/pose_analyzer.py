"""
Sport Vision — 姿态分析模块
基于 MediaPipe PoseLandmarker (Tasks API) 的人体关键点检测与生物力学分析
"""

import math
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from collections import deque
from pathlib import Path
from typing import Optional


class PoseAnalyzer:
    """封装 MediaPipe PoseLandmarker，提供关键点提取和生物力学分析"""

    # 骨骼连接定义 (使用 PoseLandmarker 的索引)
    SKELETON_CONNECTIONS = [
        # 躯干
        (11, 12),  # 左肩-右肩
        (11, 23),  # 左肩-左髋
        (12, 24),  # 右肩-右髋
        (23, 24),  # 左髋-右髋
        # 左臂
        (11, 13),  # 左肩-左肘
        (13, 15),  # 左肘-左腕
        # 右臂
        (12, 14),  # 右肩-右肘
        (14, 16),  # 右肘-右腕
        # 左腿
        (23, 25),  # 左髋-左膝
        (25, 27),  # 左膝-左踝
        # 右腿
        (24, 26),  # 右髋-右膝
        (26, 28),  # 右膝-右踝
    ]

    # 关键点名称映射
    LANDMARK_NAMES = {
        0: "nose", 11: "left_shoulder", 12: "right_shoulder",
        13: "left_elbow", 14: "right_elbow",
        15: "left_wrist", 16: "right_wrist",
        23: "left_hip", 24: "right_hip",
        25: "left_knee", 26: "right_knee",
        27: "left_ankle", 28: "right_ankle",
    }

    # 要分析的关键关节角度
    JOINT_ANGLES = {
        "left_elbow": (11, 13, 15),
        "right_elbow": (12, 14, 16),
        "left_shoulder": (13, 11, 23),
        "right_shoulder": (14, 12, 24),
        "left_knee": (23, 25, 27),
        "right_knee": (24, 26, 28),
        "left_hip": (11, 23, 25),
        "right_hip": (12, 24, 26),
    }

    def __init__(self, min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 history_size: int = 30):

        # 查找模型文件
        model_path = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_lite.task"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Pose model not found at {model_path}. "
                "Download it with: curl -sL -o models/pose_landmarker_lite.task "
                "\"https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task\""
            )

        # 配置 PoseLandmarker
        base_options = python.BaseOptions(model_asset_path=str(model_path))
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            min_pose_detection_confidence=min_detection_confidence,
            min_pose_presence_confidence=min_tracking_confidence,
            num_poses=1,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)

        self.history_size = history_size
        # 关键点历史记录（用于速度/加速度计算）
        self.keypoint_history: deque = deque(maxlen=history_size)
        # 重心轨迹
        self.center_of_mass_history: deque = deque(maxlen=history_size * 2)
        self.frame_count = 0

    def process_frame(self, frame_rgb: np.ndarray) -> Optional[dict]:
        """
        处理单帧，返回分析结果

        Returns:
            {
                "keypoints": [{x, y, z, visibility, name}, ...],
                "skeleton": [[p1_idx, p2_idx], ...],
                "joint_angles": {name: angle_degrees, ...},
                "biomechanics": {velocity, acceleration, symmetry, ...},
                "center_of_mass": {x, y},
                "confidence": float,
            }
        """
        h, w = frame_rgb.shape[:2]

        # 创建 MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # 检测
        result = self.landmarker.detect(mp_image)

        if not result.pose_landmarks or len(result.pose_landmarks) == 0:
            return None

        landmarks = result.pose_landmarks[0]  # 第一个人

        # 1. 提取关键点（像素坐标）
        keypoints = []
        for idx in self.LANDMARK_NAMES:
            if idx < len(landmarks):
                lm = landmarks[idx]
                keypoints.append({
                    "id": idx,
                    "name": self.LANDMARK_NAMES[idx],
                    "x": lm.x * w,
                    "y": lm.y * h,
                    "z": lm.z,
                    "visibility": lm.visibility if lm.visibility is not None else 0.5,
                })

        if not keypoints:
            return None

        # 过滤低置信度
        avg_visibility = np.mean([kp["visibility"] for kp in keypoints])
        if avg_visibility < 0.3:
            return None

        # 2. 计算关节角度
        joint_angles = {}
        for name, (a, b, c) in self.JOINT_ANGLES.items():
            angle = self._calculate_angle_from_landmarks(landmarks, a, b, c)
            if angle is not None:
                joint_angles[name] = round(angle, 1)

        # 3. 计算重心
        if 23 < len(landmarks) and 24 < len(landmarks):
            com_x = (landmarks[23].x + landmarks[24].x) / 2 * w
            com_y = (landmarks[23].y + landmarks[24].y) / 2 * h
        else:
            com_x, com_y = w / 2, h / 2
        center_of_mass = {"x": round(com_x, 1), "y": round(com_y, 1)}
        self.center_of_mass_history.append(center_of_mass)

        # 4. 记录关键点历史
        kp_dict = {kp["id"]: (kp["x"], kp["y"]) for kp in keypoints}
        self.keypoint_history.append(kp_dict)
        self.frame_count += 1

        # 5. 生物力学分析
        biomechanics = self._analyze_biomechanics(landmarks, w, h)

        return {
            "keypoints": keypoints,
            "skeleton": self.SKELETON_CONNECTIONS,
            "joint_angles": joint_angles,
            "biomechanics": biomechanics,
            "center_of_mass": center_of_mass,
            "confidence": round(avg_visibility, 2),
        }

    def _calculate_angle_from_landmarks(self, landmarks, a_idx, b_idx, c_idx) -> Optional[float]:
        """计算三个关键点形成的角度（以 b 为顶点）"""
        try:
            if a_idx >= len(landmarks) or b_idx >= len(landmarks) or c_idx >= len(landmarks):
                return None
            a = landmarks[a_idx]
            b = landmarks[b_idx]
            c = landmarks[c_idx]
            ba = np.array([a.x - b.x, a.y - b.y])
            bc = np.array([c.x - b.x, c.y - b.y])
            cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
            angle = np.arccos(np.clip(cosine, -1.0, 1.0))
            return math.degrees(angle)
        except Exception:
            return None

    def _analyze_biomechanics(self, landmarks, w: int, h: int) -> dict:
        """运动生物力学分析"""
        result = {
            "wrist_speed": 0.0,
            "body_lean": 0.0,
            "knee_bend": 0.0,
            "arm_extension": 0.0,
            "symmetry_score": 0.0,
        }

        if len(self.keypoint_history) < 2:
            return result

        prev = self.keypoint_history[-2]
        curr = self.keypoint_history[-1]

        # 手腕速度（取左右手中速度更大的）
        wrist_speeds = []
        for wrist_id in [15, 16]:
            if wrist_id in prev and wrist_id in curr:
                dx = curr[wrist_id][0] - prev[wrist_id][0]
                dy = curr[wrist_id][1] - prev[wrist_id][1]
                speed = math.sqrt(dx * dx + dy * dy)
                wrist_speeds.append(speed)
        result["wrist_speed"] = round(max(wrist_speeds) if wrist_speeds else 0, 1)

        # 身体倾斜角（脊柱与垂直线的夹角）
        try:
            if 11 < len(landmarks) and 12 < len(landmarks) and 23 < len(landmarks) and 24 < len(landmarks):
                mid_shoulder = np.array([
                    (landmarks[11].x + landmarks[12].x) / 2,
                    (landmarks[11].y + landmarks[12].y) / 2
                ])
                mid_hip = np.array([
                    (landmarks[23].x + landmarks[24].x) / 2,
                    (landmarks[23].y + landmarks[24].y) / 2
                ])
                spine = mid_shoulder - mid_hip
                vertical = np.array([0, -1])
                cos_angle = np.dot(spine, vertical) / (np.linalg.norm(spine) + 1e-8)
                lean_angle = math.degrees(math.acos(np.clip(cos_angle, -1.0, 1.0)))
                result["body_lean"] = round(lean_angle, 1)
        except Exception:
            pass

        # 膝盖弯曲度（取双膝平均）
        knee_angles = []
        for name in ["left_knee", "right_knee"]:
            a_id, b_id, c_id = self.JOINT_ANGLES[name]
            angle = self._calculate_angle_from_landmarks(landmarks, a_id, b_id, c_id)
            if angle is not None:
                knee_angles.append(angle)
        result["knee_bend"] = round(180 - np.mean(knee_angles) if knee_angles else 0, 1)

        # 手臂伸展度（肘部角度，越接近 180 越伸展）
        elbow_angles = []
        for name in ["left_elbow", "right_elbow"]:
            a_id, b_id, c_id = self.JOINT_ANGLES[name]
            angle = self._calculate_angle_from_landmarks(landmarks, a_id, b_id, c_id)
            if angle is not None:
                elbow_angles.append(angle)
        result["arm_extension"] = round(np.mean(elbow_angles) if elbow_angles else 0, 1)

        # 对称性评分（0-100，左右对称性）
        try:
            if 11 < len(landmarks) and 12 < len(landmarks) and 23 < len(landmarks) and 24 < len(landmarks):
                left_shoulder_y = landmarks[11].y
                right_shoulder_y = landmarks[12].y
                left_hip_y = landmarks[23].y
                right_hip_y = landmarks[24].y
                shoulder_diff = abs(left_shoulder_y - right_shoulder_y)
                hip_diff = abs(left_hip_y - right_hip_y)
                asymmetry = (shoulder_diff + hip_diff) / 2
                symmetry = max(0, 100 - asymmetry * 500)
                result["symmetry_score"] = round(symmetry, 1)
        except Exception:
            result["symmetry_score"] = 0.0

        return result

    def get_trajectory(self) -> list:
        """返回重心轨迹"""
        return list(self.center_of_mass_history)

    def reset(self):
        """重置状态"""
        self.keypoint_history.clear()
        self.center_of_mass_history.clear()
        self.frame_count = 0

    def close(self):
        """释放资源"""
        self.landmarker.close()
