export function getFollowUpQuestions(response) {
  return Array.isArray(response?.follow_up_questions)
    ? response.follow_up_questions.filter((question) =>
      question && typeof question.id === "string" && typeof question.question === "string"
      && ["choice", "number", "text"].includes(question.answer_type) && Array.isArray(question.criteria)
    )
    : [];
}

export function buildEligibilityCheckPayload(policy_id, profile, language, answers, follow_up_submitted) {
  return { policy_id, profile, language, answers, follow_up_submitted };
}
