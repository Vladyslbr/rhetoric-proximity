```html
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Rhetoric Proximity</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      line-height: 1.6;
      margin: 0;
      padding: 0;
      background: #0b0f19;
      color: #e8eaf0;
    }
    header {
      padding: 60px 20px;
      text-align: center;
      background: linear-gradient(135deg, #1a237e, #0d47a1);
    }
    header h1 {
      margin: 0;
      font-size: 2.5rem;
    }
    header p {
      max-width: 800px;
      margin: 10px auto 0;
      opacity: 0.9;
    }
    section {
      max-width: 1000px;
      margin: auto;
      padding: 40px 20px;
    }
    h2, h3 {
      color: #90caf9;
    }
    .card {
      background: #121a2a;
      border-radius: 12px;
      padding: 20px;
      margin: 20px 0;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    img {
      width: 100%;
      border-radius: 10px;
      margin-top: 10px;
    }
    code, pre {
      background: #0f172a;
      padding: 10px;
      border-radius: 8px;
      overflow-x: auto;
    }
    ul {
      padding-left: 20px;
    }
    .warning {
      border-left: 4px solid #ffb74d;
      padding-left: 10px;
      color: #ffe0b2;
    }
  </style>
</head>

<body>

<header>
  <h1>🏛️ Rhetoric Proximity</h1>
  <p>Інноваційна платформа кількісного аналізу політичної риторики в українському медіапросторі</p>
</header>

<section>

  <div class="card">
    <h2>📌 Про проєкт</h2>
    <p>
      <b>Rhetoric Proximity</b> — система аналізу політичної риторики, що усуває суб’єктивність інтерпретацій
      та переводить політичні тексти у багатовимірні числові спектри.
    </p>
    <p>
      Інструмент дозволяє аналізувати Telegram-пости, Facebook-публікації та офіційні заяви,
      автоматично визначаючи ідеологічні та риторичні маркери.
    </p>
  </div>

  <div class="card">
    <h2>⚙️ Що можна робити</h2>

    <h3>1. Аналіз політиків (дашборд)</h3>
    <p>Порівняння динаміки кількох діячів на інтерактивних графіках.</p>
    <img src="./images/image_1.png" alt="Dashboard analysis"/>

    <h3>2. Розбір контексту (Explainability)</h3>
    <p>Пошук першоджерел і підсвічування токенів залежно від впевненості моделі.</p>
    <img src="./images/image_2.png" />
    <img src="./images/image_22.png" />
    <img src="./images/image_21.png" />

    <h3>3. Аналізатор тексту (Runtime Inference)</h3>
    <p>Миттєва оцінка стороннього тексту з виділенням ключових ознак.</p>
    <img src="./images/image_41.png" />
    <img src="./images/image_42.png" />
    <img src="./images/image_43.png" />

    <h3>4. Пошук за словом (Vocabulary Analysis)</h3>
    <p>Аналіз семантичного навантаження слова та його використання політиками.</p>
    <img src="./images/image_51.png" />
    <img src="./images/image_52.png" />
    <img src="./images/image_53.png" />
  </div>

  <div class="card">
    <h2>📊 Аналізовані спектри (метрики)</h2>
    <p>Кожне повідомлення оцінюється за шкалою <code>0.0 → 1.0</code>:</p>
    <ul>
      <li><b>Мілітаризм</b> — силова логіка та військові пріоритети</li>
      <li><b>Національна ідентичність</b> — мова, суверенітет, наратив нації</li>
      <li><b>Традиціоналізм</b> — моральні та сімейні цінності</li>
      <li><b>Статизм / Порядок</b> — роль сильної держави</li>
      <li><b>Популізм</b> — “народ проти еліт”</li>
      <li><b>Ліберальна рамка</b> — права, свободи, плюралізм</li>
    </ul>
  </div>

  <div class="card">
    <h2>🧠 Архітектура моделі</h2>

    <h3>Стек технологій</h3>
    <ul>
      <li><b>Frontend:</b> Streamlit (динамічний UI)</li>
      <li><b>Ембедери:</b> SentenceTransformer (mpnet-base-v2)</li>
      <li><b>Модель:</b> MultiOutputRegressor + Ridge</li>
    </ul>

    <h3>Цільова архітектура (fine-tuning)</h3>
    <pre>
Текст
 → Ukrainian RoBERTa
 → Embedding (768)
 → Dropout (0.1–0.3)
 → Linear (768 → 256) + ReLU
 → Linear (256 → 5) + Sigmoid
 → [p1, p2, p3, p4, p5]
    </pre>

    <h3>Специфіка датасету</h3>
    <p class="warning">
      ⚠️ Модель навчена на синтетичних даних, згенерованих через OpenAI API.
      10% даних було вручну перевірено та скориговано відповідно до експертних гайдів.
    </p>
  </div>

  <div class="card">
    <h2>💻 Локальний запуск</h2>

    <h3>1. Клонування</h3>
    <pre>git clone https://github.com/your-username/rhetoric-proximity.git
cd rhetoric-proximity</pre>

    <h3>2. Віртуальне середовище</h3>
    <pre># macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate</pre>

    <h3>3. Встановлення залежностей</h3>
    <pre>pip install -r requirements.txt</pre>

    <p>Або вручну:</p>
    <pre>pip install streamlit pandas numpy sentence-transformers scikit-learn plotly joblib</pre>

    <h3>4. Структура проєкту</h3>
    <pre>
rhetoric-proximity/
├── app.py
├── political_model.joblib
└── data/
    ├── annotated_posts_zelenskyy.json
    ├── annotated_denys_smyhal.json
    └── ...
    </pre>

    <h3>5. Запуск</h3>
    <pre>streamlit run app.py</pre>

    <p>
      Після запуску відкрийте <code>http://localhost:8501</code>
    </p>
  </div>

</section>

</body>
</html>
```
