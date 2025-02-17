import requests
from bs4 import BeautifulSoup
import os
import sqlite3
import time
from pymongo import MongoClient

# Connect to SQLite database and retrieve company names
db_path = '/Users/estheragossa/PycharmProjects/ift_coursework_2024/000.Database/SQL/Equity.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT security FROM equity_static")
company_names = [row[0] for row in cursor.fetchall()]
conn.close()

# MongoDB Connection
client = MongoClient("mongodb://localhost:27019/")


# Verify connection
try:
    client.admin.command("ping")
    print(" Connected to MongoDB!")
except Exception as e:
    print(f" MongoDB connection error: {e}")

db = client["csr_reports_db"]
collection = db["reports"]

# Create directory to save CSR reports
os.makedirs('CSR_Reports', exist_ok=True)


def search_csr_reports(company_name):
    """Scrape Bing for CSR report PDFs using BeautifulSoup."""
    query = f"{company_name} sustainability report filetype:pdf"
    search_url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(search_url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.find_all("a", href=True)

        pdf_links = list(set(link["href"] for link in results if ".pdf" in link["href"]))
        return pdf_links
    else:
        print(f"Search failed for {company_name}: {response.status_code}")
        return []


# Iterate over companies and fetch CSR reports
for company in company_names:
    print(f"\nSearching CSR reports for: {company}")
    pdf_links = search_csr_reports(company)

    if pdf_links:
        print(f"Found {len(pdf_links)} CSR reports.")
        for pdf_link in pdf_links:
            print(pdf_link)

            # Store in MongoDB
            collection.insert_one({
                "company_name": company,
                "pdf_link": pdf_link,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })

            # Download the PDF
            try:
                pdf_response = requests.get(pdf_link, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if pdf_response.status_code == 200:
                    pdf_name = os.path.join("CSR_Reports", pdf_link.split("/")[-1].split("?")[0])
                    with open(pdf_name, "wb") as pdf_file:
                        pdf_file.write(pdf_response.content)
                    print(f"Downloaded: {pdf_name}")
                else:
                    print(f"Failed to download {pdf_link}")
            except Exception as e:
                print(f"Error downloading {pdf_link}: {e}")
    else:
        print("No CSR PDF reports found.")

    time.sleep(2)  # Avoid getting blocked

print("\nFinished fetching CSR reports for all companies.")
