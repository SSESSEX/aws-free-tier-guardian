def finding(check, status, severity, message):
    return {
        "check": check,
        "status": status,
        "severity": severity,
        "message": message,
    }


def is_positive_number(value):
    return isinstance(value, (int, float)) and value > 0


def format_amount(amount, unit):
    if amount is None:
        return "unknown"

    if unit:
        return f"{amount:.2f} {unit}"

    return f"{amount:.2f}"


def evaluate_cost_budget_exists(budgets):
    cost_budgets = [
        budget for budget in budgets
        if budget.get("budget_type") == "COST"
    ]

    if not cost_budgets:
        return finding(
            "BUDGETS_COST_BUDGET_EXISTS",
            "WARN",
            "HIGH",
            "No cost budget was found. Create a monthly cost budget to monitor account spend.",
        )

    return finding(
        "BUDGETS_COST_BUDGET_EXISTS",
        "PASS",
        "LOW",
        f"{len(cost_budgets)} cost budget(s) found.",
    )


def evaluate_budget_limit(budget):
    limit_amount = budget.get("budget_limit_amount")
    limit_unit = budget.get("budget_limit_unit")

    if limit_amount is None:
        return finding(
            "BUDGETS_BUDGET_LIMIT_PRESENT",
            "WARN",
            "MEDIUM",
            "Cost budget has no fixed budget limit. Planned budget limits are not assessed by this check.",
        )

    if not is_positive_number(limit_amount):
        return finding(
            "BUDGETS_BUDGET_LIMIT_PRESENT",
            "FAIL",
            "HIGH",
            "Cost budget has a zero or invalid budget limit.",
        )

    return finding(
        "BUDGETS_BUDGET_LIMIT_PRESENT",
        "PASS",
        "LOW",
        f"Cost budget limit is {format_amount(limit_amount, limit_unit)}.",
    )


def evaluate_actual_spend(budget):
    limit_amount = budget.get("budget_limit_amount")
    limit_unit = budget.get("budget_limit_unit")
    actual_amount = budget.get("actual_spend_amount")
    actual_unit = budget.get("actual_spend_unit")

    if not is_positive_number(limit_amount):
        return finding(
            "BUDGETS_ACTUAL_SPEND_THRESHOLD",
            "INFO",
            "LOW",
            "Actual spend cannot be compared because the budget limit is unavailable or invalid.",
        )

    if actual_amount is None:
        return finding(
            "BUDGETS_ACTUAL_SPEND_THRESHOLD",
            "WARN",
            "LOW",
            "Actual spend could not be determined for this cost budget.",
        )

    if limit_unit and actual_unit and limit_unit != actual_unit:
        return finding(
            "BUDGETS_ACTUAL_SPEND_THRESHOLD",
            "WARN",
            "MEDIUM",
            "Actual spend unit does not match the configured budget limit unit.",
        )

    spend_percentage = (actual_amount / limit_amount) * 100

    if spend_percentage >= 100:
        return finding(
            "BUDGETS_ACTUAL_SPEND_THRESHOLD",
            "FAIL",
            "HIGH",
            (
                f"Actual spend is {format_amount(actual_amount, actual_unit)} "
                f"({spend_percentage:.1f}% of the budget limit)."
            ),
        )

    if spend_percentage >= 80:
        return finding(
            "BUDGETS_ACTUAL_SPEND_THRESHOLD",
            "WARN",
            "MEDIUM",
            (
                f"Actual spend is {format_amount(actual_amount, actual_unit)} "
                f"({spend_percentage:.1f}% of the budget limit)."
            ),
        )

    return finding(
        "BUDGETS_ACTUAL_SPEND_THRESHOLD",
        "PASS",
        "LOW",
        (
            f"Actual spend is {format_amount(actual_amount, actual_unit)} "
            f"({spend_percentage:.1f}% of the budget limit)."
        ),
    )


def evaluate_forecast_spend(budget):
    limit_amount = budget.get("budget_limit_amount")
    limit_unit = budget.get("budget_limit_unit")
    forecast_amount = budget.get("forecast_spend_amount")
    forecast_unit = budget.get("forecast_spend_unit")

    if not is_positive_number(limit_amount):
        return finding(
            "BUDGETS_FORECAST_SPEND_THRESHOLD",
            "INFO",
            "LOW",
            "Forecast spend cannot be compared because the budget limit is unavailable or invalid.",
        )

    if forecast_amount is None:
        return finding(
            "BUDGETS_FORECAST_SPEND_THRESHOLD",
            "INFO",
            "LOW",
            "Forecast spend is not currently available for this cost budget.",
        )

    if limit_unit and forecast_unit and limit_unit != forecast_unit:
        return finding(
            "BUDGETS_FORECAST_SPEND_THRESHOLD",
            "WARN",
            "MEDIUM",
            "Forecast spend unit does not match the configured budget limit unit.",
        )

    forecast_percentage = (forecast_amount / limit_amount) * 100

    if forecast_percentage >= 100:
        return finding(
            "BUDGETS_FORECAST_SPEND_THRESHOLD",
            "FAIL",
            "HIGH",
            (
                f"Forecast spend is {format_amount(forecast_amount, forecast_unit)} "
                f"({forecast_percentage:.1f}% of the budget limit)."
            ),
        )

    if forecast_percentage >= 80:
        return finding(
            "BUDGETS_FORECAST_SPEND_THRESHOLD",
            "WARN",
            "MEDIUM",
            (
                f"Forecast spend is {format_amount(forecast_amount, forecast_unit)} "
                f"({forecast_percentage:.1f}% of the budget limit)."
            ),
        )

    return finding(
        "BUDGETS_FORECAST_SPEND_THRESHOLD",
        "PASS",
        "LOW",
        (
            f"Forecast spend is {format_amount(forecast_amount, forecast_unit)} "
            f"({forecast_percentage:.1f}% of the budget limit)."
        ),
    )


def evaluate_budget(budget):
    return [
        evaluate_budget_limit(budget),
        evaluate_actual_spend(budget),
        evaluate_forecast_spend(budget),
    ]
