---
name: mulesoft
description: Expert MuleSoft Anypoint Platform knowledge — flows, DataWeave, connectors, error handling, and PR review patterns. Apply this skill whenever reading, explaining, or reviewing MuleSoft XML or DataWeave code.
version: "1.0"
tags: [mulesoft, integration, dataweave, anypoint, xml]
---

# MuleSoft Integration Expert

This skill provides comprehensive MuleSoft Anypoint Platform knowledge for reading, explaining,
and reviewing integration code. Apply it when you encounter MuleSoft XML flows, DataWeave
transformations, or connector configurations.

---

## What Is MuleSoft?

MuleSoft Anypoint Platform is an integration platform used to connect applications, data sources,
and APIs. It runs integration logic as **flows** defined in XML, with transformations written in
**DataWeave** and external connections made through **connectors**.

---

## Flows

A **flow** is the core unit of work in MuleSoft. It processes a message from an inbound event
(a trigger) through a series of steps, producing a result or side effect.

### Types of flows

| Type | Description |
|------|-------------|
| **Flow** | Has an inbound event source (HTTP listener, scheduler, queue). The main entry point. |
| **Sub-flow** | No event source. Called by other flows via `flow-ref`. Reusable logic block. |
| **Private flow** | No event source. Similar to sub-flow but has its own error-handling scope. |

### Key message concepts

- **Payload** — the main data travelling through the flow; changes at each step.
- **Attributes** — metadata about the incoming message (HTTP headers, query params, file name).
- **Variables** — named values stored on the message for later use (`set-variable`, `vars.myVar`).
- **Target** — an operation can write its result to a variable instead of replacing the payload
  using `target="myVar"` and `targetValue="#[payload]"`.

---

## DataWeave 2.0

DataWeave is MuleSoft's functional data-transformation language. It appears inside
`<ee:transform>` blocks and has two sections separated by `---`:

```
%dw 2.0
output application/json     ← output media type
---
{ orderId: payload.id }     ← transformation expression
```

### Common patterns

| Pattern | Example | Meaning |
|---------|---------|---------|
| Field mapping | `{ name: payload.firstName }` | Rename a field |
| Conditional | `if (payload.age >= 18) "adult" else "minor"` | Branch on value |
| Map array | `payload.items map { id: $.itemId, qty: $.quantity }` | Transform each element |
| Filter | `payload.orders filter ($.status == "OPEN")` | Keep matching items |
| Reduce | `payload.lines reduce ((item, acc = 0) -> acc + item.price)` | Aggregate |
| Type coerce | `payload.amount as Number` | Cast to a type |
| Merge objects | `payload ++ { extra: "data" }` | Merge two objects |
| Default value | `payload.currency default "USD"` | Fallback if field is absent |

### Reading a DataWeave diff

- New `map` block → array is now processed element-by-element.
- New `filter` → records excluded before downstream processing.
- Type coerce added (`as Number`) → field was previously passed as-is; now strictly typed.
- New `if/else` → output now varies based on data; test both branches.
- Field rename → downstream contract changed; consumers may break.
- New `default` → null-safety added; previously absent values would have caused errors.

---

## Common Connector Types

| Connector | Key operations | Connects to |
|-----------|---------------|-------------|
| **HTTP** | `http:listener`, `http:request` | REST APIs, webhooks |
| **Salesforce** | `sfdc:query`, `sfdc:create`, `sfdc:update` | Salesforce CRM |
| **Database** | `db:select`, `db:insert`, `db:update`, `db:bulk-insert` | SQL databases |
| **File / FTP / SFTP** | `file:read`, `ftp:write`, `sftp:list` | File systems |
| **JMS / ActiveMQ / RabbitMQ** | `jms:publish`, `jms:listener` | Message queues |
| **Anypoint MQ** | `anypoint-mq:publish`, `anypoint-mq:subscriber` | MuleSoft cloud queue |
| **Kafka** | `kafka:publish`, `kafka:message-listener` | Kafka topics |
| **Email** | `email:send`, `email:listener` | SMTP/IMAP servers |
| **SAP** | `sap:function-call` | SAP ERP |
| **Workday** | `workday:invoke` | Workday HCM/Financials |
| **ServiceNow** | `servicenow:invoke` | ServiceNow ITSM |
| **Amazon S3 / SQS / SNS** | `s3:put-object`, `sqs:send-message` | AWS services |
| **Object Store** | `os:store`, `os:retrieve` | In-memory key-value cache |
| **Scheduler** | `scheduler:inbound-endpoint` | Time-based trigger (cron/fixed) |
| **VM** | `vm:publish`, `vm:listener` | In-memory queue between flows |
| **Aggregators** | `aggregators:group-based-aggregator` | Batch N messages, release together |

---

## Error Handling

MuleSoft error handlers sit at the bottom of a flow or inside a `try` scope.

| Handler | Behaviour |
|---------|-----------|
| `on-error-continue` | Catches the error; flow returns the payload set inside this block. Flow is considered **successful** — caller gets the recovery response. |
| `on-error-propagate` | Catches, optionally logs, then re-throws. Caller still sees the error. |
| No handler | Error propagates to the application-level handler or returns HTTP 500. |

### Key error fields

- `error.errorType.namespace` — connector namespace (`HTTP`, `DB`, `SFDC`, …)
- `error.errorType.identifier` — specific error (`CONNECTIVITY`, `QUERY_EXECUTION`, …)
- `error.description` — human-readable message
- `error.cause` — underlying Java exception

### PR review checklist for error handling

- `on-error-propagate` → `on-error-continue` changes failure semantics; callers may no longer see the error.
- Adding a specific `type="X:Y"` narrows which errors are caught; other errors now propagate.
- Removing an error handler exposes previously-swallowed errors.
- Missing `logException="true"` or no logger means silent failures — flag it.
- `on-error-continue` with no `set-payload` returns the failed payload — usually a bug.

---

## Flow Variables and Properties

### Variables (runtime)

```xml
<set-variable variableName="customerId" value="#[payload.id]"/>
<logger message="#[vars.customerId]"/>  <!-- access later -->
```

Variables live on the current message. They survive flow-refs to sub-flows but each
scatter-gather branch gets its own copy.

### Properties (configuration)

```xml
<http:listener-config port="${http.port}"/>
```

Loaded from `.properties` / `.yaml` files. Environment-specific values (URLs, credentials,
timeouts) must always be externalised — never hardcoded in XML.

---

## Meaningful PR Changes to Flag

| Change | Why it matters |
|--------|----------------|
| New flow added | New integration path or API endpoint |
| Flow deleted | Feature removed or consolidated |
| HTTP listener path changed | Breaking API contract change |
| New connector added | New external dependency; requires config in all environments |
| Timeout value changed | Affects reliability under load |
| Retry policy added/removed | Changes handling of transient failures |
| Scatter-gather added | Operations now run in parallel; order is non-deterministic |
| `async:async-scope` added | Processing is now fire-and-forget; errors won't reach caller |
| DataWeave field rename | Downstream consumers may break |
| Error handler type changed | Failure semantics changed for callers |
| Config property extracted | Hardcoded value moved to environment config — good change |
| Batch job added | Large-volume processing introduced |

## Anti-Patterns to Flag

- Hardcoded credentials or URLs inside XML.
- Missing error handlers on database or HTTP connector calls.
- `on-error-continue` with no logging — silently swallows failures.
- Very large single flows — should be decomposed into sub-flows.
- Multiple operations sharing the same payload without using `target` — fragile coupling.

---

## Explaining to Different Audiences

**Developers unfamiliar with MuleSoft:** Explain logical steps. Map MuleSoft concepts to
familiar analogues — a flow is like a function, a connector is like an SDK client, DataWeave
is a JSON transformation function. Mention what XML elements changed and why.

**Non-technical readers:** No code or XML. Explain in business terms: what process changed,
what data moves where, and what happens when things go wrong. Use plain sentences.

**Always cover:**
1. One-sentence summary of what the change does.
2. Which systems are involved and whether any are new.
3. How data is transformed (high level).
4. Error handling — what happens on failure.
5. Whether the change is breaking and who needs to be notified.
