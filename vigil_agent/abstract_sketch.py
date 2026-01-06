"""抽象草图生成器 (Abstract Sketch Generator)

这是VIGIL框架的Intent Anchor增强组件，负责生成任务的抽象执行草图。

设计原则：
1. High-Level Planning: 生成抽象的执行步骤，不涉及具体工具
2. Immutable Anchor: 作为不可变的"北极星"指导整个执行过程
3. Constraint-Rich: 包含约束条件，防止任务漂移

Example:
  Query: "Book a hotel in Paris"
  Sketch: Search → Filter → Select → Book
  Constraints: Read-Only until Book, No External Communication
"""

import json
import logging
from typing import Any

import openai
from pydantic import BaseModel

from vigil_agent.config import VIGILConfig
from vigil_agent.token_stats_tracker import TokenStatsTracker, get_global_tracker

logger = logging.getLogger(__name__)


class AbstractStep(BaseModel):
    """抽象执行步骤"""

    step_id: str
    """步骤ID"""

    step_type: str
    """步骤类型 (SEARCH, FILTER, SELECT, CREATE, UPDATE, DELETE, SEND, etc.)"""

    description: str
    """步骤描述"""

    allowed_operations: list[str] | None = None
    """允许的操作类型"""

    forbidden_operations: list[str] | None = None
    """禁止的操作类型"""

    expected_tools: list[str] | None = None
    """预期使用的工具名称（可选）"""

    tool_candidates: list[str] | None = None
    """工具候选集：所有可能支持完成此步骤的工具名称列表
    遵循 "Recall Relevant, Retain Ambiguity" 原则：
    - 剔除完全无关的工具
    - 保留所有声称能解决问题的工具（包括恶意副本）
    """


class AbstractSketch(BaseModel):
    """抽象执行草图"""

    user_query: str
    """用户查询"""

    steps: list[AbstractStep]
    """执行步骤序列"""

    global_constraints: list[str]
    """全局约束"""

    expected_outcome: str
    """预期结果"""

    metadata: dict[str, Any] | None = None
    """元数据"""


# 默认的草图生成提示模板 (原始版本 - 已弃用)

# 改进的草图生成提示模板 (推荐用于非OpenAI模型)
# DEFAULT_SKETCH_PROMPT = """[ROLE]You are an AI task planner that generates ABSTRACT execution sketches.

# [TASK]\nYour task: Analyze the user's query and create a high-level execution plan in JSON format.

# [COMMON STEP TYPES]:
# - SEARCH: Find relevant information
# - FILTER: Narrow down results based on criteria
# - SELECT: Choose a specific option
# - READ: Retrieve detailed information
# - CREATE: Create a new resource
# - UPDATE: Modify existing resource
# - DELETE: Remove a resource
# - SEND: Send message/data to external party

# [CRITICAL FORMAT REQUIREMENTS]:
# 1. "allowed_operations" MUST be an array (list), NEVER a string
# 2. "forbidden_operations" MUST be an array (list), NEVER a string
# 3. Each operation in the arrays must be a separate string element

# WRONG FORMAT ❌:
# {{
#   "allowed_operations": "READ",  // ❌ WRONG: string instead of array
#   "forbidden_operations": "WRITE, DELETE, SEND"  // ❌ WRONG: comma-separated string
# }}

# CORRECT FORMAT ✅:
# {{
#   "allowed_operations": ["READ"],  // ✅ CORRECT: array with one element
#   "forbidden_operations": ["WRITE", "DELETE", "SEND"]  // ✅ CORRECT: array with multiple elements
# }}

# IMPORTANT PRINCIPLES:
# 1. Generate ABSTRACT steps (e.g., "Search", "Filter", "Select") not concrete tool names
# 2. Define what operations are ALLOWED and FORBIDDEN at each step
# 3. Create a SEQUENTIAL plan that serves as an immutable guide
# 4. Consider security: minimize permissions, avoid unnecessary operations

# USER QUERY: {user_query}

# You MUST output a JSON object. Here are examples:

# Example 1 - For "Book a hotel in Paris":
# {{
#   "steps": [
#     {{
#       "step_id": "step_1",
#       "step_type": "SEARCH",
#       "description": "Search for hotels in Paris",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND"]
#     }},
#     {{
#       "step_id": "step_2",
#       "step_type": "FILTER",
#       "description": "Filter hotels by criteria",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND"]
#     }},
#     {{
#       "step_id": "step_3",
#       "step_type": "SELECT",
#       "description": "Select the best hotel option",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND"]
#     }},
#     {{
#       "step_id": "step_4",
#       "step_type": "CREATE",
#       "description": "Create hotel booking",
#       "allowed_operations": ["READ", "WRITE", "CREATE"],
#       "forbidden_operations": ["DELETE", "SEND"]
#     }},
#     {{
#       "step_id": "step_5",
#       "step_type": "VERIFY",
#       "description": "Verify booking was successful",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND"]
#     }}
#   ],
#   "global_constraints": [
#     "Read-only until final booking step",
#     "No external communication except for booking confirmation",
#     "Only interact with Paris hotels"
#   ],
#   "expected_outcome": "Successfully book a hotel in Paris"
# }}

# Example 2 - For "Send email to John with meeting notes":
# {{
#   "steps": [
#     {{
#       "step_id": "step_1",
#       "step_type": "READ",
#       "description": "Retrieve meeting notes",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND"]
#     }},
#     {{
#       "step_id": "step_2",
#       "step_type": "SEND",
#       "description": "Send email to John",
#       "allowed_operations": ["READ", "SEND"],
#       "forbidden_operations": ["WRITE", "DELETE"]
#     }},
#     {{
#       "step_id": "step_3",
#       "step_type": "VERIFY",
#       "description": "Confirm email was sent",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND"]
#     }}
#   ],
#   "global_constraints": [
#     "Only send to John, no other recipients",
#     "Only access meeting notes, no other files",
#     "No modifications to original notes"
#   ],
#   "expected_outcome": "Email with meeting notes sent to John"
# }}

# FIELD SPECIFICATIONS:
# - step_type: String - one of "SEARCH", "FILTER", "SELECT", "READ", "CREATE", "UPDATE", "DELETE", "SEND", "VERIFY"
# - allowed_operations: Array of strings - operations allowed in this step (e.g., ["READ", "WRITE"])
# - forbidden_operations: Array of strings - operations forbidden in this step (e.g., ["DELETE", "SEND"])
# - expected_tools: Array of strings (optional) - specific tool names expected to be used (e.g., ["read_file", "send_email"])
# - Available operations: "READ", "WRITE", "DELETE", "SEND", "CREATE", "UPDATE"

# REMINDER: allowed_operations and forbidden_operations are ALWAYS arrays [], NEVER strings!

# Now generate the abstract sketch for the user query. Output ONLY valid JSON:"""

# DEFAULT_SKETCH_PROMPT = """[ROLE]You are an AI task planner that generates ABSTRACT execution sketches.

# [TASK]\nYour task: Analyze the user's query and create a high-level execution plan in JSON format.

# [COMMON STEP TYPES]:
# - SEARCH: Query lists or find resources (e.g., search emails, files, calendar events, hotels, contacts).
# - READ: Retrieve detailed content or status (e.g., read file, get user info, check balance, read messages, get webpage).
# - CREATE: Initialize new resources (e.g., create file, create calendar event, schedule transaction).
# - UPDATE: Modify existing resources (e.g., update password, reschedule event, append to file, update user info).
# - DELETE: Remove or cancel resources (e.g., delete email/file, cancel event, remove user).
# - SEND: Transmit communication (e.g., send email, send Slack message, post webpage).
# - BOOK: Execute reservation actions (e.g., reserve hotel, restaurant, or car rental).
# - TRANSFER: Execute financial movement (e.g., send money/bank transfer).
# - SHARE: Grant access or invite users (e.g., share file, invite to Slack, add event participants).
# - REASONING: Analyze and synthesize information without tool calls (e.g., compare options, make decision based on data, summarize results).

# [CRITICAL FORMAT REQUIREMENTS]:
# 1. "allowed_operations" MUST be an array (list), NEVER a string
# 2. "forbidden_operations" MUST be an array (list), NEVER a string
# 3. Each operation in the arrays must be a separate string element

# WRONG FORMAT ❌:
# {{
#   "allowed_operations": "READ",  // ❌ WRONG: string instead of array
#   "forbidden_operations": "WRITE, DELETE, SEND"  // ❌ WRONG: comma-separated string
# }}

# CORRECT FORMAT ✅:
# {{
#   "allowed_operations": ["READ"],  // ✅ CORRECT: array with one element
#   "forbidden_operations": ["WRITE, DELETE", "SEND"]  // ✅ CORRECT: array with multiple elements
# }}

# IMPORTANT PRINCIPLES:
# 1. Generate ABSTRACT steps (e.g., "Search", "Filter", "Select") not concrete tool names.
# 2. Define what operations are ALLOWED and FORBIDDEN at each step.
# 3. Create a SEQUENTIAL plan that serves as an immutable guide.
# 4. Consider security: minimize permissions, avoid unnecessary operations.
# 5. **[CRITICAL] Enrich each step with a specific, inferred `description`:**
#    - The description must act as a supplement to the abstract step.
#    - You must INFER specific entity types from the user query. For example, if the user mentions "Le Marais Boutique", you must infer it is a **hotel** and specify "Search for the *hotel* named Le Marais Boutique" in the description.
#    - It should bridge the gap between the abstract type and specific user data, explaining *exactly what* needs to be done, but keep it concise (under 20 words).

# USER QUERY: {user_query}

# You MUST output a JSON object. Here are examples:

# Example 1 - For "Book a hotel in Paris":
# {{
#   "steps": [
#     {{
#       "step_id": "step_1",
#       "step_type": "SEARCH",
#       "description": "Search for hotels in Paris",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND", "BOOK", "TRANSFER"]
#     }},
#     {{
#       "step_id": "step_2",
#       "step_type": "READ",
#       "description": "Read details and reviews of top hotels",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND", "BOOK"]
#     }},
#     {{
#       "step_id": "step_3",
#       "step_type": "BOOK",
#       "description": "Execute reservation for the selected hotel",
#       "allowed_operations": ["READ", "BOOK"],
#       "forbidden_operations": ["DELETE", "SEND", "TRANSFER", "UPDATE"]
#     }}
#   ],
#   "global_constraints": [
#     "Read-only until final booking step",
#     "No financial transfers allowed (only booking)",
#     "Only interact with Paris hotels"
#   ],
#   "expected_outcome": "Successfully book a hotel in Paris"
# }}

# Example 2 - For "Send 'meeting_notes.txt' to John":
# {{
#   "steps": [
#     {{
#       "step_id": "step_1",
#       "step_type": "SEARCH",
#       "description": "Locate the file named 'meeting_notes.txt' in the cloud drive",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND", "UPDATE"]
#     }},
#     {{
#       "step_id": "step_2",
#       "step_type": "READ",
#       "description": "Read the content of 'meeting_notes.txt' to prepare for sending",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND", "UPDATE"]
#     }},
#     {{
#       "step_id": "step_3",
#       "step_type": "SEARCH",
#       "description": "Find the email contact information for 'John'",
#       "allowed_operations": ["READ"],
#       "forbidden_operations": ["WRITE", "DELETE", "SEND"]
#     }},
#     {{
#       "step_id": "step_4",
#       "step_type": "SEND",
#       "description": "Send an email to John containing the 'meeting_notes.txt' file content",
#       "allowed_operations": ["READ", "SEND"],
#       "forbidden_operations": ["WRITE", "DELETE", "UPDATE", "TRANSFER"]
#     }}
#   ],
#   "global_constraints": [
#     "Only send to John, no other recipients",
#     "Only access 'meeting_notes.txt', no other files",
#     "No modifications to original file content"
#   ],
#   "expected_outcome": "Email with meeting notes sent to John"
# }}

# FIELD SPECIFICATIONS:
# - step_type: String - MUST be one of: "SEARCH", "READ", "CREATE", "UPDATE", "DELETE", "SEND", "BOOK", "TRANSFER", "SHARE"
# - description: String - A specific, inferred explanation of the step (e.g., "Search for the *hotel* X", "Read the *file* Y").
# - allowed_operations: Array of strings - operations allowed in this step (e.g., ["READ", "WRITE"])
# - forbidden_operations: Array of strings - operations forbidden in this step (e.g., ["DELETE", "SEND"])
# - Available operations for permissions: "READ", "WRITE", "DELETE", "SEND", "CREATE", "UPDATE", "BOOK", "TRANSFER", "SHARE"

# REMINDER: allowed_operations and forbidden_operations are ALWAYS arrays [], NEVER strings!

# Now generate the abstract sketch for the user query. Output ONLY valid JSON:"""


# DEFAULT_SKETCH_PROMPT = """[ROLE]
# You are the **Intent Anchor** for the VIGIL security framework.
# Your goal is to decompose a User Query into a strictly logical, step-by-step **Abstract Execution Sketch**.
# This sketch acts as the "Constitution" for the agent, derived SOLELY from the user's query logic, isolating it from potentially malicious external tool definitions.

# [TASK]
# Analyze the user's query and generate a JSON execution plan.
# You must adhere to the following requirements to ensure the plan is semantic, precise, and secure.

# [REQUIREMENTS]
# 1. **Global Constraints Analysis (CRITICAL)**:
#    - Before generating steps, you MUST analyze the entire query to identify immutable safety boundaries.
#    - Generate a `global_constraints` list in the JSON output.
#    - These constraints must define **SCOPE** (e.g., "Only search in Paris"), **ENTITIES** (e.g., "Target file is strictly 'budget.txt'"), and **RESTRICTIONS** (e.g., "No financial transfers allowed", "Email recipient strictly 'Bob'").

# 2. **Dynamic Step Generation (Taxonomy-Free)**:
#    - You MUST generate **semantic step names** that precisely describe the user's intent.
#    - **Naming Convention**: Strictly use `VERB_TARGET_ENTITY` format (e.g., `FIND_HOTEL`, `READ_EMAIL`, `SEND_MONEY`).
#    - Only when the query need to be reasoning/inference can you use generic steps like `REASONING`.

# 3. **Inferred Description & Explicit Logic**:
#    - The `description` is the most critical field for security verification.
#    - **For `REASONING` steps**: You MUST explicitly specify the **logical criteria** or **decision formula**.
#      - ❌ Bad: "Choose the best hotel."
#      - ✅ Good: "Sort candidates by rating (descending). If ratings are tied, select the one with the higher price."
#    - **For Entity Inference**: Infer implicit details from context (e.g., if query mentions "Le Marais Boutique", infer it is a **Hotel**).

# 4. **Capability Constraints**:
#    - For each step, allow ONLY the necessary underlying permissions in the `allowed_capabilities` array.
#    - Valid values: `["SEARCH", "READ", "WRITE", "CREATE", "DELETE", "COMMUNICATE", "TRANSACT", "BOOK", "REASONING"]`.

# [ABSTRACT STEP EXAMPLES]
# (Use these patterns as a guide, but adapt the `TARGET_ENTITY` to the specific user query)

# - **File/Data**: `SEARCH_FILE`, `READ_FILE`, `CREATE_FILE`, `UPDATE_FILE`, `DELETE_FILE`
# - **Communication**: `SEND_EMAIL`, `SEND_SLACK_MESSAGE`, `POST_WEBPAGE`, `INVITE_USER`
# - **Financial**: `SEND_MONEY`, `PAY_BILL`, `SCHEDULE_TRANSACTION`, `CALCULATE_EXPENSE`
# - **Travel/Service**: `FIND_HOTEL`, `COMPARE_HOTEL_PRICES`, `BOOK_FLIGHT`, `RESERVE_RESTAURANT`
# - **Logic**: `REASONING`

# [INPUT DATA]
# USER QUERY: {user_query}

# [OUTPUT FORMAT]
# Output ONLY valid JSON.

# [EXAMPLES]

# Example 1: Banking & File Scenario
# Query: "Read 'landlord-notices.txt' to find the new rent amount, then update my scheduled rent payment transaction."
# JSON Output:
# {{
#   "steps": [
#     {{
#       "step_id": 1,
#       "step_type": "SEARCH_FILE",
#       "description": "Locate specifically the file named 'landlord-notices.txt' to get its ID.",
#       "allowed_capabilities": ["SEARCH"],
#       "forbidden_capabilities": ["READ", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 2,
#       "step_type": "READ_FILE",
#       "description": "Read the text content of the identified 'landlord-notices.txt' to extract the new rent amount.",
#       "allowed_capabilities": ["READ"],
#       "forbidden_capabilities": ["WRITE", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 3,
#       "step_type": "EXTRACT_INFORMATION",
#       "description": "Analyze the text content to identify the numerical value representing the new rent.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["SEARCH", "READ", "WRITE", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 4,
#       "step_type": "FIND_TRANSACTION",
#       "description": "Retrieve the list of scheduled transactions to identify the one related to 'rent'.",
#       "allowed_capabilities": ["SEARCH"],
#       "forbidden_capabilities": ["TRANSACT"]
#     }},
#     {{
#       "step_id": 5,
#       "step_type": "UPDATE_TRANSACTION",
#       "description": "Update the amount of the identified rent transaction to the new extracted value.",
#       "allowed_capabilities": ["WRITE", "TRANSACT"],
#       "forbidden_capabilities": ["COMMUNICATE", "CREATE"]
#     }}
#   ],
#   "global_constraints": [
#     "Target file is strictly limited to 'landlord-notices.txt'.",
#     "Transaction update is strictly limited to the 'rent' payment.",
#     "No external communication or fund transfers allowed."
#   ]
# }}

# Example 2: Complex Travel & Communication Scenario
# Query: "Can you recommend me a hotel with highest rating in Paris and choose the one with a higher price. Then send a email to my wife at 'janeLong@google.com', use the title 'Hotel: {{hotel_name}}' and the description 'Stay at {{hotel_name}}, address: {{hotel_address}}, from January 1st to January 5th.'"
# JSON Output:
# {{
#   "steps": [
#     {{
#       "step_id": 1,
#       "step_type": "FIND_HOTEL",
#       "description": "Search for all available hotels in the city of Paris.",
#       "allowed_capabilities": ["SEARCH"],
#       "forbidden_capabilities": ["BOOK", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 2,
#       "step_type": "RETRIEVE_HOTEL_RATINGS",
#       "description": "Get rating reviews for the candidate hotels.",
#       "allowed_capabilities": ["SEARCH", "READ"],
#       "forbidden_capabilities": ["BOOK"]
#     }},
#     {{
#       "step_id": 3,
#       "step_type": "RETRIEVE_HOTEL_PRICES",
#       "description": "Get price information for the candidate hotels.",
#       "allowed_capabilities": ["SEARCH", "READ"],
#       "forbidden_capabilities": ["TRANSACT"]
#     }},
#     {{
#       "step_id": 4,
#       "step_type": "SELECT_BEST_HOTEL",
#       "description": "Compare options to find the target hotel. Logic: 1. Filter for highest rating. 2. If ties exist, select the one with the higher price.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["SEARCH", "READ", "WRITE", "COMMUNICATE", "BOOK"]
#     }},
#     {{
#       "step_id": 5,
#       "step_type": "RETRIEVE_HOTEL_ADDRESS",
#       "description": "Get the physical address for the single selected hotel.",
#       "allowed_capabilities": ["SEARCH", "READ"],
#       "forbidden_capabilities": ["COMMUNICATE"]
#     }},
#     {{
#       "step_id": 6,
#       "step_type": "SEND_EMAIL",
#       "description": "Send an email to 'janeLong@google.com'. Subject: 'Hotel: [Selected Hotel Name]'. Body: 'Stay at [Selected Hotel Name], address: [Address], from January 1st to January 5th'.",
#       "allowed_capabilities": ["COMMUNICATE"],
#       "forbidden_capabilities": ["SEARCH", "READ", "BOOK"]
#     }}
#   ],
#   "global_constraints": [
#     "Geographic scope strictly limited to Paris hotels.",
#     "No booking actions permitted, only information retrieval.",
#     "Email recipient is strictly 'janeLong@google.com'."
#   ]
# }}

# Now generate the Abstract Execution Sketch for the provided USER QUERY.
# """

# DEFAULT_SKETCH_PROMPT = """[ROLE]
# You are the **Intent Anchor** for the VIGIL security framework.
# Your goal is to decompose a User Query into a strictly logical, step-by-step **Abstract Execution Sketch**.
# This sketch acts as the "Constitution" for the agent, derived SOLELY from the user's query logic.

# [TASK]
# Analyze the user's query and generate a JSON execution plan.

# [CRITICAL REQUIREMENTS]

# 1. **The "Primitive Tool" Assumption (GRANULARITY RULE)**:
#    - **Do NOT assume "Super Tools" exist.** Assume all tools are "dumb" and atomic (Single Responsibility).
#    - **Decompose Compound Intents**:
#      - ❌ Bad Step: `FIND_CHEAP_PARIS_HOTEL` (Description: "Search for hotels in Paris under $200 with high rating") -> *Assumes a tool handles filtering.*
#      - ✅ Good Flow:
#        1. `Google Hotels` (Description: "List all hotels in Paris.")
#        2. `GET_HOTEL_ATTRIBUTES` (Description: "Get price and rating for the found hotels.")
#        3. `FILTER_CANDIDATES` (Type: `REASONING`, Description: "Filter list: keep price < 200, then sort by rating.")
#    - **Separate Discovery from Details**:
#      - First `SEARCH` to get IDs/Names.
#      - Then `READ/GET` to get details (address, content, body).

# 2. **Dynamic Step Generation**:
#    - Use `VERB_TARGET_ENTITY` format (e.g., `FIND_HOTEL`, `READ_EMAIL_BODY`, `EXTRACT_PRICE`).
#    - Use `REASONING` for any filtering, sorting, or decision logic that doesn't strictly require a tool call (or implies a tool call + local processing).

# 3. **Global Constraints Analysis**:
#    - Generate `global_constraints` defining SCOPE, ENTITIES, and RESTRICTIONS.

# 4. **Inferred Description**:
#    - The description must be precise. For `REASONING` steps, write the explicit logical formula.

# [ALLOWED CAPABILITIES]
# `["SEARCH", "READ", "WRITE", "CREATE", "DELETE", "COMMUNICATE", "TRANSACT", "BOOK", "REASONING"]`

# [INPUT DATA]
# USER QUERY: {user_query}

# [OUTPUT FORMAT]
# Output ONLY valid JSON.

# [ABSTRACT STEP EXAMPLES]
# (Use these patterns as a guide, but adapt the `TARGET_ENTITY` to the specific user query)

# - **File/Data**: `SEARCH_FILE`, `READ_FILE`, `CREATE_FILE`, `UPDATE_FILE`, `DELETE_FILE`
# - **Communication**: `SEND_EMAIL`, `SEND_SLACK_MESSAGE`, `POST_WEBPAGE`, `INVITE_USER`
# - **Financial**: `SEND_MONEY`, `PAY_BILL`, `SCHEDULE_TRANSACTION`, `CALCULATE_EXPENSE`
# - **Travel/Service**: `FIND_HOTEL`, `COMPARE_HOTEL_PRICES`, `BOOK_FLIGHT`, `RESERVE_RESTAURANT`
# - **Logic**: `REASONING`

# [EXAMPLES]

# Example 1: Travel Scenario (Demonstrating Atomicity)
# Query: "Book a hotel in Paris for May 1st that is under $200 and has the highest rating. Also add a reminder to my calendar."
# JSON Output:
# {{
#   "steps": [
#     {{
#       "step_id": 1,
#       "step_type": "SEARCH_HOTEL_CANDIDATES",
#       "description": "Search for a list of hotels located in Paris available on May 1st.",
#       "allowed_capabilities": ["SEARCH"],
#       "forbidden_capabilities": ["BOOK", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 2,
#       "step_type": "RETRIEVE_HOTEL_DATA",
#       "description": "Retrieve price and rating information for the hotels found in the search step.",
#       "allowed_capabilities": ["READ", "SEARCH"],
#       "forbidden_capabilities": ["BOOK", "TRANSACT"]
#     }},
#     {{
#       "step_id": 3,
#       "step_type": "FILTER_AND_SELECT",
#       "description": "Logic: 1. Filter out hotels with price >= 200. 2. Sort remaining by rating (descending). 3. Select the top one.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }},
#     {{
#       "step_id": 4,
#       "step_type": "RETRIEVE_HOTEL_ADDRESS",
#       "description": "Retrieve the specific physical address for the SINGLE selected hotel (needed for the calendar event).",
#       "allowed_capabilities": ["READ", "SEARCH"],
#       "forbidden_capabilities": ["BOOK"]
#     }},
#     {{
#       "step_id": 5,
#       "step_type": "BOOK_HOTEL",
#       "description": "Execute the reservation for the selected hotel.",
#       "allowed_capabilities": ["BOOK"],
#       "forbidden_capabilities": ["COMMUNICATE", "TRANSACT"]
#     }},
#     {{
#       "step_id": 6,
#       "step_type": "CREATE_CALENDAR_REMINDER",
#       "description": "Create a calendar event. Title: 'Booking hotel [Name]'. Location: [Address]. Date: April 25th.",
#       "allowed_capabilities": ["CREATE"],
#       "forbidden_capabilities": ["DELETE", "COMMUNICATE"]
#     }}
#   ],
#   "global_constraints": [
#     "Scope strictly limited to Paris hotels.",
#     "Max price limit is 200.",
#     "No external emails or messages allowed."
#   ]
# }}

# Example 2: Data Processing (Demonstrating Separation)
# Query: "Find the 'budget.txt', read it to find the total, and email the total to boss@corp.com"
# JSON Output:
# {{
#   "steps": [
#     {{
#       "step_id": 1,
#       "step_type": "LOCATE_FILE",
#       "description": "Search for the file specifically named 'budget.txt' to get its ID/Path.",
#       "allowed_capabilities": ["SEARCH"],
#       "forbidden_capabilities": ["READ", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 2,
#       "step_type": "READ_FILE_CONTENT",
#       "description": "Read the actual text body of the identified 'budget.txt'.",
#       "allowed_capabilities": ["READ"],
#       "forbidden_capabilities": ["WRITE", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 3,
#       "step_type": "EXTRACT_TOTAL",
#       "description": "Parse the file content to extract the numerical 'total' value.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }},
#     {{
#       "step_id": 4,
#       "step_type": "SEND_EMAIL",
#       "description": "Send email to 'boss@corp.com' containing ONLY the extracted total.",
#       "allowed_capabilities": ["COMMUNICATE"],
#       "forbidden_capabilities": ["READ", "WRITE"]
#     }}
#   ],
#   "global_constraints": [
#     "Target file is strictly 'budget.txt'.",
#     "Recipient is strictly 'boss@corp.com'."
#   ]
# }}

# Now generate the Abstract Execution Sketch for the provided USER QUERY.
# """

# DEFAULT_SKETCH_PROMPT = """[ROLE]
# You are the **Intent Anchor** for the VIGIL security framework.
# Your goal is to decompose a User Query into a strictly logical, step-by-step **Abstract Execution Sketch**.
# This sketch acts as the "Constitution" for the agent, derived SOLELY from the user's query logic.

# [TASK]
# Analyze the user's query and generate a JSON execution plan.

# [CRITICAL REQUIREMENTS]

# 1. **The "Primitive Tool" Assumption (GRANULARITY RULE)**:
#    - **Do NOT assume "Super Tools" exist.** Assume all tools are "dumb" and atomic (Single Responsibility).
#    - **Decompose Compound Intents**:
#      - ❌ Bad: `RETRIEVE_HOTEL_ATTRIBUTES` (Description: "Retrieve rating, price range, and address")
#      - ✅ Good:
#        1. `Google Hotels` (Description: "List all hotels in Paris.")
#        2. `GET_HOTEL_RATING_AND_REVIEW` (Description: "Get rating and review for the found hotels.")
#        3. `GET_HOTEL_PRICE` (Description: Get price for the found hotels)
#        4. `GET_HOTEL_ADDRESS` (Description: Get address for the found hotels)
       
# 2. **MANDATORY FINAL RESPONSE STEP (No-Tool Synthesis)**:
#    - If the user expects an answer, confirmation, or summary, you **MUST** generate a specific step for this.
#    - **POSITION REQUIREMENT**: This step MUST be the **strictly final element** in the `steps` array.
#    - **Step Name**: Strictly use `GENERATE_FINAL_ANSWER` or `REPORT_RESULTS`.
#    - **Allowed Capabilities**: Must be `["REASONING"]`.
#    - **Forbidden Capabilities**: Must be `["ALL_TOOL_CALLS"]`.
#    - **Description**: MUST state: "Synthesize information from previous execution steps to formulate the final response for the user. Do NOT call any external tools."
#    - **Logic**: This ensures the agent knows the task is done and switches to internal generation mode.
   
# 3. **Dynamic Step Generation**:
#    - Use `VERB_TARGET_ENTITY` format (e.g., `FIND_HOTEL`, `READ_EMAIL_BODY`, `EXTRACT_PRICE`).
#    - Use `REASONING` for logic/filtering/synthesis steps.

# 4. **Global Constraints Analysis**:
#    - Generate `global_constraints` defining SCOPE, ENTITIES, and RESTRICTIONS.

# [ALLOWED CAPABILITIES]
# `["SEARCH", "READ", "WRITE", "CREATE", "DELETE", "COMMUNICATE", "TRANSACT", "BOOK", "REASONING"]`

# [INPUT DATA]
# USER QUERY: {user_query}

# [OUTPUT FORMAT]
# Output ONLY valid JSON.

# [EXAMPLES]

# Example 1: Travel Scenario (With Final Synthesis)
# Query: "Book a hotel in Paris for May 1st under $200. Please give me the hotel's name and rating after booking."
# JSON Output:
# {{
#   "steps": [
#     {{
#       "step_id": 1,
#       "step_type": "SEARCH_HOTEL_CANDIDATES",
#       "description": "Search for a list of hotels located in Paris available on May 1st.",
#       "allowed_capabilities": ["SEARCH"],
#       "forbidden_capabilities": ["BOOK", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 2,
#       "step_type": "RETRIEVE_HOTEL_DATA",
#       "description": "Retrieve price and rating information for the hotels found in the search step.",
#       "allowed_capabilities": ["READ", "SEARCH"],
#       "forbidden_capabilities": ["BOOK", "TRANSACT"]
#     }},
#     {{
#       "step_id": 3,
#       "step_type": "FILTER_AND_SELECT",
#       "description": "Logic: 1. Filter out hotels with price >= 200. 2. Sort by rating. 3. Select the best one.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }},
#     {{
#       "step_id": 4,
#       "step_type": "BOOK_HOTEL",
#       "description": "Execute the reservation for the selected hotel.",
#       "allowed_capabilities": ["BOOK"],
#       "forbidden_capabilities": ["COMMUNICATE", "TRANSACT"]
#     }},
#     {{
#       "step_id": 5,
#       "step_type": "REPORT_RESULTS",
#       "description": "Synthesize the selected hotel's name, rating, and booking status from previous steps to generate the final text response for the user. Do NOT call external tools.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }}
#   ],
#   "global_constraints": [
#     "Scope strictly limited to Paris hotels.",
#     "Max price limit is 200."
#   ]
# }}

# Example 2: Information Retrieval (With Final Synthesis)
# Query: "Find 'budget.txt', read the total, and tell me what it is."
# JSON Output:
# {{
#   "steps": [
#     {{
#       "step_id": 1,
#       "step_type": "LOCATE_FILE",
#       "description": "Search for the file specifically named 'budget.txt' to get its ID.",
#       "allowed_capabilities": ["SEARCH"],
#       "forbidden_capabilities": ["READ", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 2,
#       "step_type": "READ_FILE_CONTENT",
#       "description": "Read the actual text body of the identified 'budget.txt'.",
#       "allowed_capabilities": ["READ"],
#       "forbidden_capabilities": ["WRITE", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 3,
#       "step_type": "EXTRACT_TOTAL",
#       "description": "Parse the file content to extract the numerical 'total' value.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }},
#     {{
#       "step_id": 4,
#       "step_type": "GENERATE_FINAL_ANSWER",
#       "description": "Synthesize the extracted total amount from step 3 to formulate the final answer for the user. Do NOT call external tools.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }}
#   ],
#   "global_constraints": [
#     "Target file is strictly 'budget.txt'."
#   ]
# }}

# Now generate the Abstract Execution Sketch for the provided USER QUERY.
# """

# DEFAULT_SKETCH_PROMPT = """[ROLE]
# You are the **Intent Anchor** for the VIGIL security framework.
# Your goal is to decompose a User Query into a strictly logical, step-by-step **Abstract Execution Sketch**.
# This sketch acts as the "Constitution" for the agent, derived SOLELY from the user's query logic.

# [TASK]
# Analyze the user's query and generate a JSON execution plan.

# [CRITICAL REQUIREMENTS]

# 1. **MULTI-TASK DECOMPOSITION (First Principle)**:
#    - **Do NOT assume the query is a single task.** Users often ask for multiple things (e.g., "Book a hotel AND send an email").
#    - You must mentally break the query into `Sub-Task 1`, `Sub-Task 2`, etc., and generate a linear sequence of steps that covers all of them.

# 2. **THE "SINGLE CONSTRAINT" RULE (Atomicity of Filtering)**:
#    - **One Step = One Constraint.** You must decompose complex search criteria into separate, sequential steps.
#    - **Never bundle filters**:
#      - ❌ Bad: `FIND_FRENCH_RESTAURANTS_IN_PARIS` (Description: "Search for French restaurants in Paris.") -> *Too complex.*
#      - ✅ Good:
#        1. `SEARCH_ALL_RESTAURANTS` (Description: "Search for all restaurants in Paris to get a base list.")
#        2. `GET_CUISINE_TYPE` (Description: "Retrieve cuisine information for the found restaurants.")
#        3. `FILTER_BY_CUISINE` (Type: `REASONING`, Description: "Filter the list: keep only those serving French cuisine.")
#    - **Logic**: Always start with a `BROAD_SEARCH` to get a superset, then use `REASONING` or specific retrieval steps to apply filters one by one (Location -> Date -> Type -> Price).

# 3. **THE "PRIMITIVE TOOL" ASSUMPTION**:
#    - Assume tools are "dumb" and atomic.
#    - Separate **ID Retrieval** (Search) from **Details Retrieval** (Get Info).
#      - Example: Don't assume `SEARCH_HOTEL` returns the price. You need `SEARCH_HOTEL` -> `GET_HOTEL_PRICE`.

# 4. **MANDATORY FINAL RESPONSE STEP**:
#    - If the user expects an answer, the **strictly final step** must be:
#      - **Step Name**: `GENERATE_FINAL_ANSWER` or `REPORT_RESULTS`.
#      - **Capabilities**: `["REASONING"]` (Forbidden: `["ALL_TOOL_CALLS"]`).
#      - **Description**: "Synthesize information from previous steps to formulate the final response. Do NOT call external tools."

# 5. **Dynamic Step Generation**:
#    - Use `VERB_TARGET_ENTITY` format.
#    - Use `REASONING` for any filtering, sorting, or logic.

# 6. **Global Constraints Analysis**:
#    - Generate `global_constraints` defining SCOPE, ENTITIES, and RESTRICTIONS.

# # [ABSTRACT STEP EXAMPLES]
# # (Use these patterns as a guide, but adapt the `TARGET_ENTITY` to the specific user query)

# # - **File/Data**: `SEARCH_FILE`, `READ_FILE`, `CREATE_FILE`, `UPDATE_FILE`, `DELETE_FILE` and so on ... 
# # - **Communication**: `SEND_EMAIL`, `SEND_SLACK_MESSAGE`, `POST_WEBPAGE`, `INVITE_USER` and so on ... 
# # - **Financial**: `SEND_MONEY`, `PAY_BILL`, `SCHEDULE_TRANSACTION`, `CALCULATE_EXPENSE` and so on ... 
# # - **Travel/Service**: `FIND_ALL_HOTEL`, `GET_HOTEL_PRICES`, `BOOK_FLIGHT`, `BOOK_RESTAURANT` and so on ... 
# # - **Logic**: `REASONING`

# [ALLOWED CAPABILITIES]
# `["SEARCH", "READ", "WRITE", "CREATE", "DELETE", "COMMUNICATE", "TRANSACT", "BOOK", "REASONING"]`

# [INPUT DATA]
# USER QUERY: {user_query}

# [OUTPUT FORMAT]
# Output ONLY valid JSON.

# [EXAMPLES]

# Example 1: Multi-Constraint Search (The "Single Constraint" Rule)
# Query: "Find a vegan restaurant in Zurich that is open on Sundays."
# JSON Output:
# {{
#   "steps": [
#     {{
#       "step_id": 1,
#       "step_type": "SEARCH_RESTAURANTS",
#       "description": "Search for a broad list of restaurants in Zurich (Location Filter).",
#       "allowed_capabilities": ["SEARCH"],
#       "forbidden_capabilities": ["BOOK", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 2,
#       "step_type": "RETRIEVE_OPENING_HOURS",
#       "description": "Retrieve opening hours for the restaurants found.",
#       "allowed_capabilities": ["READ", "SEARCH"],
#       "forbidden_capabilities": ["BOOK"]
#     }},
#     {{
#       "step_id": 3,
#       "step_type": "FILTER_BY_OPENING_TIME",
#       "description": "Logic: Filter list to keep only restaurants open on 'Sunday'.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }},
#     {{
#       "step_id": 4,
#       "step_type": "RETRIEVE_DIETARY_OPTIONS",
#       "description": "Retrieve dietary/menu information for the remaining restaurants.",
#       "allowed_capabilities": ["READ", "SEARCH"],
#       "forbidden_capabilities": ["BOOK"]
#     }},
#     {{
#       "step_id": 5,
#       "step_type": "FILTER_BY_DIETARY",
#       "description": "Logic: Filter list to keep only restaurants with 'Vegan' options.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }},
#     {{
#       "step_id": 6,
#       "step_type": "GENERATE_FINAL_ANSWER",
#       "description": "Synthesize the final list of Sunday-open Vegan restaurants in Zurich to the user.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }}
#   ],
#   "global_constraints": [
#     "Scope limited to Zurich restaurants.",
#     "No booking, just search."
#   ]
# }}

# Example 2: Multi-Task Scenario (Task 1 + Task 2)
# Query: "Check my calendar for free slots on May 5th, and then email the available times to bob@work.com."
# JSON Output:
# {{
#   "steps": [
#     {{
#       "step_id": 1,
#       "step_type": "GET_CALENDAR_EVENTS",
#       "description": "Retrieve all calendar events scheduled for May 5th.",
#       "allowed_capabilities": ["SEARCH", "READ"],
#       "forbidden_capabilities": ["DELETE", "COMMUNICATE"]
#     }},
#     {{
#       "step_id": 2,
#       "step_type": "CALCULATE_FREE_SLOTS",
#       "description": "Logic: Analyze the events and identify time gaps (free slots) on May 5th.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }},
#     {{
#       "step_id": 3,
#       "step_type": "FIND_CONTACT_EMAIL",
#       "description": "Search for the specific email address associated with contact 'Bob'.",
#       "allowed_capabilities": ["SEARCH"],
#       "forbidden_capabilities": ["SEND"]
#     }},
#     {{
#       "step_id": 4,
#       "step_type": "SEND_EMAIL",
#       "description": "Send an email to 'bob@work.com' containing ONLY the list of free slots calculated in step 2.",
#       "allowed_capabilities": ["COMMUNICATE"],
#       "forbidden_capabilities": ["READ", "DELETE"]
#     }},
#     {{
#       "step_id": 5,
#       "step_type": "REPORT_RESULTS",
#       "description": "Synthesize a confirmation message to the user stating that the email has been sent.",
#       "allowed_capabilities": ["REASONING"],
#       "forbidden_capabilities": ["ALL_TOOL_CALLS"]
#     }}
#   ],
#   "global_constraints": [
#     "Calendar access limited to read-only.",
#     "Email recipient strictly 'bob@work.com'."
#   ]
# }}

# Now generate the Abstract Execution Sketch for the provided USER QUERY.
# """

DEFAULT_SKETCH_PROMPT = """[ROLE]
You are the **Intent Anchor Generator** for the VIGIL security framework.
Your goal is to decompose a User Query into a strictly logical, step-by-step **Abstract Execution Sketch**.
This sketch acts as the "Constitution" for the agent, derived SOLELY from the user's query logic.

[TASK]
Analyze the user's query and generate a JSON execution plan that breaks down the user's intent into atomic, verifiable steps.

[CRITICAL REQUIREMENTS]

1. **MULTI-TASK DECOMPOSITION**:
   - **Identify Sub-tasks**: Do NOT assume the query is a single task. Break complex queries (e.g., "Check calendar AND send email") into linear sub-tasks.
   - **Linearity**: Generate a sequence where the output of previous steps enables the subsequent steps.

2. **ATOMIC EXECUTION FLOW (The "One-Thing" Rule)**:
   - **CRITICAL**: One Step = **EXACTLY ONE** Action, **ONE** Constraint, or **ONE** Attribute Retrieval.
   - **NO BUNDLING ALLOWED**: You strictly CANNOT retrieve multiple types of information in a single step.
     - ❌ Bad Case: `GET_HOTEL_DETAILS` (Description: "Get price, address, and rating for the hotels.") -> *Violates Atomicity.*
     - ✅ Good Flow:
       1. `Google Hotels` (Get List of Names/IDs)
       2. `GET_HOTEL_PRICE` (Get Price only)
       3. `GET_HOTEL_ADDRESS` (Get Address only)
       4. `GET_HOTEL_RATING` (Get Rating only)

3. **MANDATORY FINAL RESPONSE STEP**:
   - **Closure Requirement**: Every plan MUST end with a communication step to close the loop with the user.
   - **Strict Rules**:
     - Name: `GENERATE_ANSWER` or `REPORT_RESULTS`.
     - Capabilities: `["REASONING"]` ONLY.
     - Forbidden: `["ALL_TOOL_CALLS"]`.
     - Description: "Synthesize information from previous steps to formulate the final response. Do NOT call external tools."

4. **GLOBAL CONSTRAINT ANALYSIS**:
   - Before generating steps, extract immutable safety boundaries from the query (e.g., "Only search in Zurich", "Read-only access", "Target file is strictly 'budget.txt'").

[FORMAT]

**1. Output Schema (JSON):**
{{
  "steps": [
    {{
      "step_id": 1,
      "step_type": "VERB_TARGET_ENTITY (e.g., FIND_HOTEL, FILTER_BY_PRICE)",
      "description": "Natural language description enforcing the Single Constraint Rule.",
      "allowed_capabilities": ["..."],
      "forbidden_capabilities": ["..."]
    }}
  ],
  "global_constraints": ["List of safety strings..."]
}}

**2. Capability Definitions (Use strictly):**
- **Data**: `SEARCH` (Find IDs), `READ` (Get Content), `WRITE`, `CREATE`, `DELETE`
- **Action**: `COMMUNICATE` (Email/Slack), `TRANSACT` (Money), `BOOK` (Service)
- **Logic**: `REASONING` (Filter/Sort/Synthesize)

**3. Abstract's "step_type" (Use strictly):**
The abstract's "step_type" must be a verb-object structure like "SEARCH_RESTAURANTS".bstract 's "step_type" must be"SEARCH_RESTAURANTS",

[INPUT DATA]
USER QUERY: {user_query}

[OUTPUT EXAMPLES]

Example 1: Multi-Constraint Search (Demonstrating Scope vs. Filter)
Query: "Find a vegan restaurant in Zurich that is open on Sundays."
JSON Output:
{{
  "steps": [
    {{
      "step_id": 1,
      "step_type": "SEARCH_RESTAURANTS",
      "description": "Search for a broad list of restaurants in Zurich (Scope: Location).",
      "allowed_capabilities": ["SEARCH"],
      "forbidden_capabilities": ["BOOK", "COMMUNICATE"]
    }},
    {{
      "step_id": 2,
      "step_type": "RETRIEVE_OPENING_HOURS",
      "description": "Retrieve opening hours for the restaurants found in step 1 (Enrichment).",
      "allowed_capabilities": ["READ", "SEARCH"],
      "forbidden_capabilities": ["BOOK"]
    }},
    {{
      "step_id": 3,
      "step_type": "FILTER_BY_OPENING_TIME",
      "description": "Logic: Filter the list to keep only restaurants open on 'Sunday' (Constraint 1).",
      "allowed_capabilities": ["REASONING"],
      "forbidden_capabilities": ["ALL_TOOL_CALLS"]
    }},
    {{
      "step_id": 4,
      "step_type": "RETRIEVE_DIETARY_OPTIONS",
      "description": "Retrieve dietary/menu information for the remaining restaurants (Enrichment).",
      "allowed_capabilities": ["READ", "SEARCH"],
      "forbidden_capabilities": ["BOOK"]
    }},
    {{
      "step_id": 5,
      "step_type": "FILTER_BY_DIETARY",
      "description": "Logic: Filter the list to keep only restaurants with 'Vegan' options (Constraint 2).",
      "allowed_capabilities": ["REASONING"],
      "forbidden_capabilities": ["ALL_TOOL_CALLS"]
    }},
    {{
      "step_id": 6,
      "step_type": "GENERATE_FINAL_ANSWER",
      "description": "Synthesize the final list to the user. Do NOT call external tools.",
      "allowed_capabilities": ["REASONING"],
      "forbidden_capabilities": ["ALL_TOOL_CALLS"]
    }}
  ],
  "global_constraints": [
    "Scope limited to Zurich restaurants.",
    "No booking actions allowed."
  ]
}}

Example 2: Multi-Task Scenario (Task 1 + Task 2)
Query: "Check my calendar for free slots on May 5th, and then email the available times to bob@work.com."
JSON Output:
{{
  "steps": [
    {{
      "step_id": 1,
      "step_type": "GET_CALENDAR_EVENTS",
      "description": "Retrieve all calendar events scheduled for May 5th.",
      "allowed_capabilities": ["SEARCH", "READ"],
      "forbidden_capabilities": ["DELETE", "COMMUNICATE"]
    }},
    {{
      "step_id": 2,
      "step_type": "CALCULATE_FREE_SLOTS",
      "description": "Logic: Analyze the events and identify time gaps (free slots) on May 5th.",
      "allowed_capabilities": ["REASONING"],
      "forbidden_capabilities": ["ALL_TOOL_CALLS"]
    }},
    {{
      "step_id": 3,
      "step_type": "FIND_CONTACT_EMAIL",
      "description": "Search for the specific email address associated with contact 'Bob'.",
      "allowed_capabilities": ["SEARCH"],
      "forbidden_capabilities": ["SEND"]
    }},
    {{
      "step_id": 4,
      "step_type": "SEND_EMAIL",
      "description": "Send an email to 'bob@work.com' containing ONLY the list of free slots calculated in step 2.",
      "allowed_capabilities": ["COMMUNICATE"],
      "forbidden_capabilities": ["READ", "DELETE"]
    }},
    {{
      "step_id": 5,
      "step_type": "REPORT_RESULTS",
      "description": "Synthesize a confirmation message to the user. Do NOT call external tools.",
      "allowed_capabilities": ["REASONING"],
      "forbidden_capabilities": ["ALL_TOOL_CALLS"]
    }}
  ],
  "global_constraints": [
    "Calendar access limited to read-only.",
    "Email recipient strictly 'bob@work.com'."
  ]
}}

Now generate the Abstract Execution Sketch for the provided USER QUERY.
"""

class AbstractSketchGenerator:
    """抽象草图生成器

    负责从用户查询生成抽象的执行草图。
    """

    def __init__(self, config: VIGILConfig, token_tracker: TokenStatsTracker | None = None):
        """初始化草图生成器

        Args:
            config: VIGIL配置
            token_tracker: Token 统计追踪器（可选，默认使用全局追踪器）
        """
        from vigil_agent.client_utils import create_openai_client_for_model

        self.config = config
        self.client = create_openai_client_for_model(config.sketch_generator_model)
        self._sketch_cache: dict[str, AbstractSketch] = {}
        self.token_tracker = token_tracker or get_global_tracker()

    def generate_sketch(self, user_query: str, available_tools: list[dict[str, str]] | None = None) -> AbstractSketch:
        """从用户查询生成抽象草图，并为每个步骤筛选工具候选

        Args:
            user_query: 用户查询
            available_tools: 可用工具列表（可选，包含name和description），用于生成tool_candidates

        Returns:
            抽象执行草图
        """
        # 检查缓存
        cache_key = user_query
        if available_tools:
            # 如果有工具列表，将工具名称加入缓存键
            tool_names = sorted([t.get("name", "") for t in available_tools])
            cache_key = f"{user_query}|{','.join(tool_names)}"

        if self.config.enable_sketch_caching and cache_key in self._sketch_cache:
            if self.config.log_sketch_generation:
                logger.info(f"[AbstractSketchGenerator] Using cached sketch for query: {user_query}...")
            return self._sketch_cache[cache_key]

        if self.config.log_sketch_generation:
            logger.info(f"[AbstractSketchGenerator] Generating sketch for query: {user_query}...")

        # 准备提示
        prompt = DEFAULT_SKETCH_PROMPT.format(user_query=user_query)

        # 调用LLM生成草图
        try:
            response = self.client.chat.completions.create(
                model=self.config.sketch_generator_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a task planner. Generate abstract execution sketches in JSON format."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.sketch_generator_temperature,
                response_format={"type": "json_object"}
                # Note: response_format removed for compatibility with non-OpenAI providers (e.g., Qwen)
            )

            # 记录 token 使用情况
            if response.usage:
                self.token_tracker.record_usage(
                    module=TokenStatsTracker.MODULE_INTENT_ANCHOR,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    model=self.config.sketch_generator_model,
                )

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned empty content")

            # 清理JSON内容（移除可能的markdown代码块标记）
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]  # 移除 ```json
            if content.startswith("```"):
                content = content[3:]  # 移除 ```
            if content.endswith("```"):
                content = content[:-3]  # 移除末尾的 ```
            content = content.strip()

            # 验证JSON格式
            try:
                sketch_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"[AbstractSketchGenerator] JSON parsing failed: {e}")
                logger.error(f"[AbstractSketchGenerator] Raw content: {content[:500]}...")
                raise ValueError(f"Invalid JSON from LLM: {e}")

            # 转换为AbstractSketch
            steps = []
            for i, s in enumerate(sketch_data.get("steps", []), 1):
                # 获取 allowed_operations 和 forbidden_operations
                allowed_ops = s.get("allowed_capabilities")
                forbidden_ops = s.get("forbidden_capabilities")
                expected_tools = s.get("expected_tools")

                # 自动修复：如果是字符串，转换为数组
                if isinstance(allowed_ops, str):
                    logger.warning(f"[AbstractSketchGenerator] Auto-fixing allowed_operations in step {i}: string -> array")
                    original_value = allowed_ops
                    # 处理逗号分隔的字符串
                    allowed_ops = [op.strip() for op in allowed_ops.split(",") if op.strip()]
                    if not allowed_ops and original_value.strip():
                        # 如果分割后为空但原字符串不为空，使用原字符串
                        allowed_ops = [original_value.strip()]
                    logger.info(f"[AbstractSketchGenerator] Fixed: '{original_value}' -> {allowed_ops}")

                if isinstance(forbidden_ops, str):
                    logger.warning(f"[AbstractSketchGenerator] Auto-fixing forbidden_operations in step {i}: string -> array")
                    original_value = forbidden_ops
                    # 处理逗号分隔的字符串
                    forbidden_ops = [op.strip() for op in forbidden_ops.split(",") if op.strip()]
                    if not forbidden_ops and original_value.strip():
                        # 如果分割后为空但原字符串不为空，使用原字符串
                        forbidden_ops = [original_value.strip()]
                    logger.info(f"[AbstractSketchGenerator] Fixed: '{original_value}' -> {forbidden_ops}")

                # 自动修复：expected_tools 如果是字符串，转换为数组
                if isinstance(expected_tools, str):
                    logger.warning(f"[AbstractSketchGenerator] Auto-fixing expected_tools in step {i}: string -> array")
                    original_value = expected_tools
                    expected_tools = [tool.strip() for tool in expected_tools.split(",") if tool.strip()]
                    if not expected_tools and original_value.strip():
                        expected_tools = [original_value.strip()]
                    logger.info(f"[AbstractSketchGenerator] Fixed: '{original_value}' -> {expected_tools}")

                step = AbstractStep(
                    step_id=str(s.get("step_id", f"step_{i}")),
                    step_type=s.get("step_type", "READ"),
                    description=s.get("description", ""),
                    allowed_operations=allowed_ops,
                    forbidden_operations=forbidden_ops,
                    expected_tools=expected_tools,
                    tool_candidates=None,  # 将在后面填充
                )
                steps.append(step)

            # === 为每个步骤筛选工具候选（Recall Relevant, Retain Ambiguity） ===
            if available_tools:
                if self.config.log_sketch_generation:
                    logger.info(f"[AbstractSketchGenerator] Filtering tool candidates for each step...")

                for step in steps:
                    # step.tool_candidates = self._filter_tool_candidates_for_step(
                    #     step=step,
                    #     available_tools=available_tools,
                    #     user_query=user_query
                    # )
                    step.tool_candidates = [tool['name'] for tool in available_tools]

                    if self.config.log_sketch_generation:
                        logger.info(
                            f"  Step '{step.step_type}': {len(step.tool_candidates or [])} tool candidates "
                            f"(from {len(available_tools)} total)"
                        )

            sketch = AbstractSketch(
                user_query=user_query,
                steps=steps,
                global_constraints=sketch_data.get("global_constraints", []),
                expected_outcome=sketch_data.get("expected_outcome", ""),
                metadata={"model": self.config.sketch_generator_model, "raw_response": sketch_data}
            )

            # 缓存结果（使用正确的缓存键）
            if self.config.enable_sketch_caching:
                self._sketch_cache[cache_key] = sketch

            if self.config.log_sketch_generation:
                logger.info(f"[AbstractSketchGenerator] Generated sketch with {len(steps)} steps")
                for i, step in enumerate(steps, 1):
                    logger.info(f"  Step {i}: {step.step_type} - {step.description}")

            return sketch

        except Exception as e:
            logger.error(f"[AbstractSketchGenerator] Failed to generate sketch: {e}")
            # 返回默认的保守草图
            return self._get_default_sketch(user_query)

    def _get_default_sketch(self, user_query: str) -> AbstractSketch:
        """获取默认的保守草图

        Args:
            user_query: 用户查询

        Returns:
            默认草图
        """
        logger.warning("[AbstractSketchGenerator] Using default conservative sketch")
        return AbstractSketch(
            user_query=user_query,
            steps=[
                AbstractStep(
                    step_id="step_1",
                    step_type="READ",
                    description="Gather necessary information",
                    allowed_operations=["READ"],
                    forbidden_operations=["WRITE", "DELETE", "SEND"],
                ),
                AbstractStep(
                    step_id="step_2",
                    step_type="VERIFY",
                    description="Verify the action is necessary",
                    allowed_operations=["READ"],
                    forbidden_operations=["WRITE", "DELETE", "SEND"],
                ),
            ],
            global_constraints=[
                "Default conservative mode: Minimize operations",
                "No modifications without explicit verification",
            ],
            expected_outcome="Complete the user's request safely",
        )

    def clear_cache(self) -> None:
        """清空缓存"""
        self._sketch_cache.clear()
        logger.info("[AbstractSketchGenerator] Cache cleared")

    def update_remaining_steps_dynamic(
        self,
        abstract_sketch: AbstractSketch,
        current_step_index: int,
        execution_history: list[dict],
        user_query: str,
    ) -> AbstractSketch:
        """动态更新未执行的 abstract steps

        根据当前的执行历史和用户查询，判断是否需要更新还没有执行的 abstract steps。

        Args:
            abstract_sketch: 当前的抽象草图
            current_step_index: 当前执行到的步骤索引（从0开始）
            execution_history: 执行历史记录
            user_query: 用户查询

        Returns:
            更新后的抽象草图（如果需要更新），否则返回原始草图
        """
        # 如果已经执行完所有步骤，不需要更新
        if current_step_index >= len(abstract_sketch.steps):
            if self.config.log_sketch_generation:
                logger.info(
                    "[DynamicIntentAnchor] All steps completed, no need to update"
                )
            return abstract_sketch

        # 获取已执行的步骤和未执行的步骤
        executed_steps = abstract_sketch.steps[:current_step_index]
        remaining_steps = abstract_sketch.steps[current_step_index:]

        if self.config.log_sketch_generation:
            logger.info(
                f"[DynamicIntentAnchor] Evaluating whether to update remaining steps "
                f"(executed: {len(executed_steps)}, remaining: {len(remaining_steps)})"
            )

        # 构建执行历史摘要
        execution_summary = self._build_execution_summary(execution_history)

        # 构建已执行步骤的描述
        executed_steps_desc = "\n".join([
            f"Step {i+1}: {step.step_type} - {step.description}"
            for i, step in enumerate(executed_steps)
        ])

        # 构建未执行步骤的描述
        remaining_steps_desc = "\n".join([
            f"Step {current_step_index + i + 1}: {step.step_type} - {step.description}"
            for i, step in enumerate(remaining_steps)
        ])

        # 调用 LLM 判断是否需要更新
        prompt = f"""[ROLE]
You are the **Dynamic Intent Anchor Reflector** in the VIGIL framework.
Your task is to evaluate whether the remaining abstract execution steps need to be updated based on current progress.

[INPUT CONTEXT]
1. **User's Original Query**: "{user_query}"

2. **Global Constraints**:
{chr(10).join([f"- {c}" for c in abstract_sketch.global_constraints])}

3. **Executed Steps** (Already completed):
{executed_steps_desc if executed_steps_desc else "None (this is the first step)"}

4. **Execution Results** (What actually happened):
{execution_summary if execution_summary else "No execution results yet"}

5. **Current Remaining Steps** (Not yet executed):
{remaining_steps_desc}

[TASK]
Analyze the execution results and determine if the remaining steps need to be updated.

**Update Criteria**:
1. **Deviation from Plan**: Did the actual execution deviate significantly from the original plan?
2. **New Information**: Did the execution reveal new information that wasn't considered in the original plan?
3. **Infeasibility**: Are the remaining steps no longer feasible based on what happened?
4. **Redundancy**: Have some of the remaining steps already been accomplished?
5. **Missing Steps**: Are there critical steps missing that should be added?

[CRITICAL INSTRUCTIONS]
- **Conservative Approach**: Only update if there's a clear need. Small deviations don't require updates.
- **Maintain User Intent**: Any updates must still satisfy the user's original query and global constraints.
- **Preserve Completed Work**: Never modify already executed steps.

[OUTPUT FORMAT]
Return a JSON object with the following structure:

{{
  "needs_update": true/false,
  "reasoning": "Explain why update is or isn't needed",
  "updated_steps": [
    {{
      "step_id": "unique_id",
      "step_type": "VERB_TARGET_ENTITY",
      "description": "What this step does",
      "allowed_capabilities": ["SEARCH", "READ", etc.],
      "forbidden_capabilities": ["WRITE", "DELETE", etc.]
    }}
  ]
}}

**If needs_update is false**: Return empty updated_steps array
**If needs_update is true**: Provide the COMPLETE list of remaining steps (updated)

Generate your response now (JSON only):"""

        try:
            # 调用 LLM
            response = self.client.chat.completions.create(
                model=self.config.sketch_generator_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise reflection assistant. Always respond with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.dynamic_intent_anchor_temperature,
                response_format={"type": "json_object"},
                # Note: response_format removed for compatibility with non-OpenAI providers (e.g., Qwen)
            )

            # 记录 token 使用情况
            if response.usage:
                self.token_tracker.record_usage(
                    module="DynamicIntentAnchor",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    model=self.config.dynamic_intent_anchor_model,
                )

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned empty content")

            # 解析 JSON
            import json
            result = json.loads(content.strip())

            needs_update = result.get("needs_update", False)
            reasoning = result.get("reasoning", "No reasoning provided")

            if self.config.log_sketch_generation:
                logger.info(
                    f"[DynamicIntentAnchor] Reflection result: needs_update={needs_update}"
                )
                logger.info(f"[DynamicIntentAnchor] Reasoning: {reasoning}")

            # 如果不需要更新，直接返回原始草图
            if not needs_update:
                return abstract_sketch

            # 如果需要更新，构建新的步骤列表
            updated_steps_data = result.get("updated_steps", [])
            if not updated_steps_data:
                logger.warning(
                    "[DynamicIntentAnchor] needs_update=true but no updated_steps provided. "
                    "Keeping original steps."
                )
                return abstract_sketch

            # 解析更新后的步骤
            updated_remaining_steps = []
            for i, step_data in enumerate(updated_steps_data):
                # 自动修复：确保 allowed_capabilities 和 forbidden_capabilities 是数组
                allowed_caps = step_data.get("allowed_capabilities")
                forbidden_caps = step_data.get("forbidden_capabilities")

                if isinstance(allowed_caps, str):
                    allowed_caps = [op.strip() for op in allowed_caps.split(",") if op.strip()]
                if isinstance(forbidden_caps, str):
                    forbidden_caps = [op.strip() for op in forbidden_caps.split(",") if op.strip()]

                step = AbstractStep(
                    step_id=str(step_data.get("step_id", f"step_{current_step_index + i + 1}")),
                    step_type=step_data.get("step_type", "READ"),
                    description=step_data.get("description", ""),
                    allowed_operations=allowed_caps,
                    forbidden_operations=forbidden_caps,
                    expected_tools=step_data.get("expected_tools"),
                    tool_candidates=None,  # 将在后面重新筛选
                )
                updated_remaining_steps.append(step)

            # 合并已执行的步骤和更新后的未执行步骤
            new_steps = executed_steps + updated_remaining_steps

            # 创建新的 abstract sketch
            new_sketch = AbstractSketch(
                user_query=abstract_sketch.user_query,
                steps=new_steps,
                global_constraints=abstract_sketch.global_constraints,
                expected_outcome=abstract_sketch.expected_outcome,
                metadata={
                    **(abstract_sketch.metadata or {}),
                    "dynamic_update": {
                        "updated_at_step": current_step_index,
                        "reasoning": reasoning,
                        "original_steps_count": len(abstract_sketch.steps),
                        "new_steps_count": len(new_steps),
                    }
                }
            )

            if self.config.log_sketch_generation:
                logger.info(
                    f"[DynamicIntentAnchor] ✓ Updated abstract sketch: "
                    f"{len(remaining_steps)} → {len(updated_remaining_steps)} remaining steps"
                )
                for i, step in enumerate(updated_remaining_steps, current_step_index + 1):
                    logger.info(f"  Updated Step {i}: {step.step_type} - {step.description}")

            return new_sketch

        except Exception as e:
            logger.error(f"[DynamicIntentAnchor] Failed to update steps: {e}")
            # 出错时返回原始草图
            return abstract_sketch

    def _build_execution_summary(self, execution_history: list[dict]) -> str:
        """构建执行历史摘要

        Args:
            execution_history: 执行历史记录

        Returns:
            执行历史摘要文本
        """
        if not execution_history:
            return "No execution results yet"

        summary_lines = []
        for record in execution_history:
            step_idx = record.get("step_index", "?")
            tool_name = record.get("tool_name", "unknown")
            args = record.get("arguments", {})
            result = record.get("result", "")

            # 简化参数显示
            import json
            args_str = json.dumps(args) if args else "{}"

            # 截断结果
            result_preview = result[:300] if result else "No result"

            summary_lines.append(
                f"Step {step_idx}: Called {tool_name}({args_str})\n"
                f"  Result: {result_preview}"
            )

        return "\n".join(summary_lines)

    def _filter_tool_candidates_for_step(
        self,
        step: AbstractStep,
        available_tools: list[dict[str, str]],
        user_query: str
    ) -> list[str]:
        """为特定步骤筛选工具候选

        遵循 "Recall Relevant, Retain Ambiguity" 原则：
        - 剔除完全无关的工具（如在READ步骤中剔除DELETE工具）
        - 保留所有声称能完成此步骤的工具（包括恶意的同名副本）

        Args:
            step: 抽象步骤
            available_tools: 可用工具列表
            user_query: 用户查询

        Returns:
            工具候选名称列表
        """
        step_type = step.step_type
        step_desc = step.description.lower()
        allowed_ops = step.allowed_operations or []
        forbidden_ops = step.forbidden_operations or []

        candidates = []
        tool_families = {}  # 跟踪同类工具（如 read_file, community_read_file）

        for tool in available_tools:
            tool_name = tool.get("name", "")
            tool_desc = tool.get("description", "").lower()

            # === 规则1: 基于步骤类型和操作的基本过滤 ===
            # 提取工具的核心动词
            tool_core_verb = self._extract_tool_verb(tool_name)

            # 判断工具的操作类型
            tool_operation = self._infer_tool_operation(tool_name, tool_desc)

            # 检查是否被明确禁止
            if tool_operation in forbidden_ops:
                # 即使被禁止，如果工具声称能做这个步骤，也要保留（可能是恶意工具）
                if self._tool_claims_to_support_step(tool_name, tool_desc, step_type, step_desc):
                    candidates.append(tool_name)
                    if self.config.log_sketch_generation:
                        logger.debug(
                            f"[AbstractSketchGenerator] Keeping '{tool_name}' despite forbidden operation "
                            f"(claims to support {step_type})"
                        )
                continue  # 如果不声称支持，则跳过

            # === 规则2: 检查工具是否声称能完成此步骤 ===
            claims_support = self._tool_claims_to_support_step(tool_name, tool_desc, step_type, step_desc)

            # === 规则3: 保留同类工具的所有变体 ===
            # 如果核心动词匹配步骤类型，跟踪同类工具
            if tool_core_verb:
                if tool_core_verb not in tool_families:
                    tool_families[tool_core_verb] = []
                tool_families[tool_core_verb].append(tool_name)

            # === 规则4: 基于allowed_operations的匹配 ===
            matches_allowed = False
            if allowed_ops:
                matches_allowed = tool_operation in allowed_ops

            # === 决策：只要满足以下任一条件就保留 ===
            # 1. 工具声称能完成此步骤
            # 2. 工具操作在允许列表中
            # 3. 工具核心动词与步骤类型相关
            keep_tool = (
                claims_support or
                matches_allowed or
                self._verb_matches_step_type(tool_core_verb, step_type)
            )

            if keep_tool:
                candidates.append(tool_name)

        # === 规则5: 保留同类工具的所有变体（包括恶意副本） ===
        # 如果某个动词类有多个工具，确保全部保留
        for verb, tools_in_family in tool_families.items():
            if len(tools_in_family) > 1:
                # 有多个同类工具，全部保留（可能包含恶意副本）
                for tool_name in tools_in_family:
                    if tool_name not in candidates:
                        candidates.append(tool_name)
                        if self.config.log_sketch_generation:
                            logger.debug(
                                f"[AbstractSketchGenerator] Keeping '{tool_name}' "
                                f"(part of tool family '{verb}' with {len(tools_in_family)} variants)"
                            )

        return candidates

    def _extract_tool_verb(self, tool_name: str) -> str:
        """从工具名称中提取核心动词

        Args:
            tool_name: 工具名称

        Returns:
            核心动词
        """
        # 移除常见的修饰词
        modifiers = ["advanced", "premium", "pro", "basic", "simple", "standard",
                     "official", "community", "enhanced", "optimized"]

        name_parts = tool_name.lower().split("_")
        core_parts = [part for part in name_parts if part not in modifiers]

        # 查找动词
        common_verbs = ["get", "set", "read", "write", "send", "create", "update",
                       "delete", "schedule", "list", "search", "fetch"]

        for part in core_parts:
            if part in common_verbs:
                return part

        # 如果没找到动词，返回第一个非修饰词
        return core_parts[0] if core_parts else ""

    def _infer_tool_operation(self, tool_name: str, tool_desc: str) -> str:
        """推断工具的操作类型

        Args:
            tool_name: 工具名称
            tool_desc: 工具描述

        Returns:
            操作类型（READ, WRITE, DELETE, SEND, CREATE, UPDATE, etc.）
        """
        combined = f"{tool_name} {tool_desc}".lower()

        if any(kw in combined for kw in ["delete", "remove", "drop"]):
            return "DELETE"
        elif any(kw in combined for kw in ["send", "email", "message", "notify", "post"]):
            return "SEND"
        elif any(kw in combined for kw in ["create", "add", "new"]):
            return "CREATE"
        elif any(kw in combined for kw in ["update", "modify", "change", "edit"]):
            return "UPDATE"
        elif any(kw in combined for kw in ["write", "save"]):
            return "WRITE"
        elif any(kw in combined for kw in ["get", "read", "fetch", "list", "search", "view"]):
            return "READ"
        else:
            return "READ"  # 默认假设为READ

    def _tool_claims_to_support_step(self, tool_name: str, tool_desc: str,
                                     step_type: str, step_desc: str) -> bool:
        """判断工具是否声称能支持该步骤

        Args:
            tool_name: 工具名称
            tool_desc: 工具描述
            step_type: 步骤类型
            step_desc: 步骤描述

        Returns:
            是否声称支持
        """
        combined = f"{tool_name} {tool_desc}".lower()
        step_combined = f"{step_type} {step_desc}".lower()

        # 提取关键词
        step_keywords = set(step_combined.split()) - {
            "the", "a", "an", "is", "are", "to", "for", "of", "in", "on", "with"
        }

        tool_keywords = set(combined.split()) - {
            "the", "a", "an", "is", "are", "to", "for", "of", "in", "on", "with"
        }

        # 计算重叠
        overlap = len(step_keywords & tool_keywords)

        # 如果有显著重叠，认为工具声称能支持
        return overlap >= 2 or (overlap >= 1 and len(step_keywords) <= 3)

    def _verb_matches_step_type(self, verb: str, step_type: str) -> bool:
        """判断动词是否匹配步骤类型

        Args:
            verb: 工具的核心动词
            step_type: 步骤类型

        Returns:
            是否匹配
        """
        # 映射步骤类型到相关动词
        step_type_verbs = {
            "READ": ["read", "get", "fetch", "list", "search", "view"],
            "SEARCH": ["search", "find", "list", "get", "fetch"],
            "FILTER": ["filter", "search", "list", "get"],
            "SELECT": ["select", "get", "read"],
            "CREATE": ["create", "add", "new", "schedule", "send"],
            "UPDATE": ["update", "modify", "change", "edit", "set"],
            "DELETE": ["delete", "remove", "drop"],
            "SEND": ["send", "email", "message", "notify", "post"],
            "VERIFY": ["get", "read", "fetch", "list"],
            "PAY": ["send", "schedule", "create"],  # 支付可以用send/schedule
        }

        relevant_verbs = step_type_verbs.get(step_type, [])
        return verb in relevant_verbs
