You are an expert Python 3 engineer.

Build the full MVP app described below as a single, well-structured Python script that I can run from the command line.

## High-level goal

Simulate the workflow of a Technical Support Engineer investigating inconsistent data uploads.

The app should:
- Accept a CSV file of user activity metrics.
- Validate data integrity.
- Compute summary statistics.
- Call the OpenAI Chat Completions API to generate a support-ticket-ready summary of the dataset health, likely causes, and one remediation step.

I want production-quality, well-commented code that is easy for another engineer to read and extend.

---

## Implementation Requirements

### 1. Tech & Structure

- Language: Python 3.10+.
- Single entrypoint script, e.g. `data_health_analyzer.py`.
- Use `argparse` to accept an input CSV file path:
  - Example usage: `python data_health_analyzer.py --file sample_user_metrics.csv`
- Use the official OpenAI Python client for Chat Completions.
- Read the OpenAI API key from the `OPENAI_API_KEY` environment variable (do NOT hardcode any keys).
- Include clear docstrings and inline comments explaining key steps.

### 2. Input CSV Format

The input file is a CSV with the following structure:

- Columns: `user_id,sessions,clicks,errors`
- Example:

  user_id,sessions,clicks,errors  
  U101,5,120,2  
  U102,3,95,0  
  U103,7,210,1  
  U104,,180,1  
  U105,4,-15,0  
  U101,2,60,0  

Assumptions:
- `user_id` is a string.
- `sessions`, `clicks`, `errors` are integers when present.
- There may be missing values, negative values, and duplicate user_ids.

You may use either the built-in `csv` module or `pandas`. If you use `pandas`, add a comment explaining how to install it.

### 3. Data Validation Logic

Implement data validation with the following rules:

- **Critical error:**
  - If the CSV file is completely empty (no data rows), stop execution and print a clear user-facing error message and exit with a non-zero status code.
    - Example message:
      `Error: The input file is empty. Please upload a valid dataset.`

- **Warnings (do NOT stop execution, just record):**
  - Missing values in any numeric column (`sessions`, `clicks`, `errors`).
  - Negative numbers in any numeric column.
  - Duplicate `user_id` values.

Implementation details:

- Maintain a `warnings` list of strings.
- For each problematic row, append a specific message indicating the row number and the issue.
  - Example formats (follow this style):
    - `Row 4: missing value in sessions column.`
    - `Row 5: negative value in clicks column.`
    - `Row 6: duplicate user_id U101 detected.`
- At the end of processing (if not critical error), print a **Validation Report** section:
  - If there are no warnings:
    - Print: `Validation Report: no warnings.`
  - If there are warnings:
    - Print:
      ```
      Validation Report:
      - Row 4: missing value in sessions column.
      - Row 5: negative value in clicks column.
      - Row 6: duplicate user_id U101 detected.
      ```

Make sure row numbering is 1-based and counts the first data row as row 2 (since the header is row 1). Clarify in a comment how rows are numbered.

### 4. Summary Statistics

On the **validated (but not necessarily clean)** dataset (i.e., still including rows with warnings), compute and print:

- `Total Users`: count of **unique** `user_id` values.
- `Average Sessions per User`: average of `sessions` aggregated per user (ignore rows where sessions is missing or not a valid integer).
- `% Users with Errors`: percentage of unique users that have `errors > 0` in at least one of their rows.

Implementation details:

- Use robust numeric conversion with error handling (e.g., treat non-parsable or missing values as invalid for that metric).
- When printing summary stats, use a clean, readable format like:

