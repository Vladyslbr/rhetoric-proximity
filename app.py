import streamlit as st
import pandas as pd
import json
import glob
import joblib
import numpy as np
from sentence_transformers import SentenceTransformer
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import re

# ==========================================
# 1. НАЛАШТУВАННЯ СТОРІНКИ ТА СЛОВНИКІВ
# ==========================================
st.set_page_config(page_title="Political Spectrum Tracker", layout="wide", page_icon="🏛️")
st.title("🏛️ Political Spectrum Tracker (MVP)")

# Словник для відображення назв осей українською мовою
AXIS_TRANSLATION = {
    'militarism': 'Мілітаризм',
    'national_identity': 'Національна ідентичність',
    'traditionalism': 'Традиціоналізм',
    'statism': 'Статизм',
    'populism': 'Популізм'
}

# Базовий словник для підсвічування слів (Explainability)
VOCAB = {
    'militarism': ['війн', 'збро', 'ворог', 'армі', 'ппо', 'вибух', 'ракет', 'знищ', 'солдат', 'фронт', 'сил'],
    'national_identity': ['наці', 'україн', 'мов', 'культур', 'історі', 'ідентичн', 'незалежн', 'суверен'],
    'traditionalism': ['традиці', 'сім', 'родин', 'церкв', 'бог', 'морал', 'цінност'],
    'statism': ['держав', 'закон', 'поряд', 'влад', 'контрол', 'дисциплін', 'бюджет'],
    'populism': ['народ', 'еліт', 'корупц', 'прост', 'олігарх', 'злоді', 'крад', 'люди']
}

# Кольори для осей (RGB формат для зміни прозорості)
AXIS_COLORS = {
    'militarism': '214, 39, 40',        # Червоний
    'national_identity': '44, 160, 44', # Зелений
    'traditionalism': '148, 103, 189',  # Фіолетовий
    'statism': '31, 119, 180',          # Синій
    'populism': '255, 127, 14'          # Помаранчевий
}

def highlight_text(text, row, axes):
    """Підсвічує ключові слова в тексті залежно від оцінки осі."""
    highlighted = text
    for axis in axes:
        score = row[axis]
        # Підсвічуємо тільки якщо бал значущий (> 0.25)
        if score > 0.25: 
            alpha = min(score + 0.1, 1.0) # Інтенсивність залежить від балу
            color = f"rgba({AXIS_COLORS.get(axis, '200, 200, 200')}, {alpha})"
            
            words = VOCAB.get(axis, [])
            for w in words:
                # Регулярний вираз для пошуку слів із заданим коренем
                pattern = f'(?i)({w}[а-яіїєґa-z]*)'
                replacement = f'<span style="background-color: {color}; padding: 0 4px; border-radius: 4px; color: #fff; font-weight: bold;">\\1</span>'
                highlighted = re.sub(pattern, replacement, highlighted)
    return highlighted

# ==========================================
# 2. КЕШУВАННЯ МОДЕЛЕЙ
# ==========================================
@st.cache_resource
def load_models():
    model_name = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
    encoder = SentenceTransformer(model_name)
    try:
        model = joblib.load('political_model.joblib')
    except FileNotFoundError:
        st.error("Файл 'political_model.joblib' не знайдено. Будь ласка, спочатку натренуйте модель.")
        st.stop()
    return encoder, model

encoder, model = load_models()
target_cols = ['militarism', 'national_identity', 'traditionalism', 'statism', 'populism']
translated_target_cols = [AXIS_TRANSLATION[c] for c in target_cols]

# ==========================================
# 3. КЕШУВАННЯ ТА ОБРОБКА ДАНИХ
# ==========================================
@st.cache_data
def load_data():
    all_data = []
    json_files = glob.glob("data/*.json")

    for file in json_files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        records = data if isinstance(data, list) else [data]

        for item in records:
            person = item.get("person", "Невідомо")
            for post in item.get("posts", []):
                annotation = post.get("annotation")
                if not annotation or "axes" not in annotation:
                    continue

                axes = annotation["axes"]
                row = {
                    "person": person,
                    "date": post.get("posted_at", None), 
                    "source": post.get("source", "невідомо"),
                    "text": post.get("text", "").strip(),
                    "militarism": axes.get("militarism", 0.0),
                    "national_identity": axes.get("national_identity", 0.0),
                    "traditionalism": axes.get("traditionalism", 0.0),
                    "statism": axes.get("statism", 0.0),
                    "populism": axes.get("populism", 0.0)
                }
                all_data.append(row)

    df = pd.DataFrame(all_data)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    return df

df = load_data()

# ==========================================
# 4. ІНТЕРФЕЙС: ТАБИ
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Аналіз політиків", "🔍 Аналізатор тексту", "🔑 Пошук за словом"])

# --- ТАБ 1: ДАШБОРД ПОЛІТИКІВ ---
with tab1:
    if df.empty:
        st.warning("Не знайдено розмічених даних у папці 'data/'.")
    else:
        col_settings, col_dash = st.columns([1, 3])
        
        with col_settings:
            st.subheader("Налаштування")
            selected_person = st.selectbox("Головний політик:", df['person'].unique())
            
            other_persons = [p for p in df['person'].unique() if p != selected_person]
            compare_persons = st.multiselect("Порівняти з:", other_persons)
            
            all_selected_persons = [selected_person] + compare_persons
            
            selected_axes = st.multiselect(
                "Оберіть осі для графіка:", 
                target_cols, 
                default=['militarism', 'national_identity'],
                format_func=lambda x: AXIS_TRANSLATION.get(x, x) # Відображаємо українські назви
            )
            
            available_sources = df[df['person'].isin(all_selected_persons)]['source'].unique()
            selected_sources = st.multiselect(
                "Джерела (Telegram/FB):", 
                available_sources, 
                default=available_sources
            )

            st.markdown("---")
            interval_options = {"День": "D", "Тиждень": "W", "Місяць": "M"} 
            selected_interval_label = st.selectbox("Інтервал графіка:", list(interval_options.keys()), index=1)
            resample_rule = interval_options[selected_interval_label]
            
            person_df_raw = df[df['person'].isin(all_selected_persons)]
            comp_df = person_df_raw[person_df_raw['source'].isin(selected_sources)].dropna(subset=['date'])
            
        with col_dash:
            if comp_df.empty or not selected_axes:
                st.info("Немає даних для відображення за цими фільтрами.")
            else:
                # 1. Таймлайн (Динаміка)
                st.subheader(f"Динаміка ідеології (Усереднення: {selected_interval_label})")
                
                smoothed_list = []
                for p in all_selected_persons:
                    p_df = comp_df[comp_df['person'] == p]
                    if not p_df.empty:
                        p_smooth = p_df.set_index('date').resample(resample_rule)[selected_axes].mean().dropna().reset_index()
                        p_smooth['person'] = p
                        smoothed_list.append(p_smooth)
                
                if smoothed_list:
                    smoothed_df = pd.concat(smoothed_list)
                    melted_df = smoothed_df.melt(id_vars=['date', 'person'], value_vars=selected_axes)
                    
                    fig_timeline = px.line(
                        melted_df, 
                        x='date', 
                        y='value', 
                        color='person',        
                        facet_row='variable',  
                        markers=True,
                        template="plotly_white",
                        labels={'value': 'Оцінка', 'variable': 'Вісь', 'date': 'Дата', 'person': 'Політик'}
                    )
                    
                    fig_timeline.update_layout(height=250 * len(selected_axes) + 100)
                    fig_timeline.update_yaxes(range=[0, 1])
                    
                    # Замінюємо англійські назви підграфіків на українські
                    fig_timeline.for_each_annotation(lambda a: a.update(text=AXIS_TRANSLATION.get(a.text.split("=")[-1], a.text.split("=")[-1])))
                    
                    st.plotly_chart(fig_timeline, use_container_width=True)
                
                # 2. Розбір контексту з підсвічуванням
                st.markdown("---")
                st.subheader("Розбір контексту (Пояснення оцінок)")
                st.write("Інтенсивність кольору тексту залежить від сили знайденої моделі ідеології.")
                
                min_date = comp_df['date'].min().date()
                max_date = comp_df['date'].max().date()
                selected_date = st.date_input("Оберіть дату для аналізу:", value=max_date, min_value=min_date, max_value=max_date)
                
                days_delta = 1 if resample_rule == "D" else (3 if resample_rule == "W" else 15)
                mask = (comp_df['date'].dt.date >= selected_date - timedelta(days=days_delta)) & \
                       (comp_df['date'].dt.date <= selected_date + timedelta(days=days_delta))
                
                posts_in_range = comp_df.loc[mask]
                
                if posts_in_range.empty:
                    st.write(f"Немає постів у цей період (± {days_delta} днів).")
                else:
                    for _, row in posts_in_range.head(5).iterrows():
                        date_str = row['date'].strftime('%d.%m.%Y')
                        source_tag = row['source'].upper()
                        person_tag = row['person']
                        
                        # Відображаємо українські назви осей у розшифровці
                        scores_str = " | ".join([f"{AXIS_TRANSLATION[ax]}: {row[ax]:.2f}" for ax in selected_axes])
                        highlighted_text = highlight_text(row['text'], row, selected_axes)
                        
                        with st.expander(f"[{person_tag} | {source_tag}] {date_str} — {row['text'][:50]}..."):
                            st.caption(f"Оцінки моделі: {scores_str}")
                            st.markdown(f"> {highlighted_text}", unsafe_allow_html=True)
                
                # 3. Радарний графік (Порівняння)
                st.markdown("---")
                st.subheader("Середній профіль (Порівняння)")
                
                fig_radar = go.Figure()
                colors = px.colors.qualitative.Set1 
                
                for i, p in enumerate(all_selected_persons):
                    p_df = comp_df[comp_df['person'] == p]
                    if not p_df.empty:
                        avg_scores = p_df[target_cols].mean().tolist()
                        fig_radar.add_trace(go.Scatterpolar(
                            r=avg_scores,
                            theta=translated_target_cols, # Використовуємо українські осі
                            fill='toself' if i == 0 else 'none',
                            name=p,
                            line=dict(color=colors[i % len(colors)])
                        ))
                
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1])), 
                    showlegend=True,
                    margin=dict(l=40, r=40, t=20, b=20)
                )
                st.plotly_chart(fig_radar, use_container_width=True)

# --- ТАБ 2: АНАЛІЗАТОР ТЕКСТІВ (RUNTIME) ---
with tab2:
    st.subheader("Оцінка нового тексту")
    user_text = st.text_area("Текст для аналізу:", height=150)
    
    if st.button("Аналізувати", type="primary"):
        if user_text.strip() == "":
            st.warning("Будь ласка, введіть текст.")
        else:
            with st.spinner("Обчислення..."):
                emb = encoder.encode([user_text])
                pred = model.predict(emb)[0]
                pred = np.clip(pred, 0.0, 1.0)
                
                res_col1, res_col2 = st.columns([1, 1])
                with res_col1:
                    for col, val in zip(target_cols, pred):
                        # Відображаємо українські назви у метриках
                        st.metric(label=AXIS_TRANSLATION[col], value=f"{val:.2f}")
                        st.progress(float(val))
                with res_col2:
                    fig_res_radar = go.Figure()
                    fig_res_radar.add_trace(go.Scatterpolar(
                        r=pred, 
                        theta=translated_target_cols, # Використовуємо українські осі 
                        fill='toself', 
                        marker=dict(color='#d62728')
                    ))
                    fig_res_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])))
                    st.plotly_chart(fig_res_radar, use_container_width=True)

                # ==========================================
                # ДОДАНО: Підсвічування слів для введеного тексту
                # ==========================================
                st.markdown("---")
                st.subheader("Розбір тексту (Підсвічування ознак)")
                st.write("Слова підсвічуються відповідними кольорами осей, якщо їх оцінка > 0.25. Інтенсивність кольору залежить від сили оцінки.")
                
                # Створюємо словник у форматі {axis: score}, який очікує функція highlight_text
                pred_row = {col: val for col, val in zip(target_cols, pred)}
                
                # Викликаємо функцію для всіх осей
                highlighted_user_text = highlight_text(user_text, pred_row, target_cols)
                
                # Виводимо текст у гарному форматуванні
                st.markdown(
                    f"<div style='padding: 15px; border-radius: 8px; background-color: #f9f9f9; border: 1px solid #e6e6e6; font-size: 16px; line-height: 1.6; color: #333;'>{highlighted_user_text}</div>", 
                    unsafe_allow_html=True
                )

# --- ТАБ 3: ПОШУК ЗА СЛОВОМ (RUNTIME VOCABULARY) ---
with tab3:
    st.subheader("Аналіз тематики за ключовим словом")
    st.write("Як різні політики говорять про конкретні речі? Введіть слово (наприклад, 'перемовини', 'мова', 'армія').")
    
    keyword = st.text_input("Ключове слово:")
    
    if keyword:
        kw_df = df[df['text'].str.contains(keyword, case=False, na=False)]
        
        if kw_df.empty:
            st.warning(f"Слово '{keyword}' не знайдено у жодному тексті.")
        else:
            st.success(f"Знайдено постів зі словом '{keyword}': **{len(kw_df)}**")
            
            k_col1, k_col2 = st.columns([1, 2])
            
            with k_col1:
                st.write("**Середній ідеологічний заряд цього слова:**")
                
                pol_options = ["Усі політики"] + kw_df['person'].unique().tolist()
                selected_kw_person = st.selectbox("Відобразити профіль для:", pol_options)
                
                if selected_kw_person == "Усі політики":
                    radar_df = kw_df
                    trace_name = "Середнє (Усі)"
                else:
                    radar_df = kw_df[kw_df['person'] == selected_kw_person]
                    trace_name = selected_kw_person
                
                kw_avg = radar_df[target_cols].mean().tolist()
                
                fig_kw_radar = go.Figure()
                fig_kw_radar.add_trace(go.Scatterpolar(
                    r=kw_avg, 
                    theta=translated_target_cols, # Використовуємо українські осі
                    fill='toself',
                    name=trace_name,
                    marker=dict(color='#2ca02c' if selected_kw_person == "Усі політики" else '#ff7f0e')
                ))
                fig_kw_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=False)
                st.plotly_chart(fig_kw_radar, use_container_width=True)
                
            with k_col2:
                st.write("**Хто найчастіше використовує це слово:**")
                person_counts = kw_df['person'].value_counts().reset_index()
                person_counts.columns = ['Політик', 'Кількість згадок']
                fig_bar = px.bar(person_counts, x='Політик', y='Кількість згадок', template="plotly_white")
                st.plotly_chart(fig_bar, use_container_width=True)
            
            st.subheader("Останні контекстні згадки:")
            kw_clean = kw_df.dropna(subset=['date']).sort_values('date', ascending=False)
            
            for _, row in kw_clean.head(10).iterrows():
                date_str = row['date'].strftime('%d.%m.%Y')
                pattern = f'(?i)({keyword}[а-яіїєґa-z]*)'
                highlighted_kw = re.sub(pattern, r'<span style="background-color: yellow; color: black; padding: 2px;">\1</span>', row['text'])
                
                st.markdown(f"**[{row['person']}]** {date_str} <br> {highlighted_kw}", unsafe_allow_html=True)
                st.divider()