/* 应用主模块 */
let currentPage = 'dashboard';

function switchPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));

    const pageEl = document.getElementById('page-' + page);
    const navTabEl = document.querySelector(`.nav-tab[onclick*="${page}"]`);

    if (pageEl) pageEl.classList.add('active');
    if (navTabEl) navTabEl.classList.add('active');

    currentPage = page;

    // 页面初始化
    if (page === 'dashboard') loadDashboard();
    if (page === 'user') { loadUserList(); loadUserEnums(); }
    if (page === 'analysis') loadAnalysisPage();
    if (page === 'tools') loadToolEnums();
}

function switchUserTab(tab) {
    document.querySelectorAll('#page-user .tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('#page-user .tab-btn').forEach(t => t.classList.remove('active'));
    const content = document.getElementById('tab-' + tab);
    const btn = document.querySelector(`#page-user .tab-btn[onclick*="${tab}"]`);
    if (content) content.classList.add('active');
    if (btn) btn.classList.add('active');

    if (tab === 'user-edit') loadEditUserSelect();
    if (tab === 'user-records') loadRecordUserSelect();
}

function switchAnalysisTab(tab) {
    document.querySelectorAll('#page-analysis .tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('#page-analysis .tab-btn').forEach(t => t.classList.remove('active'));
    const content = document.getElementById('tab-' + tab);
    const btn = document.querySelector(`#page-analysis .tab-btn[onclick*="${tab}"]`);
    if (content) content.classList.add('active');
    if (btn) btn.classList.add('active');

    if (tab === 'analysis-health') loadAnalysisUserChips();
    if (tab === 'analysis-report') loadReportUserChips();
}

function switchToolTab(tab) {
    document.querySelectorAll('#page-tools .tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('#page-tools .tab-btn').forEach(t => t.classList.remove('active'));
    const content = document.getElementById('tab-' + tab);
    const btn = document.querySelector(`#page-tools .tab-btn[onclick*="${tab}"]`);
    if (content) content.classList.add('active');
    if (btn) btn.classList.add('active');
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
});