import os
import json
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体与超清画质
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False  
plt.rcParams['figure.dpi'] = 300            

#  加入了第 5 种颜色：灰色的 Baseline
MODE_COLORS = {
    'baseline': '#8D99AE',      # 灰色：模型 0 (未经优化的烂摊子)
    'min_mlu': '#EF476F',       # 红色：模型 A
    'min_cost': '#118AB2',      # 蓝色：模型 B
    'sla_threshold': '#FFD166', # 黄色：模型 C
    'min_changes': '#06D6A0'    # 绿色：模型 D (你的王牌)
}

MODE_LABELS = {
    'baseline': '模型 0 (原始基准线)',
    'min_mlu': '模型 A (纯降拥堵)',
    'min_cost': '模型 B (纯降代价)',
    'sla_threshold': '模型 C (SLA 及格线)',
    'min_changes': '模型 D (最少修改)'
}

MODE_SHORT = {
    'baseline': 'Orig',
    'min_mlu': 'A',
    'min_cost': 'B',
    'sla_threshold': 'C',
    'min_changes': 'D'
}

def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "results_db.json")
    if not os.path.exists(json_path):
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def plot_grouped_bars(data, metric_index, title, ylabel, filename):
    topologies = list(data.keys())
    modes = list(MODE_LABELS.keys())
    
    x = np.arange(len(topologies))
    width = 0.15 # 柱子变多，宽度稍微收一点
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for i, mode in enumerate(modes):
        values = [data[topo].get(mode, [0,0,0])[metric_index] for topo in topologies]
        values = [v if v is not None else 0 for v in values]
        offset = (i - len(modes)/2 + 0.5) * width
        ax.bar(x + offset, values, width, label=MODE_LABELS[mode], color=MODE_COLORS[mode], edgecolor='black')

    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(topologies, fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(f"{filename}.png")
    print(f" 成功生成图表: {filename}.png")
    plt.close()

def plot_tradeoff_scatter(data):
    fig, ax = plt.subplots(figsize=(11, 7))
    coord_map = {}
    for topo, results in data.items():
        for mode, metrics in results.items():
            if metrics[0] is not None and metrics[1] is not None:
                mlu, cost = metrics[0], metrics[1]
                key = (round(cost, 1), round(mlu, 4), topo)
                if key not in coord_map:
                    coord_map[key] = []
                coord_map[key].append(mode)

    for (cost, mlu, topo), modes in coord_map.items():
        # 同心圆最大支持 5 层叠放
        sizes = [300, 180, 80, 30, 10] 
        for i, mode in enumerate(modes):
            ax.scatter(cost, mlu, color=MODE_COLORS[mode], s=sizes[i], edgecolors='black', alpha=0.9, zorder=3)
        
        short_modes = [MODE_SHORT[m] for m in modes]
        label = f"{topo} ({','.join(short_modes)})"
        ax.annotate(label, (cost, mlu), xytext=(8, 8), textcoords='offset points', fontsize=9, fontweight='bold')

    for mode, color in MODE_COLORS.items():
        ax.scatter([], [], color=color, s=120, edgecolors='black', label=MODE_LABELS[mode])

    ax.set_xlabel('Total Routing Cost (全网总路由带宽代价)', fontsize=12)
    ax.set_ylabel('Max Link Utilization (最大链路利用率 MLU)', fontsize=12)
    ax.set_title('五大模型性能折中与帕累托前沿分析', fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.5, zorder=0)
    
    ax.legend(loc='upper right', fontsize=10, bbox_to_anchor=(1, 1))
    
    plt.tight_layout()
    plt.savefig("Chart3_Tradeoff_Scatter.png")
    print(" 成功生成图表: Chart3_Tradeoff_Scatter.png")
    plt.close()

if __name__ == "__main__":
    db = load_data()
    if db:
        print(" 开始一键生成五大模型横向对比神图...")
        plot_grouped_bars(db, metric_index=0, title='五大模型 MLU 对比 (模型0为灾难现场)', ylabel='最大链路利用率 MLU', filename='Chart1_MLU_Comparison')
        plot_grouped_bars(db, metric_index=1, title='五大模型总路由代价对比', ylabel='Total Cost (全网带宽消耗)', filename='Chart2_Cost_Comparison')
        plot_grouped_bars(db, metric_index=2, title='五大模型对原始 OSPF 权重的修改次数对比', ylabel='修改的物理链路数量 (条)', filename='Chart4_Changes_Comparison')
        plot_tradeoff_scatter(db)
        print(" 全部 4 张神级图表生成完毕！这次你的心头肉“最小边数模型”王者归来了！")