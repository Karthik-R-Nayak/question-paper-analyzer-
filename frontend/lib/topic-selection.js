export function filterTopics(topics, units, subjectId, unitId, search) {
  if (!subjectId) return [];

  const subjectUnits = units.filter(
    (unit) => String(unit.subject_id) === String(subjectId)
  );
  const availableUnitIds = new Set(subjectUnits.map((unit) => String(unit.unit_id)));
  const normalizedSearch = search.trim().toLocaleLowerCase();

  return topics.filter((topic) => {
    const topicUnitId = String(topic.unit_id);
    return availableUnitIds.has(topicUnitId) &&
      (!unitId || topicUnitId === String(unitId)) &&
      topic.topic_name.toLocaleLowerCase().includes(normalizedSearch);
  });
}

export function toggleTopicId(selectedIds, topicId) {
  const normalizedId = Number(topicId);
  const normalizedIds = [...new Set(selectedIds.map(Number))];
  return normalizedIds.includes(normalizedId)
    ? normalizedIds.filter((id) => id !== normalizedId)
    : [...normalizedIds, normalizedId];
}

export function removeTopicId(selectedIds, topicId) {
  const normalizedId = Number(topicId);
  return selectedIds.map(Number).filter((id) => id !== normalizedId);
}

export function buildPaperPayload(form) {
  return {
    subject_id: Number(form.subject_id),
    semester_id: Number(form.semester_id),
    exam_type: form.exam_type,
    total_marks: Number(form.total_marks),
    questions: form.questions.map((question) => ({
      question_number: question.question_number.trim(),
      marks: Number(question.marks),
      question_text: question.question_text.trim(),
      question_type_id: Number(question.question_type_id),
      topic_ids: [...new Set(question.topic_ids.map(Number))]
    }))
  };
}
