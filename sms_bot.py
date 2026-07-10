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
    """মেসেজ থেকে ৪-৮ ডিজিট অথবা ৪-৮ অক্ষরের ইংরেজি টেক্সট OTP খুঁজে বের করার লজিক"""
    # প্রথমে মেসেজের একদম শেষের শব্দটি চেক করবে (যেমন স্ক্রিনশটের mfvhn)
    words = message.strip().split()
    if words:
        last_word = words[-1]
        # শেষের শব্দটি যদি ৪ থেকে ৮ অক্ষরের হয়, তবে সেটাকেই ওটিপি হিসেবে নিবে
        if 4 <= len(last_word) <= 8:
            return last_word
            
    # যদি শেষের শব্দে না পায়, তবে পুরো মেসেজে ৪-৮ অক্ষরের যেকোনো কোড (সংখ্যা বা অক্ষর) খুঁজবে
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
        response = requests.get(f"{API_URL}?token={PANEL_TOKEN}", timeout=10)
        if response.status_code == 200:
            full_data = response.json()
            if full_data.get('status') == 'success':
                sms_list = full_data.get('data', [])
                if isinstance(sms_list, list):
                    for sms in reversed(sms_list):
                        num = str(sms.get('num', 'Unknown')).strip()
                        sms_time = sms.get('dt', '')
                        
                        msg_unique_id = f"{num}_{sms_time}"
                        
                        if msg_unique_id not in processed_sms_ids:
                            msg_content = sms.get('message', 'No message')
                            otp = extract_otp(msg_content)
                            
                            # সার্ভিস নেম এবং নম্বর ফরম্যাট
                            masked_service = "*******"
                            masked_number = format_number(num)
                            
                            # লেআউট ডিজাইন
                            text = (
                                f"🌐 <b>{masked_service}</b>\n"
                                f"📞 {masked_number}\n\n"
                                f"💬 <code>{otp}</code>"
                            )

                            # শুধু ওনার বাটন
                            markup = InlineKeyboardMarkup()
                            markup.row(
                                InlineKeyboardButton("👤 Owner", url="https://t.me/nb269")
                            )

                            try:
                                bot.send_message(CHAT_ID, text, parse_mode='HTML', reply_markup=markup)
                                processed_sms_ids.add(msg_unique_id)
                                save_processed_ids(processed_sms_ids)
                            except Exception as send_error:
                                print(f"Sending Error: {send_error}")
                                            
    except Exception as e:
        print(f"Fetch Error: {e}")

if __name__ == "__main__":
    print("বটটি টেক্সট এবং ডিজিট উভয় প্রকার ওটিপি সাপোর্ট সহ চালু হচ্ছে...")
    while True:
        fetch_and_forward()
        time.sleep(4)
