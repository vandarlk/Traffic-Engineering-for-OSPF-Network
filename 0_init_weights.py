import os
import networkx as nx
import random

def init_random_weights():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    topo_dir = os.path.join(current_dir, "data", "topologies")
    
    if not os.path.exists(topo_dir):
        print(f" 找不到路径: {topo_dir}")
        return

    random.seed(42)  # 固定种子，保证实验可重复
    all_files = [f for f in os.listdir(topo_dir) if f.endswith('.graphml')]
    
    print(" 开始初始化随机权重...")
    for file_name in all_files:
        file_path = os.path.join(topo_dir, file_name)
        
        # 1. 读取地图
        G_raw = nx.read_graphml(file_path)
        
        # 2.  核心修复：如果是多重图，强行转换为普通图 
        if G_raw.is_multigraph():
            if G_raw.is_directed():
                G = nx.DiGraph(G_raw)
            else:
                G = nx.Graph(G_raw)
        else:
            G = G_raw
        
        # 3. 遍历所有的边，赋予随机权重
        processed = set()
        for u, v in list(G.edges()):  # 套一个 list() 防止边遍历边修改报错
            edge_key = tuple(sorted((u, v)))
            if edge_key not in processed:
                w_val = random.randint(1, 20)
                
                # 4.  核心修复：使用新版 NetworkX 推荐的 .edges 属性修改语法
                G.edges[u, v]['weight'] = w_val
                
                # 如果是有向图且存在反向边，一并修改，保证双向对称
                if G.is_directed() and G.has_edge(v, u):
                    G.edges[v, u]['weight'] = w_val
                    
                processed.add(edge_key)
        
        # 将带有新权重的普通图覆盖保存回原文件
        nx.write_graphml(G, file_path)
        print(f"  ✅ {file_name:<20} | 初始化完成")

if __name__ == "__main__":
    init_random_weights()