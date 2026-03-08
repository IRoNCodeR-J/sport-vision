/**
 * Sport Vision — Skeleton Renderer
 * Canvas-based overlay for skeleton visualization
 * (Used for additional frontend-side rendering if needed)
 */

class SkeletonRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        // Color scheme for different body parts
        this.limbColors = {
            torso: '#00d4ff',
            leftArm: '#00ffcc',
            rightArm: '#33ff88',
            leftLeg: '#cc66ff',
            rightLeg: '#ffaa33',
        };

        // Skeleton connection definition with part labels
        this.connections = [
            // Torso
            { from: 'left_shoulder', to: 'right_shoulder', part: 'torso' },
            { from: 'left_shoulder', to: 'left_hip', part: 'torso' },
            { from: 'right_shoulder', to: 'right_hip', part: 'torso' },
            { from: 'left_hip', to: 'right_hip', part: 'torso' },
            // Left arm
            { from: 'left_shoulder', to: 'left_elbow', part: 'leftArm' },
            { from: 'left_elbow', to: 'left_wrist', part: 'leftArm' },
            // Right arm
            { from: 'right_shoulder', to: 'right_elbow', part: 'rightArm' },
            { from: 'right_elbow', to: 'right_wrist', part: 'rightArm' },
            // Left leg
            { from: 'left_hip', to: 'left_knee', part: 'leftLeg' },
            { from: 'left_knee', to: 'left_ankle', part: 'leftLeg' },
            // Right leg
            { from: 'right_hip', to: 'right_knee', part: 'rightLeg' },
            { from: 'right_knee', to: 'right_ankle', part: 'rightLeg' },
        ];

        // Trail history for motion trails
        this.trailHistory = [];
        this.maxTrailLength = 15;
    }

    /**
     * Render skeleton on canvas
     * @param {Array} keypoints - Array of {name, x, y, visibility}
     * @param {number} scaleX - Scale factor for X coordinates
     * @param {number} scaleY - Scale factor for Y coordinates
     */
    render(keypoints, scaleX = 1, scaleY = 1) {
        if (!keypoints || keypoints.length === 0) return;

        const kpMap = {};
        for (const kp of keypoints) {
            kpMap[kp.name] = {
                x: kp.x * scaleX,
                y: kp.y * scaleY,
                visibility: kp.visibility,
            };
        }

        // Draw connections
        for (const conn of this.connections) {
            const from = kpMap[conn.from];
            const to = kpMap[conn.to];

            if (from && to && from.visibility > 0.5 && to.visibility > 0.5) {
                this._drawLimb(from, to, this.limbColors[conn.part]);
            }
        }

        // Draw keypoints
        for (const name in kpMap) {
            const kp = kpMap[name];
            if (kp.visibility > 0.5) {
                this._drawKeypoint(kp);
            }
        }

        // Store for trail
        const wrist = kpMap['right_wrist'];
        if (wrist && wrist.visibility > 0.5) {
            this.trailHistory.push({ x: wrist.x, y: wrist.y });
            if (this.trailHistory.length > this.maxTrailLength) {
                this.trailHistory.shift();
            }
        }

        // Draw trail
        this._drawTrail();
    }

    _drawLimb(from, to, color) {
        const ctx = this.ctx;
        // Glow effect
        ctx.shadowColor = color;
        ctx.shadowBlur = 10;
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Inner bright line
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.strokeStyle = '#ffffff88';
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    _drawKeypoint(kp) {
        const ctx = this.ctx;
        // Outer glow
        ctx.shadowColor = '#00f0ff';
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(kp.x, kp.y, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#00f0ff';
        ctx.fill();
        ctx.shadowBlur = 0;

        // White center
        ctx.beginPath();
        ctx.arc(kp.x, kp.y, 2, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
    }

    _drawTrail() {
        const ctx = this.ctx;
        if (this.trailHistory.length < 2) return;

        for (let i = 1; i < this.trailHistory.length; i++) {
            const alpha = i / this.trailHistory.length;
            const prev = this.trailHistory[i - 1];
            const curr = this.trailHistory[i];

            ctx.beginPath();
            ctx.moveTo(prev.x, prev.y);
            ctx.lineTo(curr.x, curr.y);
            ctx.strokeStyle = `rgba(255, 51, 102, ${alpha * 0.6})`;
            ctx.lineWidth = alpha * 3;
            ctx.lineCap = 'round';
            ctx.stroke();
        }
    }

    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    reset() {
        this.trailHistory = [];
        this.clear();
    }
}

// Export globally
window.SkeletonRenderer = SkeletonRenderer;
