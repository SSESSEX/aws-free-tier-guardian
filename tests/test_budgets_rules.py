from app.scanner.budgets_rules import (
    evaluate_actual_spend,
    evaluate_budget,
    evaluate_budget_limit,
    evaluate_cost_budget_exists,
    evaluate_forecast_spend,
)


def sample_budget(**overrides):
    budget = {
        "budget_name": "Monthly AWS Safety Budget",
        "budget_type": "COST",
        "budget_limit_amount": 10.0,
        "budget_limit_unit": "USD",
        "actual_spend_amount": 0.0,
        "actual_spend_unit": "USD",
        "forecast_spend_amount": 0.0,
        "forecast_spend_unit": "USD",
    }

    budget.update(overrides)
    return budget


def test_no_cost_budget_returns_warn_high():
    result = evaluate_cost_budget_exists([])

    assert result["check"] == "BUDGETS_COST_BUDGET_EXISTS"
    assert result["status"] == "WARN"
    assert result["severity"] == "HIGH"


def test_cost_budget_exists_returns_pass():
    result = evaluate_cost_budget_exists([sample_budget()])

    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_non_cost_budget_does_not_satisfy_cost_budget_check():
    result = evaluate_cost_budget_exists([
        sample_budget(budget_type="USAGE")
    ])

    assert result["status"] == "WARN"
    assert result["severity"] == "HIGH"


def test_positive_budget_limit_returns_pass():
    result = evaluate_budget_limit(sample_budget())

    assert result["check"] == "BUDGETS_BUDGET_LIMIT_PRESENT"
    assert result["status"] == "PASS"


def test_missing_budget_limit_returns_warn():
    result = evaluate_budget_limit(
        sample_budget(budget_limit_amount=None)
    )

    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_zero_budget_limit_returns_fail():
    result = evaluate_budget_limit(
        sample_budget(budget_limit_amount=0.0)
    )

    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_actual_spend_below_80_percent_returns_pass():
    result = evaluate_actual_spend(
        sample_budget(actual_spend_amount=7.5)
    )

    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_actual_spend_at_80_percent_returns_warn():
    result = evaluate_actual_spend(
        sample_budget(actual_spend_amount=8.0)
    )

    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_actual_spend_at_limit_returns_fail():
    result = evaluate_actual_spend(
        sample_budget(actual_spend_amount=10.0)
    )

    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_forecast_below_80_percent_returns_pass():
    result = evaluate_forecast_spend(
        sample_budget(forecast_spend_amount=5.0)
    )

    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_forecast_at_80_percent_returns_warn():
    result = evaluate_forecast_spend(
        sample_budget(forecast_spend_amount=8.0)
    )

    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_forecast_over_limit_returns_fail():
    result = evaluate_forecast_spend(
        sample_budget(forecast_spend_amount=12.0)
    )

    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_missing_forecast_returns_info():
    result = evaluate_forecast_spend(
        sample_budget(forecast_spend_amount=None)
    )

    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_evaluate_budget_returns_three_findings():
    results = evaluate_budget(sample_budget())

    assert len(results) == 3
    assert results[0]["check"] == "BUDGETS_BUDGET_LIMIT_PRESENT"
    assert results[1]["check"] == "BUDGETS_ACTUAL_SPEND_THRESHOLD"
    assert results[2]["check"] == "BUDGETS_FORECAST_SPEND_THRESHOLD"
