"""
Sport Vision — 动作识别模块
基于关键点时序分析的击球动作识别引擎
"""

import math
import numpy as np
from collections import deque
from typing import Optional


class ActionRecognizer:
    """
    规则引擎动作识别器
    通过关键点的时序变化识别羽毛球/网球的典型动作
    """

    # 支持识别的动作类型
    ACTIONS = {
        "serve": {"name": "发球 Serve", "icon": "🎯", "color": "#00f0ff"},
        "smash": {"name": "扣杀 Smash", "icon": "💥", "color": "#ff3366"},
        "forehand": {"name": "正手 Forehand", "icon": "➡️", "color": "#33ff88"},
        "backhand": {"name": "反手 Backhand", "icon": "⬅️", "color": "#ffaa33"},
        "lob": {"name": "挑球 Lob", "icon": "🌈", "color": "#aa66ff"},
        "drop": {"name": "吊球 Drop", "icon": "🪶", "color": "#66ddff"},
        "ready": {"name": "准备 Ready", "icon": "🧍", "color": "#888888"},
        "moving": {"name": "移动 Moving", "icon": "🏃", "color": "#ffdd44"},
    }

    def __init__(self, window_size: int = 15, debounce_frames: int = 10):
        """
        Args:
            window_size: 滑动窗口大小（帧数）
            debounce_frames: 动作去抖动间隔（防止同一动作重复触发）
        """
        self.window_size = window_size
        self.debounce_frames = debounce_frames
        # 关键点历史缓冲
        self.keypoint_buffer: deque = deque(maxlen=window_size)
        # 动作历史
        self.action_history: list = []
        self.last_action = "ready"
        self.last_action_frame = -debounce_frames
        self.frame_count = 0
        # 统计
        self.action_counts: dict = {k: 0 for k in self.ACTIONS}

    def update(self, keypoints: list, joint_angles: dict) -> dict:
        """
        输入当前帧的关键点和关节角度，输出识别结果

        Returns:
            {
                "action": str,
                "action_info": {name, icon, color},
                "confidence": float,
                "is_new_action": bool,
                "action_counts": dict,
                "action_history": list (recent 20),
            }
        """
        self.frame_count += 1

        # 构建关键点字典
        kp_map = {}
        for kp in keypoints:
            kp_map[kp["name"]] = kp
        self.keypoint_buffer.append(kp_map)

        if len(self.keypoint_buffer) < 5:
            return self._make_result("ready", 0.5, False)

        # 识别动作
        action, confidence = self._recognize(kp_map, joint_angles)

        # 去抖动
        is_new = False
        if action != self.last_action and action not in ("ready", "moving"):
            if self.frame_count - self.last_action_frame >= self.debounce_frames:
                is_new = True
                self.last_action = action
                self.last_action_frame = self.frame_count
                self.action_counts[action] = self.action_counts.get(action, 0) + 1
                self.action_history.append({
                    "action": action,
                    "frame": self.frame_count,
                    "confidence": confidence,
                })
        elif action in ("ready", "moving"):
            self.last_action = action

        return self._make_result(action, confidence, is_new)

    def _recognize(self, kp: dict, angles: dict) -> tuple:
        """核心识别逻辑"""

        # 提取关键指标
        right_wrist = kp.get("right_wrist", {})
        left_wrist = kp.get("left_wrist", {})
        right_shoulder = kp.get("right_shoulder", {})
        right_elbow = kp.get("right_elbow", {})
        right_hip = kp.get("right_hip", {})
        nose = kp.get("nose", {})

        if not all([right_wrist, right_shoulder, nose]):
            return "ready", 0.3

        wrist_y = right_wrist.get("y", 0)
        shoulder_y = right_shoulder.get("y", 0)
        hip_y = right_hip.get("y", 0)
        nose_y = nose.get("y", 0)

        wrist_x = right_wrist.get("x", 0)
        shoulder_x = right_shoulder.get("x", 0)

        # 计算手腕速度（帧间差异）
        wrist_speed = self._get_wrist_speed()
        wrist_vertical_speed = self._get_wrist_vertical_speed()

        # 肘部角度
        elbow_angle = angles.get("right_elbow", 90)
        shoulder_angle = angles.get("right_shoulder", 90)

        # === 发球检测 ===
        # 特征：手腕在头顶以上 + 手臂伸展 + 从高到低的轨迹
        if (wrist_y < nose_y and
            elbow_angle > 140 and
            shoulder_angle > 120 and
            wrist_vertical_speed > 3):
            return "serve", 0.85

        # === 扣杀检测 ===
        # 特征：手腕极高位 + 快速向下挥动 + 肘部先弯后伸
        if (wrist_y < shoulder_y - 50 and
            wrist_speed > 15 and
            wrist_vertical_speed > 8):
            return "smash", 0.80

        # === 挑球检测 ===
        # 特征：手腕从低位向上快速挥动
        if (wrist_y > hip_y and
            wrist_vertical_speed < -5 and
            wrist_speed > 8):
            return "lob", 0.70

        # === 吊球检测 ===
        # 特征：手腕在高位 + 慢速下压
        if (wrist_y < shoulder_y and
            0 < wrist_vertical_speed < 5 and
            wrist_speed < 10 and
            elbow_angle > 100):
            return "drop", 0.65

        # === 正手/反手检测 ===
        # 基于手腕相对身体的横向位置和运动方向
        lateral_speed = self._get_wrist_lateral_speed()
        if wrist_speed > 8:
            # 手腕在身体同侧（右侧）= 正手
            if wrist_x > shoulder_x and lateral_speed > 3:
                return "forehand", 0.75
            # 手腕穿过身体到对侧 = 反手
            elif wrist_x < shoulder_x and lateral_speed < -3:
                return "backhand", 0.70

        # === 移动检测 ===
        body_speed = self._get_body_speed()
        if body_speed > 5:
            return "moving", 0.60

        return "ready", 0.50

    def _get_wrist_speed(self) -> float:
        """计算手腕速度（像素/帧）"""
        if len(self.keypoint_buffer) < 2:
            return 0
        curr = self.keypoint_buffer[-1].get("right_wrist", {})
        prev = self.keypoint_buffer[-2].get("right_wrist", {})
        if not curr or not prev:
            return 0
        dx = curr.get("x", 0) - prev.get("x", 0)
        dy = curr.get("y", 0) - prev.get("y", 0)
        return math.sqrt(dx * dx + dy * dy)

    def _get_wrist_vertical_speed(self) -> float:
        """手腕垂直速度（正值=向下，负值=向上）"""
        if len(self.keypoint_buffer) < 3:
            return 0
        curr = self.keypoint_buffer[-1].get("right_wrist", {})
        prev = self.keypoint_buffer[-3].get("right_wrist", {})
        if not curr or not prev:
            return 0
        return (curr.get("y", 0) - prev.get("y", 0)) / 2

    def _get_wrist_lateral_speed(self) -> float:
        """手腕横向速度（正值=向右，负值=向左）"""
        if len(self.keypoint_buffer) < 3:
            return 0
        curr = self.keypoint_buffer[-1].get("right_wrist", {})
        prev = self.keypoint_buffer[-3].get("right_wrist", {})
        if not curr or not prev:
            return 0
        return (curr.get("x", 0) - prev.get("x", 0)) / 2

    def _get_body_speed(self) -> float:
        """身体整体移动速度（基于髋部）"""
        if len(self.keypoint_buffer) < 2:
            return 0
        curr_lh = self.keypoint_buffer[-1].get("left_hip", {})
        curr_rh = self.keypoint_buffer[-1].get("right_hip", {})
        prev_lh = self.keypoint_buffer[-2].get("left_hip", {})
        prev_rh = self.keypoint_buffer[-2].get("right_hip", {})
        if not all([curr_lh, curr_rh, prev_lh, prev_rh]):
            return 0
        cx = (curr_lh.get("x", 0) + curr_rh.get("x", 0)) / 2
        cy = (curr_lh.get("y", 0) + curr_rh.get("y", 0)) / 2
        px = (prev_lh.get("x", 0) + prev_rh.get("x", 0)) / 2
        py = (prev_lh.get("y", 0) + prev_rh.get("y", 0)) / 2
        return math.sqrt((cx - px) ** 2 + (cy - py) ** 2)

    def _make_result(self, action: str, confidence: float, is_new: bool) -> dict:
        action_info = self.ACTIONS.get(action, self.ACTIONS["ready"])
        return {
            "action": action,
            "action_info": action_info,
            "confidence": round(confidence, 2),
            "is_new_action": is_new,
            "action_counts": dict(self.action_counts),
            "action_history": self.action_history[-20:],
        }

    def reset(self):
        """重置状态"""
        self.keypoint_buffer.clear()
        self.action_history.clear()
        self.last_action = "ready"
        self.last_action_frame = -self.debounce_frames
        self.frame_count = 0
        self.action_counts = {k: 0 for k in self.ACTIONS}
