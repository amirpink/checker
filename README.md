
# Ethereum Wallet Checker

این پروژه به‌منظور جستجو و بررسی کیف پول‌های اتریوم با استفاده از **Etherscan API** طراحی شده است. هدف این برنامه بررسی موجودی کیف پول‌های اتریوم ایجاد شده از روی کلمات **mnemonic** است. این برنامه به‌طور خودکار کیف پول‌های اتریوم را بررسی کرده و اطلاعات مربوط به کیف پول‌های با موجودی (پر) و بدون موجودی (خالی) را ذخیره می‌کند.

## توضیحات

### 1. هدف برنامه
برنامه به‌طور اتوماتیک کیف پول‌های اتریوم را با استفاده از کلمات **mnemonic** ایجاد می‌کند و موجودی هر کیف پول را با استفاده از **API Etherscan** بررسی می‌کند. کیف پول‌هایی که دارای موجودی (ETH) هستند در فایل `full_wallets.json` ذخیره می‌شوند و کیف پول‌های بدون موجودی در فایل `empty_wallets.json`.

### 2. ساختار پروژه
- **progress.json**: برای ذخیره وضعیت پیشرفت پردازش.
- **full_wallets.json**: برای ذخیره کیف پول‌های دارای موجودی.
- **empty_wallets.json**: برای ذخیره کیف پول‌های بدون موجودی.

### 3. نحوه عملکرد برنامه
- این برنامه از **mnemonic** برای ایجاد آدرس‌های اتریوم استفاده می‌کند.
- موجودی هر کیف پول با استفاده از **Etherscan API** بررسی می‌شود.
- در صورت داشتن موجودی، کیف پول به‌عنوان "پر" شناسایی شده و در فایل `full_wallets.json` ذخیره می‌شود.
- در صورت نداشتن موجودی، کیف پول به‌عنوان "خالی" شناسایی شده و در فایل `empty_wallets.json` ذخیره می‌شود.
- تمامی مراحل پردازش به‌صورت موازی با استفاده از **Threading** انجام می‌شود تا سرعت پردازش افزایش یابد.
- برای مدیریت خطاها و جلوگیری از ارسال درخواست‌های بیش از حد به API، از ویژگی **Exponential Backoff** استفاده شده است.

### 4. جزئیات کد

#### 4.1 بارگذاری متغیرهای محیطی
در ابتدا، با استفاده از پکیج `dotenv`، متغیرهای محیطی از فایل `.env` بارگذاری می‌شود. این متغیرها شامل کلیدهای API برای دسترسی به **Etherscan API** هستند.

```python
from dotenv import load_dotenv
load_dotenv()
```

#### 4.2 تعریف فایل‌ها برای ذخیره وضعیت
سه فایل اصلی برای ذخیره وضعیت برنامه استفاده می‌شود:
- **progress.json**: برای ذخیره پیشرفت پردازش.
- **full_wallets.json**: برای ذخیره کیف پول‌های با موجودی.
- **empty_wallets.json**: برای ذخیره کیف پول‌های بدون موجودی.

```python
progress_file = "progress.json"
full_wallets_file = "full_wallets.json"
empty_wallets_file = "empty_wallets.json"
```

#### 4.3 پردازش کیف پول‌ها
برای هر کیف پول، ابتدا یک **mnemonic** 12 کلمه‌ای تولید شده و سپس از آن برای ایجاد آدرس اتریوم استفاده می‌شود. موجودی کیف پول با استفاده از API Etherscan بررسی می‌شود.

```python
def process_wallet(api_key, queue):
    global wallets_checked, full_wallets, empty_wallets, total_balance_eth
    mnemonic = mnemo.generate(strength=128)
    account = Account.from_mnemonic(mnemonic)
    address = account.address

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
        print(f"[+] کیف پول دارای موجودی پیدا شد: {mnemonic} ({address})")
        save_wallet_data(wallet_data, is_full_wallet=True)
    else:
        empty_wallets += 1
        print(f"[-] کیف پول خالی پیدا شد: {mnemonic} ({address})")
        save_wallet_data(wallet_data, is_full_wallet=False)

    save_progress()
```

#### 4.4 استفاده از Threading برای پردازش موازی
برای پردازش موازی و افزایش سرعت، از **Threading** استفاده شده است. هر نخ به‌طور موازی کیف پول‌ها را بررسی می‌کند.

```python
def worker():
    while True:
        for i in range(50):  # تعداد درخواست‌ها
            api_key = etherscan_api_keys[i % len(etherscan_api_keys)]
            process_wallet(api_key, queue)
        sleep(0.1)  # محدود کردن درخواست‌ها به Etherscan
```

#### 4.5 ذخیره و بارگذاری وضعیت
برای پیگیری پیشرفت پردازش، وضعیت بررسی کیف پول‌ها، تعداد کیف پول‌های پر و خالی و مجموع موجودی ETH به‌صورت دوره‌ای در فایل `progress.json` ذخیره می‌شود.

```python
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
```

### 5. نصب و راه‌اندازی پروژه

#### 5.1 ایجاد فایل `.env`
برای استفاده از **Etherscan API**، شما باید یک فایل `.env` در ریشه پروژه خود ایجاد کنید و کلیدهای API خود را در آن قرار دهید.

1. در ریشه پروژه یک فایل متنی به نام `.env` بسازید.
2. در این فایل، کلیدهای API را به شکل زیر وارد کنید:

```env
ETHERSCAN_API_KEY_1=your_api_key_1
ETHERSCAN_API_KEY_2=your_api_key_2
ETHERSCAN_API_KEY_3=your_api_key_3
ETHERSCAN_API_KEY_4=your_api_key_4
ETHERSCAN_API_KEY_5=your_api_key_5
ETHERSCAN_API_KEY_6=your_api_key_6
```

برای دریافت این کلیدها، باید در سایت [Etherscan](https://etherscan.io/) ثبت‌نام کنید.

#### 5.2 نصب وابستگی‌ها
تمامی کتابخانه‌های مورد نیاز این پروژه در فایل `requirements.txt` قرار دارند. برای نصب این کتابخانه‌ها، دستور زیر را در خط فرمان اجرا کنید:


1. برای نصب کتابخانه‌ها از دستور زیر استفاده کنید:

```bash
pip install -r requirements.txt
```

این دستور تمامی کتابخانه‌های مورد نیاز را به‌صورت خودکار نصب خواهد کرد.

#### 5.3 اجرای برنامه
برای اجرای برنامه، کافی است دستور زیر را در خط فرمان وارد کنید:

```bash
python wallet_checker.py
```

این دستور برنامه را شروع می‌کند و جستجو برای کیف پول‌های اتریوم را آغاز می‌کند.

### 6. نتیجه‌گیری
این برنامه به‌طور خودکار و موازی به بررسی کیف پول‌های اتریوم پرداخته و آن‌ها را بر اساس موجودی دسته‌بندی می‌کند. کیف پول‌های دارای موجودی در یک فایل و کیف پول‌های بدون موجودی در فایلی دیگر ذخیره می‌شوند. این کد به‌طور مؤثر می‌تواند برای یافتن کیف پول‌های اتریوم با موجودی استفاده شود.
