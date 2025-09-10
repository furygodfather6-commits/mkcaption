# mkcaption
Advanced Caption Editor Telegram Bot (Render Ready)
Yeh ek powerful Telegram bot hai jise Python me banaya gaya hai. Iski madad se aap media files (photos, videos, documents, audio) ke captions par advanced edits kar sakte hain. Ise Render par deploy karne ke liye optimize kiya gaya hai.
Naye Features
 * Watermark: Photos par custom text watermark add karein.
 * Caption Templates: Baar-baar istemal hone wale captions aur buttons ko template ke roop me save karein aur load karein.
 * Text Styling: Caption me text ko Bold ya Italic karne ke liye aasan buttons.
 * Interactive Editing: Inline keyboard se behtareen user experience.
 * Multiple Edit Modes: Replace, Append, Prepend, aur Find & Replace.
 * URL Buttons: Apne message me interactive inline URL buttons jodein.
 * Persistent Sessions: SQLite database ka istemal, jisse restart hone par bhi data safe rehta hai.
 * Render Ready: Webhook-based system aur render.yaml file ke saath, jisse deployment aasan ho.
Render par Deploy kaise karein?
Render par is bot ko deploy karna bahut aasan hai.
Step 1: GitHub par Repository Taiyar karein
 * Is code ko ek GitHub repository me upload karein. Agar aapne ise fork kiya hai, to yeh pehle se hi ho chuka hai.
 * सुनिश्चित करें कि आपकी रिपॉजिटरी में caption_editor_bot.py, requirements.txt, और render.yaml फाइलें मौजूद हैं।
Step 2: Render par Web Service Banayein
 * Apne Render Dashboard par login karein.
 * New + par click karein aur Web Service chunein.
 * Apni GitHub repository ko connect karein.
 * Render aapki render.yaml file ko automatically detect kar lega aur settings configure kar dega. Aapko bas ek naam dena hai.
   * Name: Apne bot ke liye ek unique naam dein (jaise my-caption-bot). Yeh naam aapke bot ke URL ka hissa hoga (my-caption-bot.onrender.com).
 * Advanced Settings me jayein aur do Environment Variables add karein:
   * Key: TELEGRAM_BOT_TOKEN
     * Value: Apna Telegram Bot Token yahan paste karein (jo aapko @BotFather se mila tha).
   * Key: WEBHOOK_URL
     * Value: Aapki Render service ka URL, jiske end me /webhook laga ho. Jaise: https://my-caption-bot.onrender.com/webhook
 * Create Web Service par click karein. Render dependencies install karna aur bot ko deploy karna shuru kar dega.
Step 3: Telegram ko Webhook Batayein
Aapke bot ko deploy hone ke baad, aapko Telegram ko batana hoga ki updates kahan bhej_ne hain. Iske liye aapko bas ek baar apne browser me yeh URL kholna hai:
[https://api.telegram.org/bot](https://api.telegram.org/bot)<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_WEBHOOK_URL>

 * <YOUR_BOT_TOKEN> ko apne bot ke token se replace karein.
 * <YOUR_WEBHOOK_URL> ko apne Render URL se replace karein (e.g., https://my-caption-bot.onrender.com/webhook).
Example:
https://api.telegram.org/bot12345:ABCDE/setWebhook?url=https://my-caption-bot.onrender.com/webhook
Agar browser me {"ok":true,"result":true,"description":"Webhook was set"} dikhta hai, to aapka bot taiyar hai!
Bot ka Istemal kaise karein
 * Apne bot se chat shuru karein.
 * Koi bhi file (photo, video, document) caption ke saath ya bina caption ke bhejein.
 * Bot aapko ek interactive keyboard dega jisse aap caption edit kar sakte hain, watermark laga sakte hain, ya templates ka istemal kar sakte hain.
 * Jab aapka kaam ho jaye, to ✅ Done par click karein.
