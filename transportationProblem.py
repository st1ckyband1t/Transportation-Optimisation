import gurobipy as gp
from gurobipy import GRB

def solve_multicommodity_flow(nodes, edges, travel_demand, distances, with_ferry=False):
    model = gp.Model("MultiCommodityTransportationPlanning")
    
    #commoditifying traffic from each origin node
    commodities = {
        'O1': {'origin': '1', 'destinations': ['2', '3', '4', '5', '6', '7']},
        'O4': {'origin': '4', 'destinations': ['1', '2', '3', '5', '6', '7']},
        'O5': {'origin': '5', 'destinations': ['1', '2', '3', '4', '6', '7']}
    }
    
    #introducing parameters for the ferry arc between node 2 and 6
    if with_ferry:
        ferry_distance = 0 #was not exactly sure what to add as the distance between  2 and 6 but kept it as zero since effectively no driving is happening hence no pollution
        distances[('2', '6')] = ferry_distance
        distances[('6', '2')] = ferry_distance
        edges.append(('2', '6'))
        edges.append(('6', '2'))
    
    #introducing the flow varables
    flow = {}
    for commodity, details in commodities.items():
        for (i, j) in edges:
            flow[commodity, i, j] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, 
                                                 name=f'flow_{commodity}_{i}_{j}')#flow from i to j for particular commodity
    
    #objective functions: minimize the total distance travelled 
    model.setObjective(
        gp.quicksum(flow[commodity, i, j] * distances.get((i, j), 0) 
                    for commodity, details in commodities.items() 
                    for (i, j) in edges 
                    if (i, j) in distances),
        GRB.MINIMIZE
    )
    
    #flow constraints
    for commodity, details in commodities.items():
        origin = details['origin']
        for node in nodes:
            #balancing inward and outward flow at each node conserving flow
            flow_in = gp.quicksum(flow[commodity, i, node] 
                                  for i in nodes if (i, node) in edges)
            flow_out = gp.quicksum(flow[commodity, node, j] 
                                   for j in nodes if (node, j) in edges)
            
            if node == origin:
                #traffic from origin nodes can be considered as the demand in the scenario
                model.addConstr(
                    flow_out - flow_in == 
                    gp.quicksum(travel_demand.get((origin, dest), 0) 
                                for dest in details['destinations']),
                    f'flow_conservation_{commodity}_{node}'
                )
            elif node in details['destinations']:
                model.addConstr(
                    flow_in - flow_out == 
                    travel_demand.get((origin, node), 0),
                    f'flow_conservation_{commodity}_{node}'
                )
            else:
                #conserving flow at intermediate nodes
                model.addConstr(
                    flow_in == flow_out, 
                    f'flow_conservation_{commodity}_{node}'
                )
    
    #constraints for the ferry
    if with_ferry:
        #code did not work accurately until i added a constraint of less than or equal to 2000 in both directions
        model.addConstr(
            gp.quicksum(flow[commodity, '2', '6'] 
                        for commodity in commodities.keys()) <= 2000,
            'ferry_2_to_6_capacity_constraint'
        )
        model.addConstr(
            gp.quicksum(flow[commodity, '6', '2'] 
                        for commodity in commodities.keys()) <= 2000,
            'ferry_6_to_2_capacity_constraint'
        )
    
    
    model.optimize()
    
    #calculating total distance travelled without the ferry
    if model.status == GRB.OPTIMAL:
        total_distance = model.objVal
        print(f"{'With Ferry' if with_ferry else 'Without Ferry'}:")
        print(f"Total Driving Distance: {total_distance:.2f} kilometres")
        
        #edge flows for each edge, we iterate through each edge in this for loop
        print("\nEdge Flows:")
        for (i, j) in edges:
            edge_flows = {}
            for commodity in commodities.keys():
                flow_value = flow[commodity, i, j].x
                if flow_value > 1e-6:
                    edge_flows[commodity] = flow_value
            
            if edge_flows:
                edge_total_flow = sum(edge_flows.values())
                print(f"Edge {i} -> {j}:")
                print(f"  Total Flow: {edge_total_flow:.2f}")
                for commodity, value in edge_flows.items():
                    print(f"    {commodity}: {value:.2f}")
        
        #adding in the ferry arc
        if with_ferry:
            print("\nFerry Usage:")
            ferry_2_to_6_flows = {}
            ferry_6_to_2_flows = {}
            
            for commodity in commodities.keys():
                flow_2_to_6 = flow[commodity, '2', '6'].x
                flow_6_to_2 = flow[commodity, '6', '2'].x
                
                if flow_2_to_6 > 1e-6:
                    ferry_2_to_6_flows[commodity] = flow_2_to_6
                if flow_6_to_2 > 1e-6:
                    ferry_6_to_2_flows[commodity] = flow_6_to_2
            
            print("2 -> 6 Ferry Flows:")
            total_2_to_6_flow = 0
            for commodity, value in ferry_2_to_6_flows.items():
                print(f"  {commodity}: {value:.2f}")
                total_2_to_6_flow += value
            print(f"Total 2 -> 6 Flow: {total_2_to_6_flow:.2f}")
            
            print("\n6 -> 2 Ferry Flows:")
            total_6_to_2_flow = 0
            for commodity, value in ferry_6_to_2_flows.items():
                print(f"  {commodity}: {value:.2f}")
                total_6_to_2_flow += value
            print(f"Total 6 -> 2 Flow: {total_6_to_2_flow:.2f}")
        
        return total_distance
    else:
        print("No optimal solution available")
        return None

#defining all our parameters
nodes = ['1', '2', '3', '4', '5', '6', '7']
edges = [('1', '2'), ('2', '1'), ('2', '3'), ('3', '4'), ('3', '2'), 
         ('4', '5'), ('4', '3'), ('5', '6'), ('5', '4'), 
         ('6', '7'), ('6', '5'), ('7', '6')]
travel_demand = {
    ('1', '2'): 900, ('1', '3'): 750, ('1', '4'): 40, 
    ('1', '5'): 10, ('1', '6'): 600, ('1', '7'): 550,
    ('4', '5'): 150, ('4', '6'): 1400, ('4', '7'): 1250, 
    ('4', '1'): 100, ('4', '2'): 2000, ('4', '3'): 1100,
    ('5', '6'): 3300, ('5', '7'): 2440, ('5', '4'): 200, 
    ('5', '1'): 110, ('5', '2'): 4000, ('5', '3'): 2200
}
distances = {
    ('1', '2'): 3.5, ('2', '1'): 3.5, 
    ('2', '3'): 3.0, ('3', '2'): 3.0, 
    ('3', '4'): 5.0, ('4', '3'): 5.0, 
    ('4', '5'): 25.0, ('5', '4'): 25.0, 
    ('5', '6'): 4.0, ('6', '5'): 4.0, 
    ('6', '7'): 2.5, ('7', '6'): 2.5
}


print("Scenario 1: Without Ferry")
distance_without_ferry = solve_multicommodity_flow(
    nodes.copy(), 
    edges.copy(), 
    travel_demand.copy(), 
    distances.copy(), 
    with_ferry=False
)

print("\nScenario 2: With Ferry")
distance_with_ferry = solve_multicommodity_flow(
    nodes.copy(), 
    edges.copy(), 
    travel_demand.copy(), 
    distances.copy(), 
    with_ferry=True
)

#logic to calculate total reduced distance
if distance_without_ferry is not None and distance_with_ferry is not None:
    distance_reduction = distance_without_ferry - distance_with_ferry
    percent_reduction = (distance_reduction / distance_without_ferry) * 100
    
    print(f"\nDistance Reduction: {distance_reduction:.2f} kilometres")
    print(f"Percentage Reduction: {percent_reduction:.2f}%")

    """""
    Scenario 1: Without Ferry
Restricted license - for non-production use only - expires 2026-11-23
Gurobi Optimizer version 12.0.0 build v12.0.0rc1 (mac64[arm] - Darwin 23.0.0 23A344)

CPU model: Apple M2
Thread count: 8 physical cores, 8 logical processors, using up to 8 threads

Optimize a model with 21 rows, 36 columns and 72 nonzeros
Model fingerprint: 0x06ae462d
Coefficient statistics:
  Matrix range     [1e+00, 1e+00]
  Objective range  [2e+00, 2e+01]
  Bounds range     [0e+00, 0e+00]
  RHS range        [1e+01, 1e+04]
Presolve removed 21 rows and 36 columns
Presolve time: 0.00s
Presolve: All rows and columns removed
Iteration    Objective       Primal Inf.    Dual Inf.      Time
       0    3.9925000e+05   0.000000e+00   0.000000e+00      0s

Solved in 0 iterations and 0.01 seconds (0.00 work units)
Optimal objective  3.992500000e+05
Without Ferry:
Total Driving Distance: 399250.00 kilometres

Edge Flows:
Edge 1 -> 2:
  Total Flow: 2850.00
    O1: 2850.00
Edge 2 -> 1:
  Total Flow: 210.00
    O4: 100.00
    O5: 110.00
Edge 2 -> 3:
  Total Flow: 1950.00
    O1: 1950.00
Edge 3 -> 4:
  Total Flow: 1200.00
    O1: 1200.00
Edge 3 -> 2:
  Total Flow: 6210.00
    O4: 2100.00
    O5: 4110.00
Edge 4 -> 5:
  Total Flow: 3960.00
    O1: 1160.00
    O4: 2800.00
Edge 4 -> 3:
  Total Flow: 9510.00
    O4: 3200.00
    O5: 6310.00
Edge 5 -> 6:
  Total Flow: 9540.00
    O1: 1150.00
    O4: 2650.00
    O5: 5740.00
Edge 5 -> 4:
  Total Flow: 6510.00
    O5: 6510.00
Edge 6 -> 7:
  Total Flow: 4240.00
    O1: 550.00
    O4: 1250.00
    O5: 2440.00

Scenario 2: With Ferry
Gurobi Optimizer version 12.0.0 build v12.0.0rc1 (mac64[arm] - Darwin 23.0.0 23A344)

CPU model: Apple M2
Thread count: 8 physical cores, 8 logical processors, using up to 8 threads

Optimize a model with 23 rows, 42 columns and 90 nonzeros
Model fingerprint: 0x27c2aba4
Coefficient statistics:
  Matrix range     [1e+00, 1e+00]
  Objective range  [2e+00, 2e+01]
  Bounds range     [0e+00, 0e+00]
  RHS range        [1e+01, 1e+04]
Presolve removed 10 rows and 20 columns
Presolve time: 0.00s
Presolved: 13 rows, 22 columns, 50 nonzeros

Iteration    Objective       Primal Inf.    Dual Inf.      Time
       0    5.9810000e+04   9.063750e+03   0.000000e+00      0s
       8    2.8077000e+05   0.000000e+00   0.000000e+00      0s

Solved in 8 iterations and 0.00 seconds (0.00 work units)
Optimal objective  2.807700000e+05
With Ferry:
Total Driving Distance: 280770.00 kilometres

Edge Flows:
Edge 1 -> 2:
  Total Flow: 2850.00
    O1: 2850.00
Edge 2 -> 1:
  Total Flow: 210.00
    O4: 100.00
    O5: 110.00
Edge 2 -> 3:
  Total Flow: 790.00
    O1: 790.00
Edge 3 -> 4:
  Total Flow: 40.00
    O1: 40.00
Edge 3 -> 2:
  Total Flow: 5050.00
    O4: 2940.00
    O5: 2110.00
Edge 4 -> 5:
  Total Flow: 1960.00
    O4: 1960.00
Edge 4 -> 3:
  Total Flow: 8350.00
    O4: 4040.00
    O5: 4310.00
Edge 5 -> 6:
  Total Flow: 9550.00
    O4: 1810.00
    O5: 7740.00
Edge 5 -> 4:
  Total Flow: 4510.00
    O5: 4510.00
Edge 6 -> 7:
  Total Flow: 4240.00
    O1: 550.00
    O4: 1250.00
    O5: 2440.00
Edge 6 -> 5:
  Total Flow: 10.00
    O1: 10.00
Edge 2 -> 6:
  Total Flow: 2000.00
    O1: 1160.00
    O4: 840.00
Edge 6 -> 2:
  Total Flow: 2000.00
    O5: 2000.00

Ferry Usage:
2 -> 6 Ferry Flows:
  O1: 1160.00
  O4: 840.00
Total 2 -> 6 Flow: 2000.00

6 -> 2 Ferry Flows:
  O5: 2000.00
Total 6 -> 2 Flow: 2000.00

Distance Reduction: 118480.00 kilometres
Percentage Reduction: 29.68%


The traffic originating from different nodes have to be considered as separate commodities since if we dont do that, we cant really model the 
solution currently. This is because even if we can consider every vehicle as a singular unit in the flow, the trips themselves are unique. Hence we
have to consider traffic from each origin node as a different commodity. However, these commodities are not completely independent since they all will share the same 
ferry. 

"""