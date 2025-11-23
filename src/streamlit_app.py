"""
ClimateGPT Streamlit UI - Interactive Climate Data Q&A with EDGAR Dataset
"""
import streamlit as st
import subprocess
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="ClimateGPT",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .header-container {
        text-align: center;
        padding-bottom: 2rem;
        border-bottom: 2px solid #00d4ff;
        margin-bottom: 2rem;
    }
    .header-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #00d4ff;
        margin-bottom: 0.5rem;
    }
    .header-subtitle {
        font-size: 1.1rem;
        color: #666;
    }
    .question-section {
        background-color: #f0f2f6;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .answer-section {
        background-color: #fff;
        padding: 2rem;
        border-radius: 10px;
        border-left: 4px solid #00d4ff;
        margin-top: 2rem;
    }
    .loading-spinner {
        text-align: center;
        padding: 2rem;
    }
    .success-message {
        color: #00d4ff;
        font-weight: bold;
    }
    .error-message {
        color: #ff4444;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="header-container">
        <div class="header-title">🌍 ClimateGPT</div>
        <div class="header-subtitle">Ask questions about emissions data from EDGAR v2024 Dataset</div>
    </div>
""", unsafe_allow_html=True)

# Sidebar for information
with st.sidebar:
    st.markdown("### 📊 About ClimateGPT")
    st.markdown("""
    ClimateGPT is an AI-powered assistant that answers questions about:
    - **Emissions data** from the EDGAR v2024 dataset
    - **Climate science** fundamentals
    - **Policy frameworks** and climate goals
    - **Regional and sectoral** emissions analysis

    **Personas Available:**
    - 🎯 **No Persona** (Default) - Neutral, data-focused
    - 📋 **Climate Analyst** - Policy & mitigation focus
    - 🔬 **Research Scientist** - Methodology & rigor focus
    - 💰 **Financial Analyst** - Risk & financial focus
    - 🎓 **Student** - Educational & simple explanations
    """)
    st.markdown("---")
    st.markdown("### 📈 Data Sources")
    st.markdown("""
    - **EDGAR v2024** - Emissions Database
    - Quality Score: 85-97.74% (Tier 1 Research Ready)
    - Coverage: 1970-2024
    - Sectors: Transport, Power, Waste, Agriculture, Buildings, Industrial
    """)

# Main content area
st.markdown('<div class="question-section">', unsafe_allow_html=True)

# Question input
question = st.text_area(
    "📝 Ask a question about climate and emissions:",
    placeholder="e.g., 'What were Germany's power emissions in 2023?' or 'Compare India and China emissions in 2020'",
    height=100,
    key="question_input"
)

# Persona selector
col1, col2 = st.columns([1, 1])

with col1:
    persona = st.selectbox(
        "🎭 Select Persona (Optional):",
        [
            "No Persona",
            "Climate Analyst",
            "Research Scientist",
            "Financial Analyst",
            "Student"
        ],
        index=0,
        help="Choose a persona to tailor the response style"
    )

with col2:
    show_details = st.checkbox(
        "Show Debug Info",
        value=False,
        help="Display classification, tool calls, and intermediate results"
    )

st.markdown('</div>', unsafe_allow_html=True)

# Submit button
submit_button = st.button(
    "🚀 Ask ClimateGPT",
    type="primary",
    use_container_width=True,
    key="submit_button"
)

# Process question
if submit_button:
    if not question.strip():
        st.error("❌ Please enter a question first!")
    else:
        st.markdown('<div class="answer-section">', unsafe_allow_html=True)

        # Show loading spinner
        with st.spinner("🔄 Processing your question..."):
            try:
                # Build command
                cmd = ["python", "run_llm.py", question]

                # Add persona if not "No Persona"
                if persona != "No Persona":
                    cmd.extend(["--persona", persona])

                # Add verbose flag if debug info requested
                if show_details:
                    cmd.append("--verbose")

                # Change to the correct directory
                os.chdir(Path(__file__).parent)

                # Run the query
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                output = result.stdout + result.stderr

                # Check for subprocess errors first
                if result.returncode != 0:
                    # Check for specific error patterns
                    if "504" in output or "Gateway Time-out" in output or "timed out" in output.lower():
                        st.error("❌ The external AI service is currently slow or unavailable. Please try again in a moment or with a simpler question.")
                        if show_details:
                            st.warning("**Technical Details:**")
                            st.code(output[-500:] if len(output) > 500 else output, language="text")
                    elif "KeyError" in output or "AttributeError" in output:
                        st.error("❌ Error processing question. The system may not understand this type of query.")
                        if show_details:
                            st.warning("**Technical Details:**")
                            st.code(output[-500:] if len(output) > 500 else output, language="text")
                    else:
                        st.error("❌ Failed to process question. Please check the debug info below.")
                        if show_details:
                            st.warning("**Technical Details:**")
                            st.code(output[-500:] if len(output) > 500 else output, language="text")
                else:
                    # Parse output sections
                    answer_start = output.find("=== ANSWER ===")
                    tool_call_start = output.find("--- TOOL CALL ---")
                    tool_result_start = output.find("--- TOOL RESULT")
                    classification_start = output.find("[CLASSIFICATION]")

                    # Extract sections
                    if answer_start != -1:
                        answer_text = output[answer_start + len("=== ANSWER ==="):].strip()
                        # Clean up the answer by removing [COMPLETE] message
                        if "[COMPLETE]" in answer_text:
                            answer_text = answer_text[:answer_text.find("[COMPLETE]")].strip()

                        st.markdown("### ✨ Answer")
                        st.markdown(answer_text)
                        st.success("✓ Response generated successfully")
                    else:
                        # The process succeeded but we couldn't find the answer marker
                        st.warning("⚠️ Question processed but response format unexpected. This may happen with very complex queries.")
                        # Show the raw output for inspection
                        st.info("**Raw Output (last 800 characters):**")
                        st.code(output[-800:] if len(output) > 800 else output, language="text")

                    # Show debug information if requested
                    if show_details:
                        st.markdown("---")
                        st.markdown("### 🔍 Debug Information")

                        # Classification
                        if classification_start != -1:
                            classification_section = output[classification_start:classification_start + 200]
                            st.code(classification_section, language="text")

                        # Tool call
                        if tool_call_start != -1:
                            tool_call_end = output.find("\n", tool_call_start + 50)
                            if tool_call_end == -1:
                                tool_call_end = tool_call_start + 500
                            tool_call_text = output[tool_call_start:tool_call_end]
                            st.markdown("**Tool Call:**")
                            try:
                                # Try to parse and format as JSON
                                json_start = tool_call_text.find("{")
                                json_end = tool_call_text.rfind("}") + 1
                                if json_start != -1 and json_end > json_start:
                                    json_str = tool_call_text[json_start:json_end]
                                    json_obj = json.loads(json_str)
                                    st.json(json_obj)
                                else:
                                    st.code(tool_call_text, language="json")
                            except:
                                st.code(tool_call_text, language="text")

                        # Tool result
                        if tool_result_start != -1:
                            result_section = output[tool_result_start:tool_result_start + 1000]
                            st.markdown("**Tool Result (first 1000 chars):**")
                            st.code(result_section, language="json")

                # Show persona info
                st.markdown("---")
                st.markdown("### 🎭 Response Configuration")
                col_persona, col_debug = st.columns(2)
                with col_persona:
                    st.write(f"**Persona:** {persona if persona != 'No Persona' else 'Neutral (No specific persona)'}")
                with col_debug:
                    st.write(f"**Debug Info:** {'Enabled' if show_details else 'Disabled'}")

            except subprocess.TimeoutExpired:
                st.error("❌ Request timed out (>120 seconds). Please try a simpler question or check if the MCP server is running.")
            except FileNotFoundError:
                st.error("❌ Could not find run_llm.py. Make sure you're running Streamlit from the src/ directory of the ClimateGPT project.")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                st.code(str(e), language="text")

        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #999; font-size: 0.9rem;">
        <p>ClimateGPT © 2025 | Powered by EDGAR v2024 Emissions Database</p>
        <p>Data Quality: Tier 1 - Research Ready | Confidence: HIGH</p>
    </div>
""", unsafe_allow_html=True)

# Session state for persistence (optional)
if "last_question" not in st.session_state:
    st.session_state.last_question = ""
if "last_persona" not in st.session_state:
    st.session_state.last_persona = "No Persona"
