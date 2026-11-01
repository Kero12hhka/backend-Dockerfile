# Forex AI London — Daily 09:00 Cairo

مشروع تجريبي لتحليل EURUSD وGBPUSD وGBPJPY وUSDJPY، تدريب نموذج ML على البيانات التاريخية، ثم مقارنة الأزواج الأربعة وإرسال قرار واحد فقط (أفضل BUY أو SELL أو WAIT) إلى Telegram يوميًا الساعة 09:00 بتوقيت القاهرة.

**تنبيه:** إشارات بحثية فقط، لا يوجد تداول آلي ولا ضمان للربح. ابدأ بـ Demo/Paper Trading.

## مصدر البيانات
اخترنا Twelve Data REST API لأنه يعمل على GitHub Actions دون الحاجة إلى تشغيل MT5 على Windows. بيانات الفوركس لديهم تجميعية وقد تختلف عن أسعار وسيطك، كما أن real-time وعمق التاريخ يعتمدان على الخطة.
- https://twelvedata.com/docs
- https://support.twelvedata.com/en/articles/5656039-how-to-get-historical-prices
- https://support.twelvedata.com/en/articles/11850499-understanding-price-deviations-in-commodities-and-forex-data

## رفع المشروع
1. أنشئ GitHub repository واجعله Private.
2. ارفع محتويات هذا المجلد إلى الفرع main.
3. هذه النسخة خفيفة ولا تتضمن ملفات التاريخ الكبيرة. لتدريب النموذج من جديد، ضع ملفات CSV/ZIP التاريخية داخل data/raw/ بنفس أسماء الأزواج (EURUSD, GBPUSD, GBPJPY, USDJPY). النماذج المدربة الحالية موجودة داخل models/ ويمكن استخدامها للتشغيل المباشر.
4. من Settings → Secrets and variables → Actions أضف:
   - TWELVE_DATA_API_KEY
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID

لا تضع أي token داخل الكود.

## المفاتيح
- Twelve Data: https://twelvedata.com/
- Telegram: افتح @BotFather، أنشئ bot وخذ token. افتح محادثة مع البوت واضغط Start. للحصول على Chat ID افتح `https://api.telegram.org/bot<TOKEN>/getUpdates`.

## تدريب محليًا (Python 3.11)
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m src.train
```

التقسيم الزمني: التدريب حتى نهاية 2024، اختيار RR على 2025 فقط، واختبار مستقل على 2026. يقارن 1:2 و1:2.5 و1:3. بعد تسجيل نتيجة الاختبار، يعيد تدريب نموذج النشر على كل التاريخ المتاح.

يرفع مجلد models/ وreports/ بعد التدريب إلى GitHub.

## منطق القرار اليومي
- يحلل كل زوج على حدة ثم يقارن أعلى اتجاه متاح لكل زوج.
- يرسل قرارًا نهائيًا واحدًا فقط: أفضل زوج BUY/SELL، أو WAIT إذا لم يتجاوز أي زوج عتبة النموذج.
- عتبة الاختيار وRR مأخوذتان من مرحلة التحقق التاريخي؛ درجة النموذج ليست احتمال نجاح معايرًا.
- المخاطرة المخططة الافتراضية 1% كحد أقصى (`RISK_PCT=0.01`). المشروع لا يحسب حجم اللوت ولا يرسل أوامر تداول؛ احسب الحجم وفق قيمة النقطة وعملة الحساب لدى وسيطك.
- لا تخلط بين درجة النموذج ونسبة الثقة أو معدل الفوز.

## نتائج الاختبار الحالية
الاختبار السابق على البيانات المتاحة أظهر لـ RR 1:3 عدد 27 صفقة في اختبار 2026، منها 8 رابحة و19 خاسرة، وصافي +5R قبل تكاليف التداول. هذه عينة صغيرة وليست دليلًا كافيًا على ربحية مستقبلية. فترة التحقق 2025 كانت 32 صفقة وصافي 0R. كما أن السبريد والانزلاق السعري والمنطقة الزمنية للبيانات التاريخية تحتاج تحققًا إضافيًا.

## الجدولة
`.github/workflows/daily-scan.yml` يرسل التقرير الساعة 09:00 Africa/Cairo من الاثنين إلى الجمعة. GitHub يدعم timezone-aware schedules، لكن قد يتأخر بدء الـ runner.

## تشغيل يدوي
من GitHub Actions → Daily Forex AI → Run workflow، أو محليًا:
```bash
python -m src.live_scan
```

## ملاحظات
- timestamps في ملفات CSV لا تحمل timezone صريحًا؛ الكود يفترض UTC. غيّر SOURCE_TIMEZONE إذا كانت بياناتك بتوقيت الوسيط.
- القرار الساعة 09:00 يعتمد آخر شمعة M15 مكتملة (08:45–09:00 القاهرة).
- التدريب يستخدم عينة واحدة لكل يوم ولكل زوج عند وقت القرار، حتى يطابق وقت الاستخدام الفعلي.
- Model score ليس احتمال نجاح معايرًا.
- لا تستخدم النموذج بحساب حقيقي قبل مراجعة تقرير 2026 وتجربة Demo كافية.
