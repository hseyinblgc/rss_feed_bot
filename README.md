## Telegram Rss Bot

Bir ara hobi olarak geliştirdiğim bot. Geliştirilmesi sonlandırıldı.

**Amaç**

*Kullanıcının ilettiği rss linkini belirli aralıklarla kontrol ederek güncellemeleri kullanıcıya iletmek*

**Kurulum**

`git clone https://github.com/hseyinblgc/rss_feed_bot.git && cd rss_feed_bot`

*Sanal ortamın kurulumu ve etkinleştirilmesi*

```bash
python -m venv .venv
. .venv/bin/activate
```

*Gerekli paketlerin kurulması*

`pip install -r requirements.txt`

*[rssbot.py](https://github.com/hseyinblgc/rss_feed_bot/blob/48ac333c3a529bca819aeb215bf51f9d3cd2e65b/rssbot.py#L9-L10)* daki ilgili satırları kendine göre düzenledikten sonra 
>`python rssbot.py`
ile botu başlatabilirsin.
