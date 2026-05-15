import os
import networkx as nx
import random
import json

def generate_and_save_demands():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 精准导航到 data 目录下的两个子文件夹
    data_dir = os.path.join(current_dir, "data")
    topo_dir = os.path.join(data_dir, "topologies")
    demand_dir = os.path.join(data_dir, "demands")
    
    # 自动创建 demands 文件夹（如果没有的话）
    if not os.path.exists(demand_dir):
        os.makedirs(demand_dir)

    # 检查 topologies 文件夹是否存在
    if not os.path.exists(topo_dir):
        print(f" 错误：找不到 {topo_dir} 文件夹，请确认路径并放入 .graphml 地图！")
        return

    # 遍历 topologies 文件夹下的所有地图
    for file_name in os.listdir(topo_dir):
        if not file_name.endswith('.graphml'):
            continue
            
        file_path = os.path.join(topo_dir, file_name)
        print(f"\n 正在处理网络图: {file_name}")
        
        G = nx.read_graphml(file_path)
        nodes = list(G.nodes())
        
        random.seed(42) 
        demands_list = []
        num_demands = max(3, len(nodes) // 2)
        generated_pairs = set()
        
        for _ in range(num_demands):
            src = random.choice(nodes)
            dst = random.choice(nodes)
            if src != dst and (src, dst) not in generated_pairs:
                demand_value = random.randint(50, 200)
                demands_list.append({"src": src, "dst": dst, "demand": demand_value})
                generated_pairs.add((src, dst))
                
        # 保存到 data/demands/ 文件夹
        base_name = os.path.splitext(file_name)[0]
        json_file_path = os.path.join(demand_dir, f"{base_name}_demand.json")
        
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(demands_list, f, indent=4)
            
        print(f" 已保存需求矩阵: {base_name}_demand.json")

if __name__ == "__main__":
    generate_and_save_demands()