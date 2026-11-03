"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, apiFetch } from "../lib/api.js";

const EMPTY_QUESTION = {
  question_number: "1",
  marks: "10",
  question_text: "",
  question_type_id: "",
  topic_ids: []
};

const EXAM_TYPES = ["Internal", "Mid", "End", "Supplementary"];
const EMPTY_FILTERS = Object.freeze({ q: "", subject_id: "", semester_id: "", exam_type: "" });

function buildQuery(filters, includeQuestion = false) {
  const params = new URLSearchParams();
  if (filters.subject_id) params.set("subject_id", filters.subject_id);
  if (filters.semester_id) params.set("semester_id", filters.semester_id);
  if (filters.exam_type) params.set("exam_type", filters.exam_type);
  if (includeQuestion && filters.q.trim()) params.set("q", filters.q.trim());
  return params.toString();
}

function EmptyState({ children }) {
  return <div className="empty-state">{children}</div>;
}

function BarList({ items, labelKey, valueKey, emptyMessage }) {
  const maximum = Math.max(...items.map((item) => Number(item[valueKey]) || 0), 1);
  if (!items.length) return <EmptyState>{emptyMessage}</EmptyState>;

  return (
    <div className="chart-list">
      {items.map((item, index) => {
        const value = Number(item[valueKey]) || 0;
        return (
          <div key={`${item[labelKey]}-${index}`}>
            <div className="chart-row">
              <span>{item[labelKey]}</span>
              <strong>{value}</strong>
            </div>
            <div className="bar" aria-label={`${item[labelKey]}: ${value}`}>
              <span style={{ width: `${(value / maximum) * 100}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function QuestionCards({ items }) {
  if (!items.length) {
    return <EmptyState>No questions match the current filters.</EmptyState>;
  }

  return (
    <div className="questions-list">
      {items.map((question) => (
        <article className="question-card" key={`${question.paper_id}-${question.question_id}`}>
          <h3>{question.question_text}</h3>
          <div className="meta">
            <span>{question.subject_name}</span>
            <span aria-hidden="true">•</span>
            <span>{question.exam_type}</span>
            <span aria-hidden="true">•</span>
            <span>Sem {question.semester_number}</span>
            <span aria-hidden="true">•</span>
            <span>{question.question_type}</span>
            <span aria-hidden="true">•</span>
            <span>{question.marks} marks</span>
          </div>
          <div className="topic-tags">
            {question.topics?.length
              ? question.topics.map((topic) => <span className="topic-tag" key={topic}>{topic}</span>)
              : <span className="topic-tag">No topic tags</span>}
          </div>
        </article>
      ))}
    </div>
  );
}

function PaperQuestionEditor({ question, index, questionTypes, topics, onChange, onRemove }) {
  function update(field, value) {
    onChange(index, { ...question, [field]: value });
  }

  return (
    <div className="paper-question-row">
      <div className="paper-row-grid">
        <label>
          Question no.
          <input
            required
            maxLength={10}
            value={question.question_number}
            onChange={(event) => update("question_number", event.target.value)}
          />
        </label>
        <label>
          Marks
          <input
            required
            type="number"
            min="1"
            value={question.marks}
            onChange={(event) => update("marks", event.target.value)}
          />
        </label>
        <label>
          Type
          <select
            required
            value={question.question_type_id}
            onChange={(event) => update("question_type_id", event.target.value)}
          >
            <option value="">Select type</option>
            {questionTypes.map((type) => (
              <option value={type.type_id} key={type.type_id}>{type.type_name}</option>
            ))}
          </select>
        </label>
      </div>
      <label>
        Question text
        <textarea
          required
          rows={3}
          value={question.question_text}
          placeholder="Type the question text..."
          onChange={(event) => update("question_text", event.target.value)}
        />
      </label>
      <label>
        Topic(s)
        <select
          multiple
          size={Math.min(Math.max(topics.length, 3), 6)}
          value={question.topic_ids.map(String)}
          onChange={(event) => update(
            "topic_ids",
            Array.from(event.target.selectedOptions, (option) => Number(option.value))
          )}
        >
          {topics.map((topic) => (
            <option value={topic.topic_id} key={topic.topic_id}>{topic.topic_name}</option>
          ))}
        </select>
      </label>
      <button className="secondary-btn remove-question" type="button" onClick={() => onRemove(index)}>
        Remove question
      </button>
    </div>
  );
}

export default function HomePage() {
  const [activeTab, setActiveTab] = useState("overview");
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS });
  const [subjects, setSubjects] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [questionTypes, setQuestionTypes] = useState([]);
  const [topics, setTopics] = useState([]);
  const [overview, setOverview] = useState(null);
  const [comparison, setComparison] = useState([]);
  const [patterns, setPatterns] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [papers, setPapers] = useState([]);
  const [similarQuestions, setSimilarQuestions] = useState([]);
  const [semanticQuery, setSemanticQuery] = useState("");
  const [user, setUser] = useState(null);
  const [pageError, setPageError] = useState("");
  const [semanticError, setSemanticError] = useState("");
  const [paperError, setPaperError] = useState("");
  const [paperStatus, setPaperStatus] = useState("");
  const [paperForm, setPaperForm] = useState({
    paper_id: null,
    subject_id: "",
    semester_id: "",
    exam_type: "End",
    total_marks: "",
    questions: [{ ...EMPTY_QUESTION }]
  });
  const [authMode, setAuthMode] = useState("login");
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const authDialog = useRef(null);

  const subjectNames = useMemo(
    () => new Map(subjects.map((subject) => [subject.subject_id, subject.subject_name])),
    [subjects]
  );
  const semesterNames = useMemo(
    () => new Map(semesters.map((semester) => [
      semester.semester_id,
      `Sem ${semester.semester_number} (${semester.academic_year})`
    ])),
    [semesters]
  );

  const loadOverview = useCallback(async (currentFilters) => {
    const query = buildQuery(currentFilters);
    const suffix = query ? `?${query}` : "";
    const [overviewData, comparisonData, patternData] = await Promise.all([
      apiFetch(`/api/v1/analytics/overview${suffix}`),
      apiFetch(`/api/v1/analytics/compare${currentFilters.subject_id
        ? `?subject_id=${encodeURIComponent(currentFilters.subject_id)}`
        : ""}`),
      apiFetch(`/api/v1/analytics/patterns${suffix}`)
    ]);
    setOverview(overviewData);
    setComparison(comparisonData);
    setPatterns(patternData);
  }, []);

  const loadQuestions = useCallback(async (currentFilters) => {
    const query = buildQuery(currentFilters, true);
    const params = new URLSearchParams(query);
    params.set("limit", "100");
    const results = await apiFetch(`/api/v1/search/questions?${params.toString()}`);
    setQuestions(results);
  }, []);

  const loadPapers = useCallback(async () => {
    const results = await apiFetch("/api/v1/papers");
    setPapers(results);
  }, []);

  const refreshData = useCallback(async (currentFilters) => {
    setPageError("");
    const results = await Promise.allSettled([
      loadOverview(currentFilters),
      loadQuestions(currentFilters),
      loadPapers()
    ]);
    const messages = results
      .filter((result) => result.status === "rejected")
      .map((result) => result.reason?.message || "A section could not be loaded.");
    if (messages.length) setPageError(messages.join(" "));
  }, [loadOverview, loadPapers, loadQuestions]);

  useEffect(() => {
    let active = true;
    async function initialize() {
      const initializationErrors = [];
      const [catalogResult, authResult] = await Promise.allSettled([
        Promise.all([
          apiFetch("/api/v1/catalog/subjects"),
          apiFetch("/api/v1/catalog/semesters"),
          apiFetch("/api/v1/catalog/question-types"),
          apiFetch("/api/v1/catalog/topics")
        ]),
        apiFetch("/api/v1/auth/me")
      ]);
      if (!active) return;
      if (catalogResult.status === "fulfilled") {
        const [subjectList, semesterList, typeList, topicList] = catalogResult.value;
        setSubjects(subjectList);
        setSemesters(semesterList);
        setQuestionTypes(typeList);
        setTopics(topicList);
      } else {
        initializationErrors.push(
          catalogResult.reason?.message || "Unable to load the academic catalog."
        );
      }
      if (authResult.status === "fulfilled") {
        setUser(authResult.value);
      } else if (!(authResult.reason instanceof ApiError && authResult.reason.status === 401)) {
        initializationErrors.push(authResult.reason?.message || "Unable to restore the session.");
      }
      await refreshData(EMPTY_FILTERS);
      if (initializationErrors.length) {
        setPageError((message) => [...(message ? [message] : []), ...initializationErrors].join(" "));
      }
    }

    initialize().catch((error) => {
      if (active) setPageError(error.message || "Unable to load application data.");
    });
    return () => {
      active = false;
    };
  }, [refreshData]);

  function openAuth(mode = "login") {
    setAuthMode(mode);
    setAuthError("");
    if (authDialog.current && !authDialog.current.open) {
      authDialog.current.showModal();
    }
  }

  async function submitAuth(event) {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    const formData = new FormData(event.currentTarget);
    try {
      const signedInUser = await apiFetch(`/api/v1/auth/${authMode}`, {
        method: "POST",
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password")
        })
      });
      setUser(signedInUser);
      authDialog.current?.close();
      event.currentTarget.reset();
    } catch (error) {
      setAuthError(error.message || "Unable to authenticate.");
    } finally {
      setAuthBusy(false);
    }
  }

  async function logout() {
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST" });
      setUser(null);
      setPaperStatus("You have been logged out.");
    } catch (error) {
      setPageError(error.message || "Unable to log out.");
    }
  }

  async function applyFilters(event) {
    event.preventDefault();
    await refreshData(filters);
    setActiveTab("questions");
  }

  async function searchSimilar(event) {
    event.preventDefault();
    const query = semanticQuery.trim();
    if (!query) {
      setSemanticError("Enter a question or concept to search.");
      setSimilarQuestions([]);
      return;
    }
    setSemanticError("");
    try {
      const results = await apiFetch(
        `/api/v1/semantic/similar?q=${encodeURIComponent(query)}&limit=5`
      );
      setSimilarQuestions(results);
    } catch (error) {
      setSimilarQuestions([]);
      setSemanticError(error.message || "Unable to load semantic matches.");
    }
  }

  function resetPaperForm() {
    setPaperForm({
      paper_id: null,
      subject_id: "",
      semester_id: "",
      exam_type: "End",
      total_marks: "",
      questions: [{ ...EMPTY_QUESTION }]
    });
    setPaperStatus("");
    setPaperError("");
  }

  function editPaper(paper) {
    setPaperForm({
      paper_id: paper.paper_id,
      subject_id: String(paper.subject_id),
      semester_id: String(paper.semester_id),
      exam_type: paper.exam_type,
      total_marks: String(paper.total_marks),
      questions: paper.questions.map((question) => ({
        question_number: question.question_number,
        marks: String(question.marks),
        question_text: question.question_text,
        question_type_id: String(question.question_type_id),
        topic_ids: question.topic_ids
      }))
    });
    setPaperStatus("");
    setPaperError("");
    setActiveTab("papers");
  }

  function updateQuestion(index, updatedQuestion) {
    setPaperForm((form) => ({
      ...form,
      questions: form.questions.map((question, currentIndex) =>
        currentIndex === index ? updatedQuestion : question
      )
    }));
  }

  function removeQuestion(index) {
    setPaperForm((form) => ({
      ...form,
      questions: form.questions.filter((_, currentIndex) => currentIndex !== index)
    }));
  }

  async function savePaper(event) {
    event.preventDefault();
    setPaperError("");
    setPaperStatus("");
    if (!user) {
      openAuth("login");
      setPaperError("Log in or register before saving a paper.");
      return;
    }

    const payload = {
      subject_id: Number(paperForm.subject_id),
      semester_id: Number(paperForm.semester_id),
      exam_type: paperForm.exam_type,
      total_marks: Number(paperForm.total_marks),
      questions: paperForm.questions.map((question) => ({
        question_number: question.question_number.trim(),
        marks: Number(question.marks),
        question_text: question.question_text.trim(),
        question_type_id: Number(question.question_type_id),
        topic_ids: question.topic_ids
      }))
    };

    if (
      !payload.subject_id || !payload.semester_id || !payload.total_marks ||
      !payload.questions.length ||
      payload.questions.some((question) =>
        !question.question_number || !question.question_text ||
        !question.question_type_id || question.marks < 1
      )
    ) {
      setPaperError("Complete the paper details and add at least one valid question.");
      return;
    }

    try {
      const isEditing = Boolean(paperForm.paper_id);
      const savedPaper = await apiFetch(
        isEditing ? `/api/v1/papers/${paperForm.paper_id}` : "/api/v1/papers",
        {
          method: isEditing ? "PUT" : "POST",
          body: JSON.stringify(payload)
        }
      );
      resetPaperForm();
      setPaperStatus(`Paper ${savedPaper.paper_id} ${isEditing ? "updated" : "created"} successfully.`);
      await refreshData(filters);
    } catch (error) {
      setPaperError(error.message || "Unable to save the paper.");
    }
  }

  async function deletePaper(paperId) {
    if (!user) {
      openAuth("login");
      return;
    }
    if (!window.confirm(`Delete paper ${paperId}?`)) return;
    setPaperError("");
    try {
      await apiFetch(`/api/v1/papers/${paperId}`, { method: "DELETE" });
      setPaperStatus(`Paper ${paperId} deleted.`);
      await refreshData(filters);
    } catch (error) {
      setPaperError(error.message || "Unable to delete the paper.");
    }
  }

  async function loadPaperForEdit(paperId) {
    setPaperError("");
    try {
      const paper = await apiFetch(`/api/v1/papers/${paperId}`);
      editPaper(paper);
    } catch (error) {
      setPaperError(error.message || "Unable to load the selected paper.");
    }
  }

  const totals = overview?.totals || {};

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">DBMS Project</p>
          <h1>Historical Examination Pattern Analysis</h1>
        </div>
        <nav className="dashboard-tabs" aria-label="Dashboard sections">
          {[
            ["overview", "Overview"],
            ["questions", "Question Search"],
            ["similarity", "Semantic Search"],
            ["papers", "Papers"]
          ].map(([tab, label]) => (
            <button
              className={`tab-button ${activeTab === tab ? "active" : ""}`}
              key={tab}
              type="button"
              aria-current={activeTab === tab ? "page" : undefined}
              onClick={() => setActiveTab(tab)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="auth-controls">
          {user ? (
            <>
              <span>{user.username}</span>
              <button className="secondary-btn" type="button" onClick={logout}>Log out</button>
            </>
          ) : (
            <button className="secondary-btn" type="button" onClick={() => openAuth("login")}>Log in</button>
          )}
        </div>
      </header>

      <dialog
        className="auth-dialog"
        ref={authDialog}
        onClick={(event) => {
          if (event.target === authDialog.current) authDialog.current.close();
        }}
      >
        <form onSubmit={submitAuth}>
          <div className="section-header">
            <h2>{authMode === "register" ? "Create account" : "Log in"}</h2>
            <button
              className="secondary-btn dialog-close"
              type="button"
              aria-label="Close"
              onClick={() => authDialog.current?.close()}
            >
              ×
            </button>
          </div>
          <label>
            Username
            <input name="username" type="text" minLength="3" maxLength="32" autoComplete="username" required />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              minLength="8"
              maxLength="1024"
              autoComplete={authMode === "register" ? "new-password" : "current-password"}
              required
            />
          </label>
          {authError && <p className="status-message error" role="alert">{authError}</p>}
          <button type="submit" disabled={authBusy}>
            {authBusy ? "Please wait..." : authMode === "register" ? "Register" : "Log in"}
          </button>
          <button
            className="secondary-btn"
            type="button"
            onClick={() => {
              setAuthMode((mode) => mode === "login" ? "register" : "login");
              setAuthError("");
            }}
          >
            {authMode === "register" ? "Already have an account? Log in" : "Create an account"}
          </button>
        </form>
      </dialog>

      <main className="layout">
        <aside className="panel filters-panel">
          <h2>Filters</h2>
          <form onSubmit={applyFilters}>
            <label>
              Search questions
              <input
                type="search"
                placeholder="Type topic or keyword..."
                value={filters.q}
                onChange={(event) => setFilters({ ...filters, q: event.target.value })}
              />
            </label>
            <label>
              Subject
              <select
                value={filters.subject_id}
                onChange={(event) => setFilters({ ...filters, subject_id: event.target.value })}
              >
                <option value="">All subjects</option>
                {subjects.map((subject) => (
                  <option value={subject.subject_id} key={subject.subject_id}>{subject.subject_name}</option>
                ))}
              </select>
            </label>
            <label>
              Semester
              <select
                value={filters.semester_id}
                onChange={(event) => setFilters({ ...filters, semester_id: event.target.value })}
              >
                <option value="">All semesters</option>
                {semesters.map((semester) => (
                  <option value={semester.semester_id} key={semester.semester_id}>
                    Sem {semester.semester_number} ({semester.academic_year})
                  </option>
                ))}
              </select>
            </label>
            <label>
              Exam type
              <select
                value={filters.exam_type}
                onChange={(event) => setFilters({ ...filters, exam_type: event.target.value })}
              >
                <option value="">All exam types</option>
                {EXAM_TYPES.map((type) => <option value={type} key={type}>{type}</option>)}
              </select>
            </label>
            <button type="submit">Apply filters</button>
          </form>
        </aside>

        <section className="content">
          {pageError && <div className="status-message error" role="alert">{pageError}</div>}

          {activeTab === "overview" && (
            <section aria-label="Overview">
              <div className="stats-grid">
                {[
                  ["Papers", totals.papers ?? 0],
                  ["Questions", totals.questions ?? 0],
                  ["Subjects", totals.subjects ?? 0],
                  ["Semesters", totals.semesters ?? 0]
                ].map(([label, value]) => (
                  <div className="stat-card" key={label}>
                    <div className="label">{label}</div>
                    <div className="value">{value}</div>
                  </div>
                ))}
              </div>

              <div className="analytics-grid">
                <div className="panel">
                  <h2>Question types</h2>
                  <BarList
                    items={overview?.question_types || []}
                    labelKey="type_name"
                    valueKey="count"
                    emptyMessage="No question-type data available."
                  />
                </div>
                <div className="panel">
                  <h2>Topic frequency</h2>
                  <BarList
                    items={overview?.topics || []}
                    labelKey="topic_name"
                    valueKey="count"
                    emptyMessage="No topic data available."
                  />
                </div>
                <div className="panel span-2">
                  <h2>Semester comparison</h2>
                  {comparison.length ? (
                    <div className="table-wrapper">
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
                          {comparison.map((entry, index) => (
                            <tr key={`${entry.subject_name}-${entry.semester_number}-${entry.academic_year}-${index}`}>
                              <td>{entry.subject_name}</td>
                              <td>{entry.semester_number}</td>
                              <td>{entry.academic_year}</td>
                              <td>{entry.question_count}</td>
                              <td>{entry.total_marks}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : <EmptyState>No semester comparison data available.</EmptyState>}
                </div>
                <div className="panel">
                  <h2>Unit weightage (marks)</h2>
                  <BarList
                    items={patterns?.unit_weightage || []}
                    labelKey="unit_name"
                    valueKey="total_marks"
                    emptyMessage="No unit weightage data available."
                  />
                </div>
                <div className="panel">
                  <h2>Recurring concepts</h2>
                  <BarList
                    items={patterns?.recurring_concepts || []}
                    labelKey="topic_name"
                    valueKey="frequency"
                    emptyMessage="No recurring concepts available."
                  />
                </div>
              </div>
            </section>
          )}

          {activeTab === "questions" && (
            <section className="panel" aria-label="Question search">
              <div className="section-header">
                <h2>Question search</h2>
                <span>{questions.length} results</span>
              </div>
              <QuestionCards items={questions} />
            </section>
          )}

          {activeTab === "similarity" && (
            <section className="panel" aria-label="Semantic search">
              <div className="section-header"><h2>Semantic similar questions</h2></div>
              <form className="semantic-search-row" onSubmit={searchSimilar}>
                <input
                  type="search"
                  placeholder="Try: Explain database normalization"
                  value={semanticQuery}
                  onChange={(event) => setSemanticQuery(event.target.value)}
                />
                <button type="submit">Find similar</button>
              </form>
              {semanticError && <div className="status-message error" role="alert">{semanticError}</div>}
              {similarQuestions.length ? (
                <div className="questions-list compact">
                  {similarQuestions.map((question) => (
                    <article className="question-card" key={question.question_id}>
                      <h3>{question.question_text}</h3>
                      <div className="meta"><span>Question #{question.question_id}</span></div>
                      <span className="similarity-score">
                        Similarity: {Number(question.similarity_score).toFixed(4)}
                      </span>
                    </article>
                  ))}
                </div>
              ) : !semanticError && <EmptyState>Enter a question or concept to find similar items.</EmptyState>}
            </section>
          )}

          {activeTab === "papers" && (
            <section className="panel paper-form-panel" aria-label="Paper management">
              <div className="section-header">
                <h2>{paperForm.paper_id ? `Edit paper ${paperForm.paper_id}` : "Paper ingestion"}</h2>
                {paperForm.paper_id && (
                  <button className="secondary-btn" type="button" onClick={resetPaperForm}>New paper</button>
                )}
              </div>
              {!user && (
                <div className="status-message">
                  Log in or register to create, edit, or delete papers.
                  <button className="secondary-btn" type="button" onClick={() => openAuth("login")}>Log in</button>
                </div>
              )}
              <form onSubmit={savePaper}>
                <div className="paper-form-grid">
                  <label>
                    Subject
                    <select
                      required
                      value={paperForm.subject_id}
                      onChange={(event) => setPaperForm({ ...paperForm, subject_id: event.target.value })}
                    >
                      <option value="">Choose subject</option>
                      {subjects.map((subject) => (
                        <option value={subject.subject_id} key={subject.subject_id}>{subject.subject_name}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Semester
                    <select
                      required
                      value={paperForm.semester_id}
                      onChange={(event) => setPaperForm({ ...paperForm, semester_id: event.target.value })}
                    >
                      <option value="">Choose semester</option>
                      {semesters.map((semester) => (
                        <option value={semester.semester_id} key={semester.semester_id}>
                          Sem {semester.semester_number} ({semester.academic_year})
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Exam type
                    <select
                      value={paperForm.exam_type}
                      onChange={(event) => setPaperForm({ ...paperForm, exam_type: event.target.value })}
                    >
                      {EXAM_TYPES.map((type) => <option value={type} key={type}>{type}</option>)}
                    </select>
                  </label>
                  <label>
                    Total marks
                    <input
                      required
                      type="number"
                      min="1"
                      value={paperForm.total_marks}
                      placeholder="Enter total marks"
                      onChange={(event) => setPaperForm({ ...paperForm, total_marks: event.target.value })}
                    />
                  </label>
                </div>

                <div className="paper-questions-block">
                  <div className="section-header compact-header">
                    <h3>Questions</h3>
                    <button
                      className="secondary-btn"
                      type="button"
                      onClick={() => setPaperForm((form) => ({
                        ...form,
                        questions: [
                          ...form.questions,
                          { ...EMPTY_QUESTION, question_number: String(form.questions.length + 1) }
                        ]
                      }))}
                    >
                      Add question
                    </button>
                  </div>
                  <p className="muted-copy">
                    Add all questions to submit a paper in one request. CSV or file import is not provided by the current API.
                  </p>
                  <div className="paper-question-rows">
                    {paperForm.questions.map((question, index) => (
                      <PaperQuestionEditor
                        key={`${paperForm.paper_id || "new"}-${index}`}
                        question={question}
                        index={index}
                        questionTypes={questionTypes}
                        topics={topics}
                        onChange={updateQuestion}
                        onRemove={removeQuestion}
                      />
                    ))}
                  </div>
                </div>
                <div className="paper-form-actions">
                  <button type="submit" disabled={!user}>
                    {paperForm.paper_id ? "Save paper changes" : "Create paper"}
                  </button>
                </div>
              </form>
              {paperStatus && <div className="status-message success" role="status">{paperStatus}</div>}
              {paperError && <div className="status-message error" role="alert">{paperError}</div>}

              <div className="paper-list">
                <div className="section-header"><h2>Existing papers</h2></div>
                {papers.length ? (
                  <div className="questions-list">
                    {papers.map((paper) => (
                      <article className="question-card paper-card" key={paper.paper_id}>
                        <h3>Paper #{paper.paper_id}</h3>
                        <div className="meta">
                          <span>{subjectNames.get(paper.subject_id) || `Subject ${paper.subject_id}`}</span>
                          <span>•</span>
                          <span>{semesterNames.get(paper.semester_id) || `Semester ${paper.semester_id}`}</span>
                          <span>•</span>
                          <span>{paper.exam_type}</span>
                          <span>•</span>
                          <span>{paper.total_marks} marks</span>
                          <span>•</span>
                          <span>{paper.questions.length} questions</span>
                        </div>
                        <div className="paper-card-actions">
                          <button
                            className="secondary-btn"
                            type="button"
                            onClick={() => loadPaperForEdit(paper.paper_id)}
                          >
                            Edit
                          </button>
                          <button
                            className="danger-btn"
                            type="button"
                            disabled={!user}
                            onClick={() => deletePaper(paper.paper_id)}
                          >
                            Delete
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : <EmptyState>No papers have been added yet.</EmptyState>}
              </div>
            </section>
          )}
        </section>
      </main>

      <div className="visually-hidden" aria-live="polite">
        {pageError}
      </div>
    </div>
  );
}
