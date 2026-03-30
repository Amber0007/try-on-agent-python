/**
 * AI 虚拟试衣 Agent - 前端 JavaScript
 * Python 版本
 */

// 状态管理
const state = {
  selectedOutfit: null,
  selectedAvatar: null,
  outfits: [],
  avatars: [],
  knowledge: []
};

// API 请求封装
async function api(endpoint, options = {}) {
  const response = await fetch(endpoint, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    }
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || '请求失败');
  }

  return data;
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initTabs();
  loadOutfits();
  loadAvatars();
  loadKnowledge();
});

// 导航
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');

  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const sectionId = item.dataset.section;

      // 更新激活状态
      navItems.forEach(n => n.classList.remove('active'));
      item.classList.add('active');

      // 切换 section
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      document.getElementById(sectionId).classList.add('active');
    });
  });
}

// Tabs
function initTabs() {
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const tabName = tab.dataset.tab;

      // 更新 tab 状态
      tab.parentElement.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      // 更新内容
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      document.getElementById(`tab-${tabName}`).classList.add('active');
    });
  });
}

// 加载服装列表
async function loadOutfits() {
  try {
    state.outfits = await api('/api/outfits');
    renderOutfitSelection();
    renderOutfitList();
  } catch (error) {
    console.error('加载服装失败:', error);
    showToast('加载服装失败：' + error.message, 'error');
  }
}

// 渲染服装选择（试衣页面）
function renderOutfitSelection() {
  const container = document.getElementById('outfit-selection');
  if (!container) return;

  if (state.outfits.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无服装，请先添加</div>';
    return;
  }

  const currentSelection = state.selectedOutfit;
  container.innerHTML = state.outfits.map(outfit => `
    <div class="item-card ${currentSelection === outfit.id ? 'selected' : ''}"
         onclick="selectOutfit('${outfit.id}')">
      <img src="${outfit.maskedUrl}" alt="${outfit.id}" onerror="this.style.display='none'">
      <div class="info">
        <div class="name">${outfit.id.slice(0, 8)}</div>
      </div>
    </div>
  `).join('');

  // 恢复选择状态
  state.selectedOutfit = currentSelection;
  updateTryOnButton();
}

// 渲染服装列表（管理页面）
function renderOutfitList() {
  const container = document.getElementById('outfit-list');

  if (state.outfits.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无服装</div>';
    return;
  }

  container.innerHTML = state.outfits.map(outfit => `
    <div class="item-card large">
      <button class="delete-btn" onclick="deleteOutfit('${outfit.id}')">&times;</button>
      <img src="${outfit.maskedUrl}" alt="${outfit.id}" onerror="this.style.display='none'">
      <div class="info">
        <div class="name">${outfit.id}</div>
        <div class="tags">
          ${outfit.attributes?.style ? `<span class="tag">${outfit.attributes.style}</span>` : ''}
        </div>
      </div>
    </div>
  `).join('');
}

// 选择服装
function selectOutfit(id) {
  state.selectedOutfit = id;
  renderOutfitSelection();
  updateTryOnButton();
  updatePreviewArea();
}

// 添加服装
function showAddOutfitModal() {
  document.getElementById('add-outfit-modal').classList.add('active');
}

function switchOutfitTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

  event.target.classList.add('active');
  document.getElementById(`outfit-${tab}-tab`).classList.add('active');
}

async function submitOutfit() {
  const isUrlTab = document.getElementById('outfit-url-tab')?.classList.contains('active');

  try {
    let result;
    if (isUrlTab) {
      const url = document.getElementById('outfit-url-input').value.trim();
      if (!url) {
        showToast('请输入图片 URL', 'error');
        return;
      }
      result = await api('/api/outfits/url', {
        method: 'POST',
        body: JSON.stringify({ url })
      });
    } else {
      const fileInput = document.getElementById('outfit-file-input');
      if (!fileInput.files[0]) {
        showToast('请选择图片文件', 'error');
        return;
      }

      const formData = new FormData();
      formData.append('image', fileInput.files[0]);

      const response = await fetch('/api/outfits/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || '上传失败');
      }
      result = await response.json();
    }

    showToast('服装添加成功', 'success');
    closeModal('add-outfit-modal');

    // 更新状态
    state.outfits.push(result);
    renderOutfitSelection();
    renderOutfitList();
    state.selectedOutfit = result.id;
    updateTryOnButton();

    // 清空输入
    document.getElementById('outfit-url-input').value = '';
    document.getElementById('outfit-file-input').value = '';
  } catch (error) {
    showToast('添加失败：' + error.message, 'error');
  }
}

// 删除服装
async function deleteOutfit(id) {
  if (!confirm('确定删除这个服装吗？')) return;

  try {
    await api(`/api/outfits/${id}`, { method: 'DELETE' });
    showToast('删除成功', 'success');
    loadOutfits();
  } catch (error) {
    showToast('删除失败：' + error.message, 'error');
  }
}

// 加载数字人
async function loadAvatars() {
  try {
    const filters = {};
    const genderFilter = document.getElementById('avatar-gender-filter')?.value;
    const bodyFilter = document.getElementById('avatar-body-filter')?.value;
    const poseFilter = document.getElementById('avatar-pose-filter')?.value;

    if (genderFilter) filters.gender = genderFilter;
    if (bodyFilter) filters.bodyType = bodyFilter;
    if (poseFilter) filters.pose = poseFilter;

    state.avatars = await api(`/api/avatars?${new URLSearchParams(filters)}`);

    // 保留当前选中的数字人
    const previouslySelected = state.selectedAvatar;
    renderAvatarSelection();
    renderAvatarList();

    // 恢复选择状态
    if (previouslySelected && state.avatars.some(a => a.id === previouslySelected)) {
      state.selectedAvatar = previouslySelected;
    }
    updateTryOnButton();
  } catch (error) {
    console.error('加载数字人失败:', error);
    showToast('加载数字人失败：' + error.message, 'error');
  }
}

// 渲染数字人选择（试衣页面）
function renderAvatarSelection() {
  const container = document.getElementById('avatar-selection');
  if (!container) return;

  if (state.avatars.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无匹配的数字人</div>';
    return;
  }

  const currentSelection = state.selectedAvatar;
  container.innerHTML = state.avatars.map(avatar => `
    <div class="item-card ${currentSelection === avatar.id ? 'selected' : ''}"
         onclick="selectAvatar('${avatar.id}')">
      <img src="${avatar.imageUrl}" alt="${avatar.name}" onerror="this.style.display='none'">
      <div class="info">
        <div class="name">${avatar.name}</div>
        <div class="tags">
          <span class="tag">${avatar.bodyType}</span>
          <span class="tag">${avatar.skinTone}</span>
        </div>
      </div>
    </div>
  `).join('');

  // 恢复选择状态
  state.selectedAvatar = currentSelection;
  updateTryOnButton();
}

// 渲染数字人列表（管理页面）
function renderAvatarList() {
  const container = document.getElementById('avatar-list');

  if (state.avatars.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无数字人</div>';
    return;
  }

  container.innerHTML = state.avatars.map(avatar => `
    <div class="item-card large ${avatar.custom ? 'custom' : ''}">
      ${avatar.custom ? `<button class="delete-btn" onclick="deleteAvatar('${avatar.id}')">&times;</button>` : ''}
      <img src="${avatar.imageUrl}" alt="${avatar.name}" onerror="this.style.display='none'">
      <div class="info">
        <div class="name">${avatar.name}</div>
        <div class="tags">
          <span class="tag">${avatar.gender}</span>
          <span class="tag">${avatar.bodyType}</span>
          <span class="tag">${avatar.skinTone}</span>
          <span class="tag">${avatar.pose}</span>
        </div>
      </div>
    </div>
  `).join('');
}

// 选择数字人
function selectAvatar(id) {
  state.selectedAvatar = id;
  renderAvatarSelection();
  updateTryOnButton();
  updatePreviewArea();
}

// 创建数字人
function showCreateAvatarModal() {
  document.getElementById('create-avatar-modal').classList.add('active');
}

async function submitAvatar() {
  const form = document.getElementById('create-avatar-form');
  const formData = new FormData(form);

  const data = {
    name: formData.get('name'),
    gender: formData.get('gender'),
    bodyType: formData.get('bodyType'),
    skinTone: formData.get('skinTone'),
    pose: formData.get('pose')
  };

  try {
    await api('/api/avatars', {
      method: 'POST',
      body: JSON.stringify(data)
    });
    showToast('数字人创建成功', 'success');
    closeModal('create-avatar-modal');
    loadAvatars();
    form.reset();
  } catch (error) {
    showToast('创建失败：' + error.message, 'error');
  }
}

// 删除数字人
async function deleteAvatar(id) {
  if (!confirm('确定删除这个数字人吗？')) return;

  try {
    await api(`/api/avatars/${id}`, { method: 'DELETE' });
    showToast('删除成功', 'success');
    loadAvatars();
  } catch (error) {
    showToast('删除失败：' + error.message, 'error');
  }
}

// 更新试衣按钮状态
function updateTryOnButton() {
  const btn = document.getElementById('try-on-btn');
  if (btn) {
    btn.disabled = !(state.selectedOutfit && state.selectedAvatar);
  }
}

// 更新预览区域
function updatePreviewArea() {
  const previewArea = document.getElementById('preview-area');
  if (!previewArea) return;

  const outfit = state.outfits.find(o => o.id === state.selectedOutfit);
  const avatar = state.avatars.find(a => a.id === state.selectedAvatar);

  if (outfit && avatar) {
    previewArea.innerHTML = `
      <div style="display: flex; gap: 1rem; justify-content: center; align-items: center; flex-wrap: wrap;">
        <div style="text-align: center;">
          <p style="font-size: 0.875rem; color: #666;">服装</p>
          <img src="${outfit.maskedUrl}" style="width: 150px; height: 150px; object-fit: cover; border-radius: 8px;">
        </div>
        <div style="font-size: 1.5rem;">+</div>
        <div style="text-align: center;">
          <p style="font-size: 0.875rem; color: #666;">数字人</p>
          <img src="${avatar.imageUrl}" style="width: 100px; height: 150px; object-fit: cover; border-radius: 8px;">
        </div>
      </div>
    `;
  } else if (outfit) {
    previewArea.innerHTML = `
      <div style="text-align: center;">
        <p style="font-size: 0.875rem; color: #666;">已选择服装</p>
        <img src="${outfit.maskedUrl}" style="width: 150px; height: 150px; object-fit: cover; border-radius: 8px; margin-top: 0.5rem;">
      </div>
    `;
  } else if (avatar) {
    previewArea.innerHTML = `
      <div style="text-align: center;">
        <p style="font-size: 0.875rem; color: #666;">已选择数字人</p>
        <img src="${avatar.imageUrl}" style="width: 100px; height: 150px; object-fit: cover; border-radius: 8px; margin-top: 0.5rem;">
      </div>
    `;
  }
}

// 执行试衣
async function executeTryOn() {
  if (!state.selectedOutfit || !state.selectedAvatar) {
    showToast('请选择服装和数字人', 'error');
    return;
  }

  const btn = document.getElementById('try-on-btn');
  const resultArea = document.getElementById('try-on-result');

  btn.disabled = true;
  btn.textContent = '处理中...';
  resultArea.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

  try {
    const result = await api('/api/try-on', {
      method: 'POST',
      body: JSON.stringify({
        outfitId: state.selectedOutfit,
        avatarId: state.selectedAvatar,
        mode: 'analysis'  // 默认使用分析模式
      })
    });

    if (result.success) {
      // 处理不同类型的结果
      if (result.type === 'virtual_try_on' && result.imageUrl) {
        // 图片生成模式
        resultArea.innerHTML = `
          <h4>试衣完成!</h4>
          <img src="${result.imageUrl}" alt="试衣结果" style="max-width: 100%; border-radius: 8px;">
        `;
        showToast('试衣成功', 'success');
      } else if (result.type === 'fashion_analysis' && result.analysis) {
        // 分析模式 - 解析并显示 JSON 结果
        let analysisData;
        try {
          // 尝试解析 JSON
          const jsonMatch = result.analysis.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            analysisData = JSON.parse(jsonMatch[0]);
          }
        } catch (e) {
          analysisData = null;
        }

        if (analysisData) {
          resultArea.innerHTML = `
            <h4>穿搭分析</h4>
            <div style="text-align: left; max-width: 600px; margin: 0 auto;">
              <div style="margin-bottom: 1rem;">
                <strong>风格描述:</strong>
                <p style="margin: 0.5rem 0; color: #555;">${analysisData.style_description || 'N/A'}</p>
              </div>
              <div style="margin-bottom: 1rem;">
                <strong>色彩分析:</strong>
                <p style="margin: 0.5rem 0; color: #555;">${analysisData.color_analysis || 'N/A'}</p>
              </div>
              <div style="margin-bottom: 1rem;">
                <strong>版型分析:</strong>
                <p style="margin: 0.5rem 0; color: #555;">${analysisData.fit_analysis || 'N/A'}</p>
              </div>
              <div style="margin-bottom: 1rem;">
                <strong>适合场合:</strong>
                <div style="margin: 0.5rem 0;">
                  ${(analysisData.occasion_suggestions || []).map(s => `<span class="tag" style="margin-right: 0.5rem;">${s}</span>`).join('')}
                </div>
              </div>
              <div style="margin-bottom: 1rem;">
                <strong>适合季节:</strong>
                <div style="margin: 0.5rem 0;">
                  ${(analysisData.season_suggestions || []).map(s => `<span class="tag" style="margin-right: 0.5rem;">${s}</span>`).join('')}
                </div>
              </div>
              <div style="margin-bottom: 1rem;">
                <strong>AI 绘图 Prompt:</strong>
                <p style="margin: 0.5rem 0; color: #555; font-size: 0.85rem; background: #f5f5f5; padding: 0.75rem; border-radius: 4px;">${analysisData.ai_prompt || 'N/A'}</p>
              </div>
            </div>
          `;
        } else {
          resultArea.innerHTML = `
            <h4>穿搭分析</h4>
            <p style="white-space: pre-wrap; text-align: left; max-width: 600px; margin: 0 auto;">${result.analysis}</p>
          `;
        }
        showToast('分析完成', 'success');
      } else {
        resultArea.innerHTML = `
          <h4>结果</h4>
          <p style="text-align: left; white-space: pre-wrap;">${JSON.stringify(result, null, 2)}</p>
        `;
      }
    } else {
      resultArea.innerHTML = `
        <div class="empty-state">
          <p>试衣失败：${result.error}</p>
          <p>${result.fallback?.message || ''}</p>
        </div>
      `;
      showToast('试衣失败：' + result.error, 'error');
    }
  } catch (error) {
    resultArea.innerHTML = `<div class="empty-state">请求失败：${error.message}</div>`;
    showToast('请求失败：' + error.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '开始试衣';
  }
}

// 加载穿搭知识
async function loadKnowledge() {
  try {
    state.knowledge = await api('/api/knowledge');
    renderKnowledgeList();
    loadRules();
  } catch (error) {
    console.error('加载穿搭知识失败:', error);
    showToast('加载穿搭知识失败：' + error.message, 'error');
  }
}

// 渲染穿搭知识列表
function renderKnowledgeList() {
  const container = document.getElementById('knowledge-list');

  if (state.knowledge.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无穿搭案例</div>';
    return;
  }

  container.innerHTML = state.knowledge.map(outfit => `
    <div class="item-card">
      <button class="delete-btn" onclick="deleteKnowledge('${outfit.id}')">&times;</button>
      <img src="${outfit.imageUrl}" alt="${outfit.name}" onerror="this.style.display='none'">
      <div class="info">
        <div class="name">${outfit.name}</div>
        <div class="tags">
          <span class="tag">${outfit.style}</span>
          ${(outfit.season || []).slice(0, 2).map(s => `<span class="tag">${s}</span>`).join('') || ''}
        </div>
      </div>
    </div>
  `).join('');
}

// 加载穿搭规则
async function loadRules() {
  try {
    const rules = await api('/api/knowledge/rules');
    renderRules(rules);
  } catch (error) {
    console.error('加载规则失败:', error);
  }
}

// 渲染规则
function renderRules(rules) {
  const container = document.getElementById('rules-display');

  let html = '';

  // 颜色搭配规则
  if (rules.colorMatching?.length) {
    html += `
      <div class="rule-card">
        <h4>🎨 颜色搭配法则</h4>
        <ul>
          ${rules.colorMatching.map(r => `<li><strong>${r.name}:</strong> ${r.description}（例：${r.example}）</li>`).join('')}
        </ul>
      </div>
    `;
  }

  // 风格穿搭技巧
  if (rules.styleRules?.length) {
    html += `
      <div class="rule-card">
        <h4>👔 风格穿搭技巧</h4>
        <ul>
          ${rules.styleRules.map(r => `<li><strong>${r.name}:</strong> ${r.tips.join('；')}</li>`).join('')}
        </ul>
      </div>
    `;
  }

  // 体型穿搭建议
  if (rules.bodyTypeTips?.length) {
    html += `
      <div class="rule-card">
        <h4>👤 体型穿搭建议</h4>
        <ul>
          ${rules.bodyTypeTips.map(r => `<li><strong>${r.name}:</strong> ${r.tips.join('；')}</li>`).join('')}
        </ul>
      </div>
    `;
  }

  // 季节穿搭规则
  if (rules.seasonalRules?.length) {
    html += `
      <div class="rule-card">
        <h4>🌤️ 季节穿搭规则</h4>
        <ul>
          ${rules.seasonalRules.map(r => `<li><strong>${r.name}:</strong> ${r.tips.join('；')}</li>`).join('')}
        </ul>
      </div>
    `;
  }

  container.innerHTML = html || '<div class="empty-state">暂无规则</div>';
}

// 添加穿搭知识
function showAddKnowledgeModal() {
  document.getElementById('add-knowledge-modal').classList.add('active');
}

async function submitKnowledge() {
  const form = document.getElementById('add-knowledge-form');
  const imageInput = document.getElementById('knowledge-image');

  if (!imageInput.files[0]) {
    showToast('请选择穿搭图片', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('image', imageInput.files[0]);
  formData.append('name', form.name.value);
  formData.append('style', form.style.value);
  formData.append('description', form.description.value);

  // 收集复选框
  const seasons = Array.from(form.querySelectorAll('input[name="season"]:checked')).map(cb => cb.value);
  const occasions = Array.from(form.querySelectorAll('input[name="occasion"]:checked')).map(cb => cb.value);

  if (seasons.length) formData.append('season', JSON.stringify(seasons));
  if (occasions.length) formData.append('occasion', JSON.stringify(occasions));

  try {
    const response = await fetch('/api/knowledge', {
      method: 'POST',
      body: formData
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error);
    }

    showToast('穿搭案例添加成功', 'success');
    closeModal('add-knowledge-modal');
    loadKnowledge();
    form.reset();
  } catch (error) {
    showToast('添加失败：' + error.message, 'error');
  }
}

// 删除穿搭知识
async function deleteKnowledge(id) {
  if (!confirm('确定删除这个穿搭案例吗？')) return;

  try {
    await api(`/api/knowledge/${id}`, { method: 'DELETE' });
    showToast('删除成功', 'success');
    loadKnowledge();
  } catch (error) {
    showToast('删除失败：' + error.message, 'error');
  }
}

// 关闭模态框
function closeModal(modalId) {
  document.getElementById(modalId).classList.remove('active');
}

// Toast 提示
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}
