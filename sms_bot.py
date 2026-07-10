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
    """মেসেজ থেকে ১-১০ ডিজিটের সংখ্যা অথবা অক্ষরের ওটিপি বের করার অ্যাডভান্সড লজিক"""
    if not message or message == 'No message':
        return "No OTP"
        
    # ১. প্রথমে মেসেজের একদম শেষের শব্দটি চেক করবে (যেমন স্ক্রিনশটের mfvhn বা কোড)
    words = message.strip().split()
    if words:
        last_word = words[-1].strip(".,!?:;()")
        # শেষের শব্দটি যদি ১ থেকে ১০ অক্ষরের/ডিজিটের হয়, তবে সেটাকেই ওটিপি নিবে
        if 1 <= len(last_word) <= 10:
            return last_word

    # ২. যদি মেসেজে 'code is 123456' বা 'verification code 932426' থাকে, তবে সেই সংখ্যাটা নিবে
    code_match = re.search(r'(?:code|otp|verification|is|পাসওয়ার্ড)\s*(?:is)?\s*([a-zA-Z0-9]{1,10})\b', message, re.IGNORECASE)
    if code_match:
        return code_match.group(1)

    # ৩. যদি ওপরের কিছু না মেলে, তবে পুরো মেসেজ থেকে ১-১০ ডিজিটের যেকোনো পিওর সংখ্যা খুঁজবে
    num_match = re.search(r'\b\d{1,10}\b', message)
    if num_match:
        return num_match.group(0)

    # ৪. একদম শেষে যদি হিজিবিজি টেক্সট থাকে (১-১০ ডিজিটের যেকোনো কিছু)
    any_match = re.search(r'\b[a-zA-Z0-9]{1,10}\b', message)
    if any_match:
        return any_match.group(0)

    return "No OTP"

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
        response = requests.get(f"{API_URL}?token={PANEL_TOKEN}&records=10", timeout=10)
        if response.status_code == 200:
            full_data = response.json()
            if full_data.get('status') == 'success':
                sms_list = full_data.get('data', [])
                if isinstance(sms_list, list):
                    # সোজা সিরিয়ালে লুপ চালানো হলো যাতে একটার পর একটা আগের স্টাইলে আসে
                    for sms in sms_list:
                        num = str(sms.get('num', 'Unknown')).strip()
                        sms_time = sms.get('dt', '')
                        
                        msg_unique_id = f"{num}_{sms_time}"
                        
                        if msg_unique_id not in processed_sms_ids:
                            msg_content = sms.get('message', 'No message')
                            otp = extract_otp(msg_content)
                            
                            # বাম পাশের স্ক্রিনশটের মতো ফিক্সড সার্ভিস মাস্কিং ও নম্বর ফরম্যাট
                            masked_service = "*******"
                            masked_number = format_number(num)
                            
                            # বাম পাশের স্ক্রিনশটের লেআউট ডিজাইন (১ ক্লিকে ওটিপি কপির জন্য <code></code> ব্যবহার করা হয়েছে)
                            text = (
                                f"🌐 <b>{masked_service}</b>\n"
                                f"📞 {masked_number}\n\n"
                                f"💬 <code>{otp}</code>"
                            )

                            # ওনার বাটন লেআউট
                            markup = InlineKeyboardMarkup()
                            markup.row(
                                InlineKeyboardButton("👤 Owner", url="https://t.me/nb269")
                            )

                            try:
                                bot.send_message(CHAT_ID, text, parse_mode='HTML', reply_markup=markup)
                                processed_sms_ids.add(msg_unique_id)
                                save_processed_ids(processed_sms_ids)
                                print(f"Successfully forwarded OTP for {masked_number}")
                                time.sleep(1) # টেলিগ্রাম স্প্যামিং এড়াতে ছোট গ্যাপ
                            except Exception as send_error:
                                print(f"Sending Error: {send_error}")
                                            
    except Exception as e:
        print(f"Fetch Error: {e}")

if __name__ == "__main__":
    print("১-১০ ডিজিট/অক্ষর এক্সট্রাকশন ও ট্যাপ-টু-কপি বুস্ট সহ বট চালু হচ্ছে...")
    while True:
        fetch_and_forward()
        time.sleep(4)
