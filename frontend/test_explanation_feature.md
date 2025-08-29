# Test Plan for SQL Explanation Feature

## Test Scenarios

### 1. Explanation NOT requested initially (flag is OFF)
**Steps:**
1. Ensure "Explain SQL" flag is OFF in sidebar
2. Submit a query like "How many schools with an average score in Math greater than 400 in the SAT test are exclusively virtual?"
3. Wait for SQL generation to complete

**Expected Result:**
- SQL is generated and displayed
- NO explanation is generated or shown
- No "Generating SQL explanation..." message in logs

### 2. Explanation requested initially (flag is ON)
**Steps:**
1. Turn ON "Explain SQL" flag in sidebar
2. Submit a query
3. Wait for SQL generation to complete

**Expected Result:**
- SQL is generated and displayed
- Explanation IS generated automatically
- "Generating SQL explanation..." message appears in logs
- Explanation is displayed when table data is loaded

### 3. On-demand explanation generation (flag turned ON after SQL generation)
**Steps:**
1. Ensure "Explain SQL" flag is OFF
2. Submit a query and wait for SQL to be generated
3. After SQL is ready and table is displayed, turn ON the "Explain SQL" flag

**Expected Result:**
- The system detects flag was turned on
- Calls `/explain-sql` endpoint to generate explanation
- Explanation appears below the table once generated

### 4. Toggle visibility of existing explanation
**Steps:**
1. With explanation already generated and displayed
2. Turn OFF "Explain SQL" flag
3. Turn ON "Explain SQL" flag again

**Expected Result:**
- Explanation hides when flag is OFF
- Explanation reappears when flag is ON (without regenerating)

## API Verification

### Backend Behavior:
- When `explain_generated_query` is `false` in request: No explanation generation
- When `explain_generated_query` is `true` in request: Explanation generated during pipeline
- `/explain-sql` endpoint available for on-demand generation

### Frontend Behavior:
- Stores necessary context (SQL, question) for on-demand generation
- Detects flag change from false to true
- Makes proper API call with all required fields