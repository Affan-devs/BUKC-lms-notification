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
from webdriver_manager.chrome import ChromeDriverManager

# ==================== USER CONFIGURATION ====================
# LMS Credentials
ENROLLMENT = "02-239252-073"
PASSWORD = "$Maffanzubair16"
INSTITUTE = "Karachi Campus"

# Email Configuration (Gmail)
EMAIL_SENDER = "maffanzubair960@gmail.com"  # Your Gmail address
EMAIL_PASSWORD = "uqqw bthk lyxo qlct"   # Gmail App Password (NOT your regular password!)
EMAIL_RECEIVER = "maffanzubair960@gmail.com"  # Where to receive notifications

# Course IDs
COURSE_VALUES = [
    "MTQ3Nzgx", "MTQ3Nzgz", "MTQ3Nzg1", "MTQ3Nzg3", "MTQ3Nzkx", 
    "MTQ3Nzkz", "MTQ3Nzk1", "MTQ3Nzk3", "MTQ3Nzk5"
]

# File Configuration
CSV_FILE = 'assignments_report.csv'

# ==================== HELPER FUNCTIONS ====================

def load_existing_assignments():
    """Load existing assignments from CSV to avoid duplicates"""
    existing = set()
    
    if not os.path.exists(CSV_FILE):
        print(" No existing CSV file found. Will create new one.")
        return existing
    
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Create unique identifier: Course + Title + Deadline
                identifier = f"{row['Course']}|{row['Title']}|{row['Deadline']}"
                existing.add(identifier)
        
        print(f" Loaded {len(existing)} existing assignments from CSV")
    except Exception as e:
        print(f"  Error reading CSV: {e}")
    
    return existing


def save_assignments_to_csv(all_assignments):
    """Save all assignments to CSV file"""
    keys = ["Course", "Title", "Deadline", "Date_Added"]
    
    try:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_assignments)
        
        print(f" Saved {len(all_assignments)} assignments to {CSV_FILE}")
        return True
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        return False


def send_email_notification(new_assignments):
    """Send email notification for new assignments"""
    if not new_assignments:
        print(" No new assignments to notify about.")
        return
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f" {len(new_assignments)} New Assignment(s) on LMS!"
        
        # Create HTML email body
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
                <h1> New Assignments Detected!</h1>
            </div>
            <div class="content">
                <p>You have <strong>{len(new_assignments)}</strong> new assignment(s) on https://cms.bahria.edu.pk/Logins/Student/Login.aspx:</p>
        """
        
        for assignment in new_assignments:
            html_body += f"""
                <div class="assignment">
                    <div class="course"> {assignment['Course']}</div>
                    <div class="title"> {assignment['Title']} </div>
                    <div class="deadline"> Deadline: {assignment['Deadline']}</div>
                </div>
            """
        
        html_body += f"""
            </div>
            <div class="footer">
                <p>This notification was sent on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
                <p>Check your LMS dashboard for more details</p>
            </div>
        </body>
        </html>
        """
        
        # Attach HTML body
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f" Email notification sent successfully to {EMAIL_RECEIVER}")
        print(f"   Notified about {len(new_assignments)} new assignment(s)")
        
    except smtplib.SMTPAuthenticationError:
        print(" Email authentication failed! Please check:")
        print("   1. You're using an App Password (not your regular Gmail password)")
        print("   2. 2-Factor Authentication is enabled on your Gmail account")
        print("   3. Generate App Password at: https://myaccount.google.com/apppasswords")
    except Exception as e:
        print(f" Error sending email: {e}")


# ==================== MAIN SCRAPING LOGIC ====================

# Setup Chrome
chrome_options = Options()
chrome_options.add_argument("start-maximized")
# chrome_options.add_argument("--headless=new")  # Enable for background execution

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

wait = WebDriverWait(driver, 20)

try:
    print("\n" + "="*50)
    print(" Starting LMS Assignment Checker")
    print("="*50 + "\n")
    
    # Load existing assignments from CSV
    existing_assignments = load_existing_assignments()
    
    # ================= LOGIN CMS =================
    print(" Logging into CMS...")
    driver.get("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")
    
    wait.until(EC.presence_of_element_located((By.ID, "BodyPH_tbEnrollment")))
    
    driver.find_element(By.ID, "BodyPH_tbEnrollment").send_keys(ENROLLMENT)
    driver.find_element(By.ID, "BodyPH_tbPassword").send_keys(PASSWORD)
    
    institute_dropdown = Select(driver.find_element(By.ID, "BodyPH_ddlInstituteID"))
    institute_dropdown.select_by_visible_text(INSTITUTE)
    
    driver.find_element(By.ID, "BodyPH_btnLogin").click()
    print(" Logged into CMS successfully\n")
    
    # ================= CLICK GO TO LMS =================
    print(" Opening LMS...")
    go_to_lms = wait.until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Go To LMS"))
    )
    go_to_lms.click()
    
    # Switch to new tab
    driver.switch_to.window(driver.window_handles[1])
    wait.until(EC.url_contains("lms.bahria.edu.pk"))
    print(" LMS opened successfully\n")
    
    # ================= CLICK ASSIGNMENTS =================
    print(" Navigating to Assignments page...")
    assignments_link = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//a[@href='Assignments.php']"))
    )
    assignments_link.click()
    
    wait.until(EC.presence_of_element_located((By.ID, "courseId")))
    print(" Assignments page loaded\n")
    
    # ================= SCRAPE ASSIGNMENTS =================
    all_assignments = []
    new_assignments = []
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("="*50)
    print(" Scanning courses for assignments...")
    print("="*50 + "\n")
    
    for idx, val in enumerate(COURSE_VALUES, 1):
        print(f" [{idx}/{len(COURSE_VALUES)}] Checking Course ID: {val}")
        
        try:
            # Re-find dropdown to avoid stale element errors
            dropdown_elem = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "courseId"))
            )
            course_select = Select(dropdown_elem)
            
            # Get course name
            option_element = dropdown_elem.find_element(By.XPATH, f"//option[@value='{val}']")
            course_name = option_element.text.strip()
            
            # Select course
            course_select.select_by_value(val)
            print(f"     Course: {course_name}")
            
            # Wait for table to load
            time.sleep(3)
            
            tbody = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table.table-hover tbody"))
            )
            
            table_text = tbody.text.strip()
            if "No assignment uploaded yet" in table_text or not table_text:
                print(f"      No assignments found\n")
                continue
            
            # Extract rows
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
                
                # Create unique identifier
                identifier = f"{course_name}|{title}|{deadline}"
                
                # Create assignment object
                assignment = {
                    "Course": course_name,
                    "Title": title,
                    "Deadline": deadline,
                    "Date_Added": current_date
                }
                
                # Add to all assignments list
                all_assignments.append(assignment)
                course_assignment_count += 1
                
                # Check if this is a NEW assignment
                if identifier not in existing_assignments:
                    new_assignments.append(assignment)
                    print(f"     NEW: {title} (Deadline: {deadline})")
                else:
                    print(f"    ✓ Already tracked: {title}")
            
            print(f"    Found {course_assignment_count} assignment(s)\n")
            
        except Exception as e:
            print(f"     Error processing course: {e}\n")
    
    # ================= SAVE & NOTIFY =================
    print("="*50)
    print(" Summary")
    print("="*50)
    print(f"Total assignments found: {len(all_assignments)}")
    print(f"New assignments detected: {len(new_assignments)}")
    print(f"Previously tracked: {len(all_assignments) - len(new_assignments)}")
    print("="*50 + "\n")
    
    # Save to CSV (overwrites with complete list)
    if save_assignments_to_csv(all_assignments):
        print(" CSV file updated successfully\n")
    
    # Send email notification for new assignments only
    if new_assignments:
        print("="*50)
        print(" Sending Email Notification")
        print("="*50)
        send_email_notification(new_assignments)
    else:
        print("  No new assignments to notify about. All assignments are up to date!")
    
    print("\n" + "="*50)
    print(" LMS Check Complete!")
    print("="*50 + "\n")

except Exception as e:
    import traceback
    print(f"\n Fatal Error: {e}")
    traceback.print_exc()

finally:
    driver.quit()
    print(" Browser closed. Goodbye!")