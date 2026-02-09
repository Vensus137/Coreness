---
title: Placeholders
description: Placeholder syntax, modifiers, and data access in Coreness scenarios.
keywords: placeholders, modifiers, coreness scenarios, dynamic values
---

# Placeholders

**Purpose:** Dynamic value substitution in scenario action parameters.

## Mechanics:

**All attributes in `params` automatically processed by placeholders** before action execution. This means:

- **All values in `params`** — strings, numbers, arrays, objects — go through placeholder processing
- **All nesting levels** — placeholders work at any level of `params` structure (in strings, array elements, object values)
- **Automatic processing** — happens for each scenario step before action execution
- **Data source** — system uses accumulated event data and previous action results as value source for substitution

## Placeholder Syntax:

**Simple replacement:**
```yaml
params:
  text: "Hello, {username}!"
  chat_id: "{user_id}"
```

**With modifiers:**
```yaml
params:
  text: "Hello, {username|fallback:Guest}!"
  price: "{amount|*0.9|format:currency}"
```

**Literal values in quotes:**
```yaml
params:
  text: "{'hello'|upper}"                      # HELLO (without passing through dictionary)
  duration: "{'1d 2w'|seconds}"                # 1296000 (literal time)
  calculation: "{'100'|+50}"                   # 150 (literal arithmetic)
  date_shift: "{'2024-12-25'|shift:+1 day}"   # 2024-12-26 (literal date)
  # Double quotes for strings with single quotes
  text: "{"it's working"}"                     # it's working
  # Escaped quotes
  text: "{'it\'s working'}"                    # it's working
```

**Nested placeholders:**
```yaml
params:
  text: "Answer: {status|equals:{expected}|value:OK|fallback:BAD}"
```

## ⚠️ Important: YAML Quotes for Placeholders with regex

**Problem:** YAML processes escape sequences differently in single and double quotes, which is critical for regex patterns with backslashes.

**Solution:** Use **double quotes** for regex patterns with backslashes (`\s`, `\d`, `\w`, etc.).

**Examples:**

```yaml
# ❌ ERROR - in single quotes \\s doesn't escape correctly
params:
  value: '{event_text|regex:^([^\\s]+)|lower}'  # \\s becomes \s (backslash + s), not space!

# ✅ CORRECT - double quotes correctly escape backslashes
params:
  value: "{event_text|regex:^([^\\s]+)|lower}"  # \\s becomes \s (space in regex)

# ✅ CORRECT - for regex without backslashes can use single quotes
params:
  tenant_id: '{user_state|regex:tenant_(\d+)}'  # Works, as \d doesn't require double escaping

# ✅ CORRECT - for simple regex with one backslash also use double quotes
params:
  value: "{event_text|regex:\\s+([^\\s]+)$|lower}"  # \\s for space, \\s for space

# ✅ REGULAR PLACEHOLDERS - no difference
params:
  text: "Hello, {username}!"     # Works
  text: 'Hello, {username}!'    # Also works
```

**When to use double quotes:**
- **Regex patterns with backslashes** — `{field|regex:pattern}` where pattern contains `\s`, `\d`, `\w`, `\n`, `\t`, etc.
- **Important:** In double quotes need to use double escaping: `\\s` for space, `\\d` for digit
- **Example:** `"{event_text|regex:^([^\\s]+)|lower}"` — `\\s` becomes `\s` (space in regex)

**When can use single quotes:**
- **Regex patterns without backslashes** — simple patterns without `\s`, `\d`, `\w`, etc.
- **Regular placeholders** — `{username}`, `{user_id}`
- **Simple modifiers** — `{name|upper}`, `{price|format:currency}`
- **Text values** — without special characters

**Rule:** If regex pattern has backslashes (`\s`, `\d`, `\w`, etc.) — **always use double quotes** with double escaping (`\\s`, `\\d`, `\\w`).

**Access to nested data:**
```yaml
params:
  # Dot notation for objects
  text: "User: {user.profile.name|fallback:Unknown}"
  text: "Message: {message.text}"
  
  # Indexes for arrays
  text: "First file: {attachment[0].file_id}"
  text: "Last user: {users[-1].name}"
  
  # Combined access
  text: "Event: {event.attachment[0].type}"
  text: "Data: {response.data.items[0].value}"
```

## Available Data:

**All event and previous action data available for use in placeholders:**

**Event data:**
- **`user_id`** — user ID
- **`username`** — username  
- **`chat_id`** — chat ID
- **`event_text`** — message text
- **`callback_data`** — callback button data
- **`event_date`** — event time
- **`tenant_id`** — tenant ID
- **`message_id`** — message ID
- **`reply_to_message_id`** — ID of message being replied to
- **`forward_from`** — forwarding data
- **And any other fields** — depending on event type

**Tenant configuration:**
- **`_config`** — dictionary with tenant configuration (attributes from `config.yaml`)
  - **`_config.ai_token`** — AI API key for tenant (if set)
  - **Other attributes** — depending on tenant configuration
  - Automatically available in all tenant scenarios

**Previous action data:**
- **`last_message_id`** — last sent message ID
- **`response_data`** — any data returned by previous actions
- **Other fields** — depending on actions in scenario

## Accessing Nested Elements:

> **Universal data access!** Support for dot notation for objects and indexes for arrays.

<table>
<thead>
<tr><th>Syntax</th><th>Description</th><th>Example</th><th>Result</th></tr>
</thead>
<tbody>
<tr><td colspan="4"><strong>Objects</strong></td></tr>
<tr><td><code>object.field</code></td><td>Access object field</td><td><code>{message.text}</code></td><td><code>Hello world</code></td></tr>
<tr><td><code>object.field.subfield</code></td><td>Nested fields</td><td><code>{user.profile.name}</code></td><td><code>John Doe</code></td></tr>
<tr><td colspan="4"><strong>Arrays</strong></td></tr>
<tr><td><code>array[index]</code></td><td>Access array element</td><td><code>{attachment[0].file_id}</code></td><td><code>file_1</code> (first file)</td></tr>
<tr><td><code>array[-index]</code></td><td>Negative index</td><td><code>{attachment[-1].file_id}</code></td><td><code>file_3</code> (last file)</td></tr>
<tr><td><code>array[index].field</code></td><td>Array element field</td><td><code>{users[1].name}</code></td><td><code>Bob</code> (second user name)</td></tr>
<tr><td><code>array[index][index]</code></td><td>Nested arrays</td><td><code>{matrix[0][1]}</code></td><td><code>2</code> (matrix element)</td></tr>
<tr><td colspan="4"><strong>Combined</strong></td></tr>
<tr><td><code>object.array[index].field</code></td><td>Mixed access</td><td><code>{event.attachment[0].file_id}</code></td><td><code>file_1</code></td></tr>
</tbody>
</table>

**Usage Examples:**
```yaml
params:
  # Objects
  text: "Message: {message.text}"
  text: "User: {user.profile.name|fallback:Unknown}"
  
  # Arrays
  text: "First file: {attachment[0].file_id}"
  text: "Last user: {users[-1].name|upper}"
  text: "File: {attachment[0].file_id}, size: {attachment[0].size}"
  
  # Combined access
  text: "Event: {event.attachment[0].type}"
  text: "Data: {response.data.items[0].value}"
  
  # Tenant configuration
  text: "Token: {_config.ai_token|fallback:Not set}"
  
  # Safe access
  text: "{attachment[10].file_id|fallback:File not found}"
```

## Getting File Information

**Practical example: Getting file_id and type for forwarding files**

Create scenario that shows file_id and type of all event attachments:

```yaml
file_info:
  description: "Getting file_id and type of attachments for subsequent forwarding"
  trigger:
    - event_type: "message"
      event_text: "/file"

  step:
    - action: "send_message"
      params:
        text: |
          📎 File information:
          
          file_id: <code>{event_attachment[0].file_id|fallback:{reply_attachment[0].file_id|fallback:File not found}}</code>
          type: <code>{event_attachment[0].type|fallback:{reply_attachment[0].type|fallback:Type not found}}</code>
```

**Error handling:**
- When accessing non-existent field/index returns `None`
- Can use `fallback` modifier for default value
- Negative indexes work like in Python: `-1` = last element
- Unlimited nesting depth supported

## Modifiers:

<table>
<thead>
<tr><th>Modifier</th><th>Description</th><th>Example</th><th>Result</th></tr>
</thead>
<tbody>
<tr><td colspan="4"><strong>Arithmetic Operations</strong></td></tr>
<tr><td><code>+value</code></td><td>Addition</td><td><code>{price|+100}</code></td><td><code>1500</code> (if price=1400)</td></tr>
<tr><td><code>-value</code></td><td>Subtraction</td><td><code>{price|-50}</code></td><td><code>1350</code> (if price=1400)</td></tr>
<tr><td><code>*value</code></td><td>Multiplication</td><td><code>{price|*0.9}</code></td><td><code>1260</code> (if price=1400)</td></tr>
<tr><td><code>/value</code></td><td>Division</td><td><code>{seconds|/3600}</code></td><td><code>2.5</code> (if seconds=9000)</td></tr>
<tr><td><code>%value</code></td><td>Modulo</td><td><code>{number|%7}</code></td><td><code>3</code> (if number=10)</td></tr>
<tr><td colspan="4"><strong>Case</strong></td></tr>
<tr><td><code>upper</code></td><td>Uppercase</td><td><code>{name|upper}</code></td><td><code>JOHN</code> (if name="John")</td></tr>
<tr><td><code>lower</code></td><td>Lowercase</td><td><code>{name|lower}</code></td><td><code>john</code> (if name="John")</td></tr>
<tr><td><code>title</code></td><td>Title case each word</td><td><code>{name|title}</code></td><td><code>John Doe</code> (if name="john doe")</td></tr>
<tr><td><code>capitalize</code></td><td>First letter uppercase</td><td><code>{name|capitalize}</code></td><td><code>John</code> (if name="john")</td></tr>
<tr><td><code>case:type</code></td><td>Case conversion</td><td><code>{name|case:upper}</code></td><td><code>JOHN</code> (if name="John")</td></tr>
<tr><td colspan="4"><strong>Lists</strong></td></tr>
<tr><td><code>tags</code></td><td>Convert to tags</td><td><code>{users|tags}</code></td><td><code>@user1 @user2</code></td></tr>
<tr><td><code>list</code></td><td>Bulleted list</td><td><code>{items|list}</code></td><td><code>• item1\n• item2</code></td></tr>
<tr><td><code>comma</code></td><td>Comma separated</td><td><code>{items|comma}</code></td><td><code>item1, item2</code></td></tr>
<tr><td><code>expand</code></td><td>Expand array of arrays one level (in arrays only)</td><td><code>{keyboard|expand}</code></td><td><code>[[a, b], [c]]</code> → <code>[a, b], [c]</code> (in array)</td></tr>
<tr><td><code>keys</code></td><td>Extract keys from object (dict) to array</td><td><code>{storage_values|keys}</code></td><td><code>["group1", "group2"]</code> (if storage_values={"group1": {...}, "group2": {...}})</td></tr>
<tr><td colspan="4"><strong>Transformations</strong></td></tr>
<tr><td><code>code</code></td><td>Wrap value in code block</td><td><code>{field|code}</code></td><td><code>&lt;code&gt;value&lt;/code&gt;</code></td></tr>
<tr><td colspan="4"><strong>String Formatting</strong></td></tr>
<tr><td><code>truncate:length</code></td><td>Truncate text</td><td><code>{text|truncate:50}</code></td><td><code>Very long text...</code></td></tr>
<tr><td colspan="4"><strong>Date & Time Operations</strong></td></tr>
<tr><td><code>shift:±interval</code></td><td>Shift date by interval (PostgreSQL style: +1 day, -2 hours, +1 year 2 months). Supports all date formats including ISO with timezone, correct month/year handling</td><td><code>{created|shift:+1 day}</code></td><td><code>2024-12-26</code> (if created="2024-12-25")</td></tr>
<tr><td><code>seconds</code></td><td>Convert time strings to seconds (supports format: Xw Yd Zh Km Ms)</td><td><code>{duration|seconds}</code></td><td><code>9000</code> (if duration="2h 30m")</td></tr>
<tr><td><code>to_date</code></td><td>Round date to day start (00:00:00), returns ISO format</td><td><code>{created|to_date}</code></td><td><code>2024-12-25 00:00:00</code></td></tr>
<tr><td><code>to_hour</code></td><td>Round date to hour start (minutes and seconds = 0), returns ISO format</td><td><code>{created|to_hour}</code></td><td><code>2024-12-25 15:00:00</code> (if created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_minute</code></td><td>Round date to minute start (seconds = 0), returns ISO format</td><td><code>{created|to_minute}</code></td><td><code>2024-12-25 15:30:00</code> (if created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_second</code></td><td>Round date to second start (microseconds = 0), returns ISO format</td><td><code>{created|to_second}</code></td><td><code>2024-12-25 15:30:45</code></td></tr>
<tr><td><code>to_week</code></td><td>Round date to week start (Monday 00:00:00), returns ISO format</td><td><code>{created|to_week}</code></td><td><code>2024-12-23 00:00:00</code> (if created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_month</code></td><td>Round date to month start (1st day, 00:00:00), returns ISO format</td><td><code>{created|to_month}</code></td><td><code>2024-12-01 00:00:00</code> (if created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_year</code></td><td>Round date to year start (January 1st, 00:00:00), returns ISO format</td><td><code>{created|to_year}</code></td><td><code>2024-01-01 00:00:00</code> (if created="2024-12-25 15:30:45")</td></tr>
<tr><td colspan="4"><strong>Date & Time Formatting</strong></td></tr>
<tr><td><code>format:timestamp</code></td><td>Convert to Unix timestamp</td><td><code>{date|format:timestamp}</code></td><td><code>1703512200</code></td></tr>
<tr><td><code>format:date</code></td><td>Date format (dd.mm.yyyy)</td><td><code>{timestamp|format:date}</code></td><td><code>25.12.2024</code></td></tr>
<tr><td><code>format:time</code></td><td>Time format (HH:MM)</td><td><code>{timestamp|format:time}</code></td><td><code>14:30</code></td></tr>
<tr><td><code>format:time_full</code></td><td>Time format with seconds (HH:MM:SS)</td><td><code>{timestamp|format:time_full}</code></td><td><code>14:30:45</code></td></tr>
<tr><td><code>format:datetime</code></td><td>Full format (dd.mm.yyyy HH:MM)</td><td><code>{timestamp|format:datetime}</code></td><td><code>25.12.2024 14:30</code></td></tr>
<tr><td><code>format:datetime_full</code></td><td>Full format with seconds (dd.mm.yyyy HH:MM:SS)</td><td><code>{timestamp|format:datetime_full}</code></td><td><code>25.12.2024 14:30:45</code></td></tr>
<tr><td><code>format:pg_date</code></td><td>PostgreSQL date format (YYYY-MM-DD)</td><td><code>{timestamp|format:pg_date}</code></td><td><code>2024-12-25</code></td></tr>
<tr><td><code>format:pg_datetime</code></td><td>PostgreSQL date-time format (YYYY-MM-DD HH:MM:SS)</td><td><code>{timestamp|format:pg_datetime}</code></td><td><code>2024-12-25 14:30:45</code></td></tr>
<tr><td colspan="4"><strong>Number Formatting</strong></td></tr>
<tr><td><code>format:currency</code></td><td>Currency formatting</td><td><code>{amount|format:currency}</code></td><td><code>1000.00 ₽</code></td></tr>
<tr><td><code>format:percent</code></td><td>Percentage formatting</td><td><code>{value|format:percent}</code></td><td><code>25.5%</code></td></tr>
<tr><td><code>format:number</code></td><td>Number formatting</td><td><code>{value|format:number}</code></td><td><code>1234.56</code></td></tr>
<tr><td colspan="4"><strong>Conditional</strong></td></tr>
<tr><td><code>equals:value</code></td><td>Equality check (string comparison)</td><td><code>{status|equals:active}</code></td><td><code>true</code> or <code>false</code></td></tr>
<tr><td><code>in_list:items</code></td><td>Check inclusion in list</td><td><code>{role|in_list:admin,moderator}</code></td><td><code>true</code> or <code>false</code></td></tr>
<tr><td><code>true</code></td><td>Truth check (recommended for boolean)</td><td><code>{is_active|true}</code></td><td><code>true</code> or <code>false</code></td></tr>
<tr><td><code>exists</code></td><td>Check value existence (not None and not empty string)</td><td><code>{field|exists}</code></td><td><code>true</code> or <code>false</code></td></tr>
<tr><td><code>is_null</code></td><td>Check for null (None, empty string or string "null")</td><td><code>{field|is_null}</code></td><td><code>true</code> or <code>false</code></td></tr>
<tr><td><code>value:result</code></td><td>Return value when true</td><td><code>{status|equals:active|value:Active}</code></td><td><code>Active</code> or <code>null</code></td></tr>
<tr><td colspan="4"><strong>Utility</strong></td></tr>
<tr><td><code>fallback:value</code></td><td>Default value</td><td><code>{username|fallback:Guest}</code></td><td><code>John</code> or <code>Guest</code></td></tr>
<tr><td><code>length</code></td><td>Count length</td><td><code>{text|length}</code></td><td><code>15</code> (character count)</td></tr>
<tr><td><code>length</code></td><td>Count array length</td><td><code>{array|length}</code></td><td><code>3</code> (element count)</td></tr>
<tr><td><code>regex:pattern</code></td><td>Extract by regex</td><td><code>{text|regex:(\d+)}</code></td><td><code>123</code> (first number)</td></tr>
<tr><td colspan="4"><strong>Async Actions</strong></td></tr>
<tr><td><code>ready</code></td><td>Check async action readiness</td><td><code>{_async_action.ai_req_1|ready}</code></td><td><code>true</code> if completed, <code>false</code> if executing</td></tr>
<tr><td><code>not_ready</code></td><td>Check action still executing</td><td><code>{_async_action.ai_req_1|not_ready}</code></td><td><code>true</code> if executing, <code>false</code> if ready</td></tr>
</tbody>
</table>

## Usage Examples:

```yaml
params:
  # Simple operations
  result: "{value|+100|format:currency}"
  
  # Conditional logic
  status: "{user_status|equals:active|value:Active|fallback:Inactive}"
  
  # Modifier chain
  formatted: "{price|*0.9|format:currency|fallback:0.00 ₽}"
  
  # Regex extraction (use double quotes for backslashes!)
  duration: "{event_text|regex:(\\d+)\\s*min|fallback:0}"
  
  # Dot notation
  name: "{user.profile.name|fallback:Unknown}"
  
  # Time values
  duration_seconds: "{duration|seconds}"
  duration_minutes: "{duration|seconds|/60}"
  duration_hours: "{duration|seconds|/3600}"
  formatted_time: "{duration|seconds|format:number}"
  
  # Date shifting
  tomorrow: "{created|shift:+1 day}"
  next_month: "{created|shift:+1 month|format:date}"
  complex_shift: "{created|shift:+1 year 2 months|format:datetime}"
  
  # Rounding to period start
  start_of_day: "{created|to_date}"
  start_of_week: "{created|to_week}"
  formatted_month_start: "{created|to_month|format:date}"
  
  # Boolean fields (distinguish True/False/None)
  is_active: "{is_active|equals:True|value:✅ Enabled|fallback:{is_active|equals:False|value:❌ Disabled|fallback:❓ Unknown}}"
  is_polling: "{is_polling|equals:True|value:✅ Active|fallback:{is_polling|equals:False|value:❌ Inactive|fallback:❓ Unknown}}"
  
  # String fields (use equals:value)
  status: "{user_status|equals:active|value:Active|fallback:Inactive}"
  
  # Simplified version (if None not expected)
  is_simple: "{is_active|true|value:✅ Enabled|fallback:❌ Disabled}"
  
  # Check value existence (in conditions)
  # In conditions use: {field|exists} == True or {field|exists} == False
  
  # Check for null (in conditions)
  # In conditions use: {field|is_null} == True or {field|is_null} == False
```

**Example using exists in conditions:**

```yaml
step:
  - action: "validate"
    params:
      condition: "{response_value.feedback|exists} == True"
    transition:
      - action_result: "success"
        transition_action: "continue"  # Value exists
      - action_result: "failed"
        transition_action: "jump_to_scenario"
        transition_value: "create_feedback"  # Value doesn't exist
```

## Important: boolean vs string fields

**For boolean fields (True/False):**
- **Recommended:** `{is_active|true|value:✅ Enabled|fallback:❌ Disabled}`
- **Doesn't work:** `{is_active|equals:true|value:✅ Enabled}` (string comparison)

**For string fields:**
- **Use:** `{status|equals:active|value:Active|fallback:Inactive}`
- `true` modifier not suitable for string values

## Practical Examples:

#### **Example 1: Personalized greeting**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        👋 Hello, {username|fallback:Guest}!
        
        📊 Your statistics:
        • ID: {user_id}
        • Chats: {chat_count|fallback:0}
        • Last login: {last_login|format:datetime|fallback:Unknown}
```

#### **Example 2: Dynamic menu with conditions**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        🎛️ Main Menu
        
        Status: {user_status|equals:active|value:✅ Active|fallback:❌ Inactive}
        Balance: {balance|format:currency|fallback:0.00 ₽}
      inline:
        - [{"📊 Statistics": "stats"}, {"💰 Balance": "balance"}]
        - [{"⚙️ Settings": "settings"}]
```

#### **Example 3: Error handling with fallback**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        ❌ Processing error
        
        Error code: {error_code|fallback:UNKNOWN}
        Message: {error_message|fallback:Unknown error}
        Time: {timestamp|format:datetime}
      inline:
        - [{"🔄 Retry": "retry"}, {"🏠 Main Menu": "main"}]
```

#### **Example 4: Mathematical calculations**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        💰 Cost calculation
        
        Price: {base_price|format:currency}
        Discount: {discount_percent|fallback:0}%
        Total: {base_price|*{discount_percent|/100}|*{base_price|-1}|+{base_price}|format:currency}
```

#### **Example 5: Extracting data from text**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        📝 Processing order
        
        Order number: "{event_text|regex:order\\s*(\\d+)|fallback:Not found}"
        Amount: "{event_text|regex:amount\\s*(\\d+)|format:currency|fallback:0.00 ₽}"
        Delivery time: "{event_text|regex:(\\d+)\\s*min|fallback:30}" minutes
```

#### **Example 6: Dynamic keyboard with expand modifier**
```yaml
step:
  # Get tenant list
  - action: "get_tenants_list"
    params: {}
  
  # Build dynamic keyboard from public tenants
  - action: "build_keyboard"
    params:
      items: "{public_tenant_ids}"
      keyboard_type: "inline"
      text_template: "Tenant $value$"
      callback_template: "select_tenant_$value$"
      buttons_per_row: 2
  
  # Send message with dynamic keyboard + static buttons
  - action: "send_message"
    params:
      text: "Select tenant:"
      inline:
        - "{keyboard|expand}"              # Expand dynamic keyboard
        - [{"🔙 Back": "main_menu"}]      # Static button
```

**How `expand` works:**
- `expand` modifier expands array of arrays one level **only when used in array**
- In example above `{keyboard|expand}` in `inline` array expands `[[{...}, {...}], [{...}]]` to `[{...}, {...}], [{...}]`
- This allows combining dynamically generated keyboard rows with static rows
- **Important:** `expand` works only in array context. In string or dict value remains unchanged

**Example without expand (incorrect):**
```yaml
inline:
  - "{keyboard}"                           # ❌ Gets [[[...]], [...]] - 3 nesting levels!
  - [{"🔙 Back": "main_menu"}]
```

**Example with expand (correct):**
```yaml
inline:
  - "{keyboard|expand}"                     # ✅ Gets [[...], [...]] - 2 nesting levels
  - [{"🔙 Back": "main_menu"}]
```
