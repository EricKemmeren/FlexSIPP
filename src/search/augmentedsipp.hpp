#pragma once
#include <functional>
#include <unordered_map>
#include <utility>
#include <vector>
#include <boost/heap/d_ary_heap.hpp>
#include "graph.hpp"
#include "repeat.hpp"

namespace asipp{

    inline gam_item_t get_reduced_gamma(const gam_item_t& gamma, NeighboringAgent agent) {
        // Compound recovery time reduces over the path length
        // Check compound recovery time by checking if you meet the agent again in the future
        intervalTime_t gamma_reduction = std::max(gamma.last_recovery - agent.compound_recovery_time, 0.0);

        gam_item_t reduced = reduce(gamma, gamma_reduction);
        reduced.last_recovery = agent.compound_recovery_time;
        return reduced;
    }

    template <typename Node_t>
    bool isGoal(const Node_t& n, const Location& goal_loc){
        return n.node->state.loc == goal_loc;
    }

    template <typename Node_t, typename Open_t>
    std::vector<GraphContainer> backup(const Node_t& n, Open_t& open_list){
        std::vector<GraphContainer> res;
        GraphNode* cur = n.node;
        while(cur != nullptr){
            res.push_back(cur);
			res.push_back(open_list.edge_to_parent[cur]);
            cur = open_list.parent[cur];
        }
        std::reverse(res.begin(), res.end());
        return res;
    }

    template <typename Node_t, typename Open_t>
    inline void extendOpen(const Node_t& cur, Open_t& open_list, MetaData & m, GraphNode * source, GraphNode * destination, EdgeATF edge, gamma_t gamma, GraphEdge * successor) {
        intervalTime_t zeta  = cur.g.zeta;
        intervalTime_t alpha = std::max(cur.g.alpha, edge.alpha - cur.g.delta);
        intervalTime_t beta  = std::min(cur.g.beta,  edge.beta  - cur.g.delta);
        intervalTime_t delta = cur.g.delta + edge.delta;
        std::cerr << "Extend open on edge " << edge << ". Computed parameters: zeta " << zeta << " alpha " << alpha << " beta " << beta << " delta " << delta << std::endl;

        if (cur.g.earliest_arrival_time() > edge.beta) {
            std::cerr << "cur.alpha + cur.delta > edge.beta (cur.g): " << cur.g << " > " << edge.beta << std::endl;
            return;
        }

        gam_item_t gam_after = gamma[edge.agent_after.id];

        // Check how much recovery time is used by checking the next agent visiting the current configuration
        gam_after = get_reduced_gamma(gam_after, edge.agent_after);

        intervalTime_t min_gamma = std::max(gam_after.first, alpha - (edge.beta - cur.g.delta - gam_after.second));
        intervalTime_t duration_available = std::max(static_cast<intervalTime_t>(0.0), beta - alpha);
        intervalTime_t max_gamma = gam_after.second;
        max_gamma = std::min(duration_available + min_gamma, gam_after.second);

        gamma[edge.agent_after.id] = gam_item_t(min_gamma, max_gamma, gam_after.last_recovery, gam_after.incurred_delays);

        EdgeATF arrival_time_function(zeta, alpha, beta, delta, gamma);

        std::cerr << "Created catf " << arrival_time_function << std::endl;

        intervalTime_t eat = arrival_time_function.earliest_arrival_time();
        if (eat > edge.beta) {
            std::cerr << "cur.alpha + cur.delta > edge.beta (EAT): " << eat << " > " << edge.beta << std::endl;
            return;
        }
    
        // Enqueue the destination node 
        if (open_list.handles.contains(MapNode(destination))){
            // If destination in queue, update the arrival time with shorter path
            auto handle = open_list.handles[MapNode(destination)];
            if(arrival_time_function.earliest_arrival_time() < (*handle).g.earliest_arrival_time()){
                m.decreased++;
                double h = edge.heuristic;
                Node_t new_node = open_list.decrease_key(handle, arrival_time_function, h, destination, source, successor);
                std::cerr << "Decreased with better arrival time: " << new_node << std::endl;
            } else if(arrival_time_function.beta > (*handle).g.beta) {
                if (arrival_time_function.earliest_arrival_time() <= (*handle).g.earliest_arrival_time()) {
                    m.decreased++;
                    double h = edge.heuristic;
                    Node_t new_node = open_list.decrease_key(handle, arrival_time_function, h, destination, source, successor);
                    std::cerr << "Decreased with better longer available path: " << new_node << std::endl;
                } else {
                    std::cerr << "Already found destination, but is worse. New: [" << arrival_time_function.zeta << "," << arrival_time_function.alpha << "," << arrival_time_function.beta << "," << arrival_time_function.delta << "]. Existing: [" << (*handle).g.zeta << "," << (*handle).g.alpha << "," << (*handle).g.beta << "," << (*handle).g.delta << "]" << std::endl;
                }
            } else {
            }
        }
        else{
            // Add new destination to the queue
            m.generated++;
            double h = edge.heuristic;
            Node_t new_node = open_list.emplace(arrival_time_function, h, destination, source, successor);
            std::cerr << "Added: " << new_node << std::endl;
        }
    }

    template <typename Node_t, typename Open_t>
    inline void expand(const Node_t& cur, Open_t& open_list, const Location& goal_loc, MetaData & m){
        (void)goal_loc;
        m.expanded++;
        std::cerr << "---------------- new node ----------------"<< std::endl;
        std::cerr << "At node " << *cur.node << ", time " << cur.g.earliest_arrival_time();
        std::cerr << "\n  g: " << cur.g << std::endl;

        for(GraphEdge * successor: cur.node->successors){
            if(open_list.expanded.contains(MapNode(successor->destination))){
                // Already visited location and added all outgoing edges to the queue, thus the new found path to that node is worse
                std::cerr << "Already visited successor location " << successor->destination->state.loc << " with ATF " << *successor << " at an earlier time " << std::endl;
                continue; 
            }
            gam_item_t gamma_before = cur.g.gamma[successor->edge.agent_before.id];
            gam_item_t gamma_after  = cur.g.gamma[successor->edge.agent_after.id];

            EdgeATF edge(successor->edge);
            edge.zeta = successor->edge.zeta + gamma_before.first;
            edge.alpha = successor->edge.alpha + gamma_before.first;
            edge.beta = successor->edge.beta + gamma_after.second;

            std::cerr << "Outgoing edge to " << successor->destination->state.loc << " atf " << edge << ", b: " << gamma_before << ", a: " << gamma_after << std::endl;

            gamma_t old_gamma = gamma_t(cur.g.gamma);
            old_gamma[successor->edge.agent_after.id] = gam_item_t(gamma_after.first, gamma_after.second,  gamma_after.last_recovery, gamma_after.incurred_delays);
            // Add neighbors to open list if they give a shorter path or are not visited yet
            extendOpen(cur, open_list, m, successor->source, successor->destination, edge, old_gamma, successor);

            // If there is more buffer time available than is currently being used, use it.
            intervalTime_t available_buffer_time = edge.agent_after.max_buffer_time - gamma_after.second;
            std::cerr << "Available buffer time: " << available_buffer_time << ", from max: " << edge.agent_after.max_buffer_time << std::endl;
            intervalTime_t eps = epsilon();

            // FlexSIPP new edge
            if (available_buffer_time > eps) {
                // For this extra atf, alpha is the beta of the old edge, new beta is old beta + extra available buffer time
                // Gamma for the agent after is atleast how much was used before, and max the new max buffer time.
                EdgeATF extra_edge(edge);
                extra_edge.alpha = edge.beta;
                extra_edge.beta = extra_edge.alpha + available_buffer_time;

                gamma_t new_gamma = gamma_t(cur.g.gamma);
                std::vector<incurred_delay_t> incurred_delays = gamma_after.incurred_delays;
                incurred_delays.push_back(incurred_delay_t(successor->destination->state.loc.name, gamma_after.second));
                new_gamma[successor->edge.agent_after.id] =
                        gam_item_t(
                                gamma_after.second,
                                successor->edge.agent_after.max_buffer_time,
                                gamma_after.last_recovery,
                                incurred_delays);

                std::cerr << "Additional edge " << extra_edge << ", " << new_gamma[successor->edge.agent_after.id] << std::endl;
                extendOpen(cur, open_list, m, successor->source, successor->destination, extra_edge, new_gamma, successor);
            }
        }
    }

    template<typename Open_t>
    inline void dump_open(const Open_t& open_list){
        auto cur = open_list.queue.ordered_begin();
        auto end = open_list.queue.ordered_end();
        std::cerr << "Open:";
        while(cur != end){
            std::cerr << "\t" << *cur << "\n";
            cur = std::next(cur);
        }
    }

    template<typename Open_t>
    inline std::pair<std::vector<GraphContainer>, EdgeATF> search_core(Open_t& open_list, const Location& dest, MetaData & m){
        while(!open_list.empty()){
            auto cur = open_list.top();
            if(isGoal(cur, dest)){
                auto res = std::make_pair(backup(cur, open_list), cur.g);
                std::cerr << "---------------- goal at top op open list ----------------"<< std::endl;
                std::cerr << "found path: " << cur.g << std::endl;
                return res;             
            }
            open_list.pop();
            expand(cur, open_list, dest, m);
        }
        std::cerr << "No path found " << "\n";
        return std::make_pair(std::vector<GraphContainer>(), EdgeATF());
    }

   	std::pair<std::vector<GraphNode *>, EdgeATF> search(GraphNode * source, const Location& dest, MetaData & m, double start_time);
}