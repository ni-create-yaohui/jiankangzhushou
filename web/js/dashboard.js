/* 驾驶舱模块 */
let dashChart = null;

async function loadDashboard() {
    try {
        const data = await api.listUsers();
        const users = data.users || {};

        // 用户数
        document.getElementById('dashUserCount').textContent = Object.keys(users).length;

        // 记录数
        let totalRecords = 0;
        let totalBMI = 0, bmiCount = 0;
        let totalSleep = 0, sleepCount = 0;
        let totalSteps = 0, stepsCount = 0;
        let normalCount = 0;

        for (const [uid, user] of Object.entries(users)) {
            const b = user.basic_info || {};
            const h = b.height || 170;
            const w = b.weight || 65;
            const bmi = w / (h / 100) ** 2;
            totalBMI += bmi;
            bmiCount++;
            if (bmi >= 18.5 && bmi < 24) normalCount++;

            const records = user.health_records || {};
            totalRecords += Object.keys(records).length;

            for (const [date, rec] of Object.entries(records)) {
                if (rec.sleep_hours) { totalSleep += rec.sleep_hours; sleepCount++; }
                if (rec.steps) { totalSteps += rec.steps; stepsCount++; }
            }
        }

        document.getElementById('dashRecords').textContent = totalRecords;
        document.getElementById('dashAvgBMI').textContent = bmiCount ? (totalBMI / bmiCount).toFixed(1) : '--';
        document.getElementById('dashAvgSleep').textContent = sleepCount ? (totalSleep / sleepCount).toFixed(1) : '--';
        document.getElementById('dashAvgSteps').textContent = stepsCount ? Math.round(totalSteps / stepsCount).toLocaleString() : '--';
        document.getElementById('dashHealthRate').textContent = bmiCount ? Math.round(normalCount / bmiCount * 100) + '%' : '--';

        // 图表
        renderDashChart(users);

    } catch (e) {
        console.error('加载驾驶舱失败:', e);
    }

    // 时钟
    updateClock();
    setInterval(updateClock, 1000);
}

function updateClock() {
    const now = new Date();
    const str = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    document.getElementById('dashClock').textContent = str;
}

function renderDashChart(users) {
    const chartEl = document.getElementById('dashChart');
    if (!chartEl) return;

    if (!dashChart) {
        dashChart = echarts.init(chartEl);
    }

    const weightData = [];
    const dates = [];

    for (const [uid, user] of Object.entries(users)) {
        const records = user.health_records || {};
        for (const [date, rec] of Object.entries(records)) {
            if (rec.weight) {
                dates.push(date);
                weightData.push({ date, value: rec.weight });
            }
        }
    }

    const sortedDates = [...new Set(dates)].sort().slice(-7);

    const option = {
        tooltip: { trigger: 'axis' },
        grid: { left: '12%', right: '5%', top: '10%', bottom: '15%' },
        xAxis: {
            type: 'category',
            data: sortedDates,
            axisLabel: { fontSize: 11, color: '#64748b' }
        },
        yAxis: {
            type: 'value',
            axisLabel: { fontSize: 11, color: '#64748b' }
        },
        series: [{
            type: 'line',
            smooth: true,
            data: sortedDates.map(d => {
                const rec = weightData.find(w => w.date === d);
                return rec ? rec.value : null;
            }),
            lineStyle: { color: '#2563eb', width: 2 },
            itemStyle: { color: '#2563eb' },
            areaStyle: { color: 'rgba(37,99,235,0.1)' }
        }]
    };

    dashChart.setOption(option);
}

window.addEventListener('resize', () => {
    if (dashChart) dashChart.resize();
});