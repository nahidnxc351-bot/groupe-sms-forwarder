import telebot
import requests
import time
import re
import os
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- আপনার সঠিক তথ্য ---
BOT_TOKEN = '8685475963:AAEHIgmsMgNN3lRVF-0ehLEE4Mwadv6KUDs'
CHAT_ID = '-1003919009698'
PANEL_TOKEN = 'Q1ZXQjRSQn5zVlhDZm2FaEljjnRbi5iHW4J0gX5PhUGDImhFYHiQ'
API_URL = 'http://51.77.216.195/crapi/konek/viewstats'

# ডুপ্লিকেট মেসেজ আইডি সেভ করার ফাইল
PROCESSED_DB = 'group_processed.json'

bot = telebot.TeleBot(BOT_TOKEN)

# --- ডুপ্লিকেট চেক ডাটাবেজ ফাংশন ---
def load_processed_ids():
    if os.path.exists(PROCESSED_DB):
        try:
            with open(PROCESSED_DB, 'r') as f:
                return set(json.load(f))
        except: return set()
    return set()

def save_processed_ids(id_set):
    try:
        to_save = list(id_set)[-200:]
        with open(PROCESSED_DB, 'w') as f:
            json.dump(to_save, f)
    except: pass

processed_sms_ids = load_processed_ids()

def extract_otp(message):
    """মেসেজ থেকে ওটিপি কোড খুঁজে বের করার লজিক"""
    # প্রথমে মেসেজে 'is ' বা 'code ' বা ':' এর পর কোনো ৪-৮ ডিজিটের সংখ্যা আছে কিনা দেখবে
    match = re.search(r'(?:is|code|:|💬)\s*([a-zA-Z0-9]{4,8})\b', message, re.IGNORECASE)
    if match:
        return match.group(1)
        
    # যদি না পায়, তবে শেষের শব্দটি চেক করবে
    words = message.strip().split()
    if words:
        last_word = words[-1].strip('.,!:-')
        if 4 <= len(last_word) <= 8:
            return last_word
            
    # অন্যথায় পুরো টেক্সট থেকে ৪-৮ অক্ষরের যেকোনো কোড নিবে
    otp_match = re.search(r'\b[a-zA-Z0-9]{4,8}\b', message)
    return otp_match.group(0) if otp_match else "No OTP"

def format_number(num):
    """নম্বরের প্রথম ৩ এবং শেষ ৩ ডিজিট রেখে মাঝখানে NB বসানোর লজিক"""
    clean_num = str(num).strip()
    if len(clean_num) >= 6:
        first_three = clean_num[:3]
        last_three = clean_num[-3:]
        return f"{first_three}NB{last_three}"
    return clean_num

def fetch_and_forward():
    global processed_sms_ids
    try:
        # records=10 দিয়ে প্যানেলের শেষ ১০টি এসএমএস রিড করা হচ্ছে
        response = requests.get(f"{API_URL}?token={PANEL_TOKEN}&records=10", timeout=10)
        if response.status_code == 200:
            full_data = response.json()
            if full_data.get('status') == 'success':
                sms_list = full_data.get('data', [])
                if isinstance(sms_list, list):
                    for sms in sms_list:
                        num = str(sms.get('num', 'Unknown')).strip()
                        sms_time = sms.get('dt', '')
                        
                        msg_unique_id = f"{num}_{sms_time}"
                        
                        if msg_unique_id not in processed_sms_ids:
                            msg_content = sms.get('message', 'No message')
                            otp = extract_otp(msg_content)
                            
                            service_name = str(sms.get('service', 'Omnisend')).strip()
                            masked_number = format_number(num)
                            
                            # নতুন লেআউট ডিজাইন (এখানে কমিশন টোটাল বাদ দেওয়া হয়েছে ভাই)
                            text = (
                                f"🎯 <b>SMS RECEIVED IN YOUR NUMBER!</b>\n\n"
                                f"👤 <b>Number:</b> <code>{masked_number}</code>\n"
                                f"🏢 <b>Service:</b> <code>{service_name}</code>\n"
                                f"💬 <b>Message:</b> {msg_content}\n\n"
                                f"🔑 <b>Code:</b> <code>{otp}</code>"
                            )

                            # ওনার বাটন (ক্লিক করলে আপনার আইডিতে চলে যাবে)
                            markup = InlineKeyboardMarkup()
                            markup.row(
                                InlineKeyboardButton("👤 Owner", url="https://t.me/nb269")
                            )

                            try:
                                bot.send_message(CHAT_ID, text, parse_mode='HTML', reply_markup=markup)
                                processed_sms_ids.add(msg_unique_id)
                                save_processed_ids(processed_sms_ids)
                                print(f"Successfully forwarded OTP for {masked_number}")
                                time.sleep(1) # স্প্যাম প্রোটেকশন
                            except Exception as send_error:
                                print(f"Sending Error: {send_error}")
                                            
    except Exception as e:
        print(f"Fetch Error: {e}")

if __name__ == "__main__":
    print("বটটি নতুন ওটিপি ফরম্যাট ও কমিশন রিমুভ সহ চালু হচ্ছে...")
    while True:
        fetch_and_forward()
        time.sleep(4)
