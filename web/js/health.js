/* 用户管理和健康记录模块 */
let allUsers = {};
let selectedEditUser = null;

async function loadUserEnums() {
    try {
        const enums = await api.getEnums();
        fillSelect('addGender', enums.genders);
        fillSelect('addActivityLevel', enums.activity_levels);
        fillSelect('addHealthGoal', enums.health_goals);
    } catch (e) {}
}

function fillSelect(id, options, placeholder) {
    const sel = document.getElementById(id);
    if (!sel) return;
    sel.innerHTML = placeholder ? `<option value="">${placeholder}</option>` : '';
    options.forEach(o => {
        const opt = document.createElement('option');
        opt.value = o;
        opt.textContent = o;
        sel.appendChild(opt);
    });
}

async function loadUserList() {
    try {
        const data = await api.listUsers();
        allUsers = data.users || {};
        const container = document.getElementById('userListContainer');

        if (Object.keys(allUsers).length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">👤</span>
                    <p>暂无用户数据，请先创建用户档案</p>
                    <button class="btn-blue" onclick="switchUserTab('user-add')">➕ 创建用户</button>
                </div>`;
            return;
        }

        let html = '';
        for (const [uid, user] of Object.entries(allUsers)) {
            const b = user.basic_info || {};
            const h = b.height || 170;
            const w = b.weight || 65;
            const bmi = (w / (h / 100) ** 2).toFixed(1);
            const bmiClass = bmi < 18.5 ? 'danger' : bmi < 24 ? 'normal' : bmi < 28 ? 'warning' : 'danger';
            const recordCount = Object.keys(user.health_records || {}).length;

            html += `
                <div class="user-item">
                    <div class="user-avatar">${(b.name || '?')[0]}</div>
                    <div class="user-info">
                        <div class="user-name">${b.name || '未命名'}</div>
                        <div class="user-detail">${b.gender || ''} | ${b.age || ''}岁 | ${h}cm | ${w}kg</div>
                    </div>
                    <div class="user-bmi ${bmiClass}">${bmi} BMI</div>
                    <div class="user-bmi normal">${recordCount} 条记录</div>
                </div>`;
        }
        container.innerHTML = html;
    } catch (e) {
        console.error('加载用户列表失败:', e);
    }
}

async function addUser() {
    const name = document.getElementById('addName').value.trim();
    if (!name) { showToast('请输入姓名', 'warning'); return; }

    const data = {
        name,
        gender: document.getElementById('addGender').value,
        age: parseInt(document.getElementById('addAge').value) || 25,
        height: parseFloat(document.getElementById('addHeight').value) || 170,
        weight: parseFloat(document.getElementById('addWeight').value) || 65,
        activity_level: document.getElementById('addActivityLevel').value,
        health_goal: document.getElementById('addHealthGoal').value,
    };

    try {
        const result = await api.createUser(data);
        showToast(`用户创建成功: ${result.user_id}`, 'success');
        document.getElementById('addName').value = '';
        loadUserList();
        loadDashboard();
    } catch (e) {
        showToast('创建失败: ' + e.message, 'error');
    }
}

async function loadEditUserSelect() {
    try {
        const data = await api.listUsers();
        allUsers = data.users || {};
        const sel = document.getElementById('editUserSelect');
        sel.innerHTML = '<option value="">-- 选择用户 --</option>';
        for (const uid of Object.keys(allUsers)) {
            sel.innerHTML += `<option value="${uid}">${uid} - ${allUsers[uid].basic_info?.name || ''}</option>`;
        }

        const enums = await api.getEnums();
        fillSelect('editGender', enums.genders);
        fillSelect('editActivityLevel', enums.activity_levels);
        fillSelect('editHealthGoal', enums.health_goals);
    } catch (e) {}
}

async function loadUserForEdit() {
    const uid = document.getElementById('editUserSelect').value;
    if (!uid) {
        document.getElementById('editFormContainer').style.display = 'none';
        return;
    }

    try {
        const user = await api.getUser(uid);
        const b = user.basic_info || {};
        document.getElementById('editName').value = b.name || '';
        document.getElementById('editGender').value = b.gender || '';
        document.getElementById('editAge').value = b.age || '';
        document.getElementById('editHeight').value = b.height || '';
        document.getElementById('editWeight').value = b.weight || '';
        document.getElementById('editActivityLevel').value = b.activity_level || '';
        document.getElementById('editHealthGoal').value = b.health_goal || '';
        document.getElementById('editFormContainer').style.display = 'block';
        selectedEditUser = uid;
    } catch (e) {
        showToast('加载用户失败', 'error');
    }
}

async function updateUser() {
    if (!selectedEditUser) return;
    const data = {
        name: document.getElementById('editName').value,
        gender: document.getElementById('editGender').value,
        age: parseInt(document.getElementById('editAge').value),
        height: parseFloat(document.getElementById('editHeight').value),
        weight: parseFloat(document.getElementById('editWeight').value),
        activity_level: document.getElementById('editActivityLevel').value,
        health_goal: document.getElementById('editHealthGoal').value,
    };

    try {
        await api.updateUser(selectedEditUser, data);
        showToast('用户更新成功', 'success');
        loadUserList();
        loadDashboard();
    } catch (e) {
        showToast('更新失败', 'error');
    }
}

async function deleteUserConfirm() {
    if (!selectedEditUser) return;
    if (!confirm(`确定删除用户 ${selectedEditUser} 吗？`)) return;

    try {
        await api.deleteUser(selectedEditUser);
        showToast('用户已删除', 'success');
        selectedEditUser = null;
        document.getElementById('editFormContainer').style.display = 'none';
        loadEditUserSelect();
        loadUserList();
        loadDashboard();
    } catch (e) {
        showToast('删除失败', 'error');
    }
}

// 健康记录
async function loadRecordUserSelect() {
    try {
        const data = await api.listUsers();
        allUsers = data.users || {};
        const sel = document.getElementById('recordUserSelect');
        sel.innerHTML = '<option value="">-- 选择用户 --</option>';
        for (const uid of Object.keys(allUsers)) {
            sel.innerHTML += `<option value="${uid}">${uid} - ${allUsers[uid].basic_info?.name || ''}</option>`;
        }
    } catch (e) {}
}

async function loadHealthRecords() {
    const uid = document.getElementById('recordUserSelect').value;
    if (!uid) {
        document.getElementById('healthRecordsContainer').innerHTML = `
            <div class="empty-state"><span class="empty-icon">📋</span><p>请选择用户查看健康记录</p></div>`;
        return;
    }

    try {
        const data = await api.getHealthRecords(uid);
        const records = data.health_records || {};
        const container = document.getElementById('healthRecordsContainer');

        if (Object.keys(records).length === 0) {
            container.innerHTML = `
                <div class="empty-state"><span class="empty-icon">📋</span><p>暂无健康记录</p>
                <button class="btn-blue btn-sm" onclick="showAddRecordForm()">➕ 添加记录</button></div>`;
            return;
        }

        let html = '';
        for (const [date, rec] of Object.entries(records).sort((a, b) => b[0].localeCompare(a[0]))) {
            html += `<div class="form-section" style="margin-bottom:10px">`;
            html += `<div style="font-weight:600;color:var(--primary-blue);margin-bottom:8px">${date}</div>`;
            html += `<div class="form-row" style="gap:8px">`;

            if (rec.weight) {
                html += `<div class="form-group" style="margin-bottom:0;text-align:center">
                    <div style="font-size:16px;font-weight:600">${rec.weight}</div>
                    <div style="font-size:12px;color:var(--text-secondary)">体重(kg)</div></div>`;
            }
            if (rec.blood_pressure_systolic) {
                html += `<div class="form-group" style="margin-bottom:0;text-align:center">
                    <div style="font-size:16px;font-weight:600">${rec.blood_pressure_systolic}/${rec.blood_pressure_diastolic || '--'}</div>
                    <div style="font-size:12px;color:var(--text-secondary)">血压</div></div>`;
            }
            if (rec.heart_rate) {
                html += `<div class="form-group" style="margin-bottom:0;text-align:center">
                    <div style="font-size:16px;font-weight:600">${rec.heart_rate}</div>
                    <div style="font-size:12px;color:var(--text-secondary)">心率</div></div>`;
            }
            if (rec.sleep_hours) {
                html += `<div class="form-group" style="margin-bottom:0;text-align:center">
                    <div style="font-size:16px;font-weight:600">${rec.sleep_hours}h</div>
                    <div style="font-size:12px;color:var(--text-secondary)">睡眠</div></div>`;
            }
            if (rec.steps) {
                html += `<div class="form-group" style="margin-bottom:0;text-align:center">
                    <div style="font-size:16px;font-weight:600">${rec.steps.toLocaleString()}</div>
                    <div style="font-size:12px;color:var(--text-secondary)">步数</div></div>`;
            }

            html += `</div></div>`;
        }
        container.innerHTML = html;
    } catch (e) {
        showToast('加载记录失败', 'error');
    }
}

function showAddRecordForm() {
    document.getElementById('addRecordForm').style.display = 'block';
    document.getElementById('recordDate').value = new Date().toISOString().split('T')[0];
}

function hideAddRecordForm() {
    document.getElementById('addRecordForm').style.display = 'none';
}

async function addHealthRecord() {
    const uid = document.getElementById('recordUserSelect').value;
    if (!uid) { showToast('请先选择用户', 'warning'); return; }

    const date = document.getElementById('recordDate').value;
    if (!date) { showToast('请选择日期', 'warning'); return; }

    const data = { date };
    const fields = {
        recordWeight: 'weight', recordBPSystolic: 'blood_pressure_systolic',
        recordBPDiastolic: 'blood_pressure_diastolic', recordHeartRate: 'heart_rate',
        recordSleepHours: 'sleep_hours', recordSleepQuality: 'sleep_quality',
        recordSteps: 'steps', recordCalories: 'calories_intake'
    };

    for (const [elId, key] of Object.entries(fields)) {
        const el = document.getElementById(elId);
        if (el && el.value !== '' && el.value !== null) {
            data[key] = parseFloat(el.value);
        }
    }

    try {
        await api.addHealthRecord(uid, data);
        showToast('健康记录添加成功', 'success');
        hideAddRecordForm();
        loadHealthRecords();
        loadDashboard();
    } catch (e) {
        showToast('添加失败: ' + e.message, 'error');
    }
}