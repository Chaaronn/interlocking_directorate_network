Recursive Company Tree Analyzer

This Python project uses the Companies House API to fetch and analyze the hierarchical structure of significant controllers (SIGs) for a given company. It retrieves detailed information about companies and their significant controllers recursively, creating a tree-like structure of ownership and control.
Features

    Search Companies: Search for a company by name using the Companies House API.
    Retrieve Significant Controllers: Identify and process individuals or corporate entities with significant control over a company.
    Recursive Analysis: Traverse and map the hierarchical ownership structure of companies and their controllers.
    Batch Processing: Optimized API calls to minimize redundancy and improve performance.
    Detailed Insights: Fetch additional information, including company profiles, filing history, and control details.

Requirements
Prerequisites

    Python: Version 3.8 or higher.
    API Key: Obtain an API key from the Companies House API Developer Portal.

Python Libraries

Install the required Python libraries:

pip install requests

Setup

    Clone the Repository:

git clone https://github.com/yourusername/recursive-company-tree.git
cd recursive-company-tree

Set Up Environment Variables:

    Create a .env file or export the API_KEY as an environment variable:

    export API_KEY='your_companies_house_api_key'

Run the Script: Use the Python script to analyze a company:

    python script_name.py

Usage
Functions Overview
1. Recursive Tree Analysis

from your_module import recursive_get_company_tree_from_sigs

company_tree = recursive_get_company_tree_from_sigs("Example Company")
for entity in company_tree:
    print(entity)

    Input: Company name (string).
    Output: List of dictionaries representing the company tree.

2. API Utilities

    search_ch(name): Searches for a company by name.
    get_persons_with_control_info(company_link): Retrieves information about persons with significant control over a company.
    get_company_profile(company_number): Fetches a company's detailed profile.
    get_filling_history(company_number): Retrieves a company's filing history.

Example Output

[
    {
        "company_id": "12345678",
        "company_name": "Example Company Ltd",
        "etag": "abc123",
        "name": "Parent Company",
        "nature_of_control": ["Ownership of shares: >50%", "Voting rights: >50%"],
        "link": "https://find-and-update.company-information.service.gov.uk/company/12345678",
        "kind": "corporate-entity-person-with-significant-control",
        "notified_on": "2023-01-01",
        "locality": "London",
        "accounts": {...}
    },
    ...
]

Error Handling

    Handles API errors such as 404 (not found) or 429 (rate limits).
    Gracefully handles missing data and unexpected API responses.

Limitations

    The script depends on the data provided by the Companies House API, which may have gaps or inaccuracies.
    API rate limits may require throttling for large-scale recursive searches.

Contributing

Contributions are welcome! To contribute:

    Fork the repository.
    Create a new branch:

git checkout -b feature-name

Commit your changes and push:

    git push origin feature-name

    Create a Pull Request.

License

This project is licensed under the MIT License.
Acknowledgments

    Companies House API for providing access to company data.

Feel free to customize this further based on your specific project structure or additional features.
