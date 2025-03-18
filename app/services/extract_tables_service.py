def extract_tables_and_columns(query):
    """
    Extract tables and columns from a SQL query string.
    Excludes aggregation functions (COUNT, SUM, AVG, etc.) from the columns list.
    
    Args:
        query (str): SQL query string
        
    Returns:
        tuple: (list of tables, list of columns)
    """
    import re
    
    # Convert query to lowercase for easier matching
    query = query.lower()
    
    # Extract tables
    # Look for patterns after FROM and JOIN keywords
    from_pattern = r'from\s+([a-zA-Z0-9_\.]+(?:\s*(?:as)?\s*[a-zA-Z0-9_]+)?(?:\s*,\s*[a-zA-Z0-9_\.]+(?:\s*(?:as)?\s*[a-zA-Z0-9_]+)?)*)'
    join_pattern = r'join\s+([a-zA-Z0-9_\.]+(?:\s*(?:as)?\s*[a-zA-Z0-9_]+)?)'
    
    tables = []
    
    # Find tables after FROM
    from_match = re.search(from_pattern, query)
    if from_match:
        from_tables = from_match.group(1).split(',')
        for table in from_tables:
            # Remove aliases and trim whitespace
            table = re.sub(r'\s+as\s+', ' ', table).strip()
            table = table.split()[0].strip()  # Get the first word after removing aliases
            tables.append(table)
    
    # Find tables after JOIN
    join_matches = re.finditer(join_pattern, query)
    for match in join_matches:
        join_table = match.group(1).strip()
        # Remove aliases
        join_table = re.sub(r'\s+as\s+', ' ', join_table).strip()
        join_table = join_table.split()[0].strip()
        tables.append(join_table)
    
    # Extract columns
    columns = []
    
    # Find columns in SELECT clause
    select_pattern = r'select\s+(.*?)\s+from'
    select_match = re.search(select_pattern, query, re.DOTALL | re.IGNORECASE)
    
    if select_match:
        select_columns = select_match.group(1)
        
        # Split by commas, but not within parentheses
        cols = []
        current_col = ''
        paren_count = 0
        
        for char in select_columns:
            if char == '(' and paren_count == 0:
                paren_count += 1
                current_col += char
            elif char == ')' and paren_count > 0:
                paren_count -= 1
                current_col += char
            elif char == ',' and paren_count == 0:
                cols.append(current_col.strip())
                current_col = ''
            else:
                current_col += char
        
        if current_col:
            cols.append(current_col.strip())
        
        # List of common SQL aggregation functions to exclude
        agg_functions = ['count', 'sum', 'avg', 'min', 'max', 'stdev', 'variance', 
                         'first', 'last', 'group_concat', 'string_agg', 'array_agg', 
                         'listagg', 'median', 'percentile', 'mode', 'rank', 'dense_rank', 
                         'row_number', 'ntile', 'lead', 'lag']
        
        for col in cols:
            # Handle the case of "table.column as alias"
            col = col.strip()
            if ' as ' in col.lower():
                col = col.split(' as ')[0].strip()
            
            # Check if this is an aggregation function
            is_agg_function = False
            for func in agg_functions:
                if col.lower().startswith(func + '('):
                    is_agg_function = True
                    break
            
            # Skip aggregation functions
            if is_agg_function:
                continue
                
            # Handle the case of "function(column)" for non-aggregation functions
            if '(' in col and ')' in col:
                # Try to extract column name from function
                match = re.search(r'\(([^()]*)\)', col)
                if match:
                    extracted_col = match.group(1).strip()
                    # Check if extracted content is a literal or a column
                    if not (extracted_col.startswith("'") or 
                            extracted_col.startswith('"') or 
                            extracted_col.isdigit()):
                        col = extracted_col
                    else:
                        # Skip string literals and numbers
                        continue
            
            # Handle wildcards
            if col == '*':
                columns.append(col)
            else:
                # Remove table prefix if present
                if '.' in col:
                    col = col.split('.')[1]
                columns.append(col)
    
    # Remove duplicates while preserving order
    unique_tables = []
    for table in tables:
        if table not in unique_tables:
            unique_tables.append(table)
    
    unique_columns = []
    for col in columns:
        if col not in unique_columns:
            unique_columns.append(col)
    
    return unique_tables, unique_columns