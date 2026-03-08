/**
 * Sport Vision — Main Application
 * WebSocket communication, UI orchestration, and event handling
 */

(function () {
    'use strict';

    // ============ DOM Elements ============
    const $ = (id) => document.getElementById(id);

    const heroSection = $('hero-section');
    const analysisSection = $('analysis-section');
    const videoCanvas = $('video-canvas');
    const videoOverlay = $('video-overlay');
    const progressFill = $('progress-fill');
    const statusDot = $('status-dot');
    const statusText = $('status-text');
    const actionIcon = $('action-icon');
    const actionName = $('action-name');
    const confidenceFill = $('confidence-fill');
    const confidenceText = $('confidence-text');
    const actionCard = $('action-card');
    const timelineContainer = $('timeline-container');
    const uploaInput = $('video-upload');
    const uploadBtn = $('upload-btn');
    const demoBtn = $('demo-btn');
    const demoSelector = $('demo-selector');
    const demoGrid = $('demo-grid');
    const btnStop = $('btn-stop');
    const btnBack = $('btn-back');

    const videoCtx = videoCanvas.getContext('2d');

    // ============ State ============
    let ws = null;
    let isAnalyzing = false;
    let dashboard = null;
    let currentSport = 'badminton';
    let frameImage = new Image();
    let lastActionColor = '#00f0ff';

    // ============ Initialize ============
    function init() {
        dashboard = new Dashboard();
        bindEvents();
        setStatus('ready', '就绪');
        loadDemos();
    }

    // ============ Event Binding ============
    function bindEvents() {
        // Sport toggle
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentSport = btn.dataset.sport;
            });
        });

        // Upload
        uploaInput.addEventListener('change', handleUpload);

        // Demo button
        demoBtn.addEventListener('click', () => {
            demoSelector.style.display = demoSelector.style.display === 'none' ? 'block' : 'none';
        });

        // Stop / Back
        btnStop.addEventListener('click', stopAnalysis);
        btnBack.addEventListener('click', goBack);
    }

    // ============ Status ============
    function setStatus(type, text) {
        statusDot.className = 'status-dot';
        if (type === 'processing') {
            statusDot.classList.add('processing');
        } else if (type === 'active') {
            statusDot.classList.add('active');
        }
        statusText.textContent = text;
    }

    // ============ Demo Videos ============
    async function loadDemos() {
        try {
            const resp = await fetch('/api/demos');
            const data = await resp.json();

            if (data.demos.length === 0) {
                demoGrid.innerHTML = `
                    <div class="demo-card" style="grid-column: 1/-1; text-align: center; color: var(--text-dim);">
                        <p>暂无 Demo 视频</p>
                        <p style="font-size: 0.7rem; margin-top: 8px;">
                            将 .mp4 文件放入 <code>demo_videos/</code> 目录
                        </p>
                    </div>
                `;
                return;
            }

            demoGrid.innerHTML = data.demos.map(d => `
                <div class="demo-card" data-demo-id="${d.id}" data-filename="${d.filename}">
                    <div class="demo-card-name">🎬 ${d.name}</div>
                    <div class="demo-card-size">${d.size_mb} MB</div>
                </div>
            `).join('');

            // Bind click
            demoGrid.querySelectorAll('.demo-card').forEach(card => {
                card.addEventListener('click', () => {
                    const demoId = card.dataset.demoId;
                    if (demoId) startAnalysis('demo', demoId);
                });
            });
        } catch (err) {
            console.warn('Failed to load demos:', err);
        }
    }

    // ============ Upload ============
    async function handleUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        setStatus('processing', '上传中...');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const resp = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
            });
            const data = await resp.json();

            if (data.error) {
                alert(data.error);
                setStatus('ready', '就绪');
                return;
            }

            startAnalysis('upload', null, data.path);
        } catch (err) {
            alert('上传失败: ' + err.message);
            setStatus('ready', '就绪');
        }
    }

    // ============ WebSocket Analysis ============
    function startAnalysis(source, demoId, uploadPath) {
        // Show analysis UI
        heroSection.style.display = 'none';
        analysisSection.style.display = 'block';
        videoOverlay.classList.remove('hidden');

        // Reset
        dashboard.reset();
        timelineContainer.innerHTML = '';
        progressFill.style.width = '0%';
        isAnalyzing = true;

        setStatus('processing', '连接分析引擎...');

        // Connect WebSocket
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${location.host}/ws/analyze`);

        ws.onopen = () => {
            setStatus('processing', '分析中...');

            const msg = { type: 'start', source };
            if (source === 'demo') msg.id = demoId;
            if (source === 'upload') msg.path = uploadPath;

            ws.send(JSON.stringify(msg));
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            handleWSMessage(msg);
        };

        ws.onerror = (err) => {
            console.error('WebSocket error:', err);
            setStatus('ready', '连接错误');
        };

        ws.onclose = () => {
            if (isAnalyzing) {
                setStatus('active', '分析完成');
                isAnalyzing = false;
            }
        };
    }

    function handleWSMessage(msg) {
        switch (msg.type) {
            case 'started':
                videoOverlay.classList.add('hidden');
                setStatus('processing', '分析中...');
                break;

            case 'frame':
                renderFrame(msg.data);
                break;

            case 'complete':
                setStatus('active', '分析完成');
                isAnalyzing = false;
                break;

            case 'stopped':
                setStatus('ready', '已停止');
                isAnalyzing = false;
                break;

            case 'error':
                setStatus('ready', `错误: ${msg.message}`);
                isAnalyzing = false;
                break;
        }
    }

    // ============ Frame Rendering ============
    function renderFrame(data) {
        if (!data.frame_base64) return;

        // Update progress
        progressFill.style.width = `${data.progress * 100}%`;

        // Draw frame on canvas
        frameImage.onload = () => {
            videoCanvas.width = frameImage.naturalWidth;
            videoCanvas.height = frameImage.naturalHeight;
            videoCtx.drawImage(frameImage, 0, 0);
        };
        frameImage.src = 'data:image/jpeg;base64,' + data.frame_base64;

        // Update action display
        if (data.action) {
            updateActionDisplay(data.action);
        }

        // Update dashboard
        if (data.pose) {
            dashboard.updateAngles(data.pose.joint_angles);
            dashboard.updateBiomechanics(data.pose.biomechanics);
        }

        if (data.action) {
            dashboard.updateStats(data.action.action_counts);
        }

        // Update heatmap (every 10 frames)
        if (data.frame_number % 10 === 0 && data.heatmap_data) {
            dashboard.updateHeatmap(data.heatmap_data, data.width, data.height);
        }
    }

    function updateActionDisplay(actionData) {
        const info = actionData.action_info;

        // Update icon and name
        actionIcon.textContent = info.icon;
        actionName.textContent = info.name;

        // Update confidence
        const pct = Math.round(actionData.confidence * 100);
        confidenceFill.style.width = `${pct}%`;
        confidenceText.textContent = `${pct}%`;

        // Update action card border color
        if (info.color !== lastActionColor) {
            actionCard.style.borderColor = info.color;
            actionName.style.color = info.color;
            lastActionColor = info.color;
        }

        // Add to timeline if new action
        if (actionData.is_new_action) {
            addTimelineItem(actionData);
        }
    }

    function addTimelineItem(actionData) {
        const info = actionData.action_info;
        const item = document.createElement('div');
        item.className = 'timeline-item';
        item.style.borderColor = info.color;
        item.style.color = info.color;
        item.style.background = info.color + '15';
        item.textContent = `${info.icon} ${info.name}`;
        timelineContainer.appendChild(item);

        // Auto-scroll to right
        timelineContainer.scrollLeft = timelineContainer.scrollWidth;

        // Flash the action card
        actionCard.classList.remove('flash');
        void actionCard.offsetWidth; // force reflow
        actionCard.classList.add('flash');
    }

    // ============ Controls ============
    function stopAnalysis() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'stop' }));
        }
        isAnalyzing = false;
        setStatus('ready', '已停止');
    }

    function goBack() {
        stopAnalysis();
        if (ws) {
            ws.close();
            ws = null;
        }
        analysisSection.style.display = 'none';
        heroSection.style.display = 'flex';
        setStatus('ready', '就绪');
    }

    // ============ Start ============
    document.addEventListener('DOMContentLoaded', init);
})();
