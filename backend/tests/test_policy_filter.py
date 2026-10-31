import httpx

from ai import llm
from sources import pib, registry
from sources.base import Policy


def _p(source, tags):
    return Policy(id="x", title="t", source=source, authority="a", url="u", tags=tags)


def test_policy_only_hides_untagged_pib_but_keeps_other_sources():
    args = (None, None, None, None, None)
    assert registry._matches(_p("PIB", ["policy-like"]), *args, policy_only=True)
    assert not registry._matches(_p("PIB", []), *args, policy_only=True)
    assert registry._matches(_p("PIB", []), *args, policy_only=False)
    assert registry._matches(_p("Official link", []), *args, policy_only=True)


def test_pib_tags_policy_releases_in_english_and_hindi():
    assert pib._looks_like_policy("Cabinet approves new scheme", "")
    assert pib._looks_like_policy("किसानों के लिए नई योजना", "")
    assert not pib._looks_like_policy("Navy ship visits port", "")


def test_retry_delay_is_read_from_google_reply():
    assert llm._retry_delay('{"retryDelay": "34s"}') == 34.0
    assert llm._retry_delay("no delay given") == 20.0


def _resp(body):
    return httpx.Response(429, body)


def test_daily_quota_is_not_retried_but_per_minute_is():
    assert llm._quota_exhausted(_resp("GenerateRequestsPerDayPerProjectPerModel-FreeTier"))
    assert not llm._quota_exhausted(_resp("GenerateContentInputTokensPerModelPerMinute-FreeTier"))
