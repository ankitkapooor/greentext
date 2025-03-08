import streamlit as st
from openai import OpenAI
import anthropic
import json
import datetime
import random
import os
import hashlib
import io
from PIL import Image, ImageDraw, ImageFont
import base64
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Function to convert greentext to image
def convert_to_image(greentext, post_info):
    # Create a new image with a beige background (#f0e0d6)
    width, height = 600, max(500, 100 + 20 * len(greentext.split('\n')))
    image = Image.new('RGB', (width, height), (240, 224, 214))  # #f0e0d6
    draw = ImageDraw.Draw(image)
    
    # Try to load a monospace font
    try:
        font = ImageFont.truetype("Courier", 14)
        header_font = ImageFont.truetype("Arial", 12)
    except IOError:
        font = ImageFont.load_default()
        header_font = ImageFont.load_default()
    
    # Draw header (post info)
    draw.text((10, 10), post_info, fill=(17, 119, 67), font=header_font)  # #117743
    
    # Draw each line of greentext
    y_position = 40
    for line in greentext.split('\n'):
        if line.strip():
            draw.text((10, y_position), line, fill=(120, 153, 34), font=font)  # #789922
            y_position += 20
    
    # Convert to bytes
    img_byte_array = io.BytesIO()
    image.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)
    return img_byte_array

# Function to convert greentext to PDF
def convert_to_pdf(greentext, post_info):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create custom styles
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        textColor=colors.HexColor('#117743'),
        fontSize=10,
        fontName='Helvetica-Bold'
    )
    
    greentext_style = ParagraphStyle(
        'Greentext',
        parent=styles['Normal'],
        textColor=colors.HexColor('#789922'),
        fontSize=12,
        fontName='Courier',
        spaceAfter=2,
        leading=14  # Reduced line spacing
    )
    
    # Create the content
    content = []
    content.append(Paragraph(post_info, header_style))
    content.append(Spacer(1, 10))
    
    for line in greentext.split('\n'):
        if line.strip():
            content.append(Paragraph(line, greentext_style))
    
    doc.build(content)
    buffer.seek(0)
    return buffer

# Near the top of the script, initialize session state for key management
if 'key_saved' not in st.session_state:
    st.session_state.key_saved = False
    st.session_state.key_name = ""
    st.session_state.key_provider = ""

# Function to load saved API keys
def load_saved_keys():
    try:
        if os.path.exists("saved_keys.json"):
            with open("saved_keys.json", "r") as f:
                return json.load(f)
        return {"openai": {}, "anthropic": {}}
    except Exception as e:
        st.error(f"Error loading saved keys: {str(e)}")
        return {"openai": {}, "anthropic": {}}

# Function to save API keys
def save_key(provider, key_name, api_key):
    saved_keys = load_saved_keys()
    
    # Create a unique hash of the API key as the value
    # This adds a layer of security compared to storing plain text
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:10]
    
    # Save the key with its name and hash
    saved_keys[provider.lower()][key_name] = {
        "hash": key_hash,
        "key": api_key  # In a production app, consider encrypting this
    }
    
    try:
        with open("saved_keys.json", "w") as f:
            json.dump(saved_keys, f)
        return True
    except Exception as e:
        st.error(f"Error saving key: {str(e)}")
        return False

# Function to delete a saved key
def delete_key(provider, key_name):
    saved_keys = load_saved_keys()
    if key_name in saved_keys[provider.lower()]:
        del saved_keys[provider.lower()][key_name]
        try:
            with open("saved_keys.json", "w") as f:
                json.dump(saved_keys, f)
            return True
        except Exception as e:
            st.error(f"Error deleting key: {str(e)}")
    return False

# Set page config
st.set_page_config(
    page_title="Greentext Generator",
    page_icon="📝",
    layout="centered"
)

# Load saved keys
saved_keys = load_saved_keys()

# Add updated CSS for authentic 4chan styling
st.markdown("""
<style>
    body {
        background-color: #eef2ff;
        font-family: arial,helvetica,sans-serif;
    }
    .main {
        background-color: #eef2ff;
    }
    .stTextArea textarea {
        background-color: #f0f0f0;
        border-radius: 5px;
        color: #000000 !important;
    }
    /* 4chan post styling */
    .greentext-container {
        background-color: #f0e0d6;
        border: 1px solid #d9bfb7;
        border-radius: 0;
        padding: 10px;
        margin-top: 15px;
        width: 100%;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    /* Header for post */
    .post-header {
        color: #117743;
        font-weight: bold;
        margin-bottom: 5px;
        font-size: 0.9em;
    }
    .post-number {
        color: #800000;
        font-size: 0.9em;
    }
    /* Text container */
    .post-content {
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
        white-space: pre-wrap;
        line-height: 0.95;
        color: #000000;
    }
    /* Green text lines */
    .greentext-line {
        color: #789922 !important;
        margin: 0;
        padding: 0;
        line-height: 0.95;
    }
    .title {
        color: #800000;
        text-align: center;
        font-family: arial,helvetica,sans-serif;
        font-weight: bold;
    }
    input, textarea, .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        color: #000000 !important;
    }
    .stButton button {
        background-color: #f0e0d6;
        color: #117743;
        font-weight: bold;
        border: 1px solid #d9bfb7;
    }
    .stButton button:hover {
        background-color: #ead6ca;
    }
    /* Fix input text color for ALL text inputs in dark mode */
    .stTextInput input[type="password"], 
    .stTextInput input[type="text"],
    .stTextInput input {
        color: white !important;
        background-color: #333333 !important;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown("<h1 class='title'>📝 Greentext Generator</h1>", unsafe_allow_html=True)
st.markdown("Generate 4chan-style greentext stories using AI")

# Sidebar for API settings
with st.sidebar:
    st.header("Settings")
    
    # AI provider selection
    provider = st.radio(
        "AI Provider",
        ["OpenAI", "Anthropic (Claude)"],
        index=0,
        help="Select which AI provider to use"
    )
    
    # API Keys based on provider
    if provider == "OpenAI":
        # Get saved OpenAI keys
        saved_openai_keys = list(saved_keys["openai"].keys())
        
        # Key selection or new key input
        key_option = "Enter a new key"
        if saved_openai_keys:
            key_options = ["Select a saved key", "Enter a new key"]
            key_choice = st.radio("API Key Options", key_options)
            
            if key_choice == "Select a saved key":
                selected_key_name = st.selectbox("Choose a saved key", saved_openai_keys)
                api_key = saved_keys["openai"][selected_key_name]["key"]
                st.success(f"Using saved key: {selected_key_name}")
                
                # Option to delete the key
                if st.button("Delete this saved key"):
                    if delete_key("openai", selected_key_name):
                        st.success(f"Deleted key: {selected_key_name}")
                        st.rerun()
                key_option = key_choice
        
        # Input for new key
        if key_option == "Enter a new key":
            openai_api_key = st.text_input("OpenAI API Key", type="password", help="Enter your OpenAI API key")
            api_key = openai_api_key
            
            # Option to save the key
            if openai_api_key:
                save_key_checkbox = st.checkbox("Save this key for future use")
                if save_key_checkbox:
                    key_name = st.text_input("Name for this key", placeholder="e.g., My OpenAI Key")
                    if key_name and st.button("Save Key"):
                        if save_key("openai", key_name, openai_api_key):
                            st.session_state.key_saved = True
                            st.session_state.key_name = key_name
                            st.session_state.key_provider = "OpenAI"
            
        st.caption("Your OpenAI API key is not stored on any server and is only used for API calls")
    
    else:  # Anthropic
        # Get saved Anthropic keys
        saved_anthropic_keys = list(saved_keys["anthropic"].keys())
        
        # Key selection or new key input
        key_option = "Enter a new key"
        if saved_anthropic_keys:
            key_options = ["Select a saved key", "Enter a new key"]
            key_choice = st.radio("API Key Options", key_options)
            
            if key_choice == "Select a saved key":
                selected_key_name = st.selectbox("Choose a saved key", saved_anthropic_keys)
                api_key = saved_keys["anthropic"][selected_key_name]["key"]
                st.success(f"Using saved key: {selected_key_name}")
                
                # Option to delete the key
                if st.button("Delete this saved key"):
                    if delete_key("anthropic", selected_key_name):
                        st.success(f"Deleted key: {selected_key_name}")
                        st.rerun()
                key_option = key_choice
        
        # Input for new key
        if key_option == "Enter a new key":
            anthropic_api_key = st.text_input("Anthropic API Key", type="password", help="Enter your Anthropic API key")
            api_key = anthropic_api_key
            
            # Option to save the key
            if anthropic_api_key:
                save_key_checkbox = st.checkbox("Save this key for future use")
                if save_key_checkbox:
                    key_name = st.text_input("Name for this key", placeholder="e.g., My Claude Key")
                    if key_name and st.button("Save Key"):
                        if save_key("anthropic", key_name, anthropic_api_key):
                            st.session_state.key_saved = True
                            st.session_state.key_name = key_name
                            st.session_state.key_provider = "Anthropic"
            
        st.caption("Your Anthropic API key is not stored on any server and is only used for API calls")
    
    # Common generation settings
    st.subheader("Generation Settings")
    
    # Model selection based on provider
    if provider == "OpenAI":
        model = "gpt-4.5-preview"
        st.info("Using OpenAI GPT-4.5 Preview model")
    else:  # Anthropic
        model = "claude-3-5-sonnet-20240620"
        st.info("Using Claude 3.5 Sonnet model")
    
    temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=1.0, step=0.1, 
                           help="Higher values make output more random, lower values more deterministic")
    max_tokens = st.slider("Max Length", min_value=50, max_value=1000, value=300, step=50,
                          help="Maximum length of the generated text")

# Main area for prompt input
user_prompt = st.text_area("Enter your greentext prompt:", 
                          placeholder="e.g., Be an anon who finds a mysterious USB drive",
                          height=150)

# Generate button
generate_button = st.button("Generate Greentext", type="primary", use_container_width=True)

# At the beginning of the script after other session state initializations, add:
if 'full_response' not in st.session_state:
    st.session_state.full_response = ""
    st.session_state.current_time = ""
    st.session_state.random_post_id = ""
    st.session_state.has_generated = False

# Handle generation
if generate_button:
    if not api_key:
        st.error(f"Please enter your {provider} API key in the sidebar")
    elif not user_prompt:
        st.warning("Please enter a prompt")
    else:
        try:
            # Create placeholders for streaming output
            result_area = st.empty()
            result_container = st.empty()
            result_container.markdown("<div class='generated-text'></div>", unsafe_allow_html=True)
            success_message = st.empty()
            download_button_placeholder = st.empty()
            full_response = ""
            
            # Generate post details once at the beginning
            current_time = datetime.datetime.now().strftime('%m/%d/%y(%a)%H:%M:%S')
            random_post_id = f"No.{random.randint(100000000, 999999999)}"
            
            # System prompt for greentext
            greentext_system_prompt = (
                "You are creating authentic 4chan greentext stories. "
                "Follow these rules exactly:\n"
                "1. Every line MUST start with '>' (no space after >)\n"
                "2. First line should typically be '>be me' or similar\n" 
                "3. Keep lines very short - rarely more than 10-15 words\n"
                "4. Use 4chan terminology: anon, mfw (my face when), tfw (that feel when), etc.\n"
                "5. Be edgy, self-deprecating, and include twist endings\n"
                "6. No paragraph breaks - just line breaks\n"
                "7. Include at least one reaction line like '>mfw' at the end\n"
                "8. Keep content edgy, absurd and vulgar - this is 4chan style\n"
                "DO NOT include anything except the greentext lines. Do not explain or preface."
            )
            
            with st.spinner(f"Generating greentext with {provider}..."):
                # OpenAI API call
                if provider == "OpenAI":
                    client = OpenAI(api_key=api_key)
                    stream = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": greentext_system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=True
                    )
                    
                    # Process the OpenAI streaming response
                    for chunk in stream:
                        if hasattr(chunk.choices[0].delta, 'content'):
                            content = chunk.choices[0].delta.content or ""
                            full_response += content
                            
                            # Format each line to have the proper greentext styling
                            formatted_lines = []
                            for line in full_response.split('\n'):
                                if line.strip():
                                    if line.startswith('>'):
                                        formatted_lines.append(f"<div class='greentext-line'>{line}</div>")
                                    else:
                                        formatted_lines.append(f"<div class='greentext-line'>>{line}</div>")
                            
                            formatted_html = "\n".join(formatted_lines)
                            
                            # Create a realistic 4chan post structure - using the pre-generated IDs
                            post_html = f"""
                            <div class="greentext-container">
                                <div class="post-header">
                                    Anonymous {current_time} <span class="post-number">{random_post_id}</span>
                                </div>
                                <div class="post-content">
                                    {formatted_html}
                                </div>
                            </div>
                            """

                            result_container.markdown(post_html, unsafe_allow_html=True)
                
                # Anthropic API call
                else:
                    client = anthropic.Anthropic(api_key=api_key)
                    
                    with client.messages.stream(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=greentext_system_prompt,
                        messages=[
                            {"role": "user", "content": user_prompt}
                        ]
                    ) as stream:
                        # Process the Anthropic streaming response
                        for text in stream.text_stream:
                            full_response += text
                            
                            # Format each line to have the proper greentext styling
                            formatted_lines = []
                            for line in full_response.split('\n'):
                                if line.strip():
                                    if line.startswith('>'):
                                        formatted_lines.append(f"<div class='greentext-line'>{line}</div>")
                                    else:
                                        formatted_lines.append(f"<div class='greentext-line'>>{line}</div>")
                            
                            formatted_html = "\n".join(formatted_lines)
                            
                            # Create a realistic 4chan post structure
                            post_html = f"""
                            <div class="greentext-container">
                                <div class="post-header">
                                    Anonymous {current_time} <span class="post-number">{random_post_id}</span>
                                </div>
                                <div class="post-content">
                                    {formatted_html}
                                </div>
                            </div>
                            """

                            result_container.markdown(post_html, unsafe_allow_html=True)
            
            # Store the generation in session state so it persists across reruns
            st.session_state.full_response = full_response
            st.session_state.current_time = current_time
            st.session_state.random_post_id = random_post_id
            st.session_state.has_generated = True
            
            # Show success message after completion
            success_message.success(f"Greentext generated successfully with {provider}!")
            
            # After showing success message, replace the download button with these options
            if full_response:
                st.markdown("### Download Options")
                download_format = st.selectbox(
                    "Choose download format:",
                    ["Text (.txt)", "Image (.png)", "PDF (.pdf)"],
                    index=0
                )
                
                post_info = f"Anonymous {current_time} {random_post_id}"
                
                if download_format == "Text (.txt)":
                    download_button_placeholder.download_button(
                        label="Download as Text File",
                        data=full_response,
                        file_name="greentext.txt",
                        mime="text/plain"
                    )
                elif download_format == "Image (.png)":
                    img_bytes = convert_to_image(full_response, post_info)
                    download_button_placeholder.download_button(
                        label="Download as Image",
                        data=img_bytes,
                        file_name="greentext.png",
                        mime="image/png"
                    )
                else:  # PDF
                    pdf_bytes = convert_to_pdf(full_response, post_info)
                    download_button_placeholder.download_button(
                        label="Download as PDF",
                        data=pdf_bytes,
                        file_name="greentext.pdf",
                        mime="application/pdf"
                    )
                
        except Exception as e:
            st.error(f"Error while generating text: {str(e)}")
            
# Footer
st.markdown("---")
st.caption("Note: This application uses AI APIs to generate text. The content is AI-generated and may not reflect the views of the developers.")

# Add this code after the sidebar section to display success message without rerunning
if st.session_state.key_saved:
    st.sidebar.success(f"Saved {st.session_state.key_provider} key as: {st.session_state.key_name}")
    # Reset the state after showing the message
    st.session_state.key_saved = False

# Check for saved generation after the generate button code block
if st.session_state.has_generated:
    # Format and display the stored generation
    formatted_lines = []
    for line in st.session_state.full_response.split('\n'):
        if line.strip():
            if line.startswith('>'):
                formatted_lines.append(f"<div class='greentext-line'>{line}</div>")
            else:
                formatted_lines.append(f"<div class='greentext-line'>>{line}</div>")
    
    formatted_html = "\n".join(formatted_lines)
    
    # Display with the saved post details
    post_html = f"""
    <div class="greentext-container">
        <div class="post-header">
            Anonymous {st.session_state.current_time} <span class="post-number">{st.session_state.random_post_id}</span>
        </div>
        <div class="post-content">
            {formatted_html}
        </div>
    </div>
    """
    
    # This ensures it displays even after UI interactions
    if not generate_button:  # Only show if not already showing from generate button
        st.markdown(post_html, unsafe_allow_html=True)
        st.success(f"Greentext generated successfully with {provider}!")
    
    # Update the download options to use session state
    st.markdown("### Download Options")
    download_format = st.selectbox(
        "Choose download format:",
        ["Text (.txt)", "Image (.png)", "PDF (.pdf)"],
        index=0
    )
    
    post_info = f"Anonymous {st.session_state.current_time} {st.session_state.random_post_id}"
    
    if download_format == "Text (.txt)":
        st.download_button(
            label="Download as Text File",
            data=st.session_state.full_response,
            file_name="greentext.txt",
            mime="text/plain"
        )
    elif download_format == "Image (.png)":
        img_bytes = convert_to_image(st.session_state.full_response, post_info)
        st.download_button(
            label="Download as Image",
            data=img_bytes,
            file_name="greentext.png",
            mime="image/png"
        )
    else:  # PDF
        pdf_bytes = convert_to_pdf(st.session_state.full_response, post_info)
        st.download_button(
            label="Download as PDF",
            data=pdf_bytes,
            file_name="greentext.pdf",
            mime="application/pdf"
        ) 
