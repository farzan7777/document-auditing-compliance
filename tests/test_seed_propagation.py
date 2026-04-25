from app.baseline_agent import run_baseline_internal, run_llm_agent


def test_rule_based_baseline_uses_explicit_seeds_in_output():
    result = run_baseline_internal(seeds={1: 111, 2: 222, 3: 333})
    assert result["details"]["task_1"]["seed"] == 111
    assert result["details"]["task_2"]["seed"] == 222
    assert result["details"]["task_3"]["seed"] == 333


def test_llm_baseline_uses_explicit_seeds_even_with_fallback():
    # This holds whether Groq is available or not because details are filled per task
    # from the seed map before scoring/fallback.
    result = run_llm_agent(seeds={1: 444, 2: 555, 3: 666})
    assert result["details"]["task_1"]["seed"] == 444
    assert result["details"]["task_2"]["seed"] == 555
    assert result["details"]["task_3"]["seed"] == 666
