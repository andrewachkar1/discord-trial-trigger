import threading
import time
import random
import os
from queue import Queue
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from colorama import Fore, Style, init

# ---------- INIT ----------
init(autoreset=True)

# ---------- CONFIG ----------
THREAD_COUNT = int(input("Enter number of threads: "))
os.system("cls")

TOKENS_FILE = "tokens.txt"
PROXIES_FILE = "proxies.txt"  # Optional

FAKE_ADDRESS = {
    "line1": "123 Discord Drive",
    "city": "Coolsville",
    "state": "NY",
    "postalCode": "15098"
}

# ---------- OUTPUT FOLDER ----------
output_folder = f"output/{time.strftime('%Y-%m-%d %H-%M-%S')}"
os.makedirs(output_folder, exist_ok=True)

SUCCESS_FILE = os.path.join(output_folder, "success.txt")
FAILED_FILE = os.path.join(output_folder, "failed.txt")
INVALID_FILE = os.path.join(output_folder, "invalid.txt")

token_queue = Queue()
with open(TOKENS_FILE, "r") as f:
    for line in f:
        token = line.strip()
        if token:
            token_queue.put(token)

proxies = []
if os.path.exists(PROXIES_FILE):
    with open(PROXIES_FILE, "r") as f:
        proxies = [p.strip() for p in f if p.strip()]

lock = threading.Lock()  # For thread-safe file operations

# ---------- HELPER FUNCTIONS ----------
def log(thread_id, msg, color=Fore.WHITE, emoji="ℹ️"):
    print(f"{color}[Thread {thread_id}] {emoji} {msg}{Style.RESET_ALL}")

def human_typing(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))

def switch_to_stripe_field(driver, field_name):
    driver.switch_to.default_content()
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for iframe in iframes:
        driver.switch_to.frame(iframe)
        try:
            field = driver.find_element(By.NAME, field_name)
            return field
        except:
            driver.switch_to.default_content()
    raise Exception(f"Could not find field: {field_name}")

def save_result(token, success=True, valid=True):
    with lock:
        filename = SUCCESS_FILE if success and valid else FAILED_FILE if not success and valid else INVALID_FILE
        with open(filename, "a") as f:
            f.write(token + "\n")
        # Remove token from tokens.txt
        with open(TOKENS_FILE, "r") as f:
            tokens = [t.strip() for t in f if t.strip() and t.strip() != token]
        with open(TOKENS_FILE, "w") as f:
            f.write("\n".join(tokens) + "\n")

# ---------- WORKER FUNCTION ----------
def worker(thread_id):
    while not token_queue.empty():
        token = token_queue.get()
        proxy = random.choice(proxies) if proxies else None
        driver = None
        try:
            # Setup Chrome
            options = Options()
            service = Service(log_path=os.devnull)
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--start-maximized")
            options.add_argument("--log-level=3")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            if proxy:
                options.add_argument(f'--proxy-server={proxy}')
                log(thread_id, f"Using proxy {proxy}", Fore.CYAN, "🌐")

            driver = webdriver.Chrome(service=service, options=options)

            # Open Discord login
            log(thread_id, "Opening Discord login page", Fore.YELLOW, "🌍")
            driver.get("https://discord.com/login")
            time.sleep(random.uniform(2, 5))

            # Inject token
            script = f"""
            let token = "{token}";
            function login(token) {{
                setInterval(() => {{
                    document.body.appendChild(document.createElement('iframe')).contentWindow.localStorage.token = `"${{token}}"`;
                }}, 50);
                setTimeout(() => {{
                    location.reload();
                }}, 2500);
            }}
            login(token);
            """
            driver.execute_script(script)
            log(thread_id, "Injected token into localStorage", Fore.GREEN, "🔑")
            time.sleep(random.uniform(5, 8))

            # Check login status
            if "https://discord.com/channels/@me" in driver.current_url:
                log(thread_id, f"Logged in successfully: {token[:20]}...", Fore.GREEN, "✅")
            else:
                log(thread_id, f"Invalid token: {token[:20]}...", Fore.MAGENTA, "❌")
                save_result(token, success=False, valid=False)
                driver.quit()
                continue

            time.sleep(7.5)            
            
            try:
                close_btn = driver.find_element(By.CSS_SELECTOR, "button.closeButton__1d6c7")
                driver.execute_script("arguments[0].click();", close_btn)
                log(thread_id, "Closed popup window", Fore.MAGENTA, "❌")
            except NoSuchElementException:
                log(thread_id, "No popup to close", Fore.BLUE, "ℹ️")

            # Navigate User Settings > Nitro > Subscribe
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//section//button[@aria-label='User Settings']"))
            ).click()
            log(thread_id, "Opened User Settings", Fore.YELLOW, "⚙️")
            time.sleep(random.uniform(1, 2))

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='tab' and @aria-label='Nitro']"))
            ).click()
            log(thread_id, "Opened Nitro tab", Fore.YELLOW, "💎")
            time.sleep(random.uniform(1, 2))

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Subscribe']]"))
            ).click()
            log(thread_id, "Clicked Subscribe", Fore.CYAN, "🛒")
            time.sleep(random.uniform(1, 2))

            # Payment selection
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".card_ac86f6.tier2MarketingCard__9e160"))
            ).click()
            log(thread_id, "Selected Nitro tier", Fore.CYAN, "💳")
            time.sleep(random.uniform(1, 2))

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'planOptionInterval') and text()='Monthly']"))
            ).click()
            log(thread_id, "Chose Monthly plan", Fore.CYAN, "📆")
            time.sleep(random.uniform(1, 2))

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Select']/ancestor::button"))
            ).click()
            log(thread_id, "Confirmed plan selection", Fore.CYAN, "✅")
            time.sleep(random.uniform(1, 2))

            # Payment method: Card
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Card']/ancestor::button"))
            ).click()
            log(thread_id, "Chosen Card as payment", Fore.CYAN, "💳")
            time.sleep(random.uniform(2, 5))

            driver.quit()
            save_result(token, success=True)
            log(thread_id, f"Finished successfully: {token[:20]}...", Fore.GREEN, "🎉")

        except Exception as e:
            log(thread_id, f"Failed: {token[:20]}... -> {e}", Fore.RED, "❌")
            save_result(token, success=False)
            try:
                driver.quit()
            except:
                pass

# ---------- START THREADS ----------
threads = []
for i in range(THREAD_COUNT):
    t = threading.Thread(target=worker, args=(i+1,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

print(Fore.CYAN + "[LOG] All threads finished. ✅")
