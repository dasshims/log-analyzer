Requirements

You are a Technical Support Engineer investigating a customer complaint about inconsistent data uploads.

Build a small Python app that:

1. Accepts a CSV file containing user activity metrics (e.g., user_id, sessions, clicks, errors). input file is in this format - 
    user_id,sessions,clicks,errors
    U101,5,120,2
    U102,3,95,0
    U103,7,210,1
    U104,,180,1
    U105,4,-15,0
    U101,2,60,0

2. Validates data integrity — check for missing fields, negative numbers, or duplicate user_ids.
    Rules for data validation 
        1. For ciritcal error such as empty file - Stop execution and print a clear, user-facing message:
        2. Missing values, duplicates and negatives - warnings.append(f"Row {i}: negative value in clicks column.")
        3. Print the validation result at the end of processing.

3. Computes summary statistics (total users, avg sessions per user, % with errors).

4. Calls the OpenAI Chat Completions API to:
    Summarize the health of the dataset.
    Suggest 2–3 possible reasons for inconsistency.
    Recommend one immediate remediation step.
    The output should be readable in a support ticket (clear, concise, no raw code).