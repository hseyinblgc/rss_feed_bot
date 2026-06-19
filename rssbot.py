import logging
import sqlite3
import asyncio
import feedparser
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# --- AYARLAR ---
BOT_TOKEN = "BURAYA_BOTFATHERDAN_ALDIGINIZ_TOKENI_YAZIN"
CHANNEL_ID = "@kanal_kullanici_adi_veya_id"  # Örn: @gizlihaberkanalim veya -100123456789
CHECK_INTERVAL = 3600  # Saniye cinsinden kontrol süresi (3600 sn = 1 saat)

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- VERİTABANI İŞLEMLERİ ---
def init_db():
    conn = sqlite3.connect('rss_bot.db')
    c = conn.cursor()
    # RSS kaynaklarını tutan tablo
    c.execute('''CREATE TABLE IF NOT EXISTS feeds
                 (url TEXT PRIMARY KEY, added_by TEXT)''')
    # Gönderilmiş haberleri tutan tablo (tekrarı önlemek için)
    c.execute('''CREATE TABLE IF NOT EXISTS sent_entries
                 (link TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def add_feed_to_db(url, user):
    try:
        conn = sqlite3.connect('rss_bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO feeds (url, added_by) VALUES (?, ?)", (url, user))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_feeds():
    conn = sqlite3.connect('rss_bot.db')
    c = conn.cursor()
    c.execute("SELECT url FROM feeds")
    feeds = [row[0] for row in c.fetchall()]
    conn.close()
    return feeds

def remove_feed_from_db(url):
    conn = sqlite3.connect('rss_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM feeds WHERE url=?", (url,))
    conn.commit()
    conn.close()

def is_entry_sent(link):
    conn = sqlite3.connect('rss_bot.db')
    c = conn.cursor()
    c.execute("SELECT link FROM sent_entries WHERE link=?", (link,))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_entry_as_sent(link):
    conn = sqlite3.connect('rss_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO sent_entries (link) VALUES (?)", (link,))
    conn.commit()
    conn.close()

# --- BOT KOMUTLARI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba! Ben RSS Botuyum.\n"
        "Komutlar:\n"
        "/add <url> - Yeni RSS ekle\n"
        "/list - Ekli RSS'leri listele\n"
        "/remove <url> - RSS sil"
    )

async def add_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Lütfen bir URL belirtin. Örn: /add https://site.com/rss")
        return

    url = context.args[0]
    # Basit bir doğrulama: Link çalışıyor mu?
    feed = feedparser.parse(url)
    if feed.bozo: # Hata varsa bozo 1 döner (genellikle)
        await update.message.reply_text("Bu URL geçerli bir RSS kaynağı gibi görünmüyor veya erişilemiyor.")
        return

    if add_feed_to_db(url, update.effective_user.username):
        await update.message.reply_text(f"✅ Eklendi: {url}")
        # İlk eklemede geçmişi spamlamamak için mevcut son haberleri 'gönderilmiş' olarak işaretleyebiliriz
        # Ancak şimdilik sadece veritabanına ekliyoruz.
    else:
        await update.message.reply_text("Bu RSS kaynağı zaten listede var.")

async def list_feeds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feeds = get_feeds()
    if not feeds:
        await update.message.reply_text("Henüz hiç RSS kaynağı eklenmemiş.")
    else:
        msg = "📋 **Takip Edilen Kaynaklar:**\n\n" + "\n".join(feeds)
        await update.message.reply_text(msg)

async def remove_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Silinecek URL'yi belirtin. Örn: /remove https://site.com/rss")
        return
    
    url = context.args[0]
    remove_feed_from_db(url)
    await update.message.reply_text(f"🗑️ Silindi: {url}")

async def test_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="🔔 Bu bir test mesajıdır.")
        await update.message.reply_text(f"Test mesajı {CHANNEL_ID} kanalına gönderildi.")
    except Exception as e:
        await update.message.reply_text(f"Mesaj gönderilemedi: {e}")

# --- ARKA PLAN GÖREVİ (JOB) ---

async def check_feeds_job(context: ContextTypes.DEFAULT_TYPE):
    feeds = get_feeds()
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            # Genellikle RSS'lerde en yeni haber en üsttedir.
            # Tersten (eskiden yeniye) tarayalım ki sırayla atılsın.
            for entry in reversed(feed.entries[:5]): # Her kontrolde en son 5 habere bakar
                link = entry.get('link')
                title = entry.get('title')
                
                if link and not is_entry_sent(link):
                    # Yeni içerik bulundu!
                    message = f"📢 **Yeni İçerik!**\n\n**{title}**\n\n{link}"
                    
                    # Kanala gönder
                    try:
                        await context.bot.send_message(chat_id=CHANNEL_ID, text=message)
                        mark_entry_as_sent(link)
                    except Exception as e:
                        logging.error(f"Mesaj gönderilemedi: {e}")
                        
        except Exception as e:
            logging.error(f"RSS tarama hatası ({url}): {e}")

# --- ANA ÇALIŞTIRMA ---

if __name__ == '__main__':
    # Veritabanını başlat
    init_db()
    
    # Uygulamayı oluştur
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Komutları ekle
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('add', add_feed))
    application.add_handler(CommandHandler('list', list_feeds))
    application.add_handler(CommandHandler('remove', remove_feed))
    application.add_handler(CommandHandler('test', test_message))
    
    # Zamanlanmış görevi ekle (JobQueue)
    job_queue = application.job_queue
    # İlk çalışmayı 10 saniye sonra yap, sonra her saat başı (3600 sn) tekrarla
    job_queue.run_repeating(check_feeds_job, interval=CHECK_INTERVAL, first=10)
    
    print("Bot çalışıyor...")
    application.run_polling()
