import streamlit as st
import requests
import json
import tempfile
import os

# Page configuration
st.set_page_config(
    page_title="Audio Analysis Dashboard",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS to achieve the requested layout and styling
st.markdown("""
    <style>
    /* General layout and font */
    .main {
        padding: 2rem;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Base card style */
    .card {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 0.75rem;
        border: 1px solid #e8e8e8;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        height: 100%; /* Ensures columns have same height */
    }
    
    /* Metric styling inside cards */
    .card .label {
        font-size: 1rem;
        font-weight: 500;
        color: #525252;
        text-align: center;
    }
    .card .value {
        font-size: 2.5rem;
        font-weight: 600;
        line-height: 1.2;
        text-align: center;
    }
    .card .delta {
        font-size: 0.875rem;
        font-weight: 500;
        color: #64748b;
        text-align: center;
    }
    
    /* Sentiment-specific colors */
    .positive { color: #22c55e; } /* Green */
    .neutral { color: #f59e0b; }  /* Amber */
    .negative { color: #ef4444; } /* Red */
    
    /* Divider inside the keywords card */
    .card hr {
        border: none;
        border-top: 1px solid #e8e8e8;
        margin: 1.5rem 0;
    }

    /* Keywords tags container */
    .keywords-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        justify-content: center; /* Center the tags */
    }
    .keyword-tag {
        background-color: #eef2ff;
        color: #4338ca;
        padding: 0.4rem 0.9rem;
        border-radius: 1rem;
        font-weight: 500;
        font-size: 0.9rem;
    }

    /* Speaker transcription box */
    .speaker-text {
        background-color: #f8fafc;
        padding: 1.25rem;
        border-radius: 0.5rem;
        border-left: 5px solid #6366f1;
        margin: 1rem 0;
    }

    /* Summary box */
    .summary-box {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.75rem;
        border: 1px solid #e8e8e8;
    }

    /* Section headers with icons */
    h2 {
        font-size: 1.75rem;
        color: #334155;
        margin-top: 2.5rem;
        margin-bottom: 1.5rem;
        padding-bottom: 0.75rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

# --- UI LAYOUT ---

# Header
st.title("🎙️ Audio Analysis Dashboard")
st.markdown("Upload an audio file to get transcription, sentiment analysis, and keyword extraction.")
st.markdown("---")

# File upload section
uploaded_file = st.file_uploader(
    "Choose an audio file",
    type=['mp3', 'wav', 'ogg', 'm4a', 'flac'],
    help="Supported formats: MP3, WAV, OGG, M4A, FLAC"
)

# API URL
api_url = "http://localhost:8000/get-metadata-audio-file"

# Process button
if uploaded_file is not None:
    if st.button("🔍 Analyze Audio", type="primary", use_container_width=True):
        st.session_state.analysis_result = None
        with st.spinner("Processing audio file... This may take a moment."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                headers = {"Content-Type": "application/json"}
                data = {"audio-url": tmp_file_path}
                response = requests.post(api_url, headers=headers, json=data)
                
                os.unlink(tmp_file_path)
                
                if response.status_code == 200:
                    st.session_state.analysis_result = response.json()
                    st.success("✅ Analysis completed successfully!")
                else:
                    st.error(f"❌ API Error: Received status code {response.status_code}")
                    st.code(f"Response: {response.text}", language="text")
                    
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Connection Error: Could not connect to the API. Details: {e}")
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {e}")

# --- RESULTS DISPLAY ---

if st.session_state.analysis_result:
    result = st.session_state.analysis_result
    
    if result.get('success'):
        
        # Two-column layout for Overview and Keywords
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("## 📊 Analysis Overview")
            
            # Sentiment Card
            sentiment_score = result.get('sentiment', {}).get('score', 0)
            if sentiment_score > 0.6:
                sentiment_label = "Positive"
                sentiment_color = "positive"
            elif sentiment_score < 0.4:
                sentiment_label = "Negative"
                sentiment_color = "negative"
            else:
                sentiment_label = "Neutral"
                sentiment_color = "neutral"

            st.markdown(f"""
                <div class="card">
                    <div class="label">Overall Sentiment</div>
                    <div class="value {sentiment_color}">{sentiment_label}</div>
                    <div class="delta">Score: {sentiment_score:.2f}</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("## 🔑 Keywords")
            keywords = result.get('keywords', [])
            num_keywords = len(keywords)

            # Combined Keywords Card
            keywords_html = f"""
            <div class="card">
                <div class="label">Keywords Identified</div>
                <div class="value">{num_keywords}</div>
                <div class="delta">Key topics from the audio</div>
                <hr>
            """
            
            if keywords:
                tags_html = "".join([f'<div class="keyword-tag">{kw}</div>' for kw in keywords])
                keywords_html += f'<div class="keywords-container">{tags_html}</div>'
            else:
                keywords_html += "<p style='text-align: center; color: #64748b;'>No keywords were extracted.</p>"

            keywords_html += "</div>" # Close card div
            st.markdown(keywords_html, unsafe_allow_html=True)

        # --- Full-width sections below ---
        st.markdown("<br>", unsafe_allow_html=True) # Add some space
        
        # Transcriptions section
        st.markdown("## 📝 Transcription")
        transcriptions = result.get('transcriptions', [])
        if transcriptions:
            for trans in transcriptions:
                speaker = trans.get('speaker', 'Unknown')
                text = trans.get('text', '')
                st.markdown(f"""
                    <div class="speaker-text">
                        <strong>🗣️ Speaker {speaker}:</strong>
                        <p style="margin-top: 0.5rem; font-size: 1.1rem; color: #334155;">{text}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No transcription is available for this audio.")
        
        # Summary section
        st.markdown("## 📋 Summary")
        summary = result.get('summary', 'No summary available.')
        st.markdown(f'<div class="summary-box"><p style="font-size: 1.1rem; line-height: 1.6; margin: 0;">{summary}</p></div>', unsafe_allow_html=True)
        
    else:
        st.error("❌ Analysis failed. The API returned a non-successful response.")
        st.json(result)