# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
SQLite in-memory database for the SQL Query Builder Environment.

Creates a realistic company database with departments, employees, and sales
data. The database is recreated fresh on every reset() call for clean
episode isolation.
"""

import sqlite3


def create_database() -> sqlite3.Connection:
    """Create a fresh in-memory SQLite database with seed data.

    Returns:
        sqlite3.Connection with row_factory set to sqlite3.Row
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        -- ──────────────────────────────────────────────
        -- Schema
        -- ──────────────────────────────────────────────
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            budget REAL NOT NULL,
            location TEXT NOT NULL
        );

        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            department_id INTEGER NOT NULL REFERENCES departments(id),
            salary REAL NOT NULL,
            hire_date TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE sales (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id),
            amount REAL NOT NULL,
            product TEXT NOT NULL,
            sale_date TEXT NOT NULL,
            region TEXT NOT NULL
        );

        -- ──────────────────────────────────────────────
        -- Seed data: departments (5)
        -- ──────────────────────────────────────────────
        INSERT INTO departments VALUES (1, 'Engineering',  500000, 'San Francisco');
        INSERT INTO departments VALUES (2, 'Marketing',    200000, 'New York');
        INSERT INTO departments VALUES (3, 'Sales',        300000, 'Chicago');
        INSERT INTO departments VALUES (4, 'HR',           150000, 'San Francisco');
        INSERT INTO departments VALUES (5, 'Finance',      250000, 'New York');

        -- ──────────────────────────────────────────────
        -- Seed data: employees (20)
        -- ──────────────────────────────────────────────
        INSERT INTO employees VALUES (1,  'Alice Chen',      'alice@company.com',   1, 130000, '2022-01-15', 'Senior Engineer');
        INSERT INTO employees VALUES (2,  'Bob Smith',       'bob@company.com',     1,  95000, '2023-03-20', 'Engineer');
        INSERT INTO employees VALUES (3,  'Carol Davis',     'carol@company.com',   2,  85000, '2022-06-01', 'Marketing Lead');
        INSERT INTO employees VALUES (4,  'David Wilson',    'david@company.com',   3,  75000, '2023-01-10', 'Sales Rep');
        INSERT INTO employees VALUES (5,  'Eve Johnson',     'eve@company.com',     1, 140000, '2021-08-15', 'Staff Engineer');
        INSERT INTO employees VALUES (6,  'Frank Brown',     'frank@company.com',   3,  82000, '2022-11-20', 'Sales Lead');
        INSERT INTO employees VALUES (7,  'Grace Lee',       'grace@company.com',   4,  90000, '2023-02-28', 'HR Manager');
        INSERT INTO employees VALUES (8,  'Henry Taylor',    'henry@company.com',   2,  72000, '2023-07-15', 'Content Writer');
        INSERT INTO employees VALUES (9,  'Iris Wang',       'iris@company.com',    5, 110000, '2022-04-10', 'Financial Analyst');
        INSERT INTO employees VALUES (10, 'Jack Martin',     'jack@company.com',    1, 105000, '2023-09-01', 'Engineer');
        INSERT INTO employees VALUES (11, 'Karen White',     'karen@company.com',   3,  68000, '2024-01-15', 'Sales Rep');
        INSERT INTO employees VALUES (12, 'Leo Garcia',      'leo@company.com',     5,  95000, '2023-06-20', 'Accountant');
        INSERT INTO employees VALUES (13, 'Mia Robinson',    'mia@company.com',     2,  78000, '2022-09-10', 'Designer');
        INSERT INTO employees VALUES (14, 'Noah Clark',      'noah@company.com',    1, 115000, '2022-12-01', 'Senior Engineer');
        INSERT INTO employees VALUES (15, 'Olivia Harris',   'olivia@company.com',  4,  65000, '2024-02-01', 'HR Associate');
        INSERT INTO employees VALUES (16, 'Paul Adams',      'paul@company.com',    3,  71000, '2023-04-15', 'Sales Rep');
        INSERT INTO employees VALUES (17, 'Quinn Baker',     'quinn@company.com',   5, 120000, '2021-11-10', 'Finance Manager');
        INSERT INTO employees VALUES (18, 'Rachel Moore',    'rachel@company.com',  1,  98000, '2023-11-20', 'Engineer');
        INSERT INTO employees VALUES (19, 'Sam Turner',      'sam@company.com',     2,  88000, '2022-07-25', 'Marketing Analyst');
        INSERT INTO employees VALUES (20, 'Tina Scott',      'tina@company.com',    3,  73000, '2023-08-30', 'Sales Rep');

        -- ──────────────────────────────────────────────
        -- Seed data: sales (30)
        -- ──────────────────────────────────────────────
        INSERT INTO sales VALUES (1,  4,  15000, 'Widget A', '2024-01-15', 'North');
        INSERT INTO sales VALUES (2,  6,  22000, 'Widget B', '2024-01-20', 'South');
        INSERT INTO sales VALUES (3,  4,  18000, 'Widget A', '2024-02-10', 'North');
        INSERT INTO sales VALUES (4,  11,  9000, 'Widget C', '2024-02-15', 'East');
        INSERT INTO sales VALUES (5,  6,  31000, 'Widget B', '2024-02-20', 'South');
        INSERT INTO sales VALUES (6,  16, 12000, 'Widget A', '2024-03-01', 'West');
        INSERT INTO sales VALUES (7,  4,  25000, 'Widget B', '2024-03-10', 'North');
        INSERT INTO sales VALUES (8,  20,  8000, 'Widget C', '2024-03-15', 'East');
        INSERT INTO sales VALUES (9,  6,  28000, 'Widget A', '2024-03-20', 'South');
        INSERT INTO sales VALUES (10, 11, 14000, 'Widget B', '2024-04-01', 'East');
        INSERT INTO sales VALUES (11, 16, 19000, 'Widget A', '2024-04-10', 'West');
        INSERT INTO sales VALUES (12, 4,  21000, 'Widget C', '2024-04-15', 'North');
        INSERT INTO sales VALUES (13, 6,  35000, 'Widget B', '2024-04-20', 'South');
        INSERT INTO sales VALUES (14, 20, 11000, 'Widget A', '2024-05-01', 'East');
        INSERT INTO sales VALUES (15, 11, 16000, 'Widget C', '2024-05-10', 'East');
        INSERT INTO sales VALUES (16, 4,  29000, 'Widget A', '2024-05-15', 'North');
        INSERT INTO sales VALUES (17, 6,  18000, 'Widget C', '2024-05-20', 'South');
        INSERT INTO sales VALUES (18, 16, 24000, 'Widget B', '2024-06-01', 'West');
        INSERT INTO sales VALUES (19, 11, 13000, 'Widget A', '2024-06-10', 'East');
        INSERT INTO sales VALUES (20, 20, 17000, 'Widget B', '2024-06-15', 'East');
        INSERT INTO sales VALUES (21, 4,  33000, 'Widget B', '2024-06-20', 'North');
        INSERT INTO sales VALUES (22, 6,  27000, 'Widget A', '2024-07-01', 'South');
        INSERT INTO sales VALUES (23, 16, 15000, 'Widget C', '2024-07-10', 'West');
        INSERT INTO sales VALUES (24, 11, 21000, 'Widget B', '2024-07-15', 'East');
        INSERT INTO sales VALUES (25, 4,  19000, 'Widget C', '2024-07-20', 'North');
        INSERT INTO sales VALUES (26, 20, 26000, 'Widget A', '2024-08-01', 'East');
        INSERT INTO sales VALUES (27, 6,  32000, 'Widget B', '2024-08-10', 'South');
        INSERT INTO sales VALUES (28, 16, 14000, 'Widget A', '2024-08-15', 'West');
        INSERT INTO sales VALUES (29, 11, 22000, 'Widget C', '2024-08-20', 'East');
        INSERT INTO sales VALUES (30, 4,  28000, 'Widget A', '2024-09-01', 'North');
    """)
    return conn


def get_schema_text() -> str:
    """Return a human-readable schema description for the LLM agent.

    This is what the agent sees in the observation. It must be clear enough
    for a language model to write correct SQL from.
    """
    return (
        "DATABASE SCHEMA:\n"
        "\n"
        "TABLE: departments\n"
        "  - id (INTEGER, PRIMARY KEY)\n"
        "  - name (TEXT) — department name\n"
        "  - budget (REAL) — annual budget in USD\n"
        "  - location (TEXT) — office location\n"
        "\n"
        "TABLE: employees\n"
        "  - id (INTEGER, PRIMARY KEY)\n"
        "  - name (TEXT) — full name\n"
        "  - email (TEXT) — email address\n"
        "  - department_id (INTEGER, FOREIGN KEY → departments.id)\n"
        "  - salary (REAL) — annual salary in USD\n"
        "  - hire_date (TEXT) — format YYYY-MM-DD\n"
        "  - role (TEXT) — job title\n"
        "\n"
        "TABLE: sales\n"
        "  - id (INTEGER, PRIMARY KEY)\n"
        "  - employee_id (INTEGER, FOREIGN KEY → employees.id)\n"
        "  - amount (REAL) — sale amount in USD\n"
        "  - product (TEXT) — product name (Widget A, Widget B, Widget C)\n"
        "  - sale_date (TEXT) — format YYYY-MM-DD\n"
        "  - region (TEXT) — North, South, East, or West\n"
        "\n"
        "RELATIONSHIPS:\n"
        "  employees.department_id → departments.id\n"
        "  sales.employee_id → employees.id"
    )
