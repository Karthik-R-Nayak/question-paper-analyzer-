const state = {
  subjects: [],
  semesters: [],
  questionTypes: [],
  topics: [],
  user: null,
  filters: {
    q: '',
    subject_id: '',
    semester_id: '',
    exam_type: ''
  },
  paperRows: [
    {
      question_number: '1',
      marks: 10,
      question_text: '',
      question_type_id: '',
      topic_ids: []
    }
  ]
};

const els = {
  searchInput: document.getElementById('searchInput'),
  subjectFilter: document.getElementById('subjectFilter'),
  semesterFilter: document.getElementById('semesterFilter'),
  examTypeFilter: document.getElementById('examTypeFilter'),
  applyFilters: document.getElementById('applyFilters'),
  statsGrid: document.getElementById('statsGrid'),
  questionsList: document.getElementById('questionsList'),
  questionTypesChart: document.getElementById('questionTypesChart'),
  topicsChart: document.getElementById('topicsChart'),
  semesterComparison: document.getElementById('semesterComparison'),
  semanticQueryInput: document.getElementById('semanticQueryInput'),
  semanticSearchBtn: document.getElementById('semanticSearchBtn'),
  similarQuestionsList: document.getElementById('similarQuestionsList'),
  tabButtons: document.querySelectorAll('.tab-button'),
  tabPanels: document.querySelectorAll('.tab-panel'),
  paperSubject: document.getElementById('paperSubject'),
  paperSemester: document.getElementById('paperSemester'),
  paperExamType: document.getElementById('paperExamType'),
  paperTotalMarks: document.getElementById('paperTotalMarks'),
  paperQuestionRows: document.getElementById('paperQuestionRows'),
  addQuestionBtn: document.getElementById('addQuestionBtn'),
  submitPaperBtn: document.getElementById('submitPaperBtn'),
  paperStatus: document.getElementById('paperStatus'),
  authUsername: document.getElementById('authUsername'),
  openAuthBtn: document.getElementById('openAuthBtn'),
  logoutBtn: document.getElementById('logoutBtn'),
  authDialog: document.getElementById('authDialog'),
  authForm: document.getElementById('authForm'),
  authTitle: document.getElementById('authTitle'),
  authUsernameInput: document.getElementById('authUsernameInput'),
  authPasswordInput: document.getElementById('authPasswordInput'),
  authSubmitBtn: document.getElementById('authSubmitBtn'),
  authModeToggle: document.getElementById('authModeToggle'),
  closeAuthBtn: document.getElementById('closeAuthBtn'),
  authStatus: document.getElementById('authStatus'),
  paperAuthNotice: document.getElementById('paperAuthNotice'),
  paperAuthBtn: document.getElementById('paperAuthBtn')
};

let authMode = 'login';

function setActiveTab(tabName) {
  els.tabButtons.forEach((button) => {
    button.classList.toggle('active', button.dataset.tab === tabName);
  });

  els.tabPanels.forEach((panel) => {
    panel.classList.toggle('active', panel.id === `${tabName}-panel`);
  });
}

els.tabButtons.forEach((button) => {
  button.addEventListener('click', () => setActiveTab(button.dataset.tab));
});

async function apiFetch(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    let message = text || `Request failed: ${response.status}`;
    try {
      const errorBody = JSON.parse(text);
      if (typeof errorBody.detail === 'string') {
        message = errorBody.detail;
      }
    } catch {
      // Keep the response text when it is not JSON.
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

function updateAuthControls() {
  const isLoggedIn = Boolean(state.user);
  els.authUsername.hidden = !isLoggedIn;
  els.authUsername.textContent = isLoggedIn ? state.user.username : '';
  els.openAuthBtn.hidden = isLoggedIn;
  els.logoutBtn.hidden = !isLoggedIn;
  els.paperAuthNotice.hidden = isLoggedIn;
}

function openAuthDialog(mode = 'login', message = '') {
  authMode = mode;
  const isRegister = authMode === 'register';
  els.authTitle.textContent = isRegister ? 'Create account' : 'Log in';
  els.authSubmitBtn.textContent = isRegister ? 'Register' : 'Log in';
  els.authModeToggle.textContent = isRegister ? 'Already have an account? Log in' : 'Create an account';
  els.authPasswordInput.autocomplete = isRegister ? 'new-password' : 'current-password';
  els.authStatus.textContent = message;
  els.authStatus.className = `status-message ${message ? 'error' : ''}`;
  if (!els.authDialog.open) {
    els.authDialog.showModal();
  }
}

async function loadAuthState() {
  try {
    state.user = await apiFetch('/api/v1/auth/me');
  } catch (error) {
    if (error.status !== 401) {
      console.error(error);
    }
    state.user = null;
  }
  updateAuthControls();
}

els.openAuthBtn.addEventListener('click', () => openAuthDialog());
els.paperAuthBtn.addEventListener('click', () => openAuthDialog());
els.closeAuthBtn.addEventListener('click', () => els.authDialog.close());
els.authModeToggle.addEventListener('click', () => {
  openAuthDialog(authMode === 'login' ? 'register' : 'login');
});

els.authForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const isRegister = authMode === 'register';
  try {
    state.user = await apiFetch(`/api/v1/auth/${isRegister ? 'register' : 'login'}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: els.authUsernameInput.value,
        password: els.authPasswordInput.value
      })
    });
    updateAuthControls();
    els.authDialog.close();
    els.authForm.reset();
  } catch (error) {
    console.error(error);
    els.authStatus.textContent = error.message || 'Unable to authenticate.';
    els.authStatus.className = 'status-message error';
  }
});

els.logoutBtn.addEventListener('click', async () => {
  try {
    await apiFetch('/api/v1/auth/logout', { method: 'POST' });
    state.user = null;
    updateAuthControls();
  } catch (error) {
    console.error(error);
  }
});

function setLoadingState(message) {
  els.questionsList.innerHTML = `<div class="empty-state">${message}</div>`;
}

function renderStats(data) {
  const totals = data.totals || {};
  const cards = [
    { label: 'Papers', value: totals.papers ?? 0 },
    { label: 'Questions', value: totals.questions ?? 0 },
    { label: 'Subjects', value: totals.subjects ?? 0 },
    { label: 'Semesters', value: totals.semesters ?? 0 }
  ];

  els.statsGrid.innerHTML = cards
    .map(
      (card) => `
        <div class="stat-card">
          <div class="label">${card.label}</div>
          <div class="value">${card.value}</div>
        </div>
      `
    )
    .join('');
}

function renderQuestionTypes(items) {
  const max = Math.max(...items.map((item) => item.count), 1);
  els.questionTypesChart.innerHTML = items.length
    ? items
        .map(
          (item) => `
            <div>
              <div class="chart-row">
                <span>${item.type_name}</span>
                <strong>${item.count}</strong>
              </div>
              <div class="bar"><span style="width:${(item.count / max) * 100}%"></span></div>
            </div>
          `
        )
        .join('')
    : '<div class="empty-state">No question-type data available.</div>';
}

function renderTopics(items) {
  const max = Math.max(...items.map((item) => item.count), 1);
  els.topicsChart.innerHTML = items.length
    ? items
        .map(
          (item) => `
            <div>
              <div class="chart-row">
                <span>${item.topic_name}</span>
                <strong>${item.count}</strong>
              </div>
              <div class="bar"><span style="width:${(item.count / max) * 100}%"></span></div>
            </div>
          `
        )
        .join('')
    : '<div class="empty-state">No topic data available.</div>';
}

function renderSemesterComparison(entries) {
  if (!entries.length) {
    els.semesterComparison.innerHTML = '<div class="empty-state">No semester comparison data available.</div>';
    return;
  }

  els.semesterComparison.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Subject</th>
          <th>Semester</th>
          <th>Academic Year</th>
          <th>Questions</th>
          <th>Total Marks</th>
        </tr>
      </thead>
      <tbody>
        ${entries
          .map(
            (entry) => `
              <tr>
                <td>${entry.subject_name}</td>
                <td>${entry.semester_number}</td>
                <td>${entry.academic_year}</td>
                <td>${entry.question_count}</td>
                <td>${entry.total_marks}</td>
              </tr>
            `
          )
          .join('')}
      </tbody>
    </table>
  `;
}

function renderQuestions(items) {
  if (!items.length) {
    els.questionsList.innerHTML = '<div class="empty-state">No questions match the current filters.</div>';
    return;
  }

  els.questionsList.innerHTML = items
    .map(
      (item) => `
        <article class="question-card">
          <h3>${item.question_text}</h3>
          <div class="meta">
            <span>${item.subject_name}</span>
            <span>•</span>
            <span>${item.exam_type}</span>
            <span>•</span>
            <span>Sem ${item.semester_number}</span>
            <span>•</span>
            <span>${item.question_type}</span>
            <span>•</span>
            <span>${item.marks} marks</span>
          </div>
          <div class="topic-tags">
            ${item.topics.length ? item.topics.map((topic) => `<span class="topic-tag">${topic}</span>`).join('') : '<span class="topic-tag">No topic tags</span>'}
          </div>
        </article>
      `
    )
    .join('');
}

function renderSimilarQuestions(items) {
  if (!items.length) {
    els.similarQuestionsList.innerHTML = '<div class="empty-state">No similar questions found.</div>';
    return;
  }

  els.similarQuestionsList.innerHTML = items
    .map(
      (item) => `
        <article class="question-card">
          <h3>${item.question_text}</h3>
          <div class="meta">
            <span>Question #${item.question_id}</span>
          </div>
          <span class="similarity-score">Similarity: ${item.similarity_score}</span>
        </article>
      `
    )
    .join('');
}

function renderPaperQuestionRows() {
  if (!state.paperRows.length) {
    state.paperRows = [{ question_number: '1', marks: 10, question_text: '', question_type_id: '', topic_ids: [] }];
  }

  els.paperQuestionRows.innerHTML = state.paperRows
    .map(
      (row, index) => `
        <div class="paper-question-row">
          <div class="paper-row-grid">
            <label>
              Question no.
              <input class="paper-question-number" data-index="${index}" type="text" value="${row.question_number}" />
            </label>
            <label>
              Marks
              <input class="paper-question-marks" data-index="${index}" type="number" min="1" value="${row.marks}" />
            </label>
            <label>
              Type
              <select class="paper-question-type" data-index="${index}">
                <option value="">Select type</option>
                ${state.questionTypes
                  .map(
                    (type) =>
                      `<option value="${type.type_id}" ${String(type.type_id) === String(row.question_type_id) ? 'selected' : ''}>${type.type_name}</option>`
                  )
                  .join('')}
              </select>
            </label>
          </div>
          <label>
            Question text
            <textarea class="paper-question-text" data-index="${index}" rows="3" placeholder="Type the question text...">${row.question_text}</textarea>
          </label>
          <label>
            Topic(s)
            <select class="paper-question-topics" data-index="${index}" multiple size="5">
              ${state.topics
                .map(
                  (topic) =>
                    `<option value="${topic.topic_id}" ${row.topic_ids.includes(topic.topic_id) ? 'selected' : ''}>${topic.topic_name}</option>`
                )
                .join('')}
            </select>
          </label>
          <button type="button" class="remove-question" data-index="${index}">Remove question</button>
        </div>
      `
    )
    .join('');
}

function syncPaperQuestionRow(event) {
  const input = event.target;
  const index = Number(input.dataset.index);
  if (!Number.isInteger(index) || index < 0 || index >= state.paperRows.length) {
    return;
  }

  const row = state.paperRows[index];
  if (input.matches('.paper-question-number')) {
    row.question_number = input.value;
  } else if (input.matches('.paper-question-marks')) {
    row.marks = Number(input.value);
  } else if (input.matches('.paper-question-text')) {
    row.question_text = input.value;
  } else if (input.matches('.paper-question-type')) {
    row.question_type_id = input.value ? Number(input.value) : '';
  } else if (input.matches('.paper-question-topics')) {
    row.topic_ids = Array.from(input.selectedOptions, (option) => Number(option.value));
  }
}

function showPaperStatus(message, isError = false) {
  els.paperStatus.textContent = message;
  els.paperStatus.className = `status-message ${isError ? 'error' : 'success'}`;
}

async function searchSimilarQuestions() {
  const query = (els.semanticQueryInput.value || '').trim();
  if (!query) {
    els.similarQuestionsList.innerHTML = '<div class="empty-state">Enter a question or concept to find similar items.</div>';
    return;
  }

  try {
    const items = await apiFetch(`/api/v1/semantic/similar?q=${encodeURIComponent(query)}&limit=5`);
    renderSimilarQuestions(items);
  } catch (error) {
    console.error(error);
    els.similarQuestionsList.innerHTML = '<div class="empty-state">Unable to load semantic matches.</div>';
  }
}

async function fetchCatalogData() {
  const [subjects, semesters, questionTypes, topics] = await Promise.all([
    apiFetch('/api/v1/catalog/subjects'),
    apiFetch('/api/v1/catalog/semesters'),
    apiFetch('/api/v1/catalog/question-types'),
    apiFetch('/api/v1/catalog/topics')
  ]);

  state.subjects = subjects;
  state.semesters = semesters;
  state.questionTypes = questionTypes;
  state.topics = topics;

  els.subjectFilter.innerHTML = '<option value="">All subjects</option>' +
    subjects.map((s) => `<option value="${s.subject_id}">${s.subject_name}</option>`).join('');

  els.semesterFilter.innerHTML = '<option value="">All semesters</option>' +
    semesters.map((s) => `<option value="${s.semester_id}">Sem ${s.semester_number} (${s.academic_year})</option>`).join('');

  els.paperSubject.innerHTML = '<option value="">Choose subject</option>' +
    subjects.map((s) => `<option value="${s.subject_id}">${s.subject_name}</option>`).join('');

  els.paperSemester.innerHTML = '<option value="">Choose semester</option>' +
    semesters.map((s) => `<option value="${s.semester_id}">Sem ${s.semester_number} (${s.academic_year})</option>`).join('');

  renderPaperQuestionRows();
}

async function loadOverview() {
  const params = new URLSearchParams();
  if (state.filters.subject_id) params.append('subject_id', state.filters.subject_id);
  if (state.filters.semester_id) params.append('semester_id', state.filters.semester_id);
  if (state.filters.exam_type) params.append('exam_type', state.filters.exam_type);

  const data = await apiFetch(`/api/v1/analytics/overview?${params.toString()}`);
  renderStats(data);
  renderQuestionTypes(data.question_types || []);
  renderTopics(data.topics || []);
}

async function loadComparison() {
  const params = new URLSearchParams();
  if (state.filters.subject_id) params.append('subject_id', state.filters.subject_id);
  const compare = await apiFetch(`/api/v1/analytics/compare?${params.toString()}`);
  renderSemesterComparison(compare);
}

async function loadQuestions() {
  const params = new URLSearchParams();
  if (state.filters.q) params.append('q', state.filters.q);
  if (state.filters.subject_id) params.append('subject_id', state.filters.subject_id);
  if (state.filters.semester_id) params.append('semester_id', state.filters.semester_id);
  if (state.filters.exam_type) params.append('exam_type', state.filters.exam_type);
  params.append('limit', '20');

  setLoadingState('Loading questions...');
  const items = await apiFetch(`/api/v1/search/questions?${params.toString()}`);
  renderQuestions(items);
}

async function refreshData() {
  try {
    await Promise.all([loadOverview(), loadComparison(), loadQuestions()]);
  } catch (error) {
    console.error(error);
    setLoadingState('Unable to load data from the API.');
  }
}

function createPaperPayload() {
  const subjectId = Number(els.paperSubject.value);
  const semesterId = Number(els.paperSemester.value);
  const examType = els.paperExamType.value;
  const totalMarks = Number(els.paperTotalMarks.value);

  const questions = Array.from(els.paperQuestionRows.querySelectorAll('.paper-question-row')).map((row) => {
    const questionNumber = row.querySelector('.paper-question-number').value.trim();
    const marks = Number(row.querySelector('.paper-question-marks').value);
    const questionText = row.querySelector('.paper-question-text').value.trim();
    const typeId = Number(row.querySelector('.paper-question-type').value);
    const topicIds = Array.from(row.querySelectorAll('.paper-question-topics option:checked')).map((option) => Number(option.value));

    return {
      question_number: questionNumber,
      marks,
      question_text: questionText,
      question_type_id: typeId,
      topic_ids: topicIds
    };
  }).filter((question) =>
    question.question_number &&
    Number.isInteger(question.marks) &&
    question.marks > 0 &&
    question.question_text &&
    Number.isInteger(question.question_type_id) &&
    question.question_type_id > 0
  );

  return {
    subject_id: subjectId,
    semester_id: semesterId,
    exam_type: examType,
    total_marks: totalMarks,
    questions
  };
}

async function submitPaper() {
  if (!state.user) {
    openAuthDialog('login', 'Log in or register before creating a paper.');
    return;
  }

  const payload = createPaperPayload();

  if (!payload.subject_id || !payload.semester_id || !payload.exam_type || !payload.total_marks || !payload.questions.length) {
    showPaperStatus('Please fill in the subject, semester, exam type, total marks, and at least one valid question.', true);
    return;
  }

  try {
    const createdPaper = await apiFetch('/api/v1/papers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    showPaperStatus(`Paper created successfully with ID ${createdPaper.paper_id}.`);
    state.paperRows = [{ question_number: '1', marks: 10, question_text: '', question_type_id: '', topic_ids: [] }];
    renderPaperQuestionRows();
    els.paperSubject.value = '';
    els.paperSemester.value = '';
    els.paperExamType.value = 'End';
    els.paperTotalMarks.value = '';
    await refreshData();
  } catch (error) {
    console.error(error);
    showPaperStatus(error.message || 'Failed to create paper.', true);
  }
}

els.applyFilters.addEventListener('click', () => {
  state.filters.q = els.searchInput.value.trim();
  state.filters.subject_id = els.subjectFilter.value;
  state.filters.semester_id = els.semesterFilter.value;
  state.filters.exam_type = els.examTypeFilter.value;
  refreshData();
});

els.semanticSearchBtn.addEventListener('click', searchSimilarQuestions);
els.semanticQueryInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    searchSimilarQuestions();
  }
});

els.addQuestionBtn.addEventListener('click', () => {
  if (!state.user) {
    openAuthDialog('login', 'Log in or register before adding questions.');
    return;
  }
  const nextNumber = state.paperRows.length + 1;
  state.paperRows.push({ question_number: String(nextNumber), marks: 10, question_text: '', question_type_id: '', topic_ids: [] });
  renderPaperQuestionRows();
});

els.paperQuestionRows.addEventListener('input', syncPaperQuestionRow);
els.paperQuestionRows.addEventListener('change', syncPaperQuestionRow);

els.paperQuestionRows.addEventListener('click', (event) => {
  const button = event.target.closest('.remove-question');
  if (!button) {
    return;
  }

  const index = Number(button.dataset.index);
  if (state.paperRows.length === 1) {
    state.paperRows = [{ question_number: '1', marks: 10, question_text: '', question_type_id: '', topic_ids: [] }];
    renderPaperQuestionRows();
    return;
  }

  state.paperRows.splice(index, 1);
  state.paperRows = state.paperRows.map((row, rowIndex) => ({ ...row, question_number: String(rowIndex + 1) }));
  renderPaperQuestionRows();
});

els.submitPaperBtn.addEventListener('click', submitPaper);

async function init() {
  await loadAuthState();
  await fetchCatalogData();
  await refreshData();
  if (els.semanticQueryInput.value.trim() === '') {
    els.semanticQueryInput.value = 'Explain database normalization';
    await searchSimilarQuestions();
  }
  setActiveTab('overview');
}

init();
