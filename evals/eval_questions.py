"""
Sample evaluation questions for handbook.txt
Used to test retrieval, citation accuracy, and refusal behavior.
"""

ANSWERABLE_QUESTIONS = [
    # Refund policy (page 7)
    {
        "question": "What is the refund window for software license purchases?",
        "gold_page": 7,
        "category": "refund",
        "keywords": ["30 days", "refund", "purchase"],
    },
    {
        "question": "What is the deadline for submitting a refund request?",
        "gold_page": 7,
        "category": "refund",
        "keywords": ["30 days", "billing@techcorp.com"],
    },
    {
        "question": "How long does it take to process an approved refund?",
        "gold_page": 7,
        "category": "refund",
        "keywords": ["10 business days"],
    },
    {
        "question": "What are non-refundable items?",
        "gold_page": 7,
        "category": "refund",
        "keywords": ["professional services", "onboarding", "custom development"],
    },
    # Leave policy (page 5)
    {
        "question": "How much PTO do employees get in their first two years?",
        "gold_page": 5,
        "category": "leave",
        "keywords": ["15 days"],
    },
    {
        "question": "How long is parental leave for primary caregivers?",
        "gold_page": 5,
        "category": "leave",
        "keywords": ["16 weeks"],
    },
    {
        "question": "How much advance notice is required for Q4 PTO requests?",
        "gold_page": 5,
        "category": "leave",
        "keywords": ["10 business days"],
    },
    # Expense policy (page 6)
    {
        "question": "What is the maximum reimbursement for a dinner meal?",
        "gold_page": 6,
        "category": "expenses",
        "keywords": ["$75"],
    },
    {
        "question": "How many days do employees have to submit expense reports?",
        "gold_page": 6,
        "category": "expenses",
        "keywords": ["30 days"],
    },
    # Security policy (page 11)
    {
        "question": "How often must passwords be changed for privileged accounts?",
        "gold_page": 11,
        "category": "security",
        "keywords": ["90 days"],
    },
    {
        "question": "How quickly must a data breach be reported?",
        "gold_page": 11,
        "category": "security",
        "keywords": ["1 hour"],
    },
    # Remote work (page 4)
    {
        "question": "How many days per week can employees work remotely?",
        "gold_page": 4,
        "category": "remote_work",
        "keywords": ["3 days"],
    },
    {
        "question": "How long can employees work remotely from another country without approval?",
        "gold_page": 4,
        "category": "remote_work",
        "keywords": ["14 consecutive days"],
    },
    # Benefits (page 8)
    {
        "question": "What is the annual learning stipend amount?",
        "gold_page": 8,
        "category": "benefits",
        "keywords": ["$2,000"],
    },
    {
        "question": "What percentage of 401k contributions does TechCorp match?",
        "gold_page": 8,
        "category": "benefits",
        "keywords": ["50%", "6%"],
    },
    # Company info (page 1)
    {
        "question": "When was TechCorp founded?",
        "gold_page": 1,
        "category": "company",
        "keywords": ["2010"],
    },
    {
        "question": "How many employees does TechCorp have?",
        "gold_page": 1,
        "category": "company",
        "keywords": ["2,500"],
    },
    # Performance reviews (page 9)
    {
        "question": "What rating triggers a Performance Improvement Plan?",
        "gold_page": 9,
        "category": "performance",
        "keywords": ["2", "Needs Improvement"],
    },
    {
        "question": "How long is the PIP period?",
        "gold_page": 9,
        "category": "performance",
        "keywords": ["90 days"],
    },
    # Exit procedures (page 12)
    {
        "question": "What is the required notice period for resignation?",
        "gold_page": 12,
        "category": "exit",
        "keywords": ["2 weeks"],
    },
]

UNANSWERABLE_QUESTIONS = [
    {
        "question": "What is TechCorp's stock price today?",
        "reason": "Real-time financial data not in handbook",
    },
    {
        "question": "Who is the current CEO of TechCorp?",
        "reason": "CEO name not mentioned in handbook",
    },
    {
        "question": "What is TechCorp's annual revenue?",
        "reason": "Revenue figures not disclosed in handbook",
    },
    {
        "question": "Does TechCorp have offices in Brazil?",
        "reason": "Specific country offices not listed in handbook",
    },
    {
        "question": "What is the Wi-Fi password for the San Francisco office?",
        "reason": "Network credentials not in handbook",
    },
    {
        "question": "What programming languages does TechCorp use?",
        "reason": "Technical stack not described in handbook",
    },
    {
        "question": "What is TechCorp's market cap?",
        "reason": "Financial metrics not in handbook",
    },
    {
        "question": "Who is the head of the Engineering department?",
        "reason": "Individual leadership names not in handbook",
    },
    {
        "question": "What is the cafeteria menu for today?",
        "reason": "Daily menus not in handbook",
    },
    {
        "question": "Does TechCorp offer pet insurance?",
        "reason": "Pet insurance not mentioned in benefits section",
    },
]
