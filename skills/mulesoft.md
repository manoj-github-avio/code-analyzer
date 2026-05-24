# MuleSoft Knowledge — Code Explainer Skill

This skill teaches you to read and explain MuleSoft Anypoint Platform code to any audience:
developers unfamiliar with MuleSoft, business analysts, or non-technical stakeholders.

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

### Flow anatomy

```xml
<flow name="process-order-flow">
    <!-- 1. Source: what triggers this flow -->
    <http:listener config-ref="HTTP_Listener_config" path="/orders" method="POST"/>

    <!-- 2. Transform: reshape the incoming data -->
    <ee:transform doc:name="Map to Order DTO">
        <ee:message>
            <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{ orderId: payload.id, total: payload.amount }]]></ee:set-payload>
        </ee:message>
    </ee:transform>

    <!-- 3. Process: call a database, API, or queue -->
    <db:insert config-ref="Database_Config" doc:name="Save order">
        <db:sql>INSERT INTO orders (id, total) VALUES (:orderId, :total)</db:sql>
        <db:input-parameters>#[{ orderId: payload.orderId, total: payload.total }]</db:input-parameters>
    </db:insert>

    <!-- 4. Respond -->
    <set-payload value='#[{ "status": "saved" }]' mimeType="application/json"/>
</flow>
```

### Key concepts

- **Payload** — the main data travelling through the flow; changes at each step.
- **Attributes** — metadata about the incoming message (HTTP headers, query params, file name).
- **Variables** — named values stored on the message for use later in the flow (`set-variable`, `vars.myVar`).
- **Target** — an operation can write its result to a named variable instead of replacing the payload,
  using `target="myVar"` and `targetValue="#[payload]"`.

---

## DataWeave 2.0

DataWeave is MuleSoft's functional data-transformation language. It appears inside
`<ee:transform>` blocks. Every DataWeave script has two sections:

```dataweave
%dw 2.0
output application/json   // output media type
---
// transformation expression
```

### Common patterns

| Pattern | Example | Meaning |
|---------|---------|---------|
| Field mapping | `{ name: payload.firstName }` | Rename a field |
| Conditional | `if (payload.age >= 18) "adult" else "minor"` | Branch on value |
| Map array | `payload.items map { id: $.itemId, qty: $.quantity }` | Transform each element |
| Filter | `payload.orders filter ($.status == "OPEN")` | Keep matching items |
| Reduce | `payload.lines reduce ((item, acc = 0) -> acc + item.price)` | Aggregate |
| Type coerce | `payload.amount as Number` | Cast to number |
| String interpolation | `"Hello $(payload.name)"` | Embed value in string |
| pluck (object to array) | `payload pluck { key: $$, value: $ }` | Convert object keys to array |
| Merge objects | `payload ++ { extra: "data" }` | Merge two objects |

### Reading a DataWeave diff

- A new `map` block means array iteration was added — data is now processed element-by-element.
- A new `filter` means records are being excluded before downstream processing.
- A type change (`as Number`, `as String`) means the integration now coerces a value that was passed as-is before.
- Added `if/else` means conditional logic was introduced — the output now varies based on data.
- A field rename (`newName: payload.oldName`) changes the contract with downstream consumers.

---

## Common Connector Types

| Connector | Trigger / Operation examples | What it connects to |
|-----------|------------------------------|---------------------|
| **HTTP** | `http:listener`, `http:request` | REST APIs, webhooks |
| **Salesforce** | `sfdc:query`, `sfdc:create`, `sfdc:update`, on-new-object | Salesforce CRM |
| **Database** | `db:select`, `db:insert`, `db:update`, `db:bulk-insert` | SQL databases (MySQL, Postgres, Oracle) |
| **File / FTP / SFTP** | `file:read`, `ftp:write`, `sftp:list` | File systems |
| **JMS / ActiveMQ / RabbitMQ** | `jms:publish`, `jms:listener` | Message queues |
| **Anypoint MQ** | `anypoint-mq:publish`, `anypoint-mq:subscriber` | MuleSoft cloud queue |
| **Kafka** | `kafka:publish`, `kafka:message-listener` | Kafka topics |
| **Email (SMTP/IMAP)** | `email:send`, `email:listener` | Email servers |
| **SAP** | `sap:function-call` | SAP systems |
| **Workday** | `workday:invoke` | Workday HCM/Financials |
| **ServiceNow** | `servicenow:invoke` | ServiceNow ITSM |
| **Amazon S3 / SQS / SNS** | `s3:put-object`, `sqs:send-message` | AWS services |
| **Azure Service Bus** | `azure-service-bus:send` | Azure messaging |
| **Object Store** | `os:store`, `os:retrieve` | Key-value cache across flows |
| **Scheduler** | `scheduler:inbound-endpoint` | Time-based trigger (cron or fixed) |
| **VM (Virtual Machine)** | `vm:publish`, `vm:listener` | In-memory queue between flows |
| **Aggregators** | `aggregators:group-based-aggregator` | Collect N messages, release as batch |

---

## Error Handling

MuleSoft has structured error handling at flow, sub-flow, and scope level.

### Error handler types

```xml
<error-handler>
    <!-- Catch a specific error and recover -->
    <on-error-continue enableNotifications="true" logException="true"
                       type="HTTP:CONNECTIVITY">
        <set-payload value='#[{ "error": "upstream unavailable" }]'/>
    </on-error-continue>

    <!-- Catch and re-throw (flow fails after this block) -->
    <on-error-propagate type="DB:QUERY_EXECUTION">
        <logger level="ERROR" message='#["DB error: " ++ error.description]'/>
    </on-error-propagate>
</error-handler>
```

| Handler | Behaviour |
|---------|-----------|
| `on-error-continue` | Handles the error; flow returns the payload set inside this block. Flow is considered *successful*. |
| `on-error-propagate` | Handles then re-throws. Caller sees the error. |
| No handler | Error propagates up to the application error handler or returns HTTP 500. |

### Error object fields

- `error.errorType.namespace` — connector namespace (e.g., `HTTP`, `DB`, `SALESFORCE`)
- `error.errorType.identifier` — specific error (e.g., `CONNECTIVITY`, `QUERY_EXECUTION`)
- `error.description` — human-readable message
- `error.cause` — the underlying Java exception
- `error.childErrors` — errors from scatter-gather or parallel operations

### What to look for in a PR

- Moving from `on-error-propagate` to `on-error-continue` changes failure semantics — callers may no longer see the error.
- Adding a specific `type` to an error handler narrows which errors it catches.
- Removing an error handler exposes errors that were previously swallowed.
- Adding `logException="true"` improves observability.

---

## Flow Variables and Properties

### Variables (runtime, per-message)

```xml
<set-variable variableName="customerId" value="#[payload.id]"/>
<!-- Later in the same flow -->
<logger message="#[vars.customerId]"/>
```

Variables live on the current message event. They survive across flow-refs to sub-flows but not
across async operations (scatter-gather branches start with a copy).

### Properties (configuration, static)

Properties are loaded from `.properties` or `.yaml` files and accessed via `${property.key}`.

```xml
<http:listener-config name="HTTP_Listener_config" host="0.0.0.0"
                       port="${http.port}"/>
```

Environment-specific values (URLs, credentials, timeouts) should always be externalised as
properties rather than hardcoded.

### Common patterns in diffs

- A new `set-variable` captures an intermediate value so it can be used after the payload changes.
- Replacing a hardcoded value with `${property.key}` externalises configuration.
- Reading `vars.X` instead of `payload.X` means the flow restructured its data access — the value
  was saved earlier rather than read from the current payload.

---

## Best Practices and Common Patterns

### Meaningful PR changes to watch for

| Change | Why it matters |
|--------|----------------|
| New flow added | New integration path or API endpoint |
| Flow deleted | Feature removed or consolidated |
| HTTP listener path changed | API contract breaking change — clients must update |
| New connector added | New external dependency |
| Timeout value changed | Affects reliability under load |
| Retry policy added / removed | Changes how transient failures are handled |
| Scatter-gather added | Operations now run in parallel — order is non-deterministic |
| `async:async-scope` added | Processing is now fire-and-forget |
| New DataWeave mapping | Data contract changed |
| Error handler added | Previously unhandled errors are now caught |
| Config property extracted | Hardcoded value moved to environment config |
| Batch job added | Large-volume processing introduced |

### Anti-patterns to flag

- Hardcoded credentials or URLs inside XML (should be in properties).
- Missing error handlers on database or HTTP calls.
- `on-error-continue` swallowing errors silently (no logging, no alerting).
- Very large single flows — indicates need for sub-flow decomposition.

---

## How to Explain a MuleSoft PR to Different Audiences

**For developers unfamiliar with MuleSoft:**
Focus on the logical steps — what data comes in, how it is transformed, what external system is
called, and what goes out. Map MuleSoft concepts to familiar analogues (a flow is like a
function; a connector is like an SDK client; DataWeave is like a JSON transformation function).

**For non-technical readers:**
Avoid XML and code entirely. Explain in business terms: what business process does this change
affect, what data moves where, and what happens when something goes wrong. Use plain sentences.

**Always include:**
1. A one-sentence summary of what the change does.
2. Which systems are involved (source and destination).
3. What data is transformed and how (high level).
4. Error handling — what happens when things go wrong.
5. Whether the change is breaking or non-breaking.
