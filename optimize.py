import os
import networkx as nx
import json
import gurobipy as gp
from gurobipy import GRB
import sys

def load_network_with_orig_weights(base_name):
    """
    加载网络拓扑和需求数据
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data")
    graphml_path = os.path.join(data_dir, "topologies", f"{base_name}.graphml")
    json_path = os.path.join(data_dir, "demands", f"{base_name}_demand.json")
    
    if not os.path.exists(graphml_path) or not os.path.exists(json_path):
        return None, None, None, None, None
        
    G = nx.read_graphml(graphml_path)
    nodes = list(G.nodes())
    edges = {}
    W_orig = {}
    
    for u, v, data in G.edges(data=True):
        cap = float(data.get('capacity', 1000))
        orig_w = int(data.get('weight', 10)) 
        edges[(u, v)] = cap
        edges[(v, u)] = cap
        W_orig[(u, v)] = orig_w
        W_orig[(v, u)] = orig_w
            
    demands = {}
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        for item in json_data:
            demands[(item["src"], item["dst"])] = item["demand"]
            
    return nodes, edges, demands, list(set([d for s, d in demands.keys()])), W_orig

def run_master_model(nodes, edges, demands, destinations, W_orig, network_name, mode, special_pair=None):
    """
    Gurobi 核心求解引擎 - 支持保留当前最优解逻辑
    """
    w_max, M_dist, M_flow = 20, 10000, 10000
    m = gp.Model(f"OSPF_{mode}_{network_name}")
    
    # --- 性能与近似解参数配置 ---
    m.setParam('OutputFlag', 0)
    m.setParam('TimeLimit', 100)      # 时间上限 100s
    m.setParam('MIPGap', 0.05)        # 允许 5% 的误差，大幅缩短寻找“最完美”解的时间
    m.setParam('Heuristics', 0.5)     # 投入 50% 的精力运行启发式算法，更快拿到初步可行解

    # 动态扩展目的地列表，确保包含 special_pair 的终点
    actual_destinations = list(destinations)
    if special_pair and special_pair[1] not in actual_destinations:
        actual_destinations.append(special_pair[1])

    # 变量定义
    w = m.addVars(edges.keys(), vtype=GRB.INTEGER, lb=1, ub=w_max, name="w")
    delta = m.addVars(edges.keys(), actual_destinations, vtype=GRB.BINARY, name="delta")
    dist = m.addVars(nodes, actual_destinations, lb=0, name="dist")
    f = m.addVars(edges.keys(), actual_destinations, lb=0, name="flow")
    theta = m.addVar(lb=0, ub=1.0, vtype=GRB.CONTINUOUS, name="theta")

    total_cost = gp.quicksum(f[u, v, k] for u, v in edges.keys() for k in actual_destinations)

    # 重要节点不相交路径变量
    if mode == 'disjoint_paths' and special_pair:
        src_s, dst_s = special_pair
        p1 = m.addVars(edges.keys(), vtype=GRB.BINARY, name="p1")
        p2 = m.addVars(edges.keys(), vtype=GRB.BINARY, name="p2")

    # --- 模型逻辑分支 ---
    if mode == 'baseline':
        m.setObjective(theta, GRB.MINIMIZE)
        for u, v in edges.keys():
            m.addConstr(w[u, v] == W_orig[u, v]) 

    elif mode == 'min_mlu':
        m.setObjective(theta, GRB.MINIMIZE)
            
    elif mode == 'min_cost':
        m.setObjective(total_cost, GRB.MINIMIZE)
            
    elif mode == 'sla_threshold':
        T_sla, M_penalty = 0.80, 100000 
        slack = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="slack")
        m.addConstr(theta - T_sla <= slack)
        m.setObjective(total_cost + M_penalty * slack, GRB.MINIMIZE)
            
    elif mode == 'min_changes':
        z = m.addVars(edges.keys(), vtype=GRB.BINARY, name="z")
        beta = 0.02 
        for u, v in edges.keys():
            m.addConstr(w[u, v] - W_orig[u, v] <= w_max * z[u, v])
            m.addConstr(W_orig[u, v] - w[u, v] <= w_max * z[u, v])
        m.setObjective(theta + beta * gp.quicksum(z[u, v] for u, v in edges.keys()), GRB.MINIMIZE)

    elif mode == 'disjoint_paths' and special_pair:
        src_s, dst_s = special_pair
        m.setObjective(theta, GRB.MINIMIZE)
        # 1. 链路不相交
        for u, v in edges.keys():
            m.addConstr(p1[u, v] + p2[u, v] + p1[v, u] + p2[v, u] <= 1)
        # 2. 流守恒
        for u in nodes:
            o1 = gp.quicksum(p1[u, v] for v in nodes if (u, v) in edges)
            i1 = gp.quicksum(p1[v, u] for v in nodes if (v, u) in edges)
            o2 = gp.quicksum(p2[u, v] for v in nodes if (u, v) in edges)
            i2 = gp.quicksum(p2[v, u] for v in nodes if (v, u) in edges)
            if u == src_s:
                m.addConstr(o1 - i1 == 1); m.addConstr(o2 - i2 == 1)
            elif u == dst_s:
                m.addConstr(o1 - i1 == -1); m.addConstr(o2 - i2 == -1)
            else:
                m.addConstr(o1 - i1 == 0); m.addConstr(o2 - i2 == 0)
        # 3. 约束 p1/p2 必须是 SPF 边
        for u, v in edges.keys():
            m.addConstr(p1[u, v] <= delta[u, v, dst_s])
            m.addConstr(p2[u, v] <= delta[u, v, dst_s])

    # --- 物理网络通用约束 ---
    for k in actual_destinations:
        m.addConstr(dist[k, k] == 0)
        for u, v in edges.keys():
            m.addConstr(dist[u, k] <= dist[v, k] + w[u, v])
            m.addConstr(dist[v, k] + w[u, v] - dist[u, k] <= M_dist * (1 - delta[u, v, k]))
            m.addConstr(dist[v, k] + w[u, v] - dist[u, k] >= 1 - M_dist * delta[u, v, k])

    for k in actual_destinations:
        for u in nodes:
            if u == k: continue
            flow_out = gp.quicksum(f[u, v, k] for v in nodes if (u, v) in edges.keys())
            flow_in = gp.quicksum(f[v, u, k] for v in nodes if (v, u) in edges.keys())
            m.addConstr(flow_out - flow_in == demands.get((u, k), 0))
            for v in [v for v in nodes if (u, v) in edges.keys()]:
                m.addConstr(f[u, v, k] <= M_flow * delta[u, v, k])
    
    for u, v in edges.keys():
        m.addConstr(gp.quicksum(f[u, v, k] for k in actual_destinations) <= edges[u, v] * theta)

    m.optimize()

    # --- 结果提取与状态返回 ---
    if (m.status in [GRB.OPTIMAL, GRB.TIME_LIMIT]) and (m.SolCount > 0):
        # 核心逻辑：区分最优解和当前解
        status_msg = "BEST" if m.status == GRB.OPTIMAL else "Curent Best (SAVE)"
        
        actual_mlu, actual_cost, changed_links = 0, 0, 0
        opt_weights = {}
        for u, v in edges.keys():
            opt_weights[(u, v)] = int(round(w[u, v].X))
            load = sum(f[u, v, k].X for k in actual_destinations)
            actual_cost += load
            if load / edges[u, v] > actual_mlu:
                actual_mlu = load / edges[u, v]
            if abs(w[u, v].X - W_orig[u, v]) > 0.5:
                changed_links += 1
        
        return actual_mlu, actual_cost, changed_links, opt_weights, status_msg
    else:
        return None, None, None, None, "无可行解"