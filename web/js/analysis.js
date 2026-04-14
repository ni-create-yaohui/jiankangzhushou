/* 数据分析模块 */
let selectedAnalysisUsers = new Set();

async function loadAnalysisPage() {
    loadAnalysisUserChips();
}

async function loadAnalysisUserChips() {
    try {
        const data = await api.listUsers();
        const users = data.users || {};
        const container = document.getElementById('analysisUserChips');
        if (!container) return;
        container.innerHTML = '';

        for (const [uid, user] of Object.entries(users)) {
            const chip = document.createElement('span');
            chip.className = 'chip' + (selectedAnalysisUsers.has(uid) ? ' selected' : '');
            chip.textContent = `${user.basic_info?.name || uid}`;
            chip.onclick = () => {
                if (selectedAnalysisUsers.has(uid)) {
                    selectedAnalysisUsers.delete(uid);
                    chip.classList.remove('selected');
                } else {
                    selectedAnalysisUsers.add(uid);
                    chip.classList.add('selected');
                }
            };
            container.appendChild(chip);
        }
    } catch (e) {}
}

async function loadReportUserChips() {
    const container = document.getElementById('reportUserChips');
    if (!container) return;
    container.innerHTML = '';

    try {
        const data = await api.listUsers();
        const users = data.users || {};

        for (const [uid, user] of Object.entries(users)) {
            const chip = document.createElement('span');
            chip.className = 'chip' + (selectedAnalysisUsers.has(uid) ? ' selected' : '');
            chip.textContent = `${user.basic_info?.name || uid}`;
            chip.onclick = () => {
                if (selectedAnalysisUsers.has(uid)) {
                    selectedAnalysisUsers.delete(uid);
                    chip.classList.remove('selected');
                } else {
                    selectedAnalysisUsers.add(uid);
                    chip.classList.add('selected');
                }
            };
            container.appendChild(chip);
        }
    } catch (e) {}
}

async function runHealthAnalysis() {
    if (selectedAnalysisUsers.size === 0) {
        showToast('请至少选择一个用户', 'warning');
        return;
    }

    const container = document.getElementById('healthAnalysisResult');
    container.innerHTML = '<div style="text-align:center;padding:20px"><div class="spinner" style="margin:0 auto"></div><p style="color:var(--text-secondary);margin-top:12px">正在分析...</p></div>';

    try {
        const data = await api.listUsers();
        const users = data.users || {};

        let html = '<div class="form-row" style="gap:10px;margin-bottom:16px">';
        let totalWeight = 0, wCount = 0;
        let bpNormal = 0, bpCount = 0;
        let avgSleep = 0, sCount = 0;

        for (const uid of selectedAnalysisUsers) {
            const user = users[uid];
            if (!user) continue;
            const b = user.basic_info || {};

            const h = b.height || 170;
            const w = b.weight || 65;
            totalWeight += w;
            wCount++;

            const records = user.health_records || {};
            for (const [date, rec] of Object.entries(records)) {
                if (rec.blood_pressure_systolic) {
                    bpCount++;
                    if (rec.blood_pressure_systolic < 120) bpNormal++;
                }
                if (rec.sleep_hours) {
                    avgSleep += rec.sleep_hours;
                    sCount++;
                }
            }
        }

        const avgW = wCount ? (totalWeight / wCount).toFixed(1) : '--';
        const avgS = sCount ? (avgSleep / sCount).toFixed(1) : '--';
        const bpRate = bpCount ? Math.round(bpNormal / bpCount * 100) : '--';

        html += `
            <div class="card" style="text-align:center;padding:12px">
                <div style="font-size:18px;font-weight:600;color:var(--primary-blue)">${selectedAnalysisUsers.size}</div>
                <div style="font-size:12px;color:var(--text-secondary)">用户数量</div>
            </div>
            <div class="card" style="text-align:center;padding:12px">
                <div style="font-size:18px;font-weight:600;color:var(--primary-blue)">${avgW}</div>
                <div style="font-size:12px;color:var(--text-secondary)">平均体重</div>
            </div>
            <div class="card" style="text-align:center;padding:12px">
                <div style="font-size:18px;font-weight:600;color:var(--primary-blue)">${bpRate}%</div>
                <div style="font-size:12px;color:var(--text-secondary)">血压正常率</div>
            </div>
            <div class="card" style="text-align:center;padding:12px">
                <div style="font-size:18px;font-weight:600;color:var(--primary-blue)">${avgS}</div>
                <div style="font-size:12px;color:var(--text-secondary)">平均睡眠</div>
            </div>
        `;
        html += '</div>';

        // 图表
        html += '<div class="card"><h3>体重趋势</h3><div id="analysisWeightChart" class="chart-box"></div></div>';
        html += '<div class="card"><h3>血压趋势</h3><div id="analysisBPChart" class="chart-box"></div></div>';

        container.innerHTML = html;

        drawWeightChart(users);
        drawBPChart(users);
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><span class="empty-icon">❌</span><p>分析失败: ${e.message}</p></div>`;
    }
}

function drawWeightChart(users) {
    const el = document.getElementById('analysisWeightChart');
    if (!el) return;
    const chart = echarts.init(el);
    const series = [];
    const colors = ['#e74c3c', '#3498db', '#27ae60', '#f39c12', '#9b59b6'];

    let idx = 0;
    for (const uid of selectedAnalysisUsers) {
        const user = users[uid];
        if (!user) continue;
        const records = user.health_records || {};
        const dates = [];
        const weights = [];

        for (const [date, rec] of Object.entries(records).sort()) {
            if (rec.weight) {
                dates.push(date);
                weights.push(rec.weight);
            }
        }

        if (dates.length > 0) {
            series.push({
                name: user.basic_info?.name || uid,
                type: 'line',
                data: weights,
                smooth: true,
                lineStyle: { color: colors[idx % colors.length] },
                itemStyle: { color: colors[idx % colors.length] }
            });
        }
        idx++;
    }

    chart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: series.map(s => s.name), bottom: 0 },
        grid: { top: 20, right: 20, bottom: 40, left: 50 },
        xAxis: { type: 'category', data: series[0]?.data.map((_, i) => i + 1) || [] },
        yAxis: { type: 'value', name: 'kg' },
        series
    });

    window.addEventListener('resize', () => chart.resize());
}

function drawBPChart(users) {
    const el = document.getElementById('analysisBPChart');
    if (!el) return;
    const chart = echarts.init(el);
    const systolicData = [];
    const diastolicData = [];
    const dates = [];

    for (const uid of selectedAnalysisUsers) {
        const user = users[uid];
        if (!user) continue;
        const records = user.health_records || {};

        for (const [date, rec] of Object.entries(records).sort()) {
            if (rec.blood_pressure_systolic) {
                dates.push(date);
                systolicData.push(rec.blood_pressure_systolic);
                diastolicData.push(rec.blood_pressure_diastolic || 0);
            }
        }
    }

    chart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['收缩压', '舒张压'], bottom: 0 },
        grid: { top: 20, right: 20, bottom: 40, left: 50 },
        xAxis: { type: 'category', data: dates },
        yAxis: { type: 'value', name: 'mmHg' },
        series: [
            { name: '收缩压', type: 'line', data: systolicData, smooth: true, itemStyle: { color: '#e74c3c' } },
            { name: '舒张压', type: 'line', data: diastolicData, smooth: true, itemStyle: { color: '#3498db' } }
        ]
    });

    window.addEventListener('resize', () => chart.resize());
}

async function generateHealthReport() {
    const progress = document.getElementById('reportProgress');
    progress.style.display = 'block';

    try {
        const userIds = Array.from(selectedAnalysisUsers);
        const response = await fetch('/api/v1/report/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userIds)
        });

        if (!response.ok) throw new Error('报告生成失败');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '健康分析报告.docx';
        a.click();
        window.URL.revokeObjectURL(url);
        showToast('报告已生成并开始下载', 'success');
    } catch (e) {
        showToast('报告生成失败: ' + e.message, 'error');
    } finally {
        progress.style.display = 'none';
    }
}

// 健康工具页面枚举
async function loadToolEnums() {
    try {
        const enums = await api.getEnums();
        fillSelect('calActivityLevel', enums.activity_levels);
        fillSelect('exerciseGoal', enums.health_goals);
        fillSelect('exerciseLevel', enums.fitness_levels);

        // 填充食物选择
        const foods = ['米饭(一碗)', '面条(一碗)', '鸡胸肉(100g)', '鸡蛋(1个)', '牛奶(250ml)',
            '苹果(1个)', '香蕉(1根)', '西兰花(100g)', '豆腐(100g)', '三文鱼(100g)',
            '牛肉(100g)', '红薯(100g)', '燕麦(50g)', '酸奶(200ml)', '核桃(30g)'];
        const foodSelects = document.querySelectorAll('.diet-food-select');
        foodSelects.forEach(sel => {
            sel.innerHTML = '<option value="">选择食物</option>';
            foods.forEach(f => {
                const opt = document.createElement('option');
                opt.value = f;
                opt.textContent = f;
                sel.appendChild(opt);
            });
        });
    } catch (e) {}
}

function addDietFoodRow() {
    const container = document.getElementById('dietFoodList');
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;margin-bottom:8px';
    const foods = ['米饭(一碗)', '面条(一碗)', '鸡胸肉(100g)', '鸡蛋(1个)', '牛奶(250ml)',
        '苹果(1个)', '香蕉(1根)', '西兰花(100g)', '豆腐(100g)', '三文鱼(100g)',
        '牛肉(100g)', '红薯(100g)', '燕麦(50g)', '酸奶(200ml)', '核桃(30g)'];
    row.innerHTML = `
        <select class="form-select diet-food-select" style="flex:1">
            <option value="">选择食物</option>
            ${foods.map(f => `<option value="${f}">${f}</option>`).join('')}
        </select>
        <input class="form-input diet-food-amount" type="number" value="1" style="width:70px">
        <button class="btn-danger btn-sm" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(row);
}

// BMI计算
async function calcBMI() {
    const hEl = document.getElementById('bmiHeight');
    const wEl = document.getElementById('bmiWeight');
    if (!hEl || !wEl) return;

    const h = parseFloat(hEl.value);
    const w = parseFloat(wEl.value);
    if (!h || !w) { showToast('请输入身高和体重', 'warning'); return; }

    try {
        const data = await api.calculateBMI(h, w);
        const categoryColor = data.category === '正常' ? '#00B42A' : data.category === '偏胖' || data.category === '超重' ? '#FF7D00' : data.category === '肥胖' ? '#F53F3F' : '#2D8CFF';

        const resultEl = document.getElementById('bmiResult');
        resultEl.style.display = 'block';
        resultEl.innerHTML = `
            <div style="text-align:center">
                <div style="font-size:36px;font-weight:700;color:${categoryColor}">${data.bmi}</div>
                <div style="font-size:14px;color:${categoryColor};margin-bottom:12px">${data.category}</div>
                <div style="font-size:12px;color:var(--text-secondary)">理想体重范围: ${data.ideal_weight_min} - ${data.ideal_weight_max} kg</div>
            </div>`;
    } catch (e) {
        showToast('计算失败', 'error');
    }
}

// 热量计算
async function calcCalorie() {
    const params = {
        gender: document.getElementById('calGender')?.value || '男',
        age: document.getElementById('calAge')?.value || 25,
        height: document.getElementById('calHeight')?.value || 170,
        weight: document.getElementById('calWeight')?.value || 65,
        activity_level: document.getElementById('calActivityLevel')?.value || '轻度活动',
    };

    try {
        const data = await api.calculateCalorie(params);
        const resultEl = document.getElementById('calorieResult');
        resultEl.style.display = 'block';
        resultEl.innerHTML = `
            <div style="text-align:center;margin-bottom:12px">
                <div style="font-size:12px;color:var(--text-secondary)">基础代谢率(BMR)</div>
                <div style="font-size:24px;font-weight:700;color:var(--primary-blue)">${data.bmr} kcal</div>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;text-align:center">
                <div style="padding:12px;background:#E8F3E8;border-radius:8px">
                    <div style="font-size:18px;font-weight:600;color:#00B42A">${data.lose_weight}</div>
                    <div style="font-size:12px;color:var(--text-secondary)">减脂摄入 kcal</div>
                </div>
                <div style="padding:12px;background:var(--light-blue);border-radius:8px">
                    <div style="font-size:18px;font-weight:600">${data.maintain}</div>
                    <div style="font-size:12px;color:var(--text-secondary)">维持体重 kcal</div>
                </div>
                <div style="padding:12px;background:#FCE4E4;border-radius:8px">
                    <div style="font-size:18px;font-weight:600;color:#F53F3F">${data.gain_muscle}</div>
                    <div style="font-size:12px;color:var(--text-secondary)">增肌摄入 kcal</div>
                </div>
            </div>`;
    } catch (e) {
        showToast('计算失败', 'error');
    }
}

// 饮食分析 - 通过AI聊天
function analyzeDiet() {
    const items = document.querySelectorAll('#dietFoodList > div');
    const foods = [];
    items.forEach(item => {
        const name = item.querySelector('.diet-food-select')?.value;
        const qty = item.querySelector('.diet-food-amount')?.value || 1;
        if (name) foods.push([name, parseFloat(qty)]);
    });

    if (foods.length === 0) { showToast('请至少选择一种食物', 'warning'); return; }

    const query = `请分析以下饮食的营养摄入：${JSON.stringify(foods)}`;
    toggleChat();
    setTimeout(() => {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = query;
            sendMessage();
        }
    }, 300);
}

// 运动方案 - 通过AI聊天
function getExercisePlan() {
    const goal = document.getElementById('exerciseGoal')?.value || '保持健康';
    const level = document.getElementById('exerciseLevel')?.value || '初级';
    const duration = document.getElementById('exerciseDuration')?.value || 60;

    const query = `请为我推荐一个运动方案，目标：${goal}，运动水平：${level}，每次时长：${duration}分钟`;
    toggleChat();
    setTimeout(() => {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = query;
            sendMessage();
        }
    }, 300);
}

// 睡眠评估 - 通过AI聊天
function assessSleepQuality() {
    const hours = document.getElementById('sleepHours')?.value || 7;
    const quality = document.getElementById('sleepQuality')?.value || 7;

    const query = `请评估我的睡眠质量：睡眠${hours}小时，质量评分${quality}/10`;
    toggleChat();
    setTimeout(() => {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = query;
            sendMessage();
        }
    }, 300);
}