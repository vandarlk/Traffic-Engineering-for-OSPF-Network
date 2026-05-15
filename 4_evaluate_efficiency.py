import os
import json

def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "results_db.json")
    if not os.path.exists(json_path):
        print(f" 找不到数据文件 {json_path}，请先运行 2_optimize.py")
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze_efficiency(db):
    print("\n" + "="*110)
    print(" 【核心成果挖掘：多维度优化效率 (ROI) 深度对比分析】 ")
    print("="*110)
    
    modes = ['min_mlu', 'min_cost', 'sla_threshold', 'min_changes']
    mode_names = ['模型 A (纯降拥堵)', '模型 B (纯降代价)', '模型 C (SLA及格线)', '模型 D (最少修改)']
    
    for topo, results in db.items():
        # 获取基准线数据 (作为分母)
        baseline = results.get('baseline')
        if not baseline or baseline[0] is None:
            print(f" 拓扑 {topo} 缺少有效的基线数据(Baseline)，跳过分析。")
            continue
            
        base_mlu, base_cost, _ = baseline
        
        print(f"\n 拓扑地图: {topo} (灾难基线: MLU = {base_mlu:.4f}, 总代价 = {base_cost:.0f})")
        print("-" * 110)
        print(f"{'优化模型':<20} | {'降拥堵效率 (MLU Drop)':<22} | {'带宽节省率 (Cost Saved)':<22} | {'运维性价比 (MLU降幅/修改次数)'}")
        print("-" * 110)
        
        for idx, mode in enumerate(modes):
            res = results.get(mode)
            if res and res[0] is not None:
                mlu, cost, changes = res
                
                # 1. 降拥堵效率: (基准 - 当前) / 基准
                mlu_improvement = (base_mlu - mlu) / base_mlu * 100
                
                # 2. 带宽节省率: (基准 - 当前) / 基准
                cost_savings = (base_cost - cost) / base_cost * 100
                
                # 3. 运维性价比: 绝对下降量 / 修改次数 (为了防止除以0，如果是0次修改，我们视为完美性价比，给予极大值)
                abs_mlu_drop = base_mlu - mlu
                if changes == 0:
                    roi_changes = " 无损完美优化 (0改动)"
                else:
                    # 每改动一条边，换来多少绝对 MLU 下降
                    roi = (abs_mlu_drop / changes) * 100 
                    roi_changes = f"{roi:.2f}% MLU下降/条"
                
                # 格式化输出 (带有正负号和颜色提示)
                mlu_str = f"↓ {mlu_improvement:.2f}%" if mlu_improvement > 0 else f"↑ {abs(mlu_improvement):.2f}% (恶化)"
                cost_str = f"↓ {cost_savings:.2f}%" if cost_savings > 0 else f"↑ {abs(cost_savings):.2f}% (溢价)"
                
                print(f"{mode_names[idx]:<20} | {mlu_str:<22} | {cost_str:<22} | {roi_changes}")
        print("-" * 110)

