"""
External system integration clients.

Each client reads its configuration from environment variables.
All credentials must be in .env — never hardcoded.

Available clients:
    - UnanetClient: Unanet CRM REST API
    - SharePointClient: Microsoft Graph API
    - ConfluenceClient: Atlassian Confluence REST API
"""
