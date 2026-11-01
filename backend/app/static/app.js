const state = {
  subjects: [],
  semesters: [],
  units: [],
  topics: [],
  questionTypes: [],
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

const resourceMap = {
  subjects: '/api/v1/catalog/subjects',
  semesters: '/api/v1/catalog/semesters',
  units: '/api/v1/catalog/units',
  topics: '/api/v1/catalog/topics',
  'question-types': '/api/v1/catalog/question-types'
};

const pkMap = {
  subjects: 'subject_id',
  semesters: 'semester_id',
  units: 'unit_id',
  topics: 'topic_id',
  'question-types': 'type_id'
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
  subjectPerformance: document.getElementById('subjectPerformance'),
  semanticQueryInput: document.getElementById('semanticQueryInput'),
  semanticSearchBtn: document.getElementById('semanticSearchBtn'),
  similarQuestionsList: document.getElementById('similarQuestionsList'),
  tabButtons: document.querySelectorAll('.tab-button'),
  tabPanels: document.querySelectorAll('.tab-panel'),
  catalogManager: document.getElementById('catalogManager'),
  importText: document.getElementById('importText'),
  importStatus: document.getElementById('importStatus'),
  importSampleBtn: document.getElementById('importSampleBtn'),
  importSubmitBtn: document.getElementById('importSubmitBtn'),
  paperSubject: document.getElementById('paperSubject'),
  paperSemester: document.getElementById('paperSemester'),
  paperExamType: document.getElementById('paperExamType'),
  paperTotalMarks: document.getElementById('paperTotalMarks'),
  paperQuestionRows: document.getElementById('paperQuestionRows'),
  addQuestionBtn: document.getElementById('addQuestionBtn'),
  submitPaperBtn: document.getElementById('submitPaperBtn'),
  paperStatus: document.getElementById('paperStatus')
};

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
    throw new Error(text || `Request failed: ${response.status}`);
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

function renderSubjectPerformance(entries) {
  if (!entries.length) {
    els.subjectPerformance.innerHTML = '<div class="empty-state">No subject performance data available.</div>';
    return;
  }

  els.subjectPerformance.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Subject</th>
          <th>Semester</th>
          <th>Year</th>
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
  const [subjects, semesters, units, topics, questionTypes] = await Promise.all([
    apiFetch('/api/v1/catalog/subjects'),
    apiFetch('/api/v1/catalog/semesters'),
    apiFetch('/api/v1/catalog/units'),
    apiFetch('/api/v1/catalog/topics'),
    apiFetch('/api/v1/catalog/question-types')
  ]);

  state.subjects = subjects;
  state.semesters = semesters;
  state.units = units;
  state.topics = topics;
  state.questionTypes = questionTypes;

  els.subjectFilter.innerHTML = '<option value="">All subjects</option>' +
    subjects.map((s) => `<option value="${s.subject_id}">${s.subject_name}</option>`).join('');

  els.semesterFilter.innerHTML = '<option value="">All semesters</option>' +
    semesters.map((s) => `<option value="${s.semester_id}">Sem ${s.semester_number} (${s.academic_year})</option>`).join('');

  els.paperSubject.innerHTML = '<option value="">Choose subject</option>' +
    subjects.map((s) => `<option value="${s.subject_id}">${s.subject_name}</option>`).join('');

  els.paperSemester.innerHTML = '<option value="">Choose semester</option>' +
    semesters.map((s) => `<option value="${s.semester_id}">Sem ${s.semester_number} (${s.academic_year})</option>`).join('');

  renderPaperQuestionRows();
  renderCatalogManager();
}

function renderCatalogManager() {
  const sections = [
    {
      kind: 'subjects',
      title: 'Subjects',
      primaryKey: 'subject_id',
      label: 'Subject',
      fields: [
        { name: 'subject_code', label: 'Code', type: 'text' },
        { name: 'subject_name', label: 'Name', type: 'text' },
        { name: 'department', label: 'Department', type: 'text' }
      ],
      items: state.subjects
    },
    {
      kind: 'semesters',
      title: 'Semesters',
      primaryKey: 'semester_id',
      label: 'Semester',
      fields: [
        { name: 'semester_number', label: 'Number', type: 'number' },
        { name: 'academic_year', label: 'Academic year', type: 'text' }
      ],
      items: state.semesters
    },
    {
      kind: 'units',
      title: 'Units',
      primaryKey: 'unit_id',
      label: 'Unit',
      fields: [
        { name: 'subject_id', label: 'Subject', type: 'select', options: state.subjects },
        { name: 'unit_number', label: 'Unit number', type: 'number' },
        { name: 'unit_name', label: 'Unit name', type: 'text' }
      ],
      items: state.units
    },
    {
      kind: 'topics',
      title: 'Topics',
      primaryKey: 'topic_id',
      label: 'Topic',
      fields: [
        { name: 'unit_id', label: 'Unit', type: 'select', options: state.units },
        { name: 'topic_name', label: 'Topic name', type: 'text' }
      ],
      items: state.topics
    },
    {
      kind: 'question-types',
      title: 'Question types',
      primaryKey: 'type_id',
      label: 'Question type',
      fields: [{ name: 'type_name', label: 'Type name', type: 'text' }],
      items: state.questionTypes
    }
  ];

  els.catalogManager.innerHTML = sections
    .map((section) => {
      const rows = section.items.length
        ? section.items
            .map(
              (item) => `
                <tr>
                  <td>${section.kind === 'subjects' ? item.subject_code : section.kind === 'semesters' ? `Sem ${item.semester_number}` : section.kind === 'units' ? item.unit_name : section.kind === 'topics' ? item.topic_name : item.type_name}</td>
                  <td>${section.kind === 'subjects' ? item.subject_name : section.kind === 'semesters' ? item.academic_year : section.kind === 'units' ? `${item.unit_number}` : section.kind === 'topics' ? (state.units.find((unit) => unit.unit_id === item.unit_id)?.unit_name ?? '—') : '—'}</td>
                  <td class="catalog-actions">
                    <button type="button" class="secondary-btn small" data-action="edit" data-kind="${section.kind}" data-id="${item[section.primaryKey]}">Edit</button>
                    <button type="button" class="danger-btn small" data-action="delete" data-kind="${section.kind}" data-id="${item[section.primaryKey]}">Delete</button>
                  </td>
                </tr>
              `
            )
            .join('')
        : '<tr><td colspan="3" class="muted-cell">No records yet.</td></tr>';

      const fieldsMarkup = section.fields
        .map((field) => {
          if (field.type === 'select') {
            const options = (field.options || [])
              .map((option) => {
                const value = option.subject_id ?? option.unit_id ?? option.type_id ?? option.semester_id;
                const label = option.subject_name ?? option.unit_name ?? option.type_name ?? `Sem ${option.semester_number} (${option.academic_year})`;
                return `<option value="${value}">${label}</option>`;
              })
              .join('');
            return `
              <label>
                ${field.label}
                <select name="${field.name}">
                  <option value="">Select ${field.label}</option>
                  ${options}
                </select>
              </label>
            `;
          }
          return `
            <label>
              ${field.label}
              <input type="${field.type}" name="${field.name}" />
            </label>
          `;
        })
        .join('');

      return `
        <div class="catalog-card">
          <div class="catalog-header">
            <h3>${section.title}</h3>
          </div>

          <div class="catalog-list-wrapper">
            <table class="catalog-table">
              <thead>
                <tr>
                  <th>Key</th>
                  <th>Value</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>

          <form class="catalog-form" data-kind="${section.kind}">
            <div class="catalog-form-grid">${fieldsMarkup}</div>
            <div class="catalog-form-actions">
              <button type="submit">Add ${section.label}</button>
            </div>
          </form>
        </div>
      `;
    })
    .join('');

  els.catalogManager.querySelectorAll('.catalog-form').forEach((form) => {
    form.addEventListener('submit', handleCatalogSubmit);
  });

  els.catalogManager.querySelectorAll('[data-action]').forEach((button) => {
    button.addEventListener('click', (event) => {
      const action = event.target.dataset.action;
      const kind = event.target.dataset.kind;
      const id = event.target.dataset.id;
      if (action === 'delete') {
        deleteCatalogRecord(kind, Number(id));
      }
      if (action === 'edit') {
        const item = state[kind.replace('-types', 'questionTypes')? 'question-types' : kind]?.find((entry) => String(entry[pkMap[kind] || Object.keys(entry)[0]]) === String(id));
        if (item) {
          populateCatalogForm(kind, item);
        }
      }
    });
  });
}

function populateCatalogForm(kind, item) {
  const form = document.querySelector(`.catalog-form[data-kind="${kind}"]`);
  if (!form) return;

  form.dataset.id = item[pkMap[kind]];
  form.querySelectorAll('[name]').forEach((input) => {
    const fieldName = input.name;
    const value = item[fieldName];
    if (input.tagName === 'SELECT') {
      input.value = value ?? '';
    } else {
      input.value = value ?? '';
    }
  });

  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.textContent = 'Update';
}

async function handleCatalogSubmit(event) {
  event.preventDefault();
  const form = event.target.closest('.catalog-form');
  if (!form) return;

  const kind = form.dataset.kind;
  const endpoint = resourceMap[kind];
  const id = form.dataset.id;
  const payload = {};

  form.querySelectorAll('[name]').forEach((field) => {
    const name = field.name;
    const rawValue = field.value;

    if (field.tagName === 'SELECT' && rawValue === '') {
      return;
    }

    if (rawValue === '') {
      payload[name] = kind === 'subjects' && name === 'department' ? null : rawValue;
      return;
    }

    if (['semester_number', 'unit_number', 'subject_id', 'unit_id', 'type_id', 'question_type_id'].includes(name)) {
      payload[name] = Number(rawValue);
      return;
    }

    if (name === 'department' && rawValue.trim() === '') {
      payload[name] = null;
      return;
    }

    payload[name] = rawValue.trim();
  });

  try {
    const url = id ? `${endpoint}/${id}` : endpoint;
    const method = id ? 'PUT' : 'POST';

    await apiFetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    form.dataset.id = '';
    form.reset();
    form.querySelector('button[type="submit"]').textContent = `Add ${kind === 'question-types' ? 'Question type' : kind.slice(0, -1)}`;
    await fetchCatalogData();
  } catch (error) {
    console.error(error);
    showCatalogMessage(kind, error.message || 'Failed to save catalog entry.', true);
  }
}

function showCatalogMessage(kind, message, isError = false) {
  const form = document.querySelector(`.catalog-form[data-kind="${kind}"]`);
  if (!form) return;
  const status = document.createElement('div');
  status.className = `catalog-status ${isError ? 'error' : 'success'}`;
  status.textContent = message;
  const existing = form.querySelector('.catalog-status');
  if (existing) existing.remove();
  form.appendChild(status);
}

async function deleteCatalogRecord(kind, id) {
  const endpoint = `${resourceMap[kind]}/${id}`;
  try {
    await apiFetch(endpoint, { method: 'DELETE' });
    await fetchCatalogData();
  } catch (error) {
    console.error(error);
    showCatalogMessage(kind, error.message || 'Failed to delete record.', true);
  }
}

function splitCsvishLine(line, delimiter) {
  const values = [];
  let token = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        token += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === delimiter && !inQuotes) {
      values.push(token.trim());
      token = '';
    } else {
      token += char;
    }
  }

  values.push(token.trim());
  return values.map((value) => value.replace(/^"|"$/g, '').trim());
}

function parseImportText(rawText) {
  const text = rawText.trim();
  if (!text) {
    throw new Error('Paste import data before submitting.');
  }

  if (text.startsWith('{') || text.startsWith('[')) {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) {
      return { papers: parsed };
    }
    if (parsed && Array.isArray(parsed.papers)) {
      return parsed;
    }
    throw new Error('JSON import must be an array of paper objects or an object with a papers array.');
  }

  const delimiter = text.includes(';') ? ';' : ',';
  const lines = text.split(/\r?\n/).filter((line) => line.trim() && !line.trim().startsWith('#'));
  if (!lines.length) {
    throw new Error('No valid rows found in the pasted data.');
  }

  const grouped = new Map();

  for (const line of lines) {
    const values = splitCsvishLine(line, delimiter);
    if (values.length < 12) {
      throw new Error('Each CSV row must include: subject_code, subject_name, semester_number, academic_year, exam_type, total_marks, question_number, marks, question_text, question_type, topic_name, unit_name');
    }

    const [
      subjectCode,
      subjectName,
      semesterNumber,
      academicYear,
      examType,
      totalMarks,
      questionNumber,
      marks,
      questionText,
      questionType,
      topicName,
      unitName
    ] = values;

    const key = `${subjectCode || subjectName}|${subjectName || subjectCode}|${semesterNumber}|${academicYear}|${examType}|${totalMarks}`;
    if (!grouped.has(key)) {
      grouped.set(key, {
        subject_code: subjectCode || subjectName || 'SUBJ',
        subject_name: subjectName || subjectCode || 'Imported Subject',
        semester_number: Number(semesterNumber) || 1,
        academic_year: academicYear || '2026-2027',
        exam_type: examType || 'End',
        total_marks: Number(totalMarks) || 0,
        questions: []
      });
    }

    grouped.get(key).questions.push({
      question_number: questionNumber,
      marks: Number(marks) || 1,
      question_text: questionText,
      question_type: questionType || 'Short Answer',
      topic_name: topicName || 'General',
      unit_name: unitName || 'General'
    });
  }

  return { papers: Array.from(grouped.values()) };
}

async function submitBulkImport() {
  const rawText = els.importText.value;
  try {
    const payload = parseImportText(rawText);
    const result = await apiFetch('/api/v1/papers/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    els.importStatus.innerHTML = `<span class="status-good">Imported ${result.created_papers} paper(s) and ${result.created_questions} question(s).</span>`;
    await fetchCatalogData();
    await refreshData();
  } catch (error) {
    console.error(error);
    els.importStatus.innerHTML = `<span class="status-bad">${error.message}</span>`;
  }
}

function loadSampleImport() {
  els.importText.value = `DBMS,Database Systems,5,2026-2027,End,20,1,10,Explain normalization and its dependency types,Long Answer,Normalization,Relational Databases
DBMS,Database Systems,5,2026-2027,End,20,2,10,Define ACID properties in transactions,Short Answer,Transactions,Transaction Processing`;
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

  const performance = await apiFetch(`/api/v1/analytics/subject-performance?${params.toString()}`);
  renderSubjectPerformance(performance);
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

  const questions = Array.from(els.paperQuestionRows.querySelectorAll('.paper-question-row'))
    .map((row) => {
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
    })
    .filter((question) => {
      return (
        question.question_number &&
        Number.isInteger(question.marks) &&
        question.marks > 0 &&
        question.question_text &&
        Number.isInteger(question.question_type_id) &&
        question.question_type_id > 0
      );
    });

  return {
    subject_id: subjectId,
    semester_id: semesterId,
    exam_type: examType,
    total_marks: totalMarks,
    questions
  };
}

async function submitPaper() {
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
els.importSubmitBtn.addEventListener('click', submitBulkImport);
els.importSampleBtn.addEventListener('click', loadSampleImport);

async function init() {
  await fetchCatalogData();
  await refreshData();
  if (els.semanticQueryInput.value.trim() === '') {
    els.semanticQueryInput.value = 'Explain database normalization';
    await searchSimilarQuestions();
  }
  setActiveTab('overview');
}

init();
