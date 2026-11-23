import time, csv, os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# ==================== CONFIG ====================
ENROLLMENT = os.environ["ENROLLMENT"]
PASSWORD = os.environ["PASSWORD"]
INSTITUTE = os.environ["INSTITUTE"]
EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVER = os.environ["EMAIL_RECEIVER"]

# Optional: comma-separated course NAMES (case-insensitive, partial match ok). Empty = all courses.
COURSE_NAMES = [c.strip().lower() for c in os.environ.get("COURSE_NAMES", "").split(",") if c.strip()]

CSV_FILE = "assignments_report.csv"
KEYS = ["Course", "Title", "Deadline", "Date_Added", "Notified"]
DEADLINE_WARNING_HOURS = 24


# ==================== CSV HELPERS ====================
def load_csv():
    if not os.path.exists(CSV_FILE):
        return {}
    data = {}
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row.setdefault("Notified", "no")
            data[f"{row['Course']}|{row['Title']}|{row['Deadline']}"] = row
    return data


def save_csv(data):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KEYS, extrasaction="ignore")
        w.writeheader()
        w.writerows(data.values())
    print(f"Saved {len(data)} assignments.")


def parse_deadline(s):
    try:
        return datetime.strptime(s.strip().replace("-", " ", 1), "%d %B %Y %I:%M %p")
    except ValueError:
        return None


# ==================== EMAIL ====================
def send_email(subject, html):
    msg = MIMEMultipart("alternative")
    msg["From"], msg["To"], msg["Subject"] = EMAIL_SENDER, EMAIL_RECEIVER, subject
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_SENDER, EMAIL_PASSWORD)
        s.send_message(msg)


def notify_new(items):
    body = f"<h2>New Assignments</h2><p><b>{len(items)}</b> new assignment(s).</p>"
    for a in items:
        body += (f"<div style='margin-bottom:12px;padding:10px;border:1px solid #ddd'>"
                 f"<b>Course:</b> {a['Course']}<br><b>Title:</b> {a['Title']}<br>"
                 f"<b>Deadline:</b> {a['Deadline']}</div>")
    send_email(f"{len(items)} New LMS Assignment(s)", body)
    print("New-assignment email sent.")


def notify_deadlines(items):
    body = (f"<h2 style='color:#c0392b'>Deadline Warning</h2>"
            f"<p>Due within the next <b>{DEADLINE_WARNING_HOURS} hours</b>:</p>")
    for a, hrs in items:
        color = "#e74c3c" if hrs <= 4 else "#e67e22" if hrs <= 8 else "#f39c12"
        body += (f"<div style='margin-bottom:12px;padding:10px;border-left:5px solid {color};background:#fff8f8'>"
                 f"<b>Course:</b> {a['Course']}<br><b>Title:</b> {a['Title']}<br>"
                 f"<b>Deadline:</b> {a['Deadline']}<br><b>Left:</b> {hrs}h</div>")
    send_email(f"Deadline Alert: {len(items)} due soon", body)
    print("Deadline email sent.")


def check_deadlines(data):
    """Send a one-time warning per assignment. Mutates 'Notified' flag."""
    now = datetime.now()
    cutoff = now + timedelta(hours=DEADLINE_WARNING_HOURS)
    due = []
    for row in data.values():
        dt = parse_deadline(row["Deadline"])
        if dt and now < dt <= cutoff and row.get("Notified") != "deadline":
            due.append((row, round((dt - now).total_seconds() / 3600, 1)))
    if due:
        try:
            notify_deadlines(due)
            for row, _ in due:
                row["Notified"] = "deadline"
        except Exception as e:
            print(f"Deadline email error: {e}")
    else:
        print("No new deadline warnings.")


# ==================== SCRAPER HELPERS ====================
def get_course_list(driver, wait):
    """Return [(index, name)] from the dropdown. Values are random, so we ignore them."""
    sel = Select(wait.until(EC.presence_of_element_located((By.ID, "courseId"))))
    courses = []
    for i, opt in enumerate(sel.options):
        if not (opt.get_attribute("value") or "").strip():
            continue  # placeholder "Select Course"
        name = opt.text.strip()
        if COURSE_NAMES and not any(c in name.lower() for c in COURSE_NAMES):
            continue
        courses.append((i, name))
    return courses


def scrape_course(driver, wait, index):
    # Re-find the select every time: the page refreshes after each change
    old_tbody = None
    try:
        old_tbody = driver.find_element(By.CSS_SELECTOR, "table.table.table-hover tbody")
    except Exception:
        pass

    Select(wait.until(EC.presence_of_element_located((By.ID, "courseId")))).select_by_index(index)

    if old_tbody is not None:
        try:
            WebDriverWait(driver, 10).until(EC.staleness_of(old_tbody))
        except Exception:
            time.sleep(3)  # table updated in place (AJAX), fall back to a short wait
    else:
        time.sleep(3)

    tbody = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "table.table.table-hover tbody")))
    if "No assignment uploaded yet" in tbody.text:
        return []

    results = []
    for row in tbody.find_elements(By.TAG_NAME, "tr"):
        tds = row.find_elements(By.TAG_NAME, "td")
        if not tds:
            continue
        title = tds[0].text.strip()
        try:
            deadline = row.find_element(By.CSS_SELECTOR, "small.label.label-info").text.strip()
        except Exception:
            deadline = "Not Found"
        results.append((title, deadline))
    return results


# ==================== MAIN ====================
print("\n===== LMS Assignment Checker =====\n")

data = load_csv()
print(f"Loaded {len(data)} existing assignments.")

# STEP 1: deadline warnings from existing data
check_deadlines(data)
if data:
    save_csv(data)

# STEP 2: scrape
opts = Options()
for a in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
          "--disable-gpu", "--window-size=1920,1080"):
    opts.add_argument(a)
driver = webdriver.Chrome(options=opts)
wait = WebDriverWait(driver, 20)

try:
    driver.get("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")
    wait.until(EC.presence_of_element_located((By.ID, "BodyPH_tbEnrollment")))
    driver.find_element(By.ID, "BodyPH_tbEnrollment").send_keys(ENROLLMENT)
    driver.find_element(By.ID, "BodyPH_tbPassword").send_keys(PASSWORD)
    Select(driver.find_element(By.ID, "BodyPH_ddlInstituteID")).select_by_visible_text(INSTITUTE)
    driver.find_element(By.ID, "BodyPH_btnLogin").click()

    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Go To LMS"))).click()
    wait.until(lambda d: len(d.window_handles) > 1)
    driver.switch_to.window(driver.window_handles[1])
    wait.until(EC.url_contains("lms.bahria.edu.pk"))

    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='Assignments.php']"))).click()
    wait.until(EC.presence_of_element_located((By.ID, "courseId")))

    courses = get_course_list(driver, wait)
    print(f"Courses found: {[n for _, n in courses]}")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_items = []

    for index, name in courses:
        print(f"Checking: {name}")
        try:
            items = scrape_course(driver, wait, index)
        except Exception as e:
            print(f"  Failed ({e}); keeping old data for this course.")
            continue

        for title, deadline in items:
            key = f"{name}|{title}|{deadline}"
            if key not in data:
                row = {"Course": name, "Title": title, "Deadline": deadline,
                       "Date_Added": now_str, "Notified": "no"}
                data[key] = row
                new_items.append(row)
                print(f"  NEW: {title}")

    print(f"New assignments: {len(new_items)}")

    if new_items:
        try:
            notify_new(new_items)
        except Exception as e:
            print(f"Email error: {e}")

    # Catch assignments that are new AND already due soon
    check_deadlines(data)
    save_csv(data)

except Exception:
    import traceback
    traceback.print_exc()
finally:
    driver.quit()
    print("Browser closed.")
