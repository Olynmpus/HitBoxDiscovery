# Author Jorge Mejia, 2025
# HitBoxDiscovery.py
import streamlit as st
import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt
import os

# Function to clean JSON text
def clean_json(json_text):
    json_text = json_text.encode('utf-8').decode('utf-8')  # Ensure UTF-8 encoding
    json_text = json_text.replace('\ufeff', '')  # Remove BOM if present
    return json.loads(json_text)

# Function to extract Audiometry and HIT probe data
def parse_json(json_data):
    if 'Sessions' not in json_data or not json_data['Sessions']:
        st.error("Invalid JSON: Missing 'Sessions'")
        return None, None

    session_count = len(json_data['Sessions'])
    audiometry = None
    hit_data = None
    
    # Extract session data dynamically based on available data
    for session in json_data['Sessions']:
        if 'DataSets' in session:
            data_set = session['DataSets'][0] if isinstance(session['DataSets'], list) else session['DataSets']
            data = data_set.get('Data', {}).get('Collection', [])
            
            if any('Earside' in item for item in data):
                audiometry = data  # This is the audiometry session
            elif any('Points' in item for item in data):
                hit_data = data  # This is the HIT Probe session
    
    return audiometry, hit_data

# Streamlit UI
st.title("MedRx HitBox Data Viewer")
st.write("Upload JSON files to analyze and visualize audiometry & hearing instrument test data.")

uploaded_files = st.file_uploader("Upload JSON files", type="json", accept_multiple_files=True)

targets_file = st.file_uploader("Upload Targets File", type=["xlsx"])

# Load reference Targets
@st.cache_data
def load_targets(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        targets_df = pd.read_excel(uploaded_file, usecols=[0, 4, 5, 6])
        return targets_df.to_numpy()
    except Exception as e:
        st.error(f"❌ Error loading targets file: {e}")
        return None

nl3_targets = None
if targets_file is not None:
    nl3_targets = load_targets(targets_file)
    if nl3_targets is not None:
        st.success("Prescription Targets loaded successfully!")

if uploaded_files:
    legends = {}
    data_store = []
    
    for file in uploaded_files:
        file_name = file.name
        legends[file_name] = st.text_input(f"Legend for {file_name}", value=file_name.split('.')[0])
        
        json_text = file.read().decode('utf-8')
        json_data = clean_json(json_text)
        audiometry, hit_data = parse_json(json_data)
        
        data_store.append((file_name, legends[file_name], audiometry, hit_data))
    
    # Plot Audiometry Data only if audiometry session exists
    if any(aud is not None for _, _, aud, _ in data_store):
        st.subheader("Audiometric Data")
        fig, ax = plt.subplots()
        for _, legend, audiometry, _ in data_store:
            if audiometry:
                freq, levels_right, levels_left = [], [], []
                for item in audiometry:
                    if 'Earside' in item and 'Collection' in item:
                        for point in item['Collection']:
                            freq.append(point['Frequency'])
                            if item['Earside'] == 'Right':
                                levels_right.append(point['Level'])
                            else:
                                levels_left.append(point['Level'])
                
                # Ensure x (freq) and y (levels) match in length
                min_length = min(len(freq), len(levels_right), len(levels_left))
                freq = freq[:min_length]
                levels_right = levels_right[:min_length]
                levels_left = levels_left[:min_length]
                
                if min_length > 0:
                    ax.semilogx(freq, levels_right, 'o-', label=f"{legend} - Right Ear")
                    ax.semilogx(freq, levels_left, 'o-', label=f"{legend} - Left Ear")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Hearing Level (dB HL)")
        ax.set_title("Audiometric Thresholds")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)
    
    # Plot HIT Probe Data if available
    if any(hit is not None for _, _, _, hit in data_store):
        st.subheader("HIT Probe Input-Output Curves")
        for rem_index in range(3):  # Ensure three REM measures are plotted separately
            fig, ax = plt.subplots()
            for _, legend, _, hit_data in data_store:
                if hit_data:
                    hit_freqs, input_levels, output_levels = [], [], []
                    for item in hit_data:
                        points = item.get('Points', [])
                        freq_list, input_list, output_list = [], [], []
                        for point in points:
                            freq_list.append(point['Frequency'])
                            input_list.append(point['Input'])
                            output_list.append(point['Output'])
                        hit_freqs.append(freq_list)
                        input_levels.append(input_list)
                        output_levels.append(output_list)
                    if rem_index < len(hit_freqs):
                        ax.semilogx(hit_freqs[rem_index], np.array(output_levels[rem_index]) - np.array(input_levels[rem_index]), '*-', label=f"{legend} - REM {rem_index+1}")
            if nl3_targets is not None:
                ax.semilogx(nl3_targets[:, 0], nl3_targets[:, rem_index+1], 'k*-', label=f"Prescription Targets - REM {rem_index+1}")
            ax.set_xlabel("Frequency (Hz)")
            ax.set_ylabel("Insertion Gain (dB)")
            ax.set_title(f"HIT Probe Curves - REM {rem_index+1}")
            ax.grid(True)
            ax.legend()
            st.pyplot(fig)
