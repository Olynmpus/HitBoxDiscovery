# Author Jorge Mejia, 2025
# HitBoxDiscovery.py

import streamlit as st
import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt

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

    # Extract session 1 (Audiometry)
    session1 = json_data['Sessions'][0]
    if 'DataSets' not in session1:
        st.error("Invalid JSON: No DataSets found in Session 1")
        return None, None
    
    audiometry = session1['DataSets'].get('Data', {}).get('Collection', [])
    freq, levels_right, levels_left = [], [], []
    for item in audiometry:
        if 'Earside' in item and 'Collection' in item:
            for point in item['Collection']:
                freq.append(point['Frequency'])
                if item['Earside'] == 'Right':
                    levels_right.append(point['Level'])
                else:
                    levels_left.append(point['Level'])
    
    # Extract session 2 (HIT Probe Curves)
    if len(json_data['Sessions']) < 2:
        st.error("Invalid JSON: No second session found")
        return None, None
    
    session2 = json_data['Sessions'][1]
    hit_data = session2['DataSets'].get('Data', {}).get('Collection', [])
    hit_freq, input_levels, output_levels = [], [], []
    for item in hit_data:
        points = item.get('Points', [])
        for point in points:
            hit_freq.append(point['Frequency'])
            input_levels.append(point['Input'])
            output_levels.append(point['Output'])
    
    return (freq, levels_right, levels_left), (hit_freq, input_levels, output_levels)

# Streamlit UI
st.title("MedRx HitBox Data Viewer")
st.write("Upload JSON files to analyze and visualize audiometry & hearing instrument test data.")

uploaded_files = st.file_uploader("Upload JSON files", type="json", accept_multiple_files=True)

# Load reference Targets
@st.cache_data
def load_targets():
    targets_df = pd.read_excel("Targets.xlsx", usecols=[0, 4, 5, 6])
    return targets_df.to_numpy()

nl3_targets = None
if st.button("Load NL3 Targets"):
    nl3_targets = load_targets()
    st.success("NL3 Targets loaded successfully!")

if uploaded_files:
    legends = {}
    data_store = []
    
    for file in uploaded_files:
        file_name = file.name
        legends[file_name] = st.text_input(f"Legend for {file_name}", value=file_name.split('.')[0])
        
        json_text = file.read().decode('utf-8')
        json_data = clean_json(json_text)
        aud_data, hit_data = parse_json(json_data)
        
        if aud_data and hit_data:
            data_store.append((file_name, legends[file_name], aud_data, hit_data))
    
    # Plot Audiometry Data
    st.subheader("Audiometric Data")
    fig, ax = plt.subplots()
    for _, legend, (freq, levels_right, levels_left), _ in data_store:
        ax.semilogx(freq, levels_right, 'o-', label=f"{legend} - Right Ear")
        ax.semilogx(freq, levels_left, 'o-', label=f"{legend} - Left Ear")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Hearing Level (dB HL)")
    ax.set_title("Audiometric Thresholds")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)
    
    # Plot HIT Probe Data
    st.subheader("HIT Probe Input-Output Curves")
    fig, ax = plt.subplots()
    for _, legend, _, (hit_freq, input_levels, output_levels) in data_store:
        ax.semilogx(hit_freq, np.array(output_levels) - np.array(input_levels), '*-', label=legend)
    
    # Overlay NL3 Targets if loaded
    if nl3_targets is not None:
        ax.semilogx(nl3_targets[:, 0], nl3_targets[:, 1], 'k*-', label="NL3 Targets")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Insertion Gain (dB)")
    ax.set_title("HIT Probe Curves")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

    # Export Data to Excel
    st.subheader("Export Data")
    if st.button("Download Excel File"):
        excel_data = {
            "File Name": [], "Legend": [], "Frequency (Hz)": [], "Right Ear (dB HL)": [], "Left Ear (dB HL)": [],
            "HIT Frequency (Hz)": [], "Input Level (dB)": [], "Output Level (dB)": []
        }
        
        for file_name, legend, (freq, levels_right, levels_left), (hit_freq, input_levels, output_levels) in data_store:
            excel_data["File Name"].extend([file_name] * len(freq))
            excel_data["Legend"].extend([legend] * len(freq))
            excel_data["Frequency (Hz)"].extend(freq)
            excel_data["Right Ear (dB HL)"].extend(levels_right)
            excel_data["Left Ear (dB HL)"].extend(levels_left)
            excel_data["HIT Frequency (Hz)"].extend(hit_freq)
            excel_data["Input Level (dB)"].extend(input_levels)
            excel_data["Output Level (dB)"].extend(output_levels)
        
        df = pd.DataFrame(excel_data)
        excel_filename = "Processed_HitBox_Data.xlsx"
        df.to_excel(excel_filename, index=False)
        
        st.success(f"Data exported successfully as {excel_filename}")
        st.download_button(label="Download Excel", data=df.to_excel(index=False, engine='openpyxl'), file_name=excel_filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
