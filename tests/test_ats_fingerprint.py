from scout_engine.discovery.ats_fingerprint import fingerprint_ats_url


def test_known_ats_fingerprints():
    assert fingerprint_ats_url("https://boards.greenhouse.io/acme/jobs/123").provider == "greenhouse"
    assert fingerprint_ats_url("https://jobs.lever.co/acme/abc").identifier == "acme"
    assert fingerprint_ats_url("https://jobs.ashbyhq.com/acme/abc").provider == "ashby"
    assert fingerprint_ats_url("https://apply.workable.com/acme/j/123").provider == "workable"
    assert fingerprint_ats_url("https://careers.smartrecruiters.com/Acme/job").provider == "smartrecruiters"
