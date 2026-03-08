"""
Sport Vision — 可视化渲染模块
OpenCV 帧上叠加骨骼、动作标注和轨迹
"""

import cv2
import numpy as np
from typing import Optional


class Visualizer:
    """在视频帧上渲染分析结果"""

    # 骨骼部位颜色方案（BGR）
    LIMB_COLORS = {
        # 躯干 — 蓝色系
        (11, 12): (255, 200, 0),
        (11, 23): (255, 180, 0),
        (12, 24): (255, 180, 0),
        (23, 24): (255, 160, 0),
        # 左臂 — 青色
        (11, 13): (255, 255, 0),
        (13, 15): (255, 255, 50),
        # 右臂 — 绿色
        (12, 14): (100, 255, 100),
        (14, 16): (50, 255, 50),
        # 左腿 — 紫色
        (23, 25): (255, 100, 255),
        (25, 27): (255, 50, 200),
        # 右腿 — 橙色
        (24, 26): (50, 180, 255),
        (26, 28): (0, 150, 255),
    }

    # 关键点颜色
    KEYPOINT_COLOR = (0, 240, 255)  # 亮黄色
    KEYPOINT_GLOW_COLOR = (0, 200, 255)

    def __init__(self):
        self.trajectory_points = []
        self.max_trajectory = 60

    def render_frame(self, frame: np.ndarray, analysis: Optional[dict],
                     action_result: Optional[dict]) -> np.ndarray:
        """
        在帧上叠加所有可视化元素

        Args:
            frame: BGR 原始帧
            analysis: PoseAnalyzer 输出
            action_result: ActionRecognizer 输出
        """
        overlay = frame.copy()

        if analysis:
            # 绘制骨骼
            self._draw_skeleton(overlay, analysis)
            # 绘制关键点
            self._draw_keypoints(overlay, analysis["keypoints"])
            # 绘制轨迹
            self._draw_trajectory(overlay, analysis.get("center_of_mass"))
            # 绘制关节角度
            self._draw_joint_angles(overlay, analysis)

        if action_result:
            # 绘制动作标注
            self._draw_action_label(overlay, action_result)

        # 绘制信息面板
        self._draw_info_panel(overlay, analysis, action_result)

        return overlay

    def _draw_skeleton(self, frame: np.ndarray, analysis: dict):
        """绘制骨骼连线"""
        kp_map = {kp["id"]: kp for kp in analysis["keypoints"]}

        for (a, b) in analysis["skeleton"]:
            if a in kp_map and b in kp_map:
                pa = kp_map[a]
                pb = kp_map[b]
                if pa["visibility"] > 0.5 and pb["visibility"] > 0.5:
                    pt1 = (int(pa["x"]), int(pa["y"]))
                    pt2 = (int(pb["x"]), int(pb["y"]))
                    color = self.LIMB_COLORS.get((a, b), (200, 200, 200))

                    # 发光效果：先画粗的半透明线
                    cv2.line(frame, pt1, pt2, color, 6, cv2.LINE_AA)
                    # 再画细的亮线
                    bright_color = tuple(min(255, c + 50) for c in color)
                    cv2.line(frame, pt1, pt2, bright_color, 2, cv2.LINE_AA)

    def _draw_keypoints(self, frame: np.ndarray, keypoints: list):
        """绘制关键点（带发光效果）"""
        for kp in keypoints:
            if kp["visibility"] > 0.5:
                pt = (int(kp["x"]), int(kp["y"]))
                # 外圈发光
                cv2.circle(frame, pt, 8, self.KEYPOINT_GLOW_COLOR, -1, cv2.LINE_AA)
                # 内圈亮点
                cv2.circle(frame, pt, 4, self.KEYPOINT_COLOR, -1, cv2.LINE_AA)
                # 白色中心
                cv2.circle(frame, pt, 2, (255, 255, 255), -1, cv2.LINE_AA)

    def _draw_trajectory(self, frame: np.ndarray, center_of_mass: Optional[dict]):
        """绘制重心运动轨迹"""
        if center_of_mass:
            self.trajectory_points.append(
                (int(center_of_mass["x"]), int(center_of_mass["y"]))
            )
            if len(self.trajectory_points) > self.max_trajectory:
                self.trajectory_points = self.trajectory_points[-self.max_trajectory:]

        if len(self.trajectory_points) > 1:
            for i in range(1, len(self.trajectory_points)):
                alpha = i / len(self.trajectory_points)
                color = (
                    int(100 * (1 - alpha) + 0 * alpha),
                    int(200 * (1 - alpha) + 240 * alpha),
                    int(255 * (1 - alpha) + 255 * alpha),
                )
                thickness = max(1, int(alpha * 3))
                cv2.line(frame, self.trajectory_points[i - 1],
                         self.trajectory_points[i], color, thickness, cv2.LINE_AA)

    def _draw_joint_angles(self, frame: np.ndarray, analysis: dict):
        """在关键点旁绘制关节角度"""
        kp_map = {kp["id"]: kp for kp in analysis["keypoints"]}
        angle_positions = {
            "right_elbow": 14,
            "left_elbow": 13,
            "right_knee": 26,
            "left_knee": 25,
        }
        for name, landmark_id in angle_positions.items():
            if name in analysis["joint_angles"] and landmark_id in kp_map:
                kp = kp_map[landmark_id]
                if kp["visibility"] > 0.5:
                    angle = analysis["joint_angles"][name]
                    pt = (int(kp["x"]) + 15, int(kp["y"]) - 5)
                    cv2.putText(frame, f"{angle:.0f}", pt,
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                                (0, 255, 255), 1, cv2.LINE_AA)

    def _draw_action_label(self, frame: np.ndarray, action_result: dict):
        """绘制当前识别的动作标签"""
        action_info = action_result["action_info"]
        confidence = action_result["confidence"]
        text = f"{action_info['name']} ({confidence:.0%})"

        h, w = frame.shape[:2]
        # 背景框
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
        x = w - text_size[0] - 30
        y = 50

        # 半透明背景
        overlay_rect = frame.copy()
        cv2.rectangle(overlay_rect, (x - 15, y - 35),
                      (x + text_size[0] + 15, y + 10), (0, 0, 0), -1)
        cv2.addWeighted(overlay_rect, 0.6, frame, 0.4, 0, frame)

        # 颜色条
        hex_color = action_info["color"]
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        cv2.rectangle(frame, (x - 15, y - 35), (x - 10, y + 10), (b, g, r), -1)

        # 文字
        cv2.putText(frame, text, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)

    def _draw_info_panel(self, frame: np.ndarray, analysis: Optional[dict],
                         action_result: Optional[dict]):
        """左上角信息面板"""
        h, w = frame.shape[:2]
        panel_w, panel_h = 280, 160

        # 半透明背景
        overlay_rect = frame.copy()
        cv2.rectangle(overlay_rect, (10, 10), (panel_w, panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay_rect, 0.5, frame, 0.5, 0, frame)

        # 边框
        cv2.rectangle(frame, (10, 10), (panel_w, panel_h), (0, 200, 255), 1)

        # Title
        cv2.putText(frame, "SPORT VISION", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 240, 255), 2, cv2.LINE_AA)

        y_offset = 60
        if analysis:
            bio = analysis.get("biomechanics", {})
            info_lines = [
                f"Confidence: {analysis['confidence']:.0%}",
                f"Wrist Speed: {bio.get('wrist_speed', 0):.1f} px/f",
                f"Body Lean: {bio.get('body_lean', 0):.1f} deg",
                f"Symmetry: {bio.get('symmetry_score', 0):.0f}%",
            ]
            for line in info_lines:
                cv2.putText(frame, line, (20, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
                y_offset += 22

    def reset(self):
        """重置状态"""
        self.trajectory_points.clear()
