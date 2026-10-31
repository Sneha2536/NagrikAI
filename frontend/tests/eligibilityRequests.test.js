import assert from "node:assert/strict";
import test from "node:test";

import { buildEligibilityCheckPayload, getFollowUpQuestions } from "../src/eligibilityRequests.js";

test("keeps all valid follow-up questions together for the questionnaire", () => {
  const questions = [
    { id: "criterion:0", question: "What percentile did you receive?", answer_type: "number", criteria: [{ criterion_id: 0, page: 1, quote: "above 80th percentile" }] },
    { id: "criterion:1", question: "Are you enrolled in a regular degree course?", answer_type: "choice", criteria: [{ criterion_id: 1, page: 2, quote: "regular degree courses" }] },
    { id: "criterion:2", question: "Is the institution recognized?", answer_type: "choice", criteria: [{ criterion_id: 2, page: 2, quote: "recognized by AICTE" }] },
    { id: "criterion:3", question: "Do you receive another scholarship?", answer_type: "choice", criteria: [{ criterion_id: 3, page: 2, quote: "another scholarship" }] },
  ];

  const renderedQuestions = getFollowUpQuestions({ follow_up_questions: questions });
  assert.deepEqual(renderedQuestions, questions);
  assert.equal(renderedQuestions.length, 4);
  assert.deepEqual(renderedQuestions.map((question) => question.criteria[0].criterion_id), [0, 1, 2, 3]);
});

test("serializes answers from different questions together in one eligibility request", () => {
  const payload = buildEligibilityCheckPayload(
    "policy-1",
    { education: "Class 12" },
    "en",
    { "criterion:0": 88, "criterion:1": "yes", "criterion:2": "yes", "criterion:3": "not_sure" },
    true,
  );

  assert.deepEqual(JSON.parse(JSON.stringify(payload)).answers, {
    "criterion:0": 88,
    "criterion:1": "yes",
    "criterion:2": "yes",
    "criterion:3": "not_sure",
  });
});
