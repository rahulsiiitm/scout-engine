from scout_engine.github_sync import GitHubClient


def test_github_list_issues_paginates_past_first_hundred(monkeypatch):
    client = GitHubClient("owner/repo", "token")
    calls: list[str] = []

    page_one = [{"number": i} for i in range(1, 101)]
    page_two = [{"number": i} for i in range(101, 106)]

    def fake_request(self, method, path, payload=None):
        calls.append(path)
        if "page=1" in path:
            return page_one
        if "page=2" in path:
            return page_two
        raise AssertionError(path)

    monkeypatch.setattr(GitHubClient, "_request", fake_request)

    issues = client.list_issues(state="all")

    assert len(issues) == 105
    assert issues[-1]["number"] == 105
    assert calls == [
        "/issues?state=all&per_page=100&page=1",
        "/issues?state=all&per_page=100&page=2",
    ]


def test_github_list_labels_uses_same_pagination(monkeypatch):
    client = GitHubClient("owner/repo", "token")

    first = [{"name": f"label-{i}"} for i in range(100)]
    second = [{"name": "last"}]

    def fake_request(self, method, path, payload=None):
        if "page=1" in path:
            return first
        if "page=2" in path:
            return second
        raise AssertionError(path)

    monkeypatch.setattr(GitHubClient, "_request", fake_request)

    labels = client.list_labels()

    assert len(labels) == 101
    assert labels[-1]["name"] == "last"
