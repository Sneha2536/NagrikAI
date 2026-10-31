import pytest

from routes import eligibility


AGE_CRITERION = {
    "text": "The applicant must be 18 to 35 years old.",
    "field": "age",
    "quote": "Applicants must be aged between 18 and 35 years.",
    "page": 4,
    "clause": "Section 2",
}
INCOME_CRITERION = {
    "text": "The applicant's annual income must not exceed 200000 rupees.",
    "field": "income",
    "quote": "Annual income shall not exceed 200000 rupees.",
    "page": 5,
    "clause": "Section 3",
}
OTHER_CRITERION = {
    "text": "The applicant must not currently receive another government subsidy.",
    "field": "other",
    "quote": "A person receiving another government subsidy is not eligible.",
    "page": 7,
    "clause": "Rule 5(a)",
}
MANDATORY_CRITERION = {
    "text": "The applicant must be a farmer.",
    "field": "other",
    "quote": "The applicant must be a farmer.",
    "page": 2,
    "clause": "Section 1",
}
SCHOLARSHIP_CRITERIA = [
    {"text": "The student must score above the 80th percentile in Class XII.", "field": "education", "quote": "above 80th percentile", "page": 1, "clause": "Clause A"},
    {"text": "The student must pursue a regular degree course, not correspondence, distance, or diploma courses.", "field": "education", "quote": "Pursuing regular degree courses", "page": 2, "clause": "Clause B"},
    {"text": "The institution must be recognized by AICTE or the relevant regulatory body.", "field": "education", "quote": "institutions recognized by AICTE", "page": 2, "clause": "Clause C"},
    {"text": "The student must not receive another scholarship or fee waiver.", "field": "other", "quote": "Not availing benefit of any other scholarship", "page": 2, "clause": "Clause D"},
]


def run_check(monkeypatch, criteria, model_results, *, profile=None, answers=None, submitted=False, prompt_sink=None):
    monkeypatch.setattr(eligibility, "_get_rules", lambda _: {"eligibility": criteria})

    def fake_generate(_system, prompt):
        if prompt_sink is not None:
            prompt_sink.append(prompt)
        return {"results": model_results}

    monkeypatch.setattr(eligibility, "generate_json", fake_generate)
    request = eligibility.CheckRequest(
        policy_id="policy-1",
        profile=profile or eligibility.Profile(),
        answers=answers or {},
        follow_up_submitted=submitted,
    )
    return eligibility.check(request)


def test_assessable_criteria_skip_follow_up(monkeypatch):
    result = run_check(
        monkeypatch,
        [AGE_CRITERION],
        [{"index": 0, "status": "met", "reason": "Age is in range."}],
        profile=eligibility.Profile(age=24),
    )

    assert result["verdict"] == "eligible"
    assert result["follow_up_questions"] == []


def test_missing_information_generates_question_from_unresolved_criterion(monkeypatch):
    result = run_check(monkeypatch, [AGE_CRITERION], [{"index": 0, "status": "met"}])

    question = result["follow_up_questions"][0]
    assert result["results"][0]["status"] == "unknown"
    assert question["id"] == "field:age"
    assert question["answer_type"] == "number"
    assert question["criteria"] == [{
        "criterion_id": 0,
        "text": AGE_CRITERION["text"],
        "page": 4,
        "clause": "Section 2",
        "quote": AGE_CRITERION["quote"],
    }]


def test_multiple_unresolved_criteria_produce_all_distinct_questions(monkeypatch):
    result = run_check(
        monkeypatch,
        [AGE_CRITERION, INCOME_CRITERION],
        [{"index": 0, "status": "met"}, {"index": 1, "status": "met"}],
    )

    assert [question["id"] for question in result["follow_up_questions"]] == ["field:age", "field:income"]
    assert [question["criteria"][0]["page"] for question in result["follow_up_questions"]] == [4, 5]


def test_scholarship_returns_separate_questions_for_four_different_facts(monkeypatch):
    result = run_check(
        monkeypatch,
        SCHOLARSHIP_CRITERIA,
        [{"index": i, "status": "unknown"} for i in range(4)],
        profile=eligibility.Profile(education="Class 12"),
    )

    questions = result["follow_up_questions"]
    assert [q["criteria"][0]["criterion_id"] for q in questions] == [0, 1, 2, 3]
    assert [q["answer_type"] for q in questions] == ["number", "choice", "choice", "choice"]
    assert "percentile" in questions[0]["question"]
    assert "regular degree" in questions[1]["question"]
    assert "recognized" in questions[2]["question"]
    assert "requirement below" in questions[3]["question"]
    for index, question in enumerate(questions):
        criterion = question["criteria"][0]
        assert criterion["text"] == SCHOLARSHIP_CRITERIA[index]["text"]
        assert criterion["page"] == SCHOLARSHIP_CRITERIA[index]["page"]
        assert criterion["quote"] == SCHOLARSHIP_CRITERIA[index]["quote"]


def test_unclarifiable_unknown_is_explicitly_marked_for_manual_verification(monkeypatch):
    result = run_check(
        monkeypatch,
        [AGE_CRITERION],
        [{"index": 0, "status": "unknown", "reason": "More evidence is needed."}],
        profile=eligibility.Profile(age=24),
    )

    assert result["follow_up_questions"] == []
    assert result["results"][0]["manual_verification"] is True
    assert "verify it with the scheme authority" in result["results"][0]["reason"]


def test_preserved_answer_is_reused_and_only_remaining_question_is_returned(monkeypatch):
    prompts = []
    result = run_check(
        monkeypatch,
        [AGE_CRITERION, INCOME_CRITERION],
        [{"index": 0, "status": "met"}, {"index": 1, "status": "met"}],
        answers={"field:age": 24},
        prompt_sink=prompts,
    )

    assert '"age": 24' in prompts[0]
    assert result["results"][0]["status"] == "met"
    assert [question["id"] for question in result["follow_up_questions"]] == ["field:income"]


def test_answers_to_multiple_questions_are_assessed_in_one_request(monkeypatch):
    prompts = []
    result = run_check(
        monkeypatch,
        [AGE_CRITERION, INCOME_CRITERION],
        [{"index": 0, "status": "met"}, {"index": 1, "status": "met"}],
        answers={"field:age": 24, "field:income": 150000},
        submitted=True,
        prompt_sink=prompts,
    )

    assert '"age": 24' in prompts[0]
    assert '"annual_income": 150000' in prompts[0]
    assert result["verdict"] == "eligible"
    assert result["follow_up_questions"] == []


def test_four_scholarship_answers_are_submitted_and_assessed_together(monkeypatch):
    prompts = []
    result = run_check(
        monkeypatch,
        SCHOLARSHIP_CRITERIA,
        [{"index": 0, "status": "met"}, {"index": 1, "status": "unknown"}, {"index": 2, "status": "unknown"}, {"index": 3, "status": "unknown"}],
        profile=eligibility.Profile(education="Class 12", annual_income=400000),
        answers={"criterion:0": 88, "criterion:1": "yes", "criterion:2": "yes", "criterion:3": "yes"},
        submitted=True,
        prompt_sink=prompts,
    )

    assert '"criterion:0": 88' in prompts[0]
    assert '"criterion:1": "yes"' in prompts[0]
    assert '"criterion:2": "yes"' in prompts[0]
    assert '"criterion:3": "yes"' in prompts[0]
    assert [item["status"] for item in result["results"][:4]] == ["met", "met", "met", "met"]
    assert result["follow_up_questions"] == []


def test_unanswered_scholarship_criterion_remains_unknown_after_batch_submission(monkeypatch):
    result = run_check(
        monkeypatch,
        SCHOLARSHIP_CRITERIA,
        [{"index": i, "status": "met"} for i in range(4)],
        profile=eligibility.Profile(education="Class 12", annual_income=400000),
        answers={"criterion:0": 88, "criterion:1": "yes", "criterion:2": "yes"},
        submitted=True,
    )

    assert result["results"][3]["status"] == "unknown"
    assert result["follow_up_questions"] == []


def test_not_sure_is_not_reasked_during_a_retry(monkeypatch):
    result = run_check(
        monkeypatch,
        [OTHER_CRITERION],
        [{"index": 0, "status": "met"}],
        answers={"criterion:0": "not_sure"},
    )

    assert result["results"][0]["status"] == "unknown"
    assert result["follow_up_questions"] == []


@pytest.mark.parametrize("answers", [{"criterion:0": "not_sure"}, {}])
def test_not_sure_or_unanswered_remains_unknown(monkeypatch, answers):
    result = run_check(
        monkeypatch,
        [OTHER_CRITERION],
        [{"index": 0, "status": "met", "reason": "Model guess must not override no answer."}],
        answers=answers,
        submitted=True,
    )

    assert result["results"][0]["status"] == "unknown"
    assert result["follow_up_questions"] == []


@pytest.mark.parametrize(("answer", "expected"), [("yes", "met"), ("no", "not_met")])
def test_boolean_answer_assesses_complete_mandatory_condition(monkeypatch, answer, expected):
    result = run_check(
        monkeypatch,
        [MANDATORY_CRITERION],
        [{"index": 0, "status": "unknown"}],
        answers={"criterion:0": answer},
        submitted=True,
    )

    assert result["results"][0]["status"] == expected


@pytest.mark.parametrize(("answer", "expected"), [("yes", "met"), ("no", "not_met")])
def test_exclusion_is_asked_as_the_complete_requirement(monkeypatch, answer, expected):
    result = run_check(
        monkeypatch,
        [OTHER_CRITERION],
        [{"index": 0, "status": "unknown"}],
        answers={"criterion:0": answer},
        submitted=True,
    )

    assert result["results"][0]["status"] == expected
    assert result["results"][0]["criterion"] == OTHER_CRITERION["text"]


def test_unrelated_and_malformed_answers_cannot_change_result(monkeypatch):
    prompts = []
    result = run_check(
        monkeypatch,
        [AGE_CRITERION],
        [{"index": 0, "status": "met", "reason": "Unvalidated value must not count."}],
        answers={"criterion:99": "yes", "field:age": "not a number"},
        submitted=True,
        prompt_sink=prompts,
    )

    assert result["results"][0]["status"] == "unknown"
    assert '"age": null' in prompts[0]


def test_numeric_answer_is_used_for_original_assessment(monkeypatch):
    prompts = []
    result = run_check(
        monkeypatch,
        [AGE_CRITERION],
        [{"index": 0, "status": "met", "reason": "Age is in range."}],
        answers={"field:age": 24},
        submitted=True,
        prompt_sink=prompts,
    )

    assert '"age": 24' in prompts[0]
    assert result["results"][0]["status"] == "met"


def test_result_keeps_original_source_reference(monkeypatch):
    result = run_check(monkeypatch, [AGE_CRITERION], [{"index": 0, "status": "unknown"}])

    assert {key: result["results"][0][key] for key in ("page", "clause", "quote")} == {
        "page": 4,
        "clause": "Section 2",
        "quote": AGE_CRITERION["quote"],
    }
    assert result["follow_up_questions"][0]["criteria"][0]["quote"] == AGE_CRITERION["quote"]
