import time
import csv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# ==================== CONFIGURATION FROM ENVIRONMENT VARIABLES ====================
ENROLLMENT = os.environ.get('ENROLLMENT', '02-239252-')
PASSWORD = os.environ.get('PASSWORD', 'password')
INSTITUTE = os.environ.get('INSTITUTE', 'Karachi Campus')

EMAIL_SENDER = os.environ.get('EMAIL_SENDER', 'your_email@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'your_app_password')
EMAIL_RECEIVER = os.environ.get('EMAIL_RECEIVER', 'recipient@gmail.com')

# Course values from environment (comma-separated string)
course_values_str = os.environ.get('COURSE_VALUES', 
    'MTQ3Nzgx,MTQ3Nzgz,MTQ3Nzg1,MTQ3Nzg3,MTQ3Nzkx,MTQ3Nzkz,MTQ3Nzk1,MTQ3Nzk3,MTQ3Nzk5')
COURSE_VALUES = [val.strip() for val in course_values_str.split(',')]

CSV_FILE = 'assignments_report.csv'

# ==================== HELPER FUNCTIONS ====================

def load_existing_assignments():
    """Load existing assignments from CSV to avoid duplicates"""
    existing = set()
    
    if not os.path.exists(CSV_FILE):
        print("📄 No existing CSV file found. Will create new one.")
        return existing
    
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                identifier = f"{row['Course']}|{row['Title']}|{row['Deadline']}"
                existing.add(identifier)
        
        print(f"📚 Loaded {len(existing)} existing assignments from CSV")
    except Exception as e:
        print(f"⚠️  Error reading CSV: {e}")
    
    return existing


def save_assignments_to_csv(all_assignments):
    """Save all assignments to CSV file"""
    keys = ["Course", "Title", "Deadline", "Date_Added"]
    
    try:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_assignments)
        
        print(f"💾 Saved {len(all_assignments)} assignments to {CSV_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")
        return False


def send_email_notification(new_assignments):
    """Send email notification for new assignments"""
    if not new_assignments:
        print("📧 No new assignments to notify about.")
        return
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"🔔 {len(new_assignments)} New Assignment(s) on LMS!"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .assignment {{ 
                    border: 1px solid #ddd; 
                    border-radius: 8px; 
                    padding: 15px; 
                    margin: 10px 0;
                    background-color: #f9f9f9;
                }}
                .course {{ color: #2196F3; font-weight: bold; font-size: 16px; }}
                .title {{ color: #333; font-size: 14px; margin: 5px 0; }}
                .deadline {{ color: #f44336; font-weight: bold; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎓 New Assignments Detected!</h1>
            </div>
            <div class="content">
                <p>Hello! You have <strong>{len(new_assignments)}</strong> new assignment(s) on Bahria LMS:</p>
        """
        
        for assignment in new_assignments:
            html_body += f"""
                <div class="assignment">
                    <div class="course">📚 {assignment['Course']}</div>
                    <div class="title">📝 {assignment['Title']}</div>
                    <div class="deadline">⏰ Deadline: {assignment['Deadline']}</div>
                </div>
            """
        
        html_body += f"""
            </div>
            <div class="footer">
                <p>This notification was sent on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
                <p>Check your LMS dashboard for more details</p>
                <p>🤖 Automated by GitHub Actions</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email notification sent successfully to {EMAIL_RECEIVER}")
        print(f"   Notified about {len(new_assignments)} new assignment(s)")
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Email authentication failed! Check your App Password in GitHub Secrets")
    except Exception as e:
        print(f"❌ Error sending email: {e}")


# ==================== MAIN SCRAPING LOGIC ====================

# Setup Chrome for headless mode (GitHub Actions compatible)
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Try to find Chrome binary
chrome_binary_paths = [
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
]

chrome_binary = None
for path in chrome_binary_paths:
    if os.path.exists(path):
        chrome_binary = path
        print(f"✅ Found Chrome at: {chrome_binary}")
        break

if chrome_binary:
    chrome_options.binary_location = chrome_binary

# Initialize driver without webdriver-manager (use system ChromeDriver)
try:
    # Try using ChromeDriver from PATH
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("✅ ChromeDriver initialized successfully")
except Exception as e:
    print(f"❌ Error initializing ChromeDriver: {e}")
    print("Attempting alternative method...")
    
    # Fallback: Try explicit paths
    chromedriver_paths = [
        '/usr/local/bin/chromedriver',
        '/usr/bin/chromedriver',
        './chromedriver',
    ]
    
    driver = None
    for driver_path in chromedriver_paths:
        if os.path.exists(driver_path):
            try:
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print(f"✅ ChromeDriver initialized from: {driver_path}")
                break
            except Exception as ex:
                print(f"Failed with {driver_path}: {ex}")
                continue
    
    if driver is None:
        print("❌ Could not initialize ChromeDriver")
        exit(1)

wait = WebDriverWait(driver, 20)

try:
    print("\n" + "="*50)
    print("🚀 Starting LMS Assignment Checker (GitHub Actions)")
    print("="*50 + "\n")
    
    # Load existing assignments from CSV
    existing_assignments = load_existing_assignments()
    
    # ================= LOGIN CMS =================
    print("🔐 Logging into CMS...")
    driver.get("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")
    
    wait.until(EC.presence_of_element_located((By.ID, "BodyPH_tbEnrollment")))
    
    driver.find_element(By.ID, "BodyPH_tbEnrollment").send_keys(ENROLLMENT)
    driver.find_element(By.ID, "BodyPH_tbPassword").send_keys(PASSWORD)
    
    institute_dropdown = Select(driver.find_element(By.ID, "BodyPH_ddlInstituteID"))
    institute_dropdown.select_by_visible_text(INSTITUTE)
    
    driver.find_element(By.ID, "BodyPH_btnLogin").click()
    print("✅ Logged into CMS successfully\n")
    
    # ================= CLICK GO TO LMS =================
    print("📱 Opening LMS...")
    go_to_lms = wait.until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Go To LMS"))
    )
    go_to_lms.click()
    
    driver.switch_to.window(driver.window_handles[1])
    wait.until(EC.url_contains("lms.bahria.edu.pk"))
    print("✅ LMS opened successfully\n")
    
    # ================= CLICK ASSIGNMENTS =================
    print("📋 Navigating to Assignments page...")
    assignments_link = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//a[@href='Assignments.php']"))
    )
    assignments_link.click()
    
    wait.until(EC.presence_of_element_located((By.ID, "courseId")))
    print("✅ Assignments page loaded\n")
    
    # ================= SCRAPE ASSIGNMENTS =================
    all_assignments = []
    new_assignments = []
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("="*50)
    print("🔍 Scanning courses for assignments...")
    print("="*50 + "\n")
    
    for idx, val in enumerate(COURSE_VALUES, 1):
        print(f"📚 [{idx}/{len(COURSE_VALUES)}] Checking Course ID: {val}")
        
        try:
            dropdown_elem = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "courseId"))
            )
            course_select = Select(dropdown_elem)
            
            option_element = dropdown_elem.find_element(By.XPATH, f"//option[@value='{val}']")
            course_name = option_element.text.strip()
            
            course_select.select_by_value(val)
            print(f"    📖 Course: {course_name}")
            
            time.sleep(3)
            
            tbody = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table.table-hover tbody"))
            )
            
            table_text = tbody.text.strip()
            if "No assignment uploaded yet" in table_text or not table_text:
                print(f"    ℹ️  No assignments found\n")
                continue
            
            rows = tbody.find_elements(By.TAG_NAME, "tr")
            course_assignment_count = 0
            
            for row in rows:
                tds = row.find_elements(By.TAG_NAME, "td")
                if len(tds) < 1:
                    continue
                
                title = tds[0].text.strip()
                if "No assignment uploaded yet" in title:
                    continue
                
                try:
                    deadline = row.find_element(By.CSS_SELECTOR, "small.label.label-info").text.strip()
                except:
                    deadline = "Not Found"
                
                identifier = f"{course_name}|{title}|{deadline}"
                
                assignment = {
                    "Course": course_name,
                    "Title": title,
                    "Deadline": deadline,
                    "Date_Added": current_date
                }
                
                all_assignments.append(assignment)
                course_assignment_count += 1
                
                if identifier not in existing_assignments:
                    new_assignments.append(assignment)
                    print(f"    ✨ NEW: {title} (Deadline: {deadline})")
                else:
                    print(f"    ✓ Already tracked: {title}")
            
            print(f"    📊 Found {course_assignment_count} assignment(s)\n")
            
        except Exception as e:
            print(f"    ❌ Error processing course: {e}\n")
    
    # ================= SAVE & NOTIFY =================
    print("="*50)
    print("📊 Summary")
    print("="*50)
    print(f"Total assignments found: {len(all_assignments)}")
    print(f"New assignments detected: {len(new_assignments)}")
    print(f"Previously tracked: {len(all_assignments) - len(new_assignments)}")
    print("="*50 + "\n")
    
    if save_assignments_to_csv(all_assignments):
        print("✅ CSV file updated successfully\n")
    
    if new_assignments:
        print("="*50)
        print("📧 Sending Email Notification")
        print("="*50)
        send_email_notification(new_assignments)
    else:
        print("ℹ️  No new assignments to notify about. All assignments are up to date!")
    
    print("\n" + "="*50)
    print("✅ LMS Check Complete!")
    print("="*50 + "\n")

except Exception as e:
    import traceback
    print(f"\n❌ Fatal Error: {e}")
    traceback.print_exc()
    exit(1)

finally:
    driver.quit()
    print("🔒 Browser closed. Goodbye!")
