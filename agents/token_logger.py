_token_log = []

def reset_tokens():
    global _token_log
    _token_log = []

def log_tokens(agent, prompt_tokens, completion_tokens):
    _token_log.append({
        "agent": agent,
        "input": prompt_tokens,
        "output": completion_tokens,
        "total": prompt_tokens + completion_tokens
    })

def get_token_summary():
    return {
        "by_agent": _token_log,
        "total_input": sum(t["input"] for t in _token_log),
        "total_output": sum(t["output"] for t in _token_log),
        "total_tokens": sum(t["total"] for t in _token_log),
        "estimated_cost_usd": round(sum(t["total"] for t in _token_log) * 0.0000001, 6)
    }
