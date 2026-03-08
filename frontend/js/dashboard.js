/**
 * Sport Vision — Dashboard Module
 * Gauge rendering, heatmap, and statistics display
 */

class Dashboard {
    constructor() {
        // Gauge canvases
        this.gauges = {};
        const gaugeIds = ['right-elbow', 'left-elbow', 'right-knee', 'left-knee'];
        for (const id of gaugeIds) {
            const canvas = document.getElementById(`gauge-${id}`);
            if (canvas) {
                this.gauges[id] = {
                    canvas,
                    ctx: canvas.getContext('2d'),
                    value: 0,
                    targetValue: 0,
                };
            }
        }

        // Heatmap
        this.heatmapCanvas = document.getElementById('heatmap-canvas');
        this.heatmapCtx = this.heatmapCanvas ? this.heatmapCanvas.getContext('2d') : null;
        this.heatmapData = [];

        // Stats grid
        this.statsGrid = document.getElementById('stats-grid');

        // Start gauge animation loop
        this._animateGauges();
    }

    /**
     * Update joint angle gauges
     * @param {Object} angles - {right_elbow: 145, left_elbow: 90, ...}
     */
    updateAngles(angles) {
        if (!angles) return;

        const mapping = {
            'right_elbow': 'right-elbow',
            'left_elbow': 'left-elbow',
            'right_knee': 'right-knee',
            'left_knee': 'left-knee',
        };

        for (const [key, gaugeId] of Object.entries(mapping)) {
            if (angles[key] !== undefined && this.gauges[gaugeId]) {
                this.gauges[gaugeId].targetValue = angles[key];
                // Update value label
                const valEl = document.getElementById(`val-${gaugeId}`);
                if (valEl) valEl.textContent = `${Math.round(angles[key])}°`;
            }
        }
    }

    /**
     * Update biomechanics bars
     * @param {Object} bio - {wrist_speed, body_lean, knee_bend, symmetry_score}
     */
    updateBiomechanics(bio) {
        if (!bio) return;

        // Wrist speed (0-50 range)
        this._updateBar('bar-wrist-speed', bio.wrist_speed, 50);
        this._updateValue('val-wrist-speed', `${bio.wrist_speed?.toFixed(1) || 0}`);

        // Body lean (0-45 range)
        this._updateBar('bar-body-lean', bio.body_lean, 45);
        this._updateValue('val-body-lean', `${bio.body_lean?.toFixed(1) || 0}°`);

        // Knee bend (0-90 range)
        this._updateBar('bar-knee-bend', bio.knee_bend, 90);
        this._updateValue('val-knee-bend', `${bio.knee_bend?.toFixed(1) || 0}°`);

        // Symmetry (0-100)
        this._updateBar('bar-symmetry', bio.symmetry_score, 100);
        this._updateValue('val-symmetry', `${bio.symmetry_score?.toFixed(0) || 0}%`);
    }

    /**
     * Update action statistics
     * @param {Object} counts - {serve: 2, smash: 1, ...}
     */
    updateStats(counts) {
        if (!counts || !this.statsGrid) return;

        const actionMeta = {
            serve: { icon: '🎯', label: '发球' },
            smash: { icon: '💥', label: '扣杀' },
            forehand: { icon: '➡️', label: '正手' },
            backhand: { icon: '⬅️', label: '反手' },
            lob: { icon: '🌈', label: '挑球' },
            drop: { icon: '🪶', label: '吊球' },
        };

        let html = '';
        for (const [key, meta] of Object.entries(actionMeta)) {
            const count = counts[key] || 0;
            html += `
                <div class="stat-item">
                    <span class="stat-icon">${meta.icon}</span>
                    <div class="stat-info">
                        <span class="stat-info-label">${meta.label}</span>
                        <span class="stat-info-count">${count}</span>
                    </div>
                </div>
            `;
        }
        this.statsGrid.innerHTML = html;
    }

    /**
     * Update heatmap with trajectory data
     * @param {Array} trajectoryData - [{x, y}, ...]
     * @param {number} videoWidth
     * @param {number} videoHeight
     */
    updateHeatmap(trajectoryData, videoWidth, videoHeight) {
        if (!this.heatmapCtx || !trajectoryData || trajectoryData.length === 0) return;

        const canvas = this.heatmapCanvas;
        const ctx = this.heatmapCtx;
        const w = canvas.width;
        const h = canvas.height;

        // Clear
        ctx.fillStyle = '#0c0c24';
        ctx.fillRect(0, 0, w, h);

        // Draw court outline
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;
        ctx.strokeRect(10, 10, w - 20, h - 20);
        // Center line
        ctx.beginPath();
        ctx.moveTo(w / 2, 10);
        ctx.lineTo(w / 2, h - 10);
        ctx.stroke();

        // Scale factors
        const sx = (w - 20) / (videoWidth || 960);
        const sy = (h - 20) / (videoHeight || 540);

        // Draw heatmap points
        for (let i = 0; i < trajectoryData.length; i++) {
            const p = trajectoryData[i];
            const px = 10 + p.x * sx;
            const py = 10 + p.y * sy;
            const alpha = (i / trajectoryData.length) * 0.6 + 0.1;

            // Radial gradient for heat effect
            const gradient = ctx.createRadialGradient(px, py, 0, px, py, 12);
            gradient.addColorStop(0, `rgba(255, 51, 102, ${alpha})`);
            gradient.addColorStop(0.5, `rgba(255, 170, 51, ${alpha * 0.5})`);
            gradient.addColorStop(1, `rgba(255, 170, 51, 0)`);

            ctx.beginPath();
            ctx.arc(px, py, 12, 0, Math.PI * 2);
            ctx.fillStyle = gradient;
            ctx.fill();
        }

        // Draw trajectory line
        if (trajectoryData.length > 1) {
            ctx.beginPath();
            ctx.moveTo(10 + trajectoryData[0].x * sx, 10 + trajectoryData[0].y * sy);
            for (let i = 1; i < trajectoryData.length; i++) {
                ctx.lineTo(10 + trajectoryData[i].x * sx, 10 + trajectoryData[i].y * sy);
            }
            ctx.strokeStyle = 'rgba(0, 240, 255, 0.3)';
            ctx.lineWidth = 1;
            ctx.stroke();
        }
    }

    // == Private methods ==

    _updateBar(id, value, max) {
        const el = document.getElementById(id);
        if (el) {
            const pct = Math.min(100, (value / max) * 100);
            el.style.width = `${pct}%`;
        }
    }

    _updateValue(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    _animateGauges() {
        for (const id in this.gauges) {
            const gauge = this.gauges[id];
            // Smooth interpolation
            gauge.value += (gauge.targetValue - gauge.value) * 0.15;
            this._drawGauge(gauge);
        }
        requestAnimationFrame(() => this._animateGauges());
    }

    _drawGauge(gauge) {
        const { canvas, ctx, value } = gauge;
        const w = canvas.width;
        const h = canvas.height;
        const cx = w / 2;
        const cy = h / 2;
        const radius = Math.min(w, h) / 2 - 8;

        ctx.clearRect(0, 0, w, h);

        // Background arc
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0.75 * Math.PI, 2.25 * Math.PI);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
        ctx.lineWidth = 6;
        ctx.lineCap = 'round';
        ctx.stroke();

        // Value arc
        const normalizedValue = Math.min(value / 180, 1);
        const endAngle = 0.75 * Math.PI + normalizedValue * 1.5 * Math.PI;

        // Color based on value
        let color;
        if (value < 60) color = '#ff3366';
        else if (value < 120) color = '#ffaa33';
        else color = '#33ff88';

        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0.75 * Math.PI, endAngle);
        ctx.strokeStyle = color;
        ctx.lineWidth = 6;
        ctx.lineCap = 'round';
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Center value
        ctx.fillStyle = '#e8e8f0';
        ctx.font = `600 ${w > 60 ? 14 : 11}px 'Inter', sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${Math.round(value)}°`, cx, cy + 2);
    }

    reset() {
        for (const id in this.gauges) {
            this.gauges[id].value = 0;
            this.gauges[id].targetValue = 0;
        }
        if (this.statsGrid) this.statsGrid.innerHTML = '';
        if (this.heatmapCtx) {
            this.heatmapCtx.fillStyle = '#0c0c24';
            this.heatmapCtx.fillRect(0, 0, this.heatmapCanvas.width, this.heatmapCanvas.height);
        }
    }
}

// Export globally
window.Dashboard = Dashboard;
