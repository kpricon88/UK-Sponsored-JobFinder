import os
import time
import requests
import pandas as pd
from playwright.sync_api import sync_playwright

# Constants
COMPANIES_TO_SKIP = 0
ROLE_TITLES = ["data engineer", "data architect", "enterprise architect"]
PAGE_SIZE = 20
UK_SPONSORS_API_BASE_URL = "https://uktiersponsors.co.uk/tierApi/api/tierData/Companies"
CAREERS_LINK_TEXTS = ["careers", "join us", "work with us", "vacancies"]

# Initialize results directory
timestamp = int(time.time())
results_dir = os.path.join(os.getcwd(), "results")
os.makedirs(results_dir, exist_ok=True)
csv_file_path = os.path.join(results_dir, f"found_companies_{timestamp}.csv")


# Function to navigate to the careers page
def find_company_careers_page(company, page, role_titles):
    company_name = company.get("organisationName")
    website_url = company.get("website")
    social_website = company.get("socialWebsite")
    found_roles = []

    with page.context.new_page() as company_page:
        company_page.route("**/*.{png,jpg,jpeg,gif,svg,ico}", lambda route: route.abort())
        try:
            company_page.goto(website_url, timeout=6000)
            careers_page_found = False

            for link_text in CAREERS_LINK_TEXTS:
                link = company_page.query_selector(f"a:text-matches('{link_text}', 'i')")
                if link:
                    link.click()
                    careers_page_found = True
                    break

            if careers_page_found:
                company_page.wait_for_load_state("load", timeout=6000)
                page_text = company_page.content().lower()
                if any(role.lower() in page_text for role in role_titles):
                    found_roles.append({
                        "companyName": company_name,
                        "pageUrl": company_page.url,
                        "socialWebsite": social_website,
                    })
                    print(f"🎉 Found role in company: {company_name}. Url: {company_page.url}\n")

        except Exception as e:
            print(f"❌ Website not found or error for company: {company_name}. Error: {e}")

    return found_roles


# Fetch companies and search for careers pages
def fetch_website_url():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            response = requests.post(UK_SPONSORS_API_BASE_URL, json={"PageNumber": 1, "RowsPerPage": 10})
            total_companies = response.json().get("count", 0)
            start_page_number = COMPANIES_TO_SKIP // PAGE_SIZE
            total_pages = -(-total_companies // PAGE_SIZE)  # Ceiling division

            all_found_roles = []

            for page_num in range(start_page_number, total_pages):
                response = requests.post(UK_SPONSORS_API_BASE_URL,
                                         json={"PageNumber": page_num, "RowsPerPage": PAGE_SIZE})
                companies = response.json().get("companies", [])

                print(f"Processing page {page_num + 1}/{total_pages}...")

                # Process each company
                for company in companies:
                    if company.get("website"):
                        found_roles = find_company_careers_page(company, page, ROLE_TITLES)
                        all_found_roles.extend(found_roles)

            if all_found_roles:
                pd.DataFrame(all_found_roles).to_csv(csv_file_path, index=False)
                print(f"Results saved to {csv_file_path}")

        except requests.RequestException as e:
            print(f"Error fetching companies: {e}")

        finally:
            browser.close()


fetch_website_url()
