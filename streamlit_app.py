import streamlit as st
from auth_functions import register_user, authenticate_user
import fitz  # PyMuPDF
import sqlite3
import spacy
from unidecode import unidecode
import os
import re
from spellchecker import SpellChecker
from PIL import Image
import tempfile

# Initialize SpaCy and spellchecker
nlp = spacy.load('fr_core_news_lg')
spell = SpellChecker(language='fr')

# Path dictionary for different categories
pdf_files = {
    "ELECTRICITE": [
        ("Contenu Electricité", ".github/assets/pdfs/Electricite")
    ],
    "FLUIDE": [
        ("Contenu Fluide", ".github/assets/pdfs/Fluide")
    ],
    "DOMAINE SPECIFIQUE": []
}

# Initialize SQLite connection and create table if it doesn't exist
conn = sqlite3.connect('pdf_search_results.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS pdf_results
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              pdf_path TEXT,
              page_number INTEGER,
              paragraph_text TEXT)''')
conn.commit()

def list_pdfs_in_folder(folder_path):
    pdfs = []
    if os.path.exists(folder_path):
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith(".pdf"):
                pdf_path = os.path.join(folder_path, file_name)
                pdfs.append(file_name)
    return pdfs

def correct_spelling(text):
    corrected_text = []
    predictions = {}
    words = text.split()
    for word in words:
        corrected_word = spell.correction(word)
        corrected_text.append(corrected_word)
        if corrected_word != word:
            predictions[word] = corrected_word
    return ' '.join(corrected_text), predictions

def detect_apostrophe_expressions(text):
    apostrophe_expressions = re.findall(r'\b\w+\'/.,:;?!&*()_\-=+#|{[}]\w+\b', text)
    return apostrophe_expressions

def preprocess_text(text):
    corrected_text, predictions = correct_spelling(text)
    apostrophe_expressions = detect_apostrophe_expressions(corrected_text)
    for expression in apostrophe_expressions:
        if expression in corrected_text:
            corrected_text = corrected_text.replace(expression, expression.replace("\'/.,:;?!&*()_\-=+#|{[}]", "___"))
    normalized_text = unidecode(corrected_text)
    doc = nlp(normalized_text)
    tokens = []
    for token in doc:
        if token.is_alpha and not token.is_stop:
            lemma = token.lemma_.lower()
            lemma = lemma.replace("___", "\'/.,:;?!&*()_\-=+#|{[}]") if "___" in lemma else lemma
            tokens.append(lemma)
    return " ".join(tokens), corrected_text, predictions

def search_and_save_to_db(search_text, corrected_search_text, selected_category):
    try:
        results = []
        for title, folder_path in pdf_files.get(selected_category, []):
            if os.path.isdir(folder_path):
                for file_name in os.listdir(folder_path):
                    if file_name.lower().endswith(".pdf"):
                        pdf_path = os.path.join(folder_path, file_name)
                        pdf_results = search_in_pdf(pdf_path, search_text, corrected_search_text)
                        for result in pdf_results:
                            if isinstance(result, tuple) and len(result) == 3:
                                results.append(result)
            elif folder_path.lower().endswith(".pdf"):
                pdf_results = search_in_pdf(folder_path, search_text, corrected_search_text)
                for result in pdf_results:
                    if isinstance(result, tuple) and len(result) == 3:
                        results.append(result)
        return results
    except Exception as e:
        return f"Une erreur est survenue : {str(e)}"

def search_in_pdf(pdf_path, search_text, corrected_search_text):
    results = []
    try:
        pdf_document = fitz.open(pdf_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text = page.get_text("text")
            fixed_text = " ".join(text.splitlines())
            paragraphs = fixed_text.split('. ')
            for paragraph in paragraphs:
                normalized_paragraph = unidecode(paragraph.lower())
                if all(word in normalized_paragraph for word in corrected_search_text.lower().split()):
                    if paragraph.strip():
                        c.execute("INSERT INTO pdf_results (pdf_path, page_number, paragraph_text) VALUES (?, ?, ?)",
                                  (pdf_path, page_num + 1, paragraph.strip() + '.'))
                        conn.commit()
                        results.append((pdf_path, page_num + 1, paragraph.strip() + '.'))
        pdf_document.close()
    except Exception as e:
        print(f"Erreur lors de la recherche dans {pdf_path}: {str(e)}")
    return results

def extract_page(pdf_path, page_number, paragraph):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number - 1)
    text_instances = page.search_for(paragraph)
    for inst in text_instances:
        highlight = page.add_highlight_annot(inst)
        highlight.update()
    pix = page.get_pixmap()
    return pix.tobytes("png")

def show_login_form():
    st.title("Connexion")
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if authenticate_user(username, password):
            st.session_state.user = username
            st.session_state.show_main_content = True
            st.session_state.show_login = False
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect.")

def show_registration_form():
    st.title("Inscription")
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    email = st.text_input("Email")
    full_name = st.text_input("Nom complet")
    if st.button("S'inscrire"):
        if register_user(username, password, email, full_name):
            st.success("Inscription réussie !")
            st.session_state.show_login = True
            st.session_state.show_main_content = False

def show_main_content():
    image_path = ".github/assets/Logo.jpg"
    if os.path.exists(image_path):
        image = Image.open(image_path)
        image = image.resize((300, 225), resample=Image.LANCZOS)
        st.image(image, use_column_width=False)
    else:
        st.error(f"Image introuvable : {image_path}")

    st.write("Bienvenue sur le moteur de recherche sur les normes et réglementations techniques.")
    st.write("Veuillez sélectionner un des dossiers ci-dessous.")

    categories = list(pdf_files.keys())
    selected_category = st.selectbox("Sélectionnez un domaine :", [""] + categories)

    if selected_category:
        st.write(f"Vous avez sélectionné : {selected_category}")

        if selected_category == "DOMAINE SPECIFIQUE":
            uploaded_files = st.file_uploader("Ajouter des fichiers PDF", type="pdf", accept_multiple_files=True)
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name
                        title = os.path.basename(tmp_path)
                        pdf_files["DOMAINE SPECIFIQUE"].append((title, tmp_path))

        folder_path = [folder_path for title, folder_path in pdf_files.get(selected_category, []) if os.path.isdir(folder_path)]
        if folder_path:
            pdf_files_list = list_pdfs_in_folder(folder_path[0])
            if pdf_files_list:
                st.write("Documents disponibles :")
                for pdf_name in pdf_files_list:
                    st.write(f"- {pdf_name}")

        st.write("Rechercher dans les documents PDF")
        search_text = st.text_input("Texte à rechercher :", key="search_input")

        if st.button("Rechercher") and search_text:
            processed_text, corrected_text, predictions = preprocess_text(search_text)
            if predictions:
                for original, corrected in predictions.items():
                    st.info(f"Prédiction du mot : '{original}' → '{corrected}'")

            with st.spinner("Recherche en cours..."):
                results = search_and_save_to_db(search_text, processed_text, selected_category)

            if results:
                st.write(f"Résultats trouvés : {len(results)}")
                for i, result in enumerate(results, start=1):
                    if len(result) == 3:
                        pdf_path, page_num, paragraph = result
                        file_name = os.path.basename(pdf_path)
                        link_text = f"Fichier : {file_name}, Page : {page_num}"
                        with st.expander(link_text):
                            st.write(f"**{link_text}**")
                            st.write(f"{paragraph}")
                            img_data = extract_page(pdf_path, page_num, paragraph)
                            st.image(img_data, caption=f"Page {page_num} de {file_name}")
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button(
                                    label="Télécharger le PDF complet",
                                    data=pdf_file,
                                    file_name=file_name,
                                    key=f"download_button_{i}"
                                )
            else:
                st.warning("Aucun résultat trouvé.")

def main():
    if 'user' in st.session_state and st.session_state.get('show_main_content', False):
        show_main_content()
    else:
        menu = st.sidebar.selectbox("Menu", ["Connexion", "Inscription"])
        if menu == "Inscription":
            show_registration_form()
        elif menu == "Connexion":
            show_login_form()

if __name__ == "__main__":
    main()
