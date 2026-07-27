#pragma once

#include <unordered_map>
#include <boost/heap/d_ary_heap.hpp>
#include "graph.hpp"


struct MapNode;

struct MapNode {
    GraphNode *graphNode;

    MapNode() = default;
    MapNode(GraphNode *_graphNode): graphNode(_graphNode) {}

    bool operator==(const MapNode &rhs) const {
        return (graphNode == rhs.graphNode);
    }
};

namespace std {
    template<>
    struct hash<MapNode> {
        inline size_t operator()(const MapNode& mn) const {
            return hash<GraphNode *>()(mn.graphNode);
        }
    };
}


namespace rePEAT{
    struct Node;

    struct Node{
        // Compound ATF of current search state
        EdgeATF g;

        // Cost value for A*
        intervalTime_t f;

        // @SIPP graph node, with a single safe interval
        GraphNode * node;
        Node() = default;
        Node(EdgeATF e, intervalTime_t _h, GraphNode * _node, bool optimize_total_delay):g(e),node(_node){
			f = e.earliest_arrival_time() + _h;
			if (optimize_total_delay) {
				f = f + g.sum_of_minimum_delays();
			}
            std::cerr << "Using eat " << e.earliest_arrival_time() << " and h " << _h << std::endl;
        }

        inline friend bool operator>(const Node& a, const Node& b){
            if(a.f == b.f){
                if (a.g.sum_of_minimum_delays() == b.g.sum_of_minimum_delays()) {
                    if (a.g.alpha == b.g.alpha) {
                        return a.g.beta < b.g.beta;
                    }
                    return a.g.alpha < b.g.alpha;
                }
                return a.g.sum_of_minimum_delays() > b.g.sum_of_minimum_delays();
            }
            return a.f > b.f;
        }

        inline friend std::ostream& operator<< (std::ostream& stream, const Node& n){
            stream << *n.node << " g:" << n.g << ", f:" << n.f;
            return stream;
        }
    };

    struct NodeComp{
        bool operator()(const Node * a, const Node * b){
            return *a > *b;
        }
    };

    using Queue = boost::heap::d_ary_heap<Node, boost::heap::arity<4>, boost::heap::mutable_<true>, boost::heap::compare<std::greater<Node>>>;
    typedef typename Queue::handle_type handle_t;
    struct Open{
        Queue queue;
        std::unordered_map<GraphNode *, GraphNode *> parent;
        std::unordered_map<GraphNode *, GraphEdge *> edge_to_parent;
        std::unordered_map<MapNode, handle_t> handles;
        std::unordered_map<MapNode, double> expanded;
		bool optimize_total_delay;

        // Each node in the queue is an EdgeATF, the current heuristic value, the current graphNode, the parent graphNode and the edge between them
        inline Node emplace(EdgeATF e, double h, GraphNode * n, GraphNode * p, GraphEdge * ge){
            parent[n] = p;
			edge_to_parent[n] = ge;
            Node new_node = Node(e, h, n, optimize_total_delay);
            handles[MapNode(n)] = queue.push(new_node);
            return new_node;
        }

        inline bool empty() const{
            return queue.empty();
        }

        inline Node top() const{
            return queue.top();
        }

        inline void pop(){
            Node n = top();
            expanded[MapNode(n.node)] = n.g.earliest_arrival_time();
            queue.pop();
        }

        inline Node decrease_key(handle_t handle , EdgeATF e, double h, GraphNode * n, GraphNode * p, GraphEdge * ge){
            parent[n] = p;
			edge_to_parent[n] = ge;
            Node new_node = Node(e, h, n, optimize_total_delay);
            queue.increase(handle, new_node);
            return new_node;
        }

        inline size_t size() {
            return queue.size();
        }
    };

    CompoundATF<std::vector<GraphContainer>> search(GraphNode * source, const Location& dest, MetaData & m, double start_time, gamma_t gamma, intervalTime_t search_duration, bool optimize_total_delay, bool find_first_path);
}
