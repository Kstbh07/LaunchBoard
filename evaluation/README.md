# LaunchBoard Evaluation

## Overview

This directory contains tools for manually evaluating the AI classification accuracy of LaunchBoard's job classification engine.

## Evaluation Process

### Step 1: Export classified jobs

```bash
# Export 50 classified jobs for evaluation
curl -H "X-Admin-API-Key: YOUR_KEY" http://localhost:8000/api/admin/evaluation/export -o ground_truth.csv
```

Or use the admin dashboard "Export Evaluation CSV" button.

### Step 2: Manual labeling

Open `ground_truth.csv` in a spreadsheet editor and fill in:
- `manual_role`: The correct role category (use the same categories as the AI)
- `manual_city`: The correct city
- `role_correct`: "yes" or "no"
- `city_correct`: "yes" or "no"
- `both_correct`: "yes" or "no"

Save the labeled file as `ground_truth_labeled.csv`.

### Step 3: Calculate accuracy

```bash
python evaluate.py ground_truth_labeled.csv
```

This will output:
- Role classification accuracy
- City extraction accuracy
- Combined exact-match accuracy
- Confusion matrix for role classification
- Missing/unknown prediction counts

## Important Notes

- Do NOT auto-label the AI output as correct
- Do NOT fabricate evaluation results
- The ground truth must be manually verified by a human
- Use the exact role category names from the supported list
- Record "Unknown" if you cannot determine the correct label

## Supported Role Categories

1. Software Development
2. Frontend Development
3. Backend Development
4. Full Stack Development
5. AI/ML Engineering
6. Data Science
7. Data Analytics
8. DevOps / Cloud
9. Cybersecurity
10. Mobile Development
11. QA / Testing
12. UI/UX Design
13. Product Management
14. Business Development
15. Other
