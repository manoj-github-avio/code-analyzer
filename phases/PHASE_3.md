# Phase 3: Code Explainer Agent

## What Was Implemented

A standalone Python script (`src/explainer_agent.py`) that reads a MuleSoft PR diff and produces
a plain-English explanation readable by both MuleSoft developers and non-technical stakeholders.

A reusable MuleSoft knowledge skill (`skills/mulesoft.md`) that teaches Claude about MuleSoft
flows, DataWeave, connectors, error handling, and what to look for in a PR — loaded once and
cached by the Anthropic API for cost efficiency.

A sample diff (`sample-mule-pr.diff`) for local testing without needing a real GitHub PR.

---

## Files Added

| File | Purpose |
|------|---------|
| `src/explainer_agent.py` | CLI script — sends a diff to Claude, streams the explanation |
| `skills/mulesoft.md` | Reusable MuleSoft knowledge base, cached via prompt caching |
| `sample-mule-pr.diff` | Realistic sample diff for testing |

---

## How to Run

### Prerequisites

```bash
# Install dependencies
pip install -e .

# Add your Anthropic API key to .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

### Run with the sample diff

```bash
python src/explainer_agent.py sample-mule-pr.diff
```

### Run with a real diff

```bash
# From a local git repo
git diff HEAD~1 HEAD -- "*.xml" | python src/explainer_agent.py

# From a saved diff file
python src/explainer_agent.py my-pr.diff

# Piped from another command
cat pr-23.diff | python src/explainer_agent.py
```

---

## How It Works

1. The script reads a diff from a file argument or stdin.
2. It loads `skills/mulesoft.md` — a comprehensive MuleSoft reference document.
3. It calls the Claude API (`claude-opus-4-7`) with:
   - The MuleSoft knowledge base as a cached system block (prompt caching reduces cost on repeat runs).
   - The explanation instructions as a second cached system block.
   - The diff as the user message.
4. The response streams to stdout as it arrives.
5. Cache statistics (tokens written / read) print to stderr after completion.

### Prompt caching

The MuleSoft skill and the explanation instructions are marked with `cache_control: ephemeral`.
On the first run the API writes them to cache (slightly higher cost). On subsequent runs within
5 minutes the cached prefix is reused at ~10% of the normal input token cost.

---

## Example Output

Running against `sample-mule-pr.diff` (an order-processing flow that adds Salesforce integration):

```
## Summary
This change extends the order-processing integration to also push orders into Salesforce,
adds multi-currency support, and improves logging and error handling so failures are easier
to diagnose and customers get a friendlier response when the database is unavailable.

## What changed
- Correlation ID tracking added. The incoming request's correlation ID is now saved into
  a variable so it can be included in every log line for this order.
- Order transformation enriched. The order total and line-item prices are now explicitly
  converted to numbers. A currency field is captured, defaulting to "USD". Each line item
  now has a calculated subtotal.
- Database insert now stores currency. Previously hardcoded as 'USD'.
- New step: write the order to Salesforce. After saving to the database, the flow now
  creates a custom Order__c record in Salesforce.
- Logging added. A log line is now emitted when order processing starts.
- Error handling reworked (see below).

## Systems involved
- HTTP (inbound): unchanged, still triggered by POST /api/orders.
- Orders database (existing): still used to insert order header and line items.
- Salesforce (NEW): every order now writes to Salesforce. New external dependency.

## Data flow
1. HTTP POST arrives at /api/orders.
2. Correlation ID captured.
3. Order reshaped: numbers coerced, currency captured, subtotals calculated.
4. Logged.
5. Saved to database (with currency).
6. Created in Salesforce.
7. HTTP 200 returned: { "orderId": ..., "status": "accepted" }.

## Error handling
- Database connectivity errors previously returned 500; now return 503 with a friendly
  "Service temporarily unavailable. Please retry." message. The flow is now considered
  successful even when the DB is unreachable.
- Salesforce errors are caught, logged, and re-thrown — caller sees 500.
- Risk: if the DB write succeeds but Salesforce fails, the order exists in one system
  but not the other. No compensating logic or retry queue is in place.

## Impact assessment
- Breaking: database outage response code changes from 500 to 503.
- Breaking: currency column now stores real values, not always 'USD'.
- New deployment requirement: Salesforce credentials must be configured in every environment.
- Who should test: API consumers (503 handling), Salesforce admin (custom fields exist),
  database/reporting team (currency now varies), QA (multi-currency, outage scenarios).
```

---

## Architecture Notes

- **No custom tools** — this is a single API call, not an agent loop. The diff is sent as
  a user message and Claude returns the explanation directly.
- **Streaming** — the explanation streams to stdout token-by-token for responsive UX.
- **Adaptive thinking** — `thinking: {type: "adaptive"}` lets Claude reason through complex
  diffs before producing the explanation.
- **Prompt caching** — the stable MuleSoft knowledge base and instructions are cached,
  making repeated runs cheaper and faster.
