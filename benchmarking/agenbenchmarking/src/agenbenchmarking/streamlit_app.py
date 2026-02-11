import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
import os

# Set Page Config
st.set_page_config(page_title="AI Agent Analytics", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

raw_data = load_data('assets/results.json')

if raw_data is None:
    st.error("❌ 'data.json' not found.")
    st.stop()

# --- DATA PROCESSING ---
conv_rows = []
turn_rows = []

for idx, item in enumerate(raw_data):
    conv = item.get('conversation', [])
    verdict = item.get('final_verdict', {})
    tags = item.get('tags', {})
    
    start_lat = conv[0]['time'] if conv else 0
    end_lat = conv[-1]['time'] if conv else 0
    score = verdict.get('final_score', 0)
    
    conv_rows.append({
        "conv_id": idx,
        "start_latency": start_lat,
        "end_latency": end_lat,
        "final_score": score,
        "course": tags.get('course', 'Unknown'),
        "scope": tags.get('scope', 'Unknown'),
        "length": tags.get('length', 'Short'),
        "language": tags.get('language', 'Unknown')
    })
    
    for i, turn in enumerate(conv):
        turn_rows.append({
            "turn_no": i + 1,
            "latency": turn.get('time', 0),
            "length": tags.get('length', 'Short')
        })

df = pd.DataFrame(conv_rows)
df_turns = pd.DataFrame(turn_rows)

# --- UI ---
st.title("📊 AI Agent Performance Dashboard")

# Section 1: KPI Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Avg Start Latency", f"{df['start_latency'].mean():.1f} ms")
kpi2.metric("Avg End Latency", f"{df['end_latency'].mean():.1f} ms")
kpi3.metric("Avg Final Score", f"{df['final_score'].mean():.2f}")
kpi4.metric("Critical Failures (<0.2)", len(df[df['final_score'] < 0.2]))

st.divider()

# Section 2: Latency Progression
st.subheader("Latency Progression by Turn Number")
# We group by length and turn_no to ensure we see the difference between Short and Long
prog_df = df_turns.groupby(['length', 'turn_no'])['latency'].mean().reset_index()

fig_prog = go.Figure()
colors = {'Short': '#636EFA', 'Long': '#EF553B'}

for length_cat in ['Short', 'Long']:
    subset = prog_df[prog_df['length'] == length_cat]
    if not subset.empty:
        # Bars
        fig_prog.add_trace(go.Bar(
            x=subset['turn_no'], y=subset['latency'],
            name=f"Avg Latency ({length_cat})", opacity=0.4, marker_color=colors.get(length_cat)
        ))
        # Line
        fig_prog.add_trace(go.Scatter(
            x=subset['turn_no'], y=subset['latency'],
            mode='lines+markers', name=f"Trend ({length_cat})",
            line=dict(color=colors.get(length_cat), width=3)
        ))

fig_prog.update_layout(xaxis_title="Turn Position", yaxis_title="Time (ms)", barmode='group', height=450)
st.plotly_chart(fig_prog, use_container_width=True)

st.divider()

# Section 3: The 4-Graph Tag Grid
st.subheader("Tag Performance Matrix")

# Common function for the bar charts
def get_tag_chart(tag_column, title):
    data = df.groupby(tag_column)['final_score'].mean().sort_values().reset_index()
    fig = px.bar(
        data, x='final_score', y=tag_column, 
        orientation='h', title=title,
        color='final_score', color_continuous_scale='RdYlGn',
        range_x=[0, 1]
    )
    fig.update_layout(showlegend=False, height=350, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# Row 1
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(get_tag_chart('course', "Avg Score by Course"), use_container_width=True)
with col2:
    st.plotly_chart(get_tag_chart('scope', "Avg Score by Scope"), use_container_width=True)

# Row 2
col3, col4 = st.columns(2)
with col3:
    st.plotly_chart(get_tag_chart('length', "Avg Score by Length"), use_container_width=True)
with col4:
    st.plotly_chart(get_tag_chart('language', "Avg Score by Language"), use_container_width=True)

if st.checkbox("Show Raw Flattened Data"):
    st.dataframe(df)