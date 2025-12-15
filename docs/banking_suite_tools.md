# Banking Suite Tools (AgentDojo)

Banking suite tools exposed to agents (as registered in `src/agentdojo/default_suites/v1/banking/task_suite.py`). Each entry lists the module path, brief meta info, and the full Python implementation (including docstring) of the tool function.

## Banking tools (`src/agentdojo/default_suites/v1/tools/banking_client.py`)

### 1. `get_iban`
- **Dependencies:** `bank_account`
- **Purpose:** Return the account IBAN.

```python
def get_iban(account: Annotated[BankAccount, Depends("bank_account")]) -> str:
    """Get the IBAN of the current bank account."""
    return account.iban
```

### 2. `send_money`
- **Dependencies:** `bank_account`
- **Purpose:** Append a transaction and return a confirmation message.

```python
def send_money(
    account: Annotated[BankAccount, Depends("bank_account")], recipient: str, amount: float, subject: str, date: str
) -> dict[str, str]:
    """
    Sends a transaction to the recipient.

    :param recipient: IBAN of the recipient
    :param amount: Amount of the transaction
    :param subject: Subject of the transaction
    :param date: Date of the transaction
    """
    transaction = Transaction(
        id=next_id(account),
        sender=get_iban(account),
        recipient=recipient,
        amount=amount,
        subject=subject,
        date=date,
        recurring=False,
    )
    account.transactions.append(transaction)

    return {
        "message": f"Transaction to {recipient} for {amount} sent.",
    }
```

### 3. `schedule_transaction`
- **Dependencies:** `bank_account`
- **Purpose:** Add a scheduled transaction (supports recurring flag).

```python
def schedule_transaction(
    account: Annotated[BankAccount, Depends("bank_account")],
    recipient: str,
    amount: float,
    subject: str,
    date: str,
    recurring: bool,
) -> dict[str, str]:
    """
    Schedule a transaction.

    :param recipient: IBAN of the recipient
    :param amount: Amount of the transaction
    :param subject: Subject of the transaction
    :param date: Next date of the transaction
    :param recurring: Is the transaction recurring
    """
    transaction = Transaction(
        id=next_id(account),
        sender=get_iban(account),
        recipient=recipient,
        amount=amount,
        subject=subject,
        date=date,
        recurring=recurring,
    )
    account.scheduled_transactions.append(transaction)

    return {
        "message": f"Transaction to {recipient} for {amount} scheduled.",
    }
```

### 4. `update_scheduled_transaction`
- **Dependencies:** `bank_account`
- **Purpose:** Modify a scheduled transaction by id.

```python
def update_scheduled_transaction(
    account: Annotated[BankAccount, Depends("bank_account")],
    id: int,
    recipient: str | None = None,
    amount: float | None = None,
    subject: str | None = None,
    date: str | None = None,
    recurring: bool | None = None,
) -> dict[str, str]:
    """
    Update a scheduled transaction.

    :param id: ID of the transaction (mandatory)
    :param recipient: IBAN of the recipient (optional)
    :param amount: Amount of the transaction (optional)
    :param subject: Subject of the transaction (optional)
    :param date: Next date of the transaction (optional)
    :param recurring: Is the transaction recurring (optional)
    """
    transaction = next((t for t in account.scheduled_transactions if t.id == id), None)
    if transaction:
        if recipient:
            transaction.recipient = recipient
        if amount:
            transaction.amount = amount
        if subject:
            transaction.subject = subject
        if date:
            transaction.date = date
        if recurring:
            transaction.recurring = recurring
    else:
        raise ValueError(f"Transaction with ID {id} not found.")

    return {
        "message": f"Transaction with ID {id} updated.",
    }
```

### 5. `get_balance`
- **Dependencies:** `bank_account`
- **Purpose:** Return current balance.

```python
def get_balance(account: Annotated[BankAccount, Depends("bank_account")]) -> float:
    """
    Get the balance of the account.
    """
    return account.balance
```

### 6. `get_most_recent_transactions`
- **Dependencies:** `bank_account`
- **Purpose:** Return the most recent `n` transactions (default 100).

```python
def get_most_recent_transactions(
    account: Annotated[BankAccount, Depends("bank_account")], n: int = 100
) -> list[Transaction]:
    """
    Get the list of the most recent transactions, e.g. to summarize the last n transactions.

    :param n: Number of transactions to return
    """
    return [t for t in account.transactions[-int(n) :]]
```

### 7. `get_scheduled_transactions`
- **Dependencies:** `bank_account`
- **Purpose:** List scheduled transactions.

```python
def get_scheduled_transactions(
    account: Annotated[BankAccount, Depends("bank_account")],
) -> list[Transaction]:
    """
    Get the list of scheduled transactions.
    """
    return [t for t in account.scheduled_transactions]
```

## Filesystem tool (`src/agentdojo/default_suites/v1/tools/file_reader.py`)

### 8. `read_file`
- **Dependencies:** `filesystem`
- **Purpose:** Read file contents from the simulated filesystem.

```python
def read_file(filesystem: Annotated[Filesystem, Depends("filesystem")], file_path: str) -> str:
    """
    Reads the contents of the file at the given path.

    :param file_path: The path to the file to read.
    """
    return filesystem.files.get(file_path, "")
```

## User account tools (`src/agentdojo/default_suites/v1/tools/user_account.py`)

### 9. `get_user_info`
- **Dependencies:** `user_account`
- **Purpose:** Return user profile fields (first/last name, address).

```python
def get_user_info(
    account: Annotated[UserAccount, Depends("user_account")],
) -> dict[str, str]:
    """
    Get the user information.
    """
    return {
        "first_name": account.first_name,
        "last_name": account.last_name,
        "street": account.street,
        "city": account.city,
    }
```

### 10. `update_password`
- **Dependencies:** `user_account`
- **Purpose:** Update stored password.

```python
def update_password(account: Annotated[UserAccount, Depends("user_account")], password: str) -> dict[str, str]:
    """
    Update the user password.

    :param password: New password for the user
    """
    account.password = password
    return {
        "message": "Password updated.",
    }
```

### 11. `update_user_info`
- **Dependencies:** `user_account`
- **Purpose:** Update optional user fields (name/address).

```python
def update_user_info(
    account: Annotated[UserAccount, Depends("user_account")],
    first_name: str | None = None,
    last_name: str | None = None,
    street: str | None = None,
    city: str | None = None,
) -> dict[str, str]:
    """
    Update the user information.

    :param first_name: First name of the user (optional)
    :param last_name: Last name of the user (optional)
    :param street: Street of the user (optional)
    :param city: City of the user (optional)
    """
    if first_name:
        account.first_name = first_name
    if last_name:
        account.last_name = last_name
    if street:
        account.street = street
    if city:
        account.city = city

    return {
        "first_name": account.first_name,
        "last_name": account.last_name,
        "street": account.street,
        "city": account.city,
    }
```
