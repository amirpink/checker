import json
from decimal import Decimal
import os
from mnemonic import Mnemonic
from eth_account import Account
import requests
from time import sleep
import threading
from queue import Queue
from retrying import retry
from colorama import Fore, init

# ابتدا رنگ‌ها و تنظیمات colorama را راه‌اندازی می‌کنیم
init(autoreset=True)

# بنر با رنگ صورتی
banner = '''
███╗   ███╗███████╗███╗   ██╗████████╗ █████╗ ██╗  ██╗   ██╗
████╗ ████║██╔════╝████╗  ██║╚══██╔══╝██╔══██╗██║  ╚██╗ ██╔╝
██╔████╔██║█████╗  ██╔██╗ ██║   ██║   ███████║██║   ╚████╔╝ 
██║╚██╔╝██║██╔══╝  ██║╚██╗██║   ██║   ██╔══██║██║    ╚██╔╝  
██║ ╚═╝ ██║███████╗██║ ╚████║   ██║   ██║  ██║███████╗██║   
╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝   
                                                               
'''

# تابعی برای نمایش بنر در بالای صفحه
def display_banner():
    os.system('cls' if os.name == 'nt' else 'clear')  # برای ویندوز و لینوکس/مک
    print(Fore.MAGENTA + banner)  # نمایش بنر با رنگ صورتی

# فایل‌های ذخیره وضعیت
progress_file = "progress.json"
full_wallets_file = "full_wallets.json"
empty_wallets_file = "empty_wallets.json"

# متغیرهای سراسری
wallets_checked = 0
full_wallets = 0
empty_wallets = 0
total_balance_eth = Decimal(0)

# ایجاد یک نمونه از کلاس Mnemonic برای زبان انگلیسی
mnemo = Mnemonic("english")

# API Keys به صورت مستقیم داخل کد وارد شده است
etherscan_api_keys = [
    "I9VUMFHE486HWAQ7XP5UCTNEHZWSH254KS",  # جایگزین با کلید واقعی
    "ID2SDFMC7S8478IMCXNNHHMBVK3SXD9921",  # جایگزین با کلید واقعی
    "7RGNWTKRABJ6JFE11C6SMYV9BYCCCQ6KJ8",  # جایگزین با کلید واقعی
    "9W238C489WXYX4752J2875KM8GHKRZD2AR",  # جایگزین با کلید واقعی
    "KGBNQTK4FSN5DWJWBQMIHMNEP6ZEP8ET7Y",  # جایگزین با کلید واقعی
    "I5TIUVG4VBAA4HE3PXUTQVHEUPV3EPVG36"   # جایگزین با کلید واقعی
]

# اگر هیچ API Key موجود نبود، ارور بده
if not any(etherscan_api_keys):
    raise ValueError("هیچ API Key برای Etherscan در کد یافت نشد!")

# فعال‌سازی ویژگی‌های HD Wallet در eth_account
Account.enable_unaudited_hdwallet_features()

# بررسی موجودی ETH از طریق Etherscan
def check_balance_eth(address, api_key):
    url = f'https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey={api_key}'
    retries = 5
    for i in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # بررسی وضعیت پاسخ
            data = response.json()
            if data.get('status') == '1':
                balance = Decimal(data['result']) / 10**18  # تبدیل از Wei به Ether
                return balance
            else:
                raise ValueError(f"خطا در دریافت موجودی برای {address}: {data.get('message', 'نامشخص')}")
        except requests.exceptions.RequestException as e:
            if i == retries - 1:
                print(f"خطا در بررسی موجودی ETH برای {address}: {e}")
                return Decimal(0)
            sleep(2 ** i)  # Exponential Backoff
        except ValueError as e:
            print(f"ارور در پردازش اطلاعات موجودی برای {address}: {e}")
            return Decimal(0)

# ذخیره وضعیت در فایل JSON
def save_progress():
    global wallets_checked, full_wallets, empty_wallets, total_balance_eth
    progress_data = {
        "wallets_checked": wallets_checked,
        "full_wallets": full_wallets,
        "empty_wallets": empty_wallets,
        "total_balance_eth": float(total_balance_eth)
    }
    with open(progress_file, 'w') as f:
        json.dump(progress_data, f, indent=4)

# بازیابی وضعیت از فایل JSON
def load_progress():
    global wallets_checked, full_wallets, empty_wallets, total_balance_eth
    try:
        with open(progress_file, 'r') as f:
            progress_data = json.load(f)
            wallets_checked = progress_data.get('wallets_checked', 0)
            full_wallets = progress_data.get('full_wallets', 0)
            empty_wallets = progress_data.get('empty_wallets', 0)
            total_balance_eth = Decimal(progress_data.get('total_balance_eth', 0))
    except FileNotFoundError:
        print("فایل پیشرفت پیدا نشد. شروع از ابتدا...")

# ذخیره داده‌های کیف پول در فایل‌های جداگانه
def save_wallet_data(wallet_data, is_full_wallet):
    try:
        if is_full_wallet:
            with open(full_wallets_file, 'a') as f:
                json.dump(wallet_data, f, indent=4)
                f.write('\n')  # برای جدا کردن هر ورودی از دیگری
        else:
            with open(empty_wallets_file, 'a') as f:
                json.dump(wallet_data, f, indent=4)
                f.write('\n')  # برای جدا کردن هر ورودی از دیگری
    except Exception as e:
        print(f"خطا در ذخیره داده‌های کیف پول: {e}")

# پردازش کیف پول‌ها به صورت موازی
def process_wallet(api_key, queue):
    global wallets_checked, full_wallets, empty_wallets, total_balance_eth
    mnemonic = mnemo.generate(strength=128)
    account = Account.from_mnemonic(mnemonic)
    address = account.address

    # بررسی موجودی
    balance_eth = check_balance_eth(address, api_key)
    wallets_checked += 1

    wallet_data = {
        "mnemonic": mnemonic,
        "address": address,
        "balances": {"ETH": str(balance_eth)}
    }

    if balance_eth > 0:
        full_wallets += 1
        total_balance_eth += balance_eth
        save_wallet_data(wallet_data, is_full_wallet=True)
        print(f"[+] کیف پول دارای موجودی پیدا شد: {mnemonic} ({address})")
    else:
        empty_wallets += 1
        save_wallet_data(wallet_data, is_full_wallet=False)
        print(f"[-] کیف پول خالی پیدا شد: {mnemonic} ({address})")

    # ذخیره وضعیت پیشرفت در هر مرحله
    save_progress()

# تابعی برای نمایش وضعیت به روز
def display_status():
    while True:
        # نمایش بنر و وضعیت به روز
        display_banner()
        print(f"مجموع کیف پول‌های بررسی شده: {wallets_checked}")
        print(f"مجموع کیف پول‌های پر: {full_wallets}")
        print(f"مجموع کیف پول‌های خالی: {empty_wallets}")
        print(f"مجموع موجودی اتریوم: {total_balance_eth:.4f} ETH")
        sleep(2)  # مدت زمان برای رفرش کردن صفحه و بنر

# کد اصلی
def main():
    # بارگذاری پیشرفت
    load_progress()

    # ایجاد و شروع حلقه برای نمایش وضعیت به روز
    status_thread = threading.Thread(target=display_status, daemon=True)
    status_thread.start()

    queue = Queue()

    def worker():
        while True:
            for i in range(50):  # تعداد درخواست‌ها
                api_key = etherscan_api_keys[i % len(etherscan_api_keys)]
                process_wallet(api_key, queue)
            sleep(0.1)  # محدود کردن درخواست‌ها به Etherscan

    # استفاده از Threading برای پردازش موازی
    threads = []
    for _ in range(5):  # تعداد نخ‌ها
        thread = threading.Thread(target=worker)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
