import requests
import os
import sqlite3
import time
import re
from pymongo import MongoClient

# Google API credentials
API_KEY = "AIzaSyA2BcIPxjME4tuosiZnxmrOmwF-1XeatrQ"
SEARCH_ENGINE_ID = "904582a1658934c87"

# Connect to SQLite database and retrieve company names
db_path = '/Users/estheragossa/PycharmProjects/ift_coursework_2024/000.Database/SQL/Equity.db' #add path to your Equity.db
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT security FROM equity_static")
company_names = [row[0] for row in cursor.fetchall()]
conn.close()

# MongoDB Connection
client = MongoClient("mongodb://localhost:27019/")
db = client["csr_reports_db1"]
collection = db["reports"]

# Verify connection
try:
    client.admin.command("ping")
    print("Connected to MongoDB!")
except Exception as e:
    print(f"MongoDB connection error: {e}")

# Create directory to save CSR reports
os.makedirs('CSR_Reports', exist_ok=True)


def extract_year_from_url_or_snippet(url, snippet):
    """Extracts the year from the URL or snippet text."""
    year_pattern = re.compile(r'(20[0-2][0-9])')  # Matches years 2000-2029

    url_match = year_pattern.search(url)
    snippet_match = year_pattern.search(snippet)

    if url_match:
        return url_match.group(1)
    elif snippet_match:
        return snippet_match.group(1)
    return "Unknown"


def search_csr_reports(company_name):
    """Search for CSR report PDFs using Google Custom Search."""
    query = f"{company_name} sustainability report filetype:pdf"
    url = f"https://www.googleapis.com/customsearch/v1?q={requests.utils.quote(query)}&key={API_KEY}&cx={SEARCH_ENGINE_ID}"

    response = requests.get(url)
    if response.status_code == 200:
        results = response.json().get('items', [])
        pdf_links = [(item['link'], item.get('snippet', '')) for item in results if
                     item['link'].lower().endswith('.pdf')]
        return pdf_links  # Return links with snippets
    else:
        print(f"API Error for {company_name}: {response.status_code}")
        return []


# Iterate over companies and fetch CSR reports
for company in company_names:
    print(f"\nSearching CSR reports for: {company}")
    pdf_links = search_csr_reports(company)

    if pdf_links:
        print(f"Found {len(pdf_links)} CSR reports:")
        fetched_years = set()

        for pdf_link, snippet in pdf_links:
            report_year = extract_year_from_url_or_snippet(pdf_link, snippet)

            if report_year in fetched_years:
                continue  # Skip duplicate years

            print(f"Storing report for {report_year}: {pdf_link}")
            fetched_years.add(report_year)

            # Store in MongoDB
            collection.insert_one({
                "company_name": company,
                "pdf_link": pdf_link,
                "report_year": report_year
            })

            # Download the PDF
            try:
                pdf_response = requests.get(pdf_link, timeout=10)
                if pdf_response.status_code == 200:
                    pdf_name = os.path.join('CSR_Reports', pdf_link.split('/')[-1].split('?')[0])
                    with open(pdf_name, 'wb') as pdf_file:
                        pdf_file.write(pdf_response.content)
                    print(f"Downloaded: {pdf_name}")
                else:
                    print(f"Failed to download {pdf_link}")
            except Exception as e:
                print(f"Error downloading {pdf_link}: {e}")
    else:
        print("No CSR PDF reports found.")

    time.sleep(2)  # Avoid hitting API rate limits

print("\nFinished fetching CSR reports for all companies.")

