import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPaperPayload,
  filterTopics,
  removeTopicId,
  toggleTopicId
} from "./topic-selection.js";

const units = [
  { unit_id: 1, subject_id: 10, unit_number: 1, unit_name: "Foundations" },
  { unit_id: 2, subject_id: 10, unit_number: 2, unit_name: "Queries" },
  { unit_id: 3, subject_id: 20, unit_number: 1, unit_name: "Processes" }
];

const topics = [
  { topic_id: 101, unit_id: 1, topic_name: "Relational Model" },
  { topic_id: 102, unit_id: 2, topic_name: "Query Planning" },
  { topic_id: 201, unit_id: 3, topic_name: "Process Scheduling" }
];

test("topic search filters by name, selected subject, and optional unit", () => {
  assert.deepEqual(filterTopics(topics, units, 10, "", "query"), [topics[1]]);
  assert.deepEqual(filterTopics(topics, units, 10, 1, ""), [topics[0]]);
  assert.deepEqual(filterTopics(topics, units, 20, "", "RELATIONAL"), []);
  assert.deepEqual(filterTopics(topics, units, "", "", ""), []);
});

test("topic selection adds multiple unique IDs and toggles selected topics off", () => {
  const selected = toggleTopicId([], topics[0].topic_id);
  const multiple = toggleTopicId(selected, topics[1].topic_id);

  assert.deepEqual(multiple, [101, 102]);
  assert.deepEqual(toggleTopicId(multiple, topics[0].topic_id), [102]);
  assert.deepEqual(toggleTopicId(["101", 101], topics[1].topic_id), [101, 102]);
});

test("removing a topic chip keeps the remaining selected IDs", () => {
  assert.deepEqual(removeTopicId([101, 102, 201], 102), [101, 201]);
});

test("paper submission keeps multiple selected topic IDs as numbers", () => {
  const payload = buildPaperPayload({
    subject_id: "10",
    semester_id: "5",
    exam_type: "End",
    total_marks: "20",
    questions: [
      {
        question_number: "1a",
        marks: "10",
        question_text: "Explain the relational model.",
        question_type_id: "3",
        topic_ids: [101, "102", 999, 101]
      }
    ]
  });

  assert.deepEqual(payload.questions[0].topic_ids, [101, 102, 999]);
  assert.equal(payload.subject_id, 10);
  assert.equal(payload.semester_id, 5);
});
