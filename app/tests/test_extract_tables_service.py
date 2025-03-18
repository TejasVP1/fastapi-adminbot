import pytest
from app.services.extract_tables_service import extract_tables_and_columns

@pytest.mark.parametrize(
    "query, expected_tables, expected_columns",
    [
        # Simple SELECT
        ("SELECT name, age FROM users", ["users"], ["name", "age"]),

        # Multiple tables with JOIN
        ("SELECT u.id, o.amount FROM users u JOIN orders o ON u.id = o.user_id", ["users", "orders"], ["id", "amount"]),

        # Aliases in FROM
        ("SELECT t1.name FROM employees AS t1", ["employees"], ["name"]),

        # Aliases in JOIN
        ("SELECT t1.name, t2.salary FROM employees t1 JOIN payroll t2 ON t1.id = t2.emp_id", ["employees", "payroll"], ["name", "salary"]),

        # Aggregation function (should exclude column)
        ("SELECT COUNT(id), SUM(salary) FROM employees", ["employees"], []),

        # Wildcard SELECT
        ("SELECT * FROM customers", ["customers"], ["*"]),

        # Multiple columns with AS alias
        ("SELECT name AS full_name, age AS years FROM people", ["people"], ["name", "age"]),

        # Multiple tables in FROM clause
        ("SELECT name FROM employees, departments", ["employees", "departments"], ["name"]),

        # Complex query with WHERE, GROUP BY
        ("SELECT department, AVG(salary) FROM employees WHERE age > 30 GROUP BY department", ["employees"], ["department"]),

        # Query with functions that are not aggregations
        ("SELECT LOWER(email), LENGTH(name) FROM users", ["users"], ["email", "name"]),
    ]
)
def test_extract_tables_and_columns(query, expected_tables, expected_columns):
    """Test table and column extraction from SQL queries."""
    tables, columns = extract_tables_and_columns(query)
    assert tables == expected_tables
    assert columns == expected_columns
