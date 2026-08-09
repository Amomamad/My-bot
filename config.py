import os
from dotenv import load_dotenv

load_dotenv()

# خواندن اطلاعات از فایل .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

# کیف پول‌ها
TRON_WALLET = os.getenv("TRON_WALLET")
TON_WALLET = os.getenv("TON_WALLET")

# حداقل خریدها
MIN_STARS_BUY = 50
MIN_REACTION_STARS_BUY = 5
NFT_FEE_PERCENT = 5

# قیمت‌ها (به تومان)
DEFAULT_PRICES = {
    "stars_per_unit": 1200,
    "ton_per_unit": 350000,
    "tron_per_unit": 12000,
    "premium_3m": 1200000,
    "premium_6m": 2100000,
    "premium_12m": 3800000,
}
