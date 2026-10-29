const state = {
  subjects: [],
  semesters: [],
  filters: {
    q: '',
    subject_id: '',
    semester_id: '',
    exam_type: ''
  }
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
  similarQuestionsList: document.getElementById('similarQuestionsList')
};

async function apiFetch(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

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
  const [subjects, semesters] = await Promise.all([
    apiFetch('/api/v1/catalog/subjects'),
    apiFetch('/api/v1/catalog/semesters')
  ]);

  state.subjects = subjects;
  state.semesters = semesters;

  els.subjectFilter.innerHTML = '<option value="">All subjects</option>' +
    subjects.map((s) => `<option value="${s.subject_id}">${s.subject_name}</option>`).join('');

  els.semesterFilter.innerHTML = '<option value="">All semesters</option>' +
    semesters.map((s) => `<option value="${s.semester_id}">Sem ${s.semester_number} (${s.academic_year})</option>`).join('');
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

async function init() {
  await fetchCatalogData();
  await refreshData();
  if (els.semanticQueryInput.value.trim() === '') {
    els.semanticQueryInput.value = 'Explain database normalization';
    await searchSimilarQuestions();
  }
}

init();
