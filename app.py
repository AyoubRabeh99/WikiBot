import streamlit as st
import wikipedia
import re
import openai
import json

# Interface utilisateur avec Streamlit
st.title("Explorateur de pages Wikipedia avec Chatbot")

# Entrée de la clé API OpenAI
api_key_input = st.text_input("Entrez votre clé API OpenAI :", type="password")

if api_key_input:
    # Définir la clé OpenAI
    openai.api_key = api_key_input

    # Définir la langue à utiliser (français ici)
    wikipedia.set_lang("fr")

    # Fonction pour extraire le titre de la page à partir de l'URL
    def get_title_from_url(url):
        match = re.search(r"/wiki/([^#]+)", url)
        if match:
            return match.group(1).replace("_", " ")
        return None

    # Fonction pour trouver les titres des sections principales uniquement
    def find_main_sections(content):
        sections = re.findall(r'^==\s(.*?)\s==$', content, re.MULTILINE)
        return sections

    # Fonction pour extraire le texte d'une section spécifique
    def extract_section_content(content, section_name):
        section_pattern = re.compile(rf'==\s{re.escape(section_name)}\s==')
        next_section_pattern = re.compile(r'^==\s.*?\s==$', re.MULTILINE)

        section_start = section_pattern.search(content)
        if not section_start:
            return None

        section_end = next_section_pattern.search(content, section_start.end())

        if section_end:
            return content[section_start.end():section_end.start()]
        else:
            return content[section_start.end():]

    # Fonction pour générer un résumé du texte donné avec l'API OpenAI
    def summarize_text(text):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "Vous êtes un assistant spécialisé dans le résumé de textes."},
                {"role": "user", "content": f"Voici un texte. Merci de le résumer de manière concise : {text}"}
            ],
            max_tokens=500,
            temperature=0.5
        )
        return response.choices[0].message['content']

    # Fonction pour traduire le texte donné avec l'API OpenAI
    def translate_text(text, target_language):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "Vous êtes un assistant spécialisé dans la traduction de textes."},
                {"role": "user", "content": f"Voici un texte. Merci de le traduire en {target_language} : {text}"}
            ],
            max_tokens=500,
            temperature=0.5
        )
        return response.choices[0].message['content']

    # Fonction pour répondre aux questions de l'utilisateur sur la section en utilisant l'API OpenAI
    def ask_question(conversation_history, user_question):
        # Ajout de la nouvelle question à l'historique de conversation
        conversation_history.append({"role": "user", "content": user_question})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=conversation_history,
            max_tokens=500,
            temperature=0.5
        )

        # Récupération de la réponse et ajout à l'historique de conversation
        answer = response.choices[0].message['content']
        conversation_history.append({"role": "assistant", "content": answer})

        return answer, conversation_history

    # Entrée de l'URL de la page Wikipedia
    url = st.text_input("Entrez l'URL de la page Wikipedia :")

    if url:
        page_name = get_title_from_url(url)

        if page_name:
            try:
                page = wikipedia.page(page_name, auto_suggest=False)
                content = page.content
                main_sections = find_main_sections(content)

                # Créer un dictionnaire où chaque clé est une section, et la valeur est le contenu de la section
                section_dict = {}
                for section in main_sections:
                    section_content = extract_section_content(content, section)
                    section_dict[section] = section_content

                # Choix du traitement
                treatment_option = st.radio(
                    "Choisissez l'étendue du traitement :",
                    ("Afficher la page entière", "Traiter une section spécifique"))

                if treatment_option == "Afficher la page entière":
                    st.subheader("Sections principales :")
                    with st.expander("Voir les sections principales"):
                        for title in main_sections:
                            st.write(f"- {title}")

                    if st.checkbox("Afficher le texte de la page entière"):
                        st.text_area("Contenu de la page", content, height=300)

                elif treatment_option == "Traiter une section spécifique":
                    section_choice_for_treatment = st.selectbox("Choisissez une section à traiter :", list(section_dict.keys()))

                    if section_choice_for_treatment:
                        section_text = section_dict[section_choice_for_treatment]
                        st.text_area(f"Contenu de la section : {section_choice_for_treatment}",
                                     section_text, height=300)

                        # Traitement immédiat basé sur le choix de l'utilisateur
                        processing_type = st.radio(
                            "Sélectionnez le type de traitement :",
                            ("Résumé de la section", "Traduction de la section", "Chatbot"))

                        if processing_type == "Résumé de la section":
                            # Génération du résumé immédiatement après sélection
                            summary = summarize_text(section_text)
                            st.subheader("Résumé de la section")
                            st.text_area(f"Résumé de '{section_choice_for_treatment}'", summary, height=200)
                            st.download_button("Télécharger le résumé", summary, file_name=f"resume_{section_choice_for_treatment}.txt")

                        elif processing_type == "Traduction de la section":
                            target_language = st.text_input("Entrez la langue de traduction :")
                            if target_language:
                                # Traduction immédiatement après saisie
                                translation = translate_text(section_text, target_language)
                                st.subheader(f"Traduction en {target_language}")
                                st.text_area(f"Traduction de '{section_choice_for_treatment}'", translation, height=200)
                                st.download_button("Télécharger la traduction", translation, file_name=f"traduction_{section_choice_for_treatment}.txt")

                        elif processing_type == "Chatbot":
                            st.subheader(f"Chatbot pour la section : {section_choice_for_treatment}")

                            # Initialiser l'historique de conversation si ce n'est pas déjà fait
                            if "conversation_history" not in st.session_state:
                                st.session_state.conversation_history = [
                                    {"role": "system", "content": f"Vous êtes un assistant capable de répondre à des questions basées uniquement sur la section suivante : {section_text}"}
                                ]

                            # Afficher la conversation en cours
                            if st.session_state.conversation_history:
                                conversation_display = ""
                                for message in st.session_state.conversation_history:
                                    if message['role'] == 'user':
                                        conversation_display += f"**Utilisateur** : {message['content']}\n\n"
                                    elif message['role'] == 'assistant':
                                        conversation_display += f"**Assistant** : {message['content']}\n\n"

                                st.markdown(conversation_display)

                            # Saisie de la question de l'utilisateur
                            user_question = st.text_input("Posez une question :", key="chatbot_question")

                            # Si une question est posée, envoyer la question au chatbot et obtenir la réponse
                            if user_question:
                                answer, st.session_state.conversation_history = ask_question(st.session_state.conversation_history, user_question)
                                st.success(f"Assistant : {answer}")
                                
                            # Option pour effacer l'historique de la conversation
                            if st.button("Clear Chat"):
                                st.session_state.conversation_history = [
                                    {"role": "system", "content": f"Vous êtes un assistant capable de répondre à des questions basées uniquement sur la section suivante : {section_text}"}
                                ]
                                st.success("Historique du chat effacé.")

                            # Option pour télécharger toute la conversation sous forme de fichier .txt
                            if st.session_state.conversation_history:
                                conversation_text = ""
                                for message in st.session_state.conversation_history:
                                    if message['role'] == 'user':
                                        conversation_text += f"Utilisateur : {message['content']}\n"
                                    elif message['role'] == 'assistant':
                                        conversation_text += f"Assistant : {message['content']}\n"

                                st.download_button("Télécharger la conversation", conversation_text, file_name="chatbot.txt")

            except wikipedia.exceptions.DisambiguationError as e:
                st.error(f"Erreur de désambiguïsation. Options disponibles : {e.options}")
            except wikipedia.exceptions.PageError:
                st.error(f"La page '{page_name}' n'existe pas.")
        else:
            st.error("L'URL fournie n'est pas valide ou ne contient pas de titre de page.")
