from src.quality.rules import detect_outliers, rule_missing, rule_non_negative


def test_rule_missing():
    hit, _ = rule_missing('close', None)
    assert hit


def test_rule_non_negative():
    hit, _ = rule_non_negative('volume', -1)
    assert hit


def test_outlier_detection():
    idx = detect_outliers([1, 1, 1, 10], threshold=1.5)
    assert idx == [3]
