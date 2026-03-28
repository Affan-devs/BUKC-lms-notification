import time
import csv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# ==================== USER CONFIGURATION ====================

ENROLLMENT = os.environ.get("ENROLLMENT")
PASSWORD = os.environ.get("PASSWORD")
INSTITUTE = os.environ.get("INSTITUTE")

EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

course_values_str = os.environ.get(
    "COURSE_VALUES",
)
COURSE_VALUES = [val.strip() for val in course_values_str.split(",")]

CSV_FILE = "assignments_report.csv"
DEADLINE_WARNING_HOURS = 18
# ==================== HELPER FUNCTIONS ====================

def load_existing_assignments():
    existing = set()

    if not os.path.exists(CSV_FILE):
        print("No existing CSV found.")
        return existing

    try:
        with open(CSV_FILE, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                identifier = f"{row['Course']}|{row['Title']}|{row['Deadline']}"
                existing.add(identifier)

        print(f"Loaded {len(existing)} existing assignments.")
    except Exception as e:
        print(f"Error reading CSV: {e}")

    return existing


def save_assignments_to_csv(all_assignments):
    keys = ["Course", "Title", "Deadline", "Date_Added"]

    try:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_assignments)

        print(f"Saved {len(all_assignments)} assignments.")
        return True
    except Exception as e:
        print(f"Error saving CSV: {e}")
        return False


def parse_deadline(deadline_str):
    """
    Parse deadline string in format: '15 March 2026-12:00 pm'
    Returns a datetime object or None if parsing fails.
    """
    try:
        normalized = deadline_str.strip().replace("-", " ", 1)
        return datetime.strptime(normalized, "%d %B %Y %I:%M %p")
    except ValueError as e:
        print(f"  Could not parse deadline '{deadline_str}': {e}")
        return None

def check_upcoming_deadlines():
    upcoming = []

    if not os.path.exists(CSV_FILE):
        return upcoming

    now = datetime.now()
    warning_cutoff = now + timedelta(hours=DEADLINE_WARNING_HOURS)

    try:
        with open(CSV_FILE, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                deadline_dt = parse_deadline(row["Deadline"])

                if deadline_dt is None:
                    continue

                if now < deadline_dt <= warning_cutoff:
                    hours_left = (deadline_dt - now).total_seconds() / 3600
                    row["Hours_Left"] = round(hours_left, 1)
                    row["Deadline_DT"] = deadline_dt
                    upcoming.append(row)

    except Exception as e:
        pass

    return upcoming

def send_email_notification(new_assignments):
    if not new_assignments:
        print("No new assignments to notify.")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        msg["Subject"] = f"{len(new_assignments)} New LMS Assignment(s)"

        html_body = f"""
        <html>
        <body>
            <h2>New Assignments Detected</h2>
            <p>You have <strong>{len(new_assignments)}</strong> new assignment(s).</p>
        """

        for assignment in new_assignments:
            html_body += f"""
            <div style="margin-bottom:15px;padding:10px;border:1px solid #ddd;">
                <strong>Course:</strong> {assignment['Course']}<br>
                <strong>Title:</strong> {assignment['Title']}<br>
                <strong>Deadline:</strong> {assignment['Deadline']}
            </div>
            """

        html_body += f"""
            <p>Checked on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        print("Email notification sent successfully.")

    except Exception as e:
        print(f"Email error: {e}")


def send_deadline_warning_email(upcoming_assignments):
    """
    Sends a deadline warning email for assignments due within the warning window.
    """
    if not upcoming_assignments:
        print("No upcoming deadlines to warn about.")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        msg["Subject"] = f" Deadline Alert: {len(upcoming_assignments)}!"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #c0392b;"> Deadline Warning</h2>
            <p>The following <strong>{len(upcoming_assignments)}</strong> assignment(s) are due within the next <strong>18 hours</strong>:</p>
        """

        for assignment in upcoming_assignments:
            hours_left = assignment.get("Hours_Left", "?")

            if isinstance(hours_left, float) and hours_left <= 4:
                border_color ="#e74c3c"   
                urgency_label = f"🔴 Only {hours_left}h left!"
            elif isinstance(hours_left, float) and hours_left <= 6:
                border_color = "#e67e22"  
                urgency_label = f"🟠 {hours_left}h left"
            else:
                border_color = "#f39c12"  
                urgency_label = f"🟡 {hours_left}h left"

            html_body += f"""
            <div style="margin-bottom:15px; padding:12px; border-left:5px solid {border_color}; background:#fff8f8;">
                <strong>Course:</strong> {assignment['Course']}<br>
                <strong>Title:</strong> {assignment['Title']}<br>
                <strong>Deadline:</strong> {assignment['Deadline']}<br>
                <strong>Status:</strong> {urgency_label}
            </div>
            """

        html_body += f"""
            <hr>
            <p style="color: #7f8c8d; font-size: 12px;">
                This alert was generated on {datetime.now().strftime("%d %B %Y at %I:%M %p")}
            </p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"Deadline warning email sent for {len(upcoming_assignments)} assignment(s).")

    except Exception as e:
        print(f"Deadline warning email error: {e}")


# ==================== MAIN SCRIPT ====================

print("\n========== LMS Assignment Checker ==========\n")

# ── STEP 1: Check deadlines from existing CSV before scraping ──
upcoming_deadlines = check_upcoming_deadlines()
if upcoming_deadlines:
    send_deadline_warning_email(upcoming_deadlines)
else:
    print("No assignments due within 24 hours.")

# ── STEP 2: Scrape LMS for new assignments ──
print("\n--- Scraping LMS for new assignments ---\n")

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)

try:
    existing_assignments = load_existing_assignments()

    print("Logging into CMS...")
    driver.get("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")

    wait.until(EC.presence_of_element_located((By.ID, "BodyPH_tbEnrollment")))

    driver.find_element(By.ID, "BodyPH_tbEnrollment").send_keys(ENROLLMENT)
    driver.find_element(By.ID, "BodyPH_tbPassword").send_keys(PASSWORD)

    institute_dropdown = Select(driver.find_element(By.ID, "BodyPH_ddlInstituteID"))
    institute_dropdown.select_by_visible_text(INSTITUTE)

    driver.find_element(By.ID, "BodyPH_btnLogin").click()
    print("CMS login successful.")

    go_to_lms = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Go To LMS")))
    go_to_lms.click()

    driver.switch_to.window(driver.window_handles[1])
    wait.until(EC.url_contains("lms.bahria.edu.pk"))
    print("LMS opened.")

    assignments_link = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//a[@href='Assignments.php']"))
    )
    assignments_link.click()

    wait.until(EC.presence_of_element_located((By.ID, "courseId")))


    all_assignments = []
    new_assignments = []
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for val in COURSE_VALUES:
        print(f"Checking course ID: {val}")

        dropdown_elem = wait.until(
            EC.presence_of_element_located((By.ID, "courseId"))
        )
        course_select = Select(dropdown_elem)

        try:
            option_element = dropdown_elem.find_element(
                By.XPATH, f"//option[@value='{val}']"
            )
        except:
            print("Course not found in dropdown.")
            continue

        course_name = option_element.text.strip()
        course_select.select_by_value(val)

        time.sleep(3)

        tbody = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table.table.table-hover tbody")
            )
        )

        if "No assignment uploaded yet" in tbody.text:
            print("No assignments.")
            continue

        rows = tbody.find_elements(By.TAG_NAME, "tr")

        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if not tds:
                continue

            title = tds[0].text.strip()

            try:
                deadline = row.find_element(
                    By.CSS_SELECTOR, "small.label.label-info"
                ).text.strip()
            except:
                deadline = "Not Found"

            identifier = f"{course_name}|{title}|{deadline}"

            assignment = {
                "Course": course_name,
                "Title": title,
                "Deadline": deadline,
                "Date_Added": current_date,
            }

            all_assignments.append(assignment)

            if identifier not in existing_assignments:
                new_assignments.append(assignment)
                print(f"NEW: {title}")

    print(f"\nTotal found: {len(all_assignments)}")
    print(f"New: {len(new_assignments)}")

    if save_assignments_to_csv(all_assignments):
        print("CSV updated.")

    if new_assignments:
        send_email_notification(new_assignments)
    else:
        print("No new assignments detected.")

except Exception as e:
    import traceback
    print("Fatal Error:")
    traceback.print_exc()

finally:
    driver.quit()
    print("Browser closed.")
