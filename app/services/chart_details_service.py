import logging
import google.generativeai as genai
from app.core.config import config
import seaborn as sns
import pandas as pd
import matplotlib as plt

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def generate_chart_details(query_results: list, user_query: str) -> dict:
    """
    Determines whether a chart is needed, what type of chart should be used, 
    and what details are required for visualization based on the query results.
    
    Args:
        query_results (list): The SQL query result as a list of dictionaries.
        user_query (str): The original user input.

    Returns:
        dict: A dictionary containing chart recommendations.
    """

    # Instruction for Gemini
    system_instruction = (
        "You are an AI assistant that determines whether a chart is needed based on SQL query results. "
        "If a chart is needed, you must identify the best chart type and extract relevant details for visualization. "
        "Always return the response in JSON format with the following structure:\n"
        "{\n"
        '  "needs_chart": true/false,  # Whether a chart is needed\n'
        '  "chart_type": "bar/line/pie/etc.",  # Best type of chart\n'
        '  "x_axis": "column_name",  # Data for X-axis\n'
        '  "y_axis": "column_name",  # Data for Y-axis\n'
        '  "additional_info": "Any extra details needed for better visualization"\n'
        "}\n\n"
        
        "## Rules for Selecting Chart Types:\n"
        "- Use a Line Chart if the data represents trends over time (e.g., monthly disbursed amounts).\n"
        "- Use a Bar Chart for category-wise comparisons (e.g., loan types and their total amounts).\n"
        "- Use a Pie Chart if showing percentage distribution (e.g., loan type distribution).\n"
        "- Use a Scatter Plot if comparing two numerical values.\n"
        "- If the data has only one row, return needs_chart: false.\n\n"

        "## Example Inputs and Outputs:\n"
        "User Query: 'Show me the total loan disbursed per month in 2025.'\n"
        "Query Result: [ {'month': 'Jan', 'total_disbursed': 50000}, {'month': 'Feb', 'total_disbursed': 60000} ]\n"
        "Expected Output:\n"
        "{\n"
        '  "needs_chart": true,\n'
        '  "chart_type": "line",\n'
        '  "x_axis": "month",\n'
        '  "y_axis": "total_disbursed",\n'
        '  "additional_info": "Trend of total loan disbursement over months"\n'
        "}\n\n"

        "User Query: 'Show me the latest loan details of user 123.'\n"
        "Query Result: [ {'loan_id': 10, 'principal': 5000, 'status': 'DISBURSED'} ]\n"
        "Expected Output:\n"
        "{\n"
        '  "needs_chart": false\n'
        "}\n\n"

        "## User Query:\n"
        f"{user_query}\n\n"
        "## Query Results:\n"
        f"{query_results}\n\n"
        "Now, analyze the data and provide a structured JSON response."
    )

    # Log details
    logging.info(f"User Query: {user_query}")
    logging.info(f"Query Results: {query_results}")

    # Generate chart recommendations
    response = model.generate_content([system_instruction])
    output = response.text.strip()

    # Log the generated response
    logging.info(f"Generated Chart Details: {output}")

    return output


def generate_graph(query_results: pd.DataFrame, graph_details: dict):
    """Generates a graph based on the given details."""
    chart_type = graph_details.get("chart_type")
    x_axis = graph_details.get("x_axis")
    y_axis = graph_details.get("y_axis")
    additional_info = graph_details.get("additional_info", "")

    if chart_type == "None" or not x_axis or not y_axis:
        logging.warning("No valid chart type identified.")
        return None

    plt.figure(figsize=(10, 6))

    if chart_type == "Bar":
        sns.barplot(data=query_results, x=x_axis, y=y_axis)
    elif chart_type == "Line":
        sns.lineplot(data=query_results, x=x_axis, y=y_axis, marker="o")
    elif chart_type == "Pie":
        query_results.groupby(x_axis)[y_axis].sum().plot(kind="pie", autopct="%1.1f%%")
    elif chart_type == "Scatter":
        sns.scatterplot(data=query_results, x=x_axis, y=y_axis)
    elif chart_type == "Histogram":
        sns.histplot(data=query_results, x=x_axis, bins=10, kde=True)
    elif chart_type == "Box":
        sns.boxplot(data=query_results, x=x_axis, y=y_axis)
    elif chart_type == "Multi-line":
        sns.lineplot(data=query_results, x=x_axis, y=y_axis, hue=additional_info)
    elif chart_type == "Grouped Bar":
        sns.barplot(data=query_results, x=x_axis, y=y_axis, hue=additional_info)

    plt.title(f"{chart_type} Chart for {x_axis} vs {y_axis}")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
