import streamlit as st
import os
import subprocess
import uuid
import openai
from dotenv import load_dotenv
import re


st.sidebar.title("🔑 OpenAI API Key")

if "user_api_key" not in st.session_state:
    st.session_state.user_api_key = ""

st.sidebar.text_input("Enter your OpenAI API Key", type="password", key="user_api_key")

if not st.session_state.user_api_key:
    st.warning("Please enter your OpenAI API key to use the app.")
    st.stop()



# Load .env file for API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Directory to save files
DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Session state initialization
if "detected_language" not in st.session_state:
    st.session_state.detected_language = None
if 'transcription_text' not in st.session_state:
    st.session_state.transcription_text = ""
if 'current_audio_file' not in st.session_state:
    st.session_state.current_audio_file = ""
if 'user_translation' not in st.session_state:
    st.session_state.user_translation = {}
if 'display_text' not in st.session_state:
    st.session_state.display_text = ""
if 'flashcards' not in st.session_state:
    st.session_state.flashcards = []

def transcribe_audio(audio_path):
    """Transcribe the given audio file using OpenAI's Whisper API."""
    openai.api_key = st.session_state.user_api_key  # Set the user’s API key here
    with open(audio_path, "rb") as audio_file:
        try:
            result = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            st.session_state.detected_language = "Unknown"  # API response doesn't return language reliably
            return result.text
        except openai.OpenAIError as e:
            st.error(f"Transcription failed: {e}")
            return ""

def convert_audio_to_wav(input_file):
    """Convert audio file to WAV using ffmpeg subprocess."""
    output_file = input_file.rsplit('.', 1)[0] + '.wav'
    subprocess.run(['ffmpeg', '-y', '-i', input_file, output_file],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_file

def download_youtube_audio(url):
    """Download YouTube audio using yt-dlp."""
    audio_file = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4()}.mp4")
    subprocess.run(['yt-dlp', '-f', 'bestaudio', '-o', audio_file, url],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return audio_file

def save_transcription(text, save_path):
    """Save the transcription text to a file."""
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(text)

def translate_text(text, target_language, detected_language):
    """Translate text using GPT-4o-mini."""
    openai.api_key = st.session_state.user_api_key
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": f"You are a professional translator. The following text is in {detected_language}. Translate it directly into {target_language}, keeping the meaning as accurate and natural as possible."
            },{
                "role": "user",
                "content": text
            }]
        )
        return response.choices[0].message.content.strip()
    except openai.OpenAIError as e:
        return f"(Translation unavailable: {e})"

def split_sentences(text):
    """Split text into sentences by punctuation."""
    return [s.strip() for s in re.split(r'(?<=[。！？\.\!\?])\s*', text) if s.strip()]





# App UI
st.title("🗣️YATTA!\n🈶Your Audio Transcription & Translation App!🔤")

# YouTube URL input
url_input = st.text_input("Enter YouTube Video URL:")

if st.button("Download Audio & Transcribe from YouTube"):
    if url_input:
        try:
            st.write("Starting download and transcription process...")
            audio_file = download_youtube_audio(url_input)
            wav_file = convert_audio_to_wav(audio_file)
            transcription = transcribe_audio(wav_file)

            st.session_state.transcription_text = transcription
            st.session_state.current_audio_file = wav_file
            st.session_state.display_text = "\n".join(split_sentences(transcription))

            st.audio(wav_file, format="audio/wav")
            st.success("Download and transcription complete!")
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please enter a YouTube URL.")

# File uploader for local audio
uploaded_file = st.file_uploader("Or upload an audio file (MP3, WAV, etc.)", type=["mp3", "wav"])

if uploaded_file is not None:
    try:
        file_path = os.path.join(DOWNLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        wav_file = convert_audio_to_wav(file_path)
        transcription = transcribe_audio(wav_file)

        st.session_state.transcription_text = transcription
        st.session_state.current_audio_file = wav_file
        st.session_state.display_text = "\n".join(split_sentences(transcription))

        st.audio(wav_file, format="audio/wav")
        st.success("Upload and transcription complete!")
    except Exception as e:
        st.error(f"Error: {e}")

# Editable transcription text area
if st.session_state.transcription_text:
    st.subheader("📝 Editable Transcription (one sentence per line):")
    edited_text = st.text_area(
        "Edit transcription below:",
        st.session_state.display_text,
        height=300
    )
    st.session_state.display_text = edited_text

    if st.button("Save Transcription to Text File"):
        save_path = os.path.join(DOWNLOAD_DIR, f"transcription_{uuid.uuid4()}.txt")
        save_transcription(edited_text, save_path)
        st.success("Transcription saved!")

        with open(save_path, "r", encoding="utf-8") as f:
            st.download_button(
                label="Download Transcription",
                data=f,
                file_name="transcription.txt",
                mime="text/plain"
            )

    st.subheader("🌐 Translate Sentences:")
    target_language = st.selectbox("Select Language for Translation:", ["Polish", "English", "Spanish", "German", "French"])

    if st.session_state.current_audio_file:
        st.audio(st.session_state.current_audio_file, format="audio/wav")

    sentences = [s for s in edited_text.split("\n") if s.strip()]

    for i, sentence in enumerate(sentences):
        st.markdown(f"**Sentence {i+1}:** {sentence}")

        user_translation = st.text_area("Your translation", height=70, key=f"user_translation_{i}")
        st.session_state.user_translation[sentence] = user_translation

        if user_translation.strip():
            ai_translation = translate_text(sentence, target_language, st.session_state.detected_language)
            st.markdown(f"**AI Translation:** {ai_translation}")

            # Create a temporary variable to store user selection
            correct = st.selectbox(
                "Is the AI translation correct?",
                options=["", "Yes", "No"],
                key=f"correct_{i}",
                index=1 if st.session_state.get(f"correct_{i}", "") == "Yes" else 0
            )

            if correct == "Yes":
                st.write("✅ Great!")
                if sentence in [fc["text"] for fc in st.session_state.flashcards]:
                    st.session_state.flashcards = [
                        fc for fc in st.session_state.flashcards if fc["text"] != sentence
                    ]
            elif correct == "No":
                st.write("❌ Added to Flashcards for later practice.")
                if sentence not in [fc["text"] for fc in st.session_state.flashcards]:
                    st.session_state.flashcards.append({"id": i, "text": sentence})

# Flashcards in sidebar
with st.sidebar:
    st.header("📝 Flashcards")

    if st.session_state.flashcards:
        # Loop over dicts of form {"id":…, "text":…}
        for flashcard in st.session_state.flashcards:
            fid = flashcard["id"]
            txt = flashcard["text"]

            st.markdown(f"**Practice:** {txt}")

            user_flash_translation = st.text_area(
                "Your translation",
                key=f"flash_translation_{fid}"
            )

            if user_flash_translation.strip():
                # Pass the string txt, not the dict
                ai_flash_translation = translate_text(
                    txt,
                    target_language,
                    st.session_state.detected_language
                )
                st.markdown(f"**AI Translation:** {ai_flash_translation}")

                # Use selectbox with a blank default so nothing is chosen initially
                choice = st.selectbox(
                    "Is your translation correct?",
                    ["", "Yes", "No"],
                    key=f"correct_{fid}",
                    index=1 if st.session_state.get(f"correct_{fid}", "") == "Yes" else 0
                )

                if choice == "Yes":
                    st.success("✅ Well done — removing from flashcards.")
                    st.session_state.flashcards = [
                        fc for fc in st.session_state.flashcards if fc["id"] != fid
                    ]
                    

    else:
        st.write("No sentences in flashcards. Keep translating!")
