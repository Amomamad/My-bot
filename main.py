import logging
import random
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
import database as db
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))


(
    WAIT_SUPPORT, WAIT_CHARGE_AMOUNT, WAIT_RECEIPT, WAIT_TARGET_USER, WAIT_STARS_REACTION,
    WAIT_STARS_DIRECT, WAIT_NFT_LINK, WAIT_DISCOUNT_CODE, WAIT_REDEEM_CODE,
    ADMIN_CHARGE_ID, ADMIN_CHARGE_AMOUNT, ADMIN_BLOCK_ID, ADMIN_BROADCAST,
    ADMIN_SET_PRICE_VAL, ADMIN_SET_TEXT_VAL, ADMIN_SET_NFT_PRICE,
    ADMIN_ADD_PROD_CAT, ADMIN_ADD_PROD_TITLE, ADMIN_ADD_PROD_PRICE,
    ADMIN_ADD_GIFT_CODE, ADMIN_ADD_GIFT_VAL
) = range(21)

CANCEL_KEYWORD = "🔙 بازگشت به منوی اصلی"

def get_main_keyboard(user_id):
    kb = [
        ["🛍 خرید محصول", "💰 کیف پول"],
        ["👤 حساب کاربری", "👥 زیر مجموعه گیری"],
        ["🎁 گردونه شانس", "🎟 فعال‌سازی کد هدیه"],
        ["📦 سفارش‌های من", "💬 پشتیبانی"]
    ]
    if user_id == ADMIN_ID:
        kb.append(["⚙️ پنل مدیریت"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def cancel_kb():
    return ReplyKeyboardMarkup([[CANCEL_KEYWORD]], resize_keyboard=True)

async def check_blocked(update: Update) -> bool:
    user_obj = update.effective_user
    if not user_obj:
        return False
    user = db.get_user(user_obj.id)
    if user and user['is_blocked']:
        if update.message:
            await update.message.reply_text("❌ **حساب کاربری شما مسدود می‌باشد.**", parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer("❌ حساب کاربری شما مسدود است.", show_alert=True)
        return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref_id = int(args[0]) if args and args[0].isdigit() and int(args[0]) != user.id else None
    
    db.add_or_update_user(user.id, user.username, user.full_name, ref_id)
    if await check_blocked(update): return
    
    txt = (
        f"👋 **سلام {user.first_name} عزیز!**\n\n"
        "✨ به فروشگاه بزرگ خدمات تلگرام و کریپتو خوش آمدید.\n"
        "برای شروع خرید یا استفاده از امکانات ربات، از منوی زیر استفاده کنید:"
    )
    if update.message:
        await update.message.reply_text(txt, reply_markup=get_main_keyboard(user.id), parse_mode="Markdown")
    return ConversationHandler.END

async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("🔄 به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard(update.effective_user.id))
    return ConversationHandler.END

async def show_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    user = db.get_user(update.effective_user.id)
    refs = db.get_referral_count(user['user_id'])
    orders = db.get_user_orders(user['user_id'])
    
    msg = (
        f"👤 **حساب کاربری شما**\n\n"
        f"🆔 **شناسه:** `{user['user_id']}`\n"
        f"👤 **نام:** {user['full_name']}\n"
        f"💰 **موجودی کیف پول:** {user['balance']:,} تومان\n"
        f"👥 **تعداد زیرمجموعه‌ها:** {refs} نفر\n"
        f"📦 **سفارشات ثبت‌شده:** {len(orders)} عدد"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    user_id = update.effective_user.id
    ref_link = f"https://t.me/premium_grams_bot?start={user_id}"
    refs = db.get_referral_count(user_id)
    
    msg = (
        f"👥 **سیستم درآمدزایی و دعوت دوستان**\n\n"
        f"با دعوت هر یک از دوستان خود به ربات، اعتبار رایگان کسب کنید!\n"
        f"🔗 **لینک اختصاصی شما:**\n`{ref_link}`\n\n"
        f"📊 **تعداد افراد دعوت‌شده:** {refs} نفر"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def wheel_of_fortune(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    user = db.get_user(update.effective_user.id)
    
    if user['last_wheel_claim']:
        try:
            last_time = datetime.strptime(user['last_wheel_claim'], '%Y-%m-%d %H:%M:%S')
            if datetime.now() - last_time < timedelta(hours=24):
                rem = timedelta(hours=24) - (datetime.now() - last_time)
                hours, remainder = divmod(rem.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await update.message.reply_text(f"⏳ **شما امروز گردونه را چرخانده‌اید!**\nزمان باقی‌مانده تا شانس بعدی: {hours} ساعت و {minutes} دقیقه")
                return
        except Exception:
            pass

    reward = random.choice([2000, 5000, 10000, 15000, 20000])
    db.update_balance(user['user_id'], reward)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_wheel_claim = ? WHERE user_id = ?", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user['user_id']))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"🎉 **تبریک! گردونه شانس چرخید و مبلغ {reward:,} تومان به کیف پول شما اضافه شد!**", parse_mode="Markdown")

async def redeem_code_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    await update.message.reply_text("🎟 **لطفاً کد هدیه خود را وارد کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return WAIT_REDEEM_CODE

async def process_redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code_text = update.message.text.strip()
    code_info = db.get_discount_code(code_text)
    
    if code_info and code_info['code_type'] == 'GIFT_BALANCE':
        amt = code_info['amount_or_percent']
        db.update_balance(update.effective_user.id, amt)
        db.disable_discount_code(code_text)
        await update.message.reply_text(f"🎉 **کد هدیه با موفقیت فعال شد!**\nمبلغ {amt:,} تومان به کیف پول اضافه شد.", reply_markup=get_main_keyboard(update.effective_user.id), parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ کد هدیه نامعتبر است یا قبلاً استفاده شده.", reply_markup=get_main_keyboard(update.effective_user.id))
    return ConversationHandler.END

async def show_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    user = db.get_user(update.effective_user.id)
    card = db.get_setting("card_number") or "ثبت نشده"
    tron = db.get_setting("tron_wallet") or "ثبت نشده"
    ton = db.get_setting("ton_wallet") or "ثبت نشده"
    
    msg = (
        f"💰 **کیف پول و شارژ حساب**\n\n"
        f"💵 **موجودی شما:** {user['balance']:,} تومان\n\n"
        f"💳 **کارت به کارت (ریالی):**\n`{card}`\n\n"
        f"🔴 **ترون (TRX - TRC20):**\n`{tron}`\n\n"
        f"💎 **تون کوین (TON):**\n`{ton}`\n\n"
        "جهت شارژ حساب، ابتدا روی دکمه زیر کلیک کنید:"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➕ ورود مبلغ و ارسال فیش واریزی", callback_data="start_charge")]])
    await update.message.reply_text(msg, reply_markup=kb, parse_mode="Markdown")

async def charge_start_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("💵 **لطفاً مبلغ واریزی خود را به تومان وارد کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return WAIT_CHARGE_AMOUNT

async def process_charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ لطفاً مبلغ را به‌صورت عدد وارد کنید:")
        return WAIT_CHARGE_AMOUNT
    
    context.user_data['requested_charge'] = int(update.message.text)
    await update.message.reply_text("📸 **اکنون تصویر، فایل یا رسید واریزی خود را ارسال کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return WAIT_RECEIPT

async def process_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amt = context.user_data.get('requested_charge', 0)
    
    caption = (
        f"📥 **رسید واریزی جدید**\n\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 آیدی عددی: `{user.id}`\n"
        f"💰 مبلغ درخواستی: **{amt:,} تومان**"
    )
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⚡️ تایید و شارژ مستقیم", callback_data=f"admcharge_{user.id}_{amt}")]])
    
    try:
        if update.message.photo:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=kb, parse_mode="Markdown")
        elif update.message.document:
            await context.bot.send_document(chat_id=ADMIN_ID, document=update.message.document.file_id, caption=caption, reply_markup=kb, parse_mode="Markdown")
        else:
            txt_content = update.message.text or "بدون متن توضیحی"
            await context.bot.send_message(chat_id=ADMIN_ID, text=caption + f"\n\n💬 **متن/پیام ارسالی:**\n{txt_content}", reply_markup=kb, parse_mode="Markdown")
        
        await update.message.reply_text("✅ **رسید واریزی شما با موفقیت برای مدیریت ارسال شد.**\nپس از تایید، موجودی شما به‌صورت خودکار شارژ خواهد شد.", reply_markup=get_main_keyboard(user.id), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending receipt to admin {ADMIN_ID}: {e}")
        await update.message.reply_text("❌ خطا در ارسال رسید به ادمین. لطفاً مطمئن شوید که ربات را در چت شخصی خود استارت کرده‌اید.", reply_markup=get_main_keyboard(user.id))
        
    return ConversationHandler.END

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ تلگرام پرمیوم", callback_data="cat_⭐ تلگرام پرمیوم"), InlineKeyboardButton("🌟 تلگرام استارز", callback_data="cat_🌟 تلگرام استارز")],
        [InlineKeyboardButton("🔥 ریکشن استارز", callback_data="cat_🔥 ریکشن استارز"), InlineKeyboardButton("🖼️ گیفت NFT", callback_data="cat_🖼️ گیفت NFT")],
        [InlineKeyboardButton("💎 ارز تون (TON)", callback_data="cat_💎 ارز تون (TON)"), InlineKeyboardButton("🔴 ارز ترون (TRX)", callback_data="cat_🔴 ارز ترون (TRX)")],
        [InlineKeyboardButton("🎁 گیفت‌های تلگرام", callback_data="cat_🎁 گیفت‌های تلگرام")]
    ])
    await update.message.reply_text("🛍 **لطفاً دسته‌بندی محصول مورد نظر را انتخاب کنید:**", reply_markup=kb, parse_mode="Markdown")

async def handle_category_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.replace("cat_", "")
    context.user_data['selected_category'] = cat
    
    if cat in ["⭐ تلگرام پرمیوم", "🌟 تلگرام استارز", "🎁 گیفت‌های تلگرام"]:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 خرید برای خودم", callback_data="target_self")],
            [InlineKeyboardButton("🎁 هدیه به دیگری", callback_data="target_other")]
        ])
        await query.message.reply_text(f"🛍 **بخش انتخابی:** {cat}\n\nمشخص کنید این محصول برای چه کسی فعال شود:", reply_markup=kb, parse_mode="Markdown")
    else:
        context.user_data['target_type'] = "خودم"
        context.user_data['target_input'] = str(query.from_user.id)
        await show_product_options(query.message, context, cat)

async def handle_target_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    cat = context.user_data.get('selected_category')
    
    if choice == "target_self":
        context.user_data['target_type'] = "خودم"
        context.user_data['target_input'] = str(query.from_user.id)
        await show_product_options(query.message, context, cat)
    else:
        context.user_data['target_type'] = "دیگری"
        await query.message.reply_text("✏️ **آیدی عددی یا یوزرنیم (با @) گیرنده را وارد کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
        return WAIT_TARGET_USER

async def process_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target_input'] = update.message.text
    cat = context.user_data.get('selected_category')
    await show_product_options(update.message, context, cat)
    return ConversationHandler.END

async def show_product_options(message_obj, context, category):
    if category == "⭐ تلگرام پرمیوم":
        desc = db.get_setting("text_prem_desc") or "خرید اشتراک تلگرام پرمیوم با بهترین قیمت."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐️ ۳ ماهه (۳۵۰,۰۰۰ تومان)", callback_data="buy_prod_350000_پرمیوم 3 ماهه")],
            [InlineKeyboardButton("⭐️ ۶ ماهه (۶۵۰,۰۰۰ تومان)", callback_data="buy_prod_650000_پرمیوم 6 ماهه")],
            [InlineKeyboardButton("⭐️ ۱۲ ماهه (۱,۲۰۰,۰۰۰ تومان)", callback_data="buy_prod_1200000_پرمیوم 12 ماهه")]
        ])
        await message_obj.reply_text(f"{desc}\n\n👇 **انتخاب پلن:**", reply_markup=kb, parse_mode="Markdown")

    elif category == "🌟 تلگرام استارز":
        desc = db.get_setting("text_stars_desc") or "خرید تلگرام استارز فوری."
        unit_str = db.get_setting("stars_per_unit")
        unit = int(unit_str) if unit_str and unit_str.isdigit() else 1000
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✨ ۵۰ استارز ({unit*50:,} تومان)", callback_data=f"buy_prod_{unit*50}_50 استارز")],
            [InlineKeyboardButton(f"✨ ۱۰۰ استارز ({unit*100:,} تومان)", callback_data=f"buy_prod_{unit*100}_100 استارز")],
            [InlineKeyboardButton("✏️ ورود تعداد دلخواه (حداقل ۵۰)", callback_data="buy_stars_custom")]
        ])
        await message_obj.reply_text(f"{desc}\n\n👇 **انتخاب بسته:**", reply_markup=kb, parse_mode="Markdown")

    elif category == "🔥 ریکشن استارز":
        await message_obj.reply_text("🔥 **ریکشن استارز (حداقل ۵ عدد):**\nلطفاً لینک پست کانال مورد نظر را ارسال کنید:", reply_markup=cancel_kb(), parse_mode="Markdown")
        return WAIT_STARS_REACTION

    elif category == "🖼️ گیفت NFT":
        await message_obj.reply_text("🖼️ **گیفت NFT تلگرام:**\nلطفاً لینک گیفت مورد نظر را بفرستید تا برای ادمین ارسال و قیمت‌گذاری گردد:", reply_markup=cancel_kb(), parse_mode="Markdown")
        return WAIT_NFT_LINK

    elif category == "💎 ارز تون (TON)":
        desc = db.get_setting("text_ton_desc") or "خرید ارز دیجیتال TON."
        p_str = db.get_setting("ton_price_toman")
        p = int(p_str) if p_str and p_str.isdigit() else 350000
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💎 ۱ TON ({p:,} تومان)", callback_data=f"buy_prod_{p}_1 TON")],
            [InlineKeyboardButton(f"💎 ۵ TON ({p*5:,} تومان)", callback_data=f"buy_prod_{p*5}_5 TON")]
        ])
        await message_obj.reply_text(f"{desc}\n\n👇 **انتخاب مقدار:**", reply_markup=kb, parse_mode="Markdown")

    elif category == "🔴 ارز ترون (TRX)":
        desc = db.get_setting("text_trx_desc") or "خرید ارز دیجیتال TRX."
        p_str = db.get_setting("trx_price_toman")
        p = int(p_str) if p_str and p_str.isdigit() else 7000
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🔴 ۱۰ TRX ({p*10:,} تومان)", callback_data=f"buy_prod_{p*10}_10 TRX")],
            [InlineKeyboardButton(f"🔴 ۵۰ TRX ({p*50:,} تومان)", callback_data=f"buy_prod_{p*50}_50 TRX")]
        ])
        await message_obj.reply_text(f"{desc}\n\n👇 **انتخاب مقدار:**", reply_markup=kb, parse_mode="Markdown")

    elif category == "🎁 گیفت‌های تلگرام":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🧸 گیفت تدی (۱۵۰,۰۰۰ تومان)", callback_data="buy_prod_150000_گیفت تدی")],
            [InlineKeyboardButton("🎂 گیفت کیک تولد (۲۰۰,۰۰۰ تومان)", callback_data="buy_prod_200000_گیفت کیک تولد")],
            [InlineKeyboardButton("❤️ گیفت قلب (۱۰۰,۰۰۰ تومان)", callback_data="buy_prod_100000_گیفت قلب")],
            [InlineKeyboardButton("🌹 گیفت گل (۱۲۰,۰۰۰ تومان)", callback_data="buy_prod_120000_گیفت گل")]
        ])
        await message_obj.reply_text("🎁 **لطفاً گیفت تلگرامی مورد نظر خود را انتخاب کنید:**", reply_markup=kb, parse_mode="Markdown")

async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    
    if len(data) > 2 and data[1] == "stars" and data[2] == "custom":
        await query.message.reply_text("✏️ **تعداد استارز مورد نظر را وارد کنید (حداقل ۵۰):**", reply_markup=cancel_kb(), parse_mode="Markdown")
        return WAIT_STARS_DIRECT

    try:
        price = int(data[2])
        p_name = "_".join(data[3:])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ خطایی در پردازش اطلاعات محصول رخ داد.")
        return

    context.user_data['checkout_price'] = price
    context.user_data['checkout_pname'] = p_name
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟 کد تخفیف دارم", callback_data="apply_discount")],
        [InlineKeyboardButton("✅ پرداخت و ثبت نهایی سفارش", callback_data="confirm_final_checkout")]
    ])
    
    await query.message.reply_text(f"🛍 **پیش‌فاکتور خرید:**\n📌 محصول: **{p_name}**\n💰 قیمت: **{price:,} تومان**", reply_markup=kb, parse_mode="Markdown")

async def process_stars_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    unit_str = db.get_setting("stars_per_unit")
    unit = int(unit_str) if unit_str and unit_str.isdigit() else 1000
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ لطفاً عدد معتبر وارد کنید:")
        return WAIT_STARS_DIRECT
        
    cnt = int(update.message.text)
    if cnt < 50:
        await update.message.reply_text("⚠️ حداقل سفارش ۵۰ عدد می‌باشد. عدد معتبر وارد کنید:")
        return WAIT_STARS_DIRECT
    price = cnt * unit
    context.user_data['checkout_price'] = price
    context.user_data['checkout_pname'] = f"{cnt} استارز مستقیم"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ پرداخت و ثبت نهایی", callback_data="confirm_final_checkout")]])
    await update.message.reply_text(f"✨ **قیمت {cnt} استارز:** {price:,} تومان", reply_markup=kb, parse_mode="Markdown")
    return ConversationHandler.END

async def process_stars_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    unit_str = db.get_setting("stars_per_unit")
    unit = int(unit_str) if unit_str and unit_str.isdigit() else 1000
    price = 5 * unit
    context.user_data['checkout_price'] = price
    context.user_data['checkout_pname'] = f"۵ ریکشن استارز (پست: {link})"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ پرداخت و ثبت نهایی", callback_data="confirm_final_checkout")]])
    await update.message.reply_text("🔥 **سفارش ریکشن استارز آماده ثبت است:**", reply_markup=kb, parse_mode="Markdown")
    return ConversationHandler.END

async def process_nft_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    user = update.effective_user
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💰 قیمت‌گذاری گیفت NFT", callback_data=f"pricenft_{user.id}")]])
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🖼️ **درخواست قیمت‌گذاری گیفت NFT**\n👤 کاربر: {user.full_name} (`{user.id}`)\n🔗 لینک: {link}",
            reply_markup=kb, parse_mode="Markdown"
        )
        await update.message.reply_text("✅ لینک گیفت شما با موفقیت برای مدیریت ارسال شد.\n⏳ پس از بررسی، قیمت نهایی برای شما ارسال می‌گردد.", reply_markup=get_main_keyboard(user.id), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error forwarding NFT link to admin {ADMIN_ID}: {e}")
        await update.message.reply_text("❌ خطا در ارسال لینک به مدیریت. لطفاً مطمئن شوید که ربات را استارت کرده‌اید.", reply_markup=get_main_keyboard(user.id), parse_mode="Markdown")
        
    return ConversationHandler.END

async def admin_price_nft_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        target_uid = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ شناسه کاربر نامعتبر است.")
        return

    context.user_data['nft_target_user'] = target_uid
    await query.message.reply_text(f"💰 **قیمت پایه گیفت را برای کاربر `{target_uid}` به تومان وارد کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return ADMIN_SET_NFT_PRICE

async def admin_price_nft_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ لطفاً مبلغ را به‌صورت عدد وارد کنید:")
        return ADMIN_SET_NFT_PRICE
        
    base_p = int(update.message.text)
    fee = int(base_p * 0.05)
    total = base_p + fee
    uid = context.user_data.get('nft_target_user')
    
    if not uid:
        await update.message.reply_text("❌ کاربر هدف یافت نشد.", reply_markup=get_main_keyboard(ADMIN_ID))
        return ConversationHandler.END

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ پرداخت و ثبت نهایی", callback_data="confirm_final_checkout")]])
    
    context.application.user_data.setdefault(uid, {})['checkout_price'] = total
    context.application.user_data[uid]['checkout_pname'] = "گیفت NFT تلگرام"
    context.application.user_data[uid]['target_type'] = "خودم"
    context.application.user_data[uid]['target_input'] = str(uid)
    
    try:
        await context.bot.send_message(
            chat_id=uid,
            text=f"🖼️ **پیش‌فاکتور گیفت NFT شما:**\nقیمت پایه: {base_p:,} تومان\n+ ۵٪ کارمزد: {fee:,} تومان\n💰 **مجموع:** {total:,} تومان",
            reply_markup=kb, parse_mode="Markdown"
        )
        await update.message.reply_text("✅ پیش‌فاکتور با موفقیت برای کاربر ارسال گردید.", reply_markup=get_main_keyboard(ADMIN_ID), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال پیام به کاربر: {e}", reply_markup=get_main_keyboard(ADMIN_ID), parse_mode="Markdown")
        
    return ConversationHandler.END

async def ask_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("🎟 **کد تخفیف خود را وارد کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return WAIT_DISCOUNT_CODE

async def process_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code_text = update.message.text.strip()
    code_info = db.get_discount_code(code_text)
    
    if code_info and code_info['code_type'] == 'PERCENT':
        pct = code_info['amount_or_percent']
        old_p = context.user_data.get('checkout_price', 0)
        new_p = int(old_p * (100 - pct) / 100)
        context.user_data['checkout_price'] = new_p
        
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ پرداخت و ثبت نهایی", callback_data="confirm_final_checkout")]])
        await update.message.reply_text(f"🎉 **کد تخفیف {pct}٪ اعمال شد!**\n💰 قیمت جدید: **{new_p:,} تومان**", reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ کد تخفیف نامعتبر است.")
    return ConversationHandler.END

async def confirm_final_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    price = context.user_data.get('checkout_price') or context.application.user_data.get(user_id, {}).get('checkout_price', 0)
    p_name = context.user_data.get('checkout_pname') or context.application.user_data.get(user_id, {}).get('checkout_pname', 'محصول')
    t_type = context.user_data.get('target_type') or context.application.user_data.get(user_id, {}).get('target_type', 'خودم')
    t_input = context.user_data.get('target_input') or context.application.user_data.get(user_id, {}).get('target_input', str(user_id))
    
    user = db.get_user(user_id)
    if user['balance'] < price:
        await query.message.reply_text("❌ **موجودی کیف پول شما کافی نیست!**\nلطفاً ابتدا از بخش کیف پول حساب خود را شارژ کنید.", parse_mode="Markdown")
        return
        
    db.update_balance(user_id, -price)
    order_id = db.create_order(user_id, p_name, t_type, t_input, price)
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🚀 **سفارش جدید #{order_id}**\n👤 کاربر: {query.from_user.full_name} (`{user_id}`)\n"
                 f"📦 محصول: **{p_name}**\n🎯 دریافت‌کننده: **{t_type}** ({t_input})\n💰 مبلغ: **{price:,} تومان**",
            parse_mode="Markdown"
        )
    except Exception:
        pass
    
    await query.message.reply_text(
        f"✅ **سفارش شما با موفقیت ثبت شد!**\n\n🔢 شناسه پیگیری: `{order_id}`\n⏳ **وضعیت:** سفارش شما در حال انجام است.",
        reply_markup=get_main_keyboard(user_id), parse_mode="Markdown"
    )

async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    orders = db.get_user_orders(update.effective_user.id)
    if not orders:
        await update.message.reply_text("📦 شما هنوز هیچ سفارشی ثبت نکرده‌اید.")
        return
    msg = "📦 **لیست سفارشات شما:**\n\n"
    for o in orders:
        msg += f"🔹 **کد #{o['id']}** | {o['product_name']}\n💰 {o['price']:,} تومان | وضعیت: {o['status']}\n--------------------\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    await update.message.reply_text("💬 **پیام خود را جهت ارسال به پشتیبانی بنویسید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return WAIT_SUPPORT

async def process_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"💬 **پیام پشتیبانی از** {user.full_name} (`{user.id}`):\n\n{update.message.text}", parse_mode="Markdown")
    except Exception:
        pass
    await update.message.reply_text("✅ پیام شما برای پشتیبانی ارسال شد.", reply_markup=get_main_keyboard(user.id))
    return ConversationHandler.END

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    u, o, s = db.get_stats()
    msg = f"⚙️ **پنل مدیریت ربات**\n\n👥 کل کاربران: {u} نفر\n📦 کل سفارشات: {o} عدد\n💵 فروش کل: {s:,} تومان"
    kb = ReplyKeyboardMarkup([
        ["➕ افزودن محصول جدید", "💵 شارژ حساب کاربر"],
        ["🎟 ساخت کد هدیه", "📢 ارسال پیام همگانی"],
        ["📝 ویرایش متن توضیحات", "🚫 مسدود/آزاد کاربر"],
        [CANCEL_KEYWORD]
    ], resize_keyboard=True)
    await update.message.reply_text(msg, reply_markup=kb, parse_mode="Markdown")

async def admin_add_prod_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("📦 **عنوان محصول جدید را وارد کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return ADMIN_ADD_PROD_TITLE

async def admin_add_prod_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_prod_title'] = update.message.text
    await update.message.reply_text("💰 **قیمت محصول را به تومان وارد کنید:**", parse_mode="Markdown")
    return ADMIN_ADD_PROD_PRICE

async def admin_add_prod_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ لطفاً مبلغ را به‌صورت عدد وارد کنید:")
        return ADMIN_ADD_PROD_PRICE
    title = context.user_data.get('new_prod_title', 'محصول')
    price = int(update.message.text)
    db.add_custom_product("GENERAL", title, price, "")
    await update.message.reply_text(f"✅ محصول **{title}** با قیمت {price:,} تومان به فروشگاه اضافه شد.", reply_markup=get_main_keyboard(ADMIN_ID), parse_mode="Markdown")
    return ConversationHandler.END

async def admin_add_gift_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("🎟 **عبارت کد هدیه را وارد کنید (مثلاً GIFT100):**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return ADMIN_ADD_GIFT_CODE

async def admin_add_gift_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_gift_code'] = update.message.text.strip()
    await update.message.reply_text("💵 **مبلغ اعتبار هدیه را به تومان وارد کنید:**", parse_mode="Markdown")
    return ADMIN_ADD_GIFT_VAL

async def admin_add_gift_val(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ لطفاً مبلغ را به‌صورت عدد وارد کنید:")
        return ADMIN_ADD_GIFT_VAL
    code = context.user_data.get('new_gift_code', 'GIFT')
    amt = int(update.message.text)
    db.add_discount_code(code, amt, 'GIFT_BALANCE')
    await update.message.reply_text(f"✅ کد هدیه `{code}` به ارزش {amt:,} تومان ساخته شد.", reply_markup=get_main_keyboard(ADMIN_ID), parse_mode="Markdown")
    return ConversationHandler.END

async def admin_texts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐️ متن پرمیوم", callback_data="settext_text_prem_desc")],
        [InlineKeyboardButton("🌟 متن استارز", callback_data="settext_text_stars_desc")],
        [InlineKeyboardButton("💎 متن TON", callback_data="settext_text_ton_desc")],
        [InlineKeyboardButton("🔴 متن TRX", callback_data="settext_text_trx_desc")]
    ])
    await update.message.reply_text("📝 **کدام متن توضیحات را می‌خواهید ویرایش کنید؟**", reply_markup=kb, parse_mode="Markdown")

async def admin_set_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.replace("settext_", "")
    context.user_data['edit_text_key'] = key
    await query.message.reply_text("✏️ **متن جدید را بفرستید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return ADMIN_SET_TEXT_VAL

async def admin_set_text_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    key = context.user_data.get('edit_text_key')
    if key:
        db.update_setting(key, txt)
        await update.message.reply_text("✅ متن بروزرسانی شد.", reply_markup=get_main_keyboard(ADMIN_ID))
    else:
        await update.message.reply_text("❌ خطا در ویرایش تنظیمات.")
    return ConversationHandler.END

async def admin_block_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("🔢 **آیدی عددی کاربر را وارد کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return ADMIN_BLOCK_ID

async def admin_block_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ آیدی باید عددی باشد:")
        return ADMIN_BLOCK_ID
    uid = int(update.message.text)
    user = db.get_user(uid)
    if not user:
        await update.message.reply_text("❌ کاربر یافت نشد.", reply_markup=get_main_keyboard(ADMIN_ID))
        return ConversationHandler.END
    new_status = 0 if user['is_blocked'] else 1
    db.set_block_status(uid, new_status)
    status_str = "مسدود" if new_status == 1 else "آزاد"
    await update.message.reply_text(f"✅ وضعیت کاربر `{uid}` به حالت {status_str} درآمد.", reply_markup=get_main_keyboard(ADMIN_ID), parse_mode="Markdown")
    return ConversationHandler.END

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("📢 **پیام همگانی خود را ارسال کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return ADMIN_BROADCAST

async def admin_broadcast_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = db.get_all_user_ids()
    cnt = 0
    for uid in users:
        try:
            await context.bot.copy_message(chat_id=uid, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            cnt += 1
        except Exception: 
            pass
    await update.message.reply_text(f"✅ پیام به {cnt} کاربر ارسال گردید.", reply_markup=get_main_keyboard(ADMIN_ID))
    return ConversationHandler.END

async def admin_charge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    query = update.callback_query
    if query and query.data.startswith("admcharge_"):
        await query.answer()
        parts = query.data.split("_")
        try:
            uid, amt = int(parts[1]), int(parts[2])
            db.update_balance(uid, amt)
            
            # اصلاح خطای ویرایش متن برای پیام‌های حاوی عکس یا کپشن
            new_caption = (query.message.caption or "") + f"\n\n✅ **حساب کاربر به میزان {amt:,} تومان شارژ گردید.**"
            try:
                await query.message.edit_caption(caption=new_caption, parse_mode="Markdown")
            except Exception:
                await query.message.edit_text(f"✅ حساب کاربر `{uid}` به میزان {amt:,} تومان شارژ گردید.", parse_mode="Markdown")
                
            await context.bot.send_message(chat_id=uid, text=f"🎉 **حساب شما به میزان {amt:,} تومان شارژ شد.**", parse_mode="Markdown")
        except Exception as e:
            await query.message.reply_text(f"❌ خطا در شارژ حساب: {e}")
        return ConversationHandler.END
    
    await update.message.reply_text("🔢 **آیدی عددی کاربر را وارد کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return ADMIN_CHARGE_ID


async def admin_charge_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ آیدی باید عدد باشد:")
        return ADMIN_CHARGE_ID
    context.user_data['charge_id'] = int(update.message.text)
    await update.message.reply_text("💵 **مبلغ شارژ (تومان) را وارد کنید:**", reply_markup=cancel_kb(), parse_mode="Markdown")
    return ADMIN_CHARGE_AMOUNT

async def admin_charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ مبلغ باید عدد باشد:")
        return ADMIN_CHARGE_AMOUNT
    uid = context.user_data.get('charge_id')
    amt = int(update.message.text)
    db.update_balance(uid, amt)
    await update.message.reply_text(f"✅ حساب کاربر `{uid}` به میزان {amt:,} تومان شارژ شد.", reply_markup=get_main_keyboard(ADMIN_ID), parse_mode="Markdown")
    try:
        await context.bot.send_message(chat_id=uid, text=f"🎉 **حساب شما به میزان {amt:,} تومان شارژ شد.**", parse_mode="Markdown")
    except Exception:
        pass
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    target_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_target_choice, pattern="^target_")],
        states={WAIT_TARGET_USER: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), process_target_user)]},
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    receipt_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(charge_start_amount, pattern="^start_charge$")],
        states={
            WAIT_CHARGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), process_charge_amount)],
            WAIT_RECEIPT: [MessageHandler(~filters.Regex(CANCEL_KEYWORD), process_receipt)]
        },
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    support_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💬 پشتیبانی$"), support_start)],
        states={WAIT_SUPPORT: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), process_support)]},
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    redeem_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🎟 فعال‌سازی کد هدیه$"), redeem_code_start)],
        states={WAIT_REDEEM_CODE: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), process_redeem_code)]},
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    stars_reaction_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_category_select, pattern="^cat_🔥 ریکشن استارز$")],
        states={WAIT_STARS_REACTION: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), process_stars_reaction)]},
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    stars_direct_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_buy_callback, pattern="^buy_stars_custom$")],
        states={WAIT_STARS_DIRECT: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), process_stars_direct)]},
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    nft_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_category_select, pattern="^cat_🖼️ گیفت NFT$"),
            CallbackQueryHandler(admin_price_nft_start, pattern="^pricenft_")
        ],
        states={
            WAIT_NFT_LINK: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), process_nft_link)],
            ADMIN_SET_NFT_PRICE: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), admin_price_nft_finish)]
        },
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    discount_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_discount_code, pattern="^apply_discount$")],
        states={WAIT_DISCOUNT_CODE: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), process_discount_code)]},
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    admin_add_prod_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ افزودن محصول جدید$"), admin_add_prod_start)],
        states={
            ADMIN_ADD_PROD_TITLE: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), admin_add_prod_title)],
            ADMIN_ADD_PROD_PRICE: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), admin_add_prod_price)]
        },
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    admin_add_gift_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🎟 ساخت کد هدیه$"), admin_add_gift_start)],
        states={
            ADMIN_ADD_GIFT_CODE: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), admin_add_gift_code)],
            ADMIN_ADD_GIFT_VAL: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), admin_add_gift_val)]
        },
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    admin_charge_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^💵 شارژ حساب کاربر$"), admin_charge_start),
            CallbackQueryHandler(admin_charge_start, pattern="^admcharge_")
        ],
        states={
            ADMIN_CHARGE_ID: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), admin_charge_id)],
            ADMIN_CHARGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), admin_charge_amount)]
        },
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    admin_text_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_text_start, pattern="^settext_")],
        states={ADMIN_SET_TEXT_VAL: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), admin_set_text_finish)]},
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    admin_block_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🚫 مسدود/آزاد کاربر$"), admin_block_start)],
        states={ADMIN_BLOCK_ID: [MessageHandler(filters.TEXT & ~filters.Regex(CANCEL_KEYWORD), admin_block_finish)]},
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    admin_broad_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📢 ارسال پیام همگانی$"), admin_broadcast_start)],
        states={ADMIN_BROADCAST: [MessageHandler(~filters.Regex(CANCEL_KEYWORD), admin_broadcast_finish)]},
        fallbacks=[MessageHandler(filters.Regex(CANCEL_KEYWORD), cancel_action)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(target_conv)
    app.add_handler(receipt_conv)
    app.add_handler(support_conv)
    app.add_handler(redeem_conv)
    app.add_handler(stars_reaction_conv)
    app.add_handler(stars_direct_conv)
    app.add_handler(nft_conv)
    app.add_handler(discount_conv)
    app.add_handler(admin_add_prod_conv)
    app.add_handler(admin_add_gift_conv)
    app.add_handler(admin_charge_conv)
    app.add_handler(admin_text_conv)
    app.add_handler(admin_block_conv)
    app.add_handler(admin_broad_conv)

    app.add_handler(MessageHandler(filters.Regex("^👤 حساب کاربری$"), show_account))
    app.add_handler(MessageHandler(filters.Regex("^👥 زیر مجموعه گیری$"), show_referral))
    app.add_handler(MessageHandler(filters.Regex("^💰 کیف پول$"), show_wallet))
    app.add_handler(MessageHandler(filters.Regex("^🛍 خرید محصول$"), shop_menu))
    app.add_handler(MessageHandler(filters.Regex("^🎁 گردونه شانس$"), wheel_of_fortune))
    app.add_handler(MessageHandler(filters.Regex("^📦 سفارش‌های من$"), show_my_orders))
    app.add_handler(MessageHandler(filters.Regex("^⚙️ پنل مدیریت$"), admin_panel))
    app.add_handler(MessageHandler(filters.Regex("^📝 ویرایش متن توضیحات$"), admin_texts_menu))
    app.add_handler(MessageHandler(filters.Regex(f"^{CANCEL_KEYWORD}$"), start))

    app.add_handler(CallbackQueryHandler(handle_category_select, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(handle_buy_callback, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(confirm_final_checkout, pattern="^confirm_final_checkout$"))

    app.add_error_handler(error_handler)

    print("🤖 Bot fully fixed and running successfully...")
    app.run_polling()

if __name__ == "__main__":
    main()
