# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Task definitions for the SQL Query Builder Environment.

Three difficulty tiers, each with multiple questions:
  - simple_lookup (easy): Basic SELECT, WHERE, JOIN, ORDER BY
  - analytics_query (medium): GROUP BY, HAVING, subqueries, aggregates
  - complex_report (hard): Window functions, CTEs, RANK, running totals
"""

TASKS = {
    # ═══════════════════════════════════════════════════════
    # EASY — Simple lookups, basic joins, filtering (7 questions)
    # ═══════════════════════════════════════════════════════
    "simple_lookup": {
        "difficulty": "easy",
        "description": "Write basic SQL queries using SELECT, WHERE, JOIN, and ORDER BY.",
        "questions": [
            {
                "id": "easy_1",
                "question": "Find all employees in the Engineering department. Return their name and salary, sorted by salary descending.",
                "expected_sql": """
                    SELECT e.name, e.salary
                    FROM employees e
                    JOIN departments d ON e.department_id = d.id
                    WHERE d.name = 'Engineering'
                    ORDER BY e.salary DESC
                """,
                "hints": ["You need to JOIN employees with departments", "Filter using WHERE on the department name"],
            },
            {
                "id": "easy_2",
                "question": "List all employees hired after 2023-06-01, sorted by hire date. Return their name, role, and hire_date.",
                "expected_sql": """
                    SELECT name, role, hire_date
                    FROM employees
                    WHERE hire_date > '2023-06-01'
                    ORDER BY hire_date
                """,
                "hints": ["Use WHERE with a date string comparison"],
            },
            {
                "id": "easy_3",
                "question": "Find the total number of employees in each department. Return the department name and the employee count. Sort by employee count descending.",
                "expected_sql": """
                    SELECT d.name, COUNT(e.id) AS employee_count
                    FROM departments d
                    LEFT JOIN employees e ON d.id = e.department_id
                    GROUP BY d.name
                    ORDER BY employee_count DESC
                """,
                "hints": ["Use COUNT() with GROUP BY", "LEFT JOIN ensures departments with zero employees appear"],
            },
            {
                "id": "easy_4",
                "question": "List all unique products that have been sold. Return the product name, sorted alphabetically.",
                "expected_sql": """
                    SELECT DISTINCT product
                    FROM sales
                    ORDER BY product
                """,
                "hints": ["Use SELECT DISTINCT to avoid duplicates"],
            },
            {
                "id": "easy_5",
                "question": "Find the employee with the email 'alice@company.com'. Return her name and role.",
                "expected_sql": """
                    SELECT name, role
                    FROM employees
                    WHERE email = 'alice@company.com'
                """,
                "hints": ["Filter using WHERE on the email column"],
            },
            {
                "id": "easy_6",
                "question": "Find all employees working in either the 'Sales' or 'Marketing' departments. Return their name and department name, sorted by department name.",
                "expected_sql": """
                    SELECT e.name, d.name AS department_name
                    FROM employees e
                    JOIN departments d ON e.department_id = d.id
                    WHERE d.name IN ('Sales', 'Marketing')
                    ORDER BY d.name
                """,
                "hints": ["Use the IN clause for multiple OR conditions"],
            },
            {
                "id": "easy_7",
                "question": "Find the names and budgets of all departments located in 'New York'. Sort by budget descending.",
                "expected_sql": """
                    SELECT name, budget
                    FROM departments
                    WHERE location = 'New York'
                    ORDER BY budget DESC
                """,
                "hints": ["Filter by location"],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════
    # MEDIUM — Aggregations, subqueries, HAVING, multi-table (7 questions)
    # ═══════════════════════════════════════════════════════
    "analytics_query": {
        "difficulty": "medium",
        "description": "Write analytical SQL using GROUP BY, HAVING, subqueries, and multi-table JOINs.",
        "questions": [
            {
                "id": "med_1",
                "question": "Find the top 3 departments by average employee salary. Return the department name, average salary rounded to 2 decimal places (as avg_salary), and the number of employees (as num_employees). Sort by average salary descending.",
                "expected_sql": """
                    SELECT d.name,
                           ROUND(AVG(e.salary), 2) AS avg_salary,
                           COUNT(e.id) AS num_employees
                    FROM departments d
                    JOIN employees e ON d.id = e.department_id
                    GROUP BY d.name
                    ORDER BY avg_salary DESC
                    LIMIT 3
                """,
                "hints": ["Use AVG() and ROUND() for the average salary", "GROUP BY department"],
            },
            {
                "id": "med_2",
                "question": "Find each salesperson's total sales amount and number of sales. Only include salespeople with total sales exceeding $100,000. Return employee name, total_sales (rounded to 2 decimals), and num_sales. Sort by total_sales descending.",
                "expected_sql": """
                    SELECT e.name,
                           ROUND(SUM(s.amount), 2) AS total_sales,
                           COUNT(s.id) AS num_sales
                    FROM employees e
                    JOIN sales s ON e.id = s.employee_id
                    GROUP BY e.id, e.name
                    HAVING SUM(s.amount) > 100000
                    ORDER BY total_sales DESC
                """,
                "hints": ["Use HAVING (not WHERE) to filter after GROUP BY"],
            },
            {
                "id": "med_3",
                "question": "Find employees whose salary is above the average salary of their own department. Return the employee name, their salary, their department name (as dept_name), and their department's average salary rounded to 2 decimals (as dept_avg). Sort by salary descending.",
                "expected_sql": """
                    SELECT e.name, e.salary, d.name AS dept_name,
                           ROUND(dept_avg.avg_sal, 2) AS dept_avg
                    FROM employees e
                    JOIN departments d ON e.department_id = d.id
                    JOIN (
                        SELECT department_id, AVG(salary) AS avg_sal
                        FROM employees
                        GROUP BY department_id
                    ) dept_avg ON e.department_id = dept_avg.department_id
                    WHERE e.salary > dept_avg.avg_sal
                    ORDER BY e.salary DESC
                """,
                "hints": ["Use a subquery to compute each department's average salary"],
            },
            {
                "id": "med_4",
                "question": "Count how many sales each product has generated. Return the product name and the count of sales (as sales_count). Sort by sales_count descending.",
                "expected_sql": """
                    SELECT product, COUNT(id) AS sales_count
                    FROM sales
                    GROUP BY product
                    ORDER BY sales_count DESC
                """,
                "hints": ["Use GROUP BY on the product column"],
            },
            {
                "id": "med_5",
                "question": "Find the total sales amount generated by each region. Return the region and the total amount (as total_amount). Sort by total_amount descending.",
                "expected_sql": """
                    SELECT region, SUM(amount) AS total_amount
                    FROM sales
                    GROUP BY region
                    ORDER BY total_amount DESC
                """,
                "hints": ["Aggregate the sales table using GROUP BY region"],
            },
            {
                "id": "med_6",
                "question": "List all departments where the average employee salary is strictly greater than $90,000. Return the department name and the average salary (rounded to 2 decimals). Sort by average salary descending.",
                "expected_sql": """
                    SELECT d.name, ROUND(AVG(e.salary), 2) AS avg_salary
                    FROM departments d
                    JOIN employees e ON d.id = e.department_id
                    GROUP BY d.name
                    HAVING AVG(e.salary) > 90000
                    ORDER BY avg_salary DESC
                """,
                "hints": ["Use HAVING to filter groups"],
            },
            {
                "id": "med_7",
                "question": "Find all employees who have made at least 3 sales. Return their name and the total number of sales (as sales_count). Sort by sales_count descending.",
                "expected_sql": """
                    SELECT e.name, COUNT(s.id) AS sales_count
                    FROM employees e
                    JOIN sales s ON e.id = s.employee_id
                    GROUP BY e.id, e.name
                    HAVING COUNT(s.id) >= 3
                    ORDER BY sales_count DESC
                """,
                "hints": ["Aggregate by employee and count records in the sales table"],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════
    # HARD — Window functions, CTEs, RANK, running totals (7 questions)
    # ═══════════════════════════════════════════════════════
    "complex_report": {
        "difficulty": "hard",
        "description": "Write advanced SQL using window functions (RANK, SUM OVER), CTEs, and complex aggregations.",
        "questions": [
            {
                "id": "hard_1",
                "question": "For each sales region, find the month with the highest total sales. Return the region, the month (formatted as YYYY-MM), the total_sales for that month, and the rank (1 = highest). Only show the #1 month per region. Sort by total_sales descending.",
                "expected_sql": """
                    WITH monthly_sales AS (
                        SELECT region,
                               SUBSTR(sale_date, 1, 7) AS month,
                               SUM(amount) AS total_sales,
                               RANK() OVER (
                                   PARTITION BY region
                                   ORDER BY SUM(amount) DESC
                               ) AS rank
                        FROM sales
                        GROUP BY region, SUBSTR(sale_date, 1, 7)
                    )
                    SELECT region, month, total_sales, rank
                    FROM monthly_sales
                    WHERE rank = 1
                    ORDER BY total_sales DESC
                """,
                "hints": ["First aggregate sales by region + month", "Then use RANK() OVER (PARTITION BY region ORDER BY total DESC)"],
            },
            {
                "id": "hard_2",
                "question": "Calculate a running cumulative sales total for each salesperson over time. Return the employee name, sale_date, individual sale amount, and the cumulative_total. Sort by employee name, then sale_date.",
                "expected_sql": """
                    SELECT e.name, s.sale_date, s.amount,
                           SUM(s.amount) OVER (
                               PARTITION BY e.id
                               ORDER BY s.sale_date
                               ROWS UNBOUNDED PRECEDING
                           ) AS cumulative_total
                    FROM employees e
                    JOIN sales s ON e.id = s.employee_id
                    ORDER BY e.name, s.sale_date
                """,
                "hints": ["Use SUM() as a window function not an aggregate", "PARTITION BY employee", "ROWS UNBOUNDED PRECEDING"],
            },
            {
                "id": "hard_3",
                "question": "Create a department performance report. For each department show: dept_name, total_employees, avg_salary (rounded to 2 decimals), total_dept_sales (total sales by employees in that dept, 0 if none), and sales_per_employee (total_dept_sales / total_employees, rounded to 2 decimals). Sort by sales_per_employee descending.",
                "expected_sql": """
                    WITH dept_stats AS (
                        SELECT department_id,
                               COUNT(*) AS total_employees,
                               ROUND(AVG(salary), 2) AS avg_salary
                        FROM employees
                        GROUP BY department_id
                    ),
                    dept_sales AS (
                        SELECT e.department_id,
                               COALESCE(SUM(s.amount), 0) AS total_dept_sales
                        FROM employees e
                        LEFT JOIN sales s ON e.id = s.employee_id
                        GROUP BY e.department_id
                    )
                    SELECT d.name AS dept_name,
                           ds.total_employees,
                           ds.avg_salary,
                           dsales.total_dept_sales,
                           ROUND(dsales.total_dept_sales * 1.0 / ds.total_employees, 2) AS sales_per_employee
                    FROM departments d
                    JOIN dept_stats ds ON d.id = ds.department_id
                    JOIN dept_sales dsales ON d.id = dsales.department_id
                    ORDER BY sales_per_employee DESC
                """,
                "hints": ["Use LEFT JOIN from employees to sales (not all employees have sales)", "COALESCE(SUM(s.amount), 0) handles departments with no sales", "COUNT(DISTINCT e.id) avoids over-counting when employees have multiple sales", "Multiply by 1.0 before dividing to get a float result in SQLite"],
            },
            {
                "id": "hard_4",
                "question": "Calculate what percentage each employee's salary uses out of their department's total allowed budget. Return employee name, department name, their salary, the department budget, and the percentage (salary / budget * 100) rounded to 2 decimals (as pct_of_budget). Sort by pct_of_budget descending.",
                "expected_sql": """
                    SELECT e.name, d.name AS department_name, e.salary, d.budget,
                           ROUND((e.salary * 100.0) / d.budget, 2) AS pct_of_budget
                    FROM employees e
                    JOIN departments d ON e.department_id = d.id
                    ORDER BY pct_of_budget DESC
                """,
                "hints": ["Use simple math in the SELECT clause", "Multiply by 100.0 to ensure a float division"],
            },
            {
                "id": "hard_5",
                "question": "Rank employees within their department based on their salary. Return employee name, department name, salary, and their rank (1 = highest salary in that dept). Sort by department name, then rank.",
                "expected_sql": """
                    SELECT e.name, d.name AS department_name, e.salary,
                           RANK() OVER (
                               PARTITION BY d.id
                               ORDER BY e.salary DESC
                           ) AS rank
                    FROM employees e
                    JOIN departments d ON e.department_id = d.id
                    ORDER BY d.name, rank
                """,
                "hints": ["Use RANK() OVER with PARTITION BY department id"],
            },
            {
                "id": "hard_6",
                "question": "Find the overall 'employee of the month' for each combined month across the entire company based on total sales. Return the month (YYYY-MM), employee name, and total_sales, strictly filtered to only the #1 top salesperson per month.",
                "expected_sql": """
                    WITH monthly_scores AS (
                        SELECT SUBSTR(sale_date, 1, 7) AS month,
                               e.name,
                               SUM(amount) AS total_sales,
                               RANK() OVER (
                                   PARTITION BY SUBSTR(sale_date, 1, 7)
                                   ORDER BY SUM(amount) DESC
                               ) as rank
                        FROM sales s
                        JOIN employees e ON s.employee_id = e.id
                        GROUP BY SUBSTR(sale_date, 1, 7), e.name
                    )
                    SELECT month, name, total_sales
                    FROM monthly_scores
                    WHERE rank = 1
                    ORDER BY month
                """,
                "hints": ["Use a CTE to first calculate everyone's monthly totals and ranks", "PARTITION BY the month string"],
            },
            {
                "id": "hard_7",
                "question": "Find how much each product type contributed to each region's sales as a percentage. Return region, product, and sales_pct (the percentage of that region's total sales made up by that product, rounded to 2 decimals). Sort by region, then sales_pct descending.",
                "expected_sql": """
                    WITH region_totals AS (
                        SELECT region, SUM(amount) as region_total
                        FROM sales
                        GROUP BY region
                    ),
                    product_region_totals AS (
                        SELECT region, product, SUM(amount) as product_total
                        FROM sales
                        GROUP BY region, product
                    )
                    SELECT p.region, p.product,
                           ROUND((p.product_total * 100.0) / r.region_total, 2) AS sales_pct
                    FROM product_region_totals p
                    JOIN region_totals r ON p.region = r.region
                    ORDER BY p.region, sales_pct DESC
                """,
                "hints": ["Calculate total sales per region first using a CTE", "Calculate sales by region AND product in a second CTE", "Join them together to find the percentage"],
            },
        ],
    },
}
