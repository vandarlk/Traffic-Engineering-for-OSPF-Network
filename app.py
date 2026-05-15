import streamlit as st
import pandas as pd
import plotly.express as px
import os
import networkx as nx
import matplotlib.pyplot as plt
import io

# Import algorithm engine 
# Ensure optimize.py returns: mlu, cost, changes, opt_w, status
from optimize import load_network_with_orig_weights, run_master_model

# --- 1. Page Configuration and Global Styles ---
st.set_page_config(page_title="OSPF Optimization Platform", layout="wide")
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #4CA1AF; color: white; font-weight: bold; }
    .stProgress .st-bo { background-color: #4CA1AF; }
    </style>
    """, unsafe_allow_html=True)

# Global Visualization Styles
GLOBAL_LABEL_BOX = dict(facecolor='white', alpha=0.85, edgecolor='none', boxstyle='round,pad=0.2')
NODE_STYLE = {"node_color": "#2C3E50", "node_size": 650, "edgecolors": "white", "linewidths": 1.5}
TEXT_STYLE = {"font_size": 9, "font_color": "white", "font_weight": "bold"}

st.title("OSPF Traffic Engineering: Optimization and Visualization Platform")

topo_dir = "data/topologies"
if not os.path.exists(topo_dir):
    os.makedirs(topo_dir, exist_ok=True)

# Initialize Session State
if 'df_results' not in st.session_state: st.session_state.df_results = None
if 'weight_cache' not in st.session_state: st.session_state.weight_cache = {}

# --- 2. Core Logic: Generate Evaluation Report ---
def generate_detailed_report(df_results):
    report_data = []
    for topo in df_results["Topology"].unique():
        topo_df = df_results[df_results["Topology"] == topo]
        base_row = topo_df[topo_df["mode_key"] == "baseline"]
        if base_row.empty: continue
        
        b_mlu = base_row.iloc[0]["MLU (%)"]
        b_cost = base_row.iloc[0]["Total Cost"]
        
        for _, row in topo_df.iterrows():
            mlu_gain_abs = b_mlu - row["MLU (%)"]
            mlu_gain_pct = (mlu_gain_abs / b_mlu * 100) if b_mlu != 0 else 0
            cost_gain_pct = ((b_cost - row["Total Cost"]) / b_cost * 100) if b_cost != 0 else 0
            roi = mlu_gain_abs / row["Changes"] if row["Changes"] > 0 else (mlu_gain_abs if row["mode_key"] != "baseline" else 0)
            
            report_data.append({
                "Network Topology": topo,
                "Optimization Model": row["Model"],
                "Initial MLU (%)": f"{b_mlu}%",
                "Optimized MLU (%)": f"{row['MLU (%)']}%",
                "Congestion Reduction (%)": f"{round(mlu_gain_pct, 2)}%",
                "Initial Cost": b_cost,
                "Optimized Cost": row["Total Cost"],
                "Bandwidth Savings (%)": f"{round(cost_gain_pct, 2)}%",
                "Weight Changes": row["Changes"],
                "ROI (Drop/Link)": f"{round(roi, 2)}%",
                "Solver Status": row["Status"]
            })
    return pd.DataFrame(report_data)

# --- 3. Sidebar Configuration ---
with st.sidebar:
    st.header("Topology Management")
    uploaded_file = st.file_uploader("Upload Topology (.graphml)", type=['graphml'])
    if uploaded_file:
        with open(os.path.join(topo_dir, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("File uploaded successfully")
    
    st.divider()
    available_maps = [f.replace(".graphml", "") for f in os.listdir(topo_dir) if f.endswith('.graphml')]
    model_options = {
        'baseline': 'Model 0 (Baseline)',
        'min_mlu': 'Model A (Min MLU)',
        'min_cost': 'Model B (Min Cost)',
        'sla_threshold': 'Model C (SLA Threshold)',
        'min_changes': 'Model D (Min Changes)'
    }

# --- 4. Main Tabs ---
tab1, tab2, tab3 = st.tabs(["Results Analysis & ROI", "Weight Editor", "Reliability Verification"])

# --- TAB 1: Comparative Analysis ---
with tab1:
    st.subheader("Batch Optimization Experiments")
    c_cfg1, c_cfg2 = st.columns(2)
    sel_maps = c_cfg1.multiselect("Select Topologies", available_maps, key="t1_maps")
    sel_modes = c_cfg2.multiselect("Select Models (Include Baseline)", options=list(model_options.keys()), format_func=lambda x: model_options[x], key="t1_modes")
    
    if st.button("Run Batch Experiments", type="primary"):
        if not sel_maps or not sel_modes:
            st.warning("Please select topologies and models.")
        else:
            all_res = []
            prog = st.progress(0)
            total = len(sel_maps) * len(sel_modes)
            count = 0
            for topo in sel_maps:
                nodes, edges, demands, dests, W_orig = load_network_with_orig_weights(topo)
                for mode in sel_modes:
                    count += 1
                    prog.progress(count / total)
                    mlu, cost, chg, opt_w, status = run_master_model(nodes, edges, demands, dests, W_orig, topo, mode)
                    if mlu is not None:
                        all_res.append({
                            "Topology": topo, "Model": model_options[mode], "mode_key": mode,
                            "MLU (%)": round(mlu*100, 2), "Total Cost": round(cost, 2), "Changes": chg, "Status": status
                        })
                        st.session_state.weight_cache[f"{topo}_{mode}"] = opt_w
            st.session_state.df_results = pd.DataFrame(all_res)

    if st.session_state.df_results is not None:
        df = st.session_state.df_results
        
        st.divider()
        st.subheader("Optimization Gains and ROI Evaluation Report")
        report_df = generate_detailed_report(df)
        if not report_df.empty:
            st.dataframe(report_df, use_container_width=True, hide_index=True)
            csv_data = report_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("Download Full Report (CSV)", data=csv_data, file_name='ospf_optimization_report.csv', mime='text/csv')

        c1, c2, c3 = st.columns(3)
        with c1: st.plotly_chart(px.bar(df, x="Topology", y="MLU (%)", color="Model", barmode="group", text_auto=True, title="MLU Comparison"), use_container_width=True)
        with c2: st.plotly_chart(px.bar(df, x="Topology", y="Changes", color="Model", barmode="group", text_auto=True, title="Configuration Changes"), use_container_width=True)
        with c3: st.plotly_chart(px.bar(df, x="Topology", y="Total Cost", color="Model", barmode="group", text_auto=True, title="Total Cost"), use_container_width=True)

        st.divider()
        st.subheader("Topology Mirror Comparison")
        vc1, vc2 = st.columns(2)
        v_topo = vc1.selectbox("Select Topology", df["Topology"].unique(), key="v_t")
        available_v_modes = df[df["Topology"]==v_topo]["mode_key"].unique()
        v_mode_key = vc2.selectbox("Select Model", available_v_modes, format_func=lambda x: model_options[x], key="v_m")
        
        ckey = f"{v_topo}_{v_mode_key}"
        if ckey in st.session_state.weight_cache:
            opt_w = st.session_state.weight_cache[ckey]
            _, _, _, _, W_orig = load_network_with_orig_weights(v_topo)
            G = nx.read_graphml(os.path.join(topo_dir, f"{v_topo}.graphml"))
            pos = nx.spring_layout(G, seed=42, k=2.5)
            cl, cr = st.columns(2)
            with cl:
                st.write("**Baseline State**")
                fig_l, ax_l = plt.subplots(figsize=(10, 8))
                nx.draw(G, pos, ax=ax_l, with_labels=True, width=1.5, edge_color="#BDC3C7", **NODE_STYLE, **TEXT_STYLE)
                nx.draw_networkx_edge_labels(G, pos, edge_labels=W_orig, font_color='red', font_size=8, bbox=GLOBAL_LABEL_BOX)
                st.pyplot(fig_l)
            with cr:
                st.write(f"**Optimized State ({model_options[v_mode_key]})**")
                fig_r, ax_r = plt.subplots(figsize=(10, 8))
                nx.draw(G, pos, ax=ax_r, with_labels=True, width=1.5, edge_color="#BDC3C7", **NODE_STYLE, **TEXT_STYLE)
                nx.draw_networkx_edge_labels(G, pos, edge_labels=opt_w, font_color='#2980B9', font_size=8, font_weight='bold', bbox=GLOBAL_LABEL_BOX)
                st.pyplot(fig_r)
                
                d1, d2 = st.columns(2)
                buf_img = io.BytesIO()
                fig_r.savefig(buf_img, format="png", bbox_inches='tight', dpi=300)
                d1.download_button("Download PNG", data=buf_img.getvalue(), file_name=f"{v_topo}_{v_mode_key}.png")
                
                G_out = G.copy()
                for (u, v), wv in opt_w.items(): G_out[u][v]['weight'] = int(wv)
                nx.write_graphml(G_out, "temp_opt.graphml")
                with open("temp_opt.graphml", "rb") as f:
                    d2.download_button("Download GraphML", data=f, file_name=f"{v_topo}_{v_mode_key}_opt.graphml")

# --- TAB 2: Weight Editor ---
with tab2:
    st.header("Manual Weight Configuration")
    if available_maps:
        edit_target = st.selectbox("Select Network", available_maps, key="ed_file")
        path_ed = os.path.join(topo_dir, f"{edit_target}.graphml")
        G_ed = nx.read_graphml(path_ed)
        col_g, col_e = st.columns([1.2, 1])
        with col_g:
            pos_ed = nx.spring_layout(G_ed, seed=42, k=3.5)
            fig_ed, ax_ed = plt.subplots(figsize=(10, 8))
            nx.draw(G_ed, pos_ed, ax=ax_ed, with_labels=True, **NODE_STYLE, **TEXT_STYLE)
            nx.draw_networkx_edge_labels(G_ed, pos_ed, edge_labels={(u, v): d.get('weight', 10) for u, v, d in G_ed.edges(data=True)}, font_color='red', font_size=8, bbox=GLOBAL_LABEL_BOX)
            st.pyplot(fig_ed)
        with col_e:
            df_ed = pd.DataFrame([{"Node A": u, "Node B": v, "Current Weight": int(d.get('weight', 10))} for u, v, d in G_ed.edges(data=True)])
            new_df = st.data_editor(df_ed, use_container_width=True, hide_index=True)
            if st.button("Save Modifications"):
                for _, row in new_df.iterrows(): G_ed[row["Node A"]][row["Node B"]]['weight'] = row["Current Weight"]
                nx.write_graphml(G_ed, path_ed)
                st.success("Modifications saved successfully")
                st.rerun()

# --- TAB 3: Reliability ---
with tab3:
    st.subheader("Critical Service Reliability and Disjoint Path Analysis")
    if available_maps:
        s_topo_name = st.selectbox("Select Target Topology", available_maps, key="s_t_box")
        ns, es, ds, dts, Ws = load_network_with_orig_weights(s_topo_name)
        cs1, cs2 = st.columns(2)
        sn, dn = cs1.selectbox("Source Node", ns, index=0), cs2.selectbox("Destination Node", ns, index=len(ns)-1)
        
        if st.button("Run Reliability Optimization", type="primary"):
            mlu, cost, chg, opt_w, status = run_master_model(ns, es, ds, dts, Ws, s_topo_name, 'disjoint_paths', special_pair=(sn, dn))
            
            if mlu:
                st.info(f"Status: {status} | Final MLU: {round(mlu*100, 2)}%")
                
                G_s = nx.read_graphml(os.path.join(topo_dir, f"{s_topo_name}.graphml"))
                pos_s = nx.spring_layout(G_s, seed=42, k=2.5)
                
                col_l, col_r = st.columns(2)
                with col_l:
                    st.write("**Baseline State**")
                    fig_sl, ax_sl = plt.subplots(figsize=(10, 8))
                    nx.draw(G_s, pos_s, ax=ax_sl, with_labels=True, **NODE_STYLE, **TEXT_STYLE)
                    nx.draw_networkx_edge_labels(G_s, pos_s, edge_labels=Ws, font_color='red', font_size=8, bbox=GLOBAL_LABEL_BOX)
                    st.pyplot(fig_sl)
                with col_r:
                    st.write("**Optimized Disjoint Path State**")
                    fig_sr, ax_sr = plt.subplots(figsize=(10, 8))
                    nx.draw(G_s, pos_s, ax=ax_sr, with_labels=True, **NODE_STYLE, **TEXT_STYLE)
                    nx.draw_networkx_edge_labels(G_s, pos_s, edge_labels=opt_w, font_color='#2980B9', font_size=8, font_weight='bold', bbox=GLOBAL_LABEL_BOX)
                    st.pyplot(fig_sr)
            else:
                st.error("Optimization failed: No physically disjoint paths available for this pair.")