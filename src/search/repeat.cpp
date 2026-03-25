#include "atf.hpp"
#include "augmentedsipp.hpp"
#include "repeat.hpp"

//double update_reference_time(const EdgeATF& path, rePEAT::Open& open_list){
//    intervalTime_t upper_bound = path.beta;
//    intervalTime_t lower_bound = path.alpha;
////    std::cerr << "Starting update tref with alpha " << lower_bound << " beta " << upper_bound << " delta " << path.delta << " gamma [";
////    for (gam_item_t gamma : path.gamma) {
////        std::cerr << "<" << gamma.first << ", " << gamma.second << ">, ";
////    }
////    std::cerr << "]\n";
////    std::cerr << "Queue has " << open_list.size() << " elements." << std::endl;
//    while(lower_bound < upper_bound){
//        if(open_list.empty()){
//            return std::numeric_limits<double>::infinity();
//        }
//        auto n = open_list.top();
//        open_list.pop();
////        std::cerr << "popped " << n << std::endl;
//        lower_bound = n.g.alpha;
////        std::cerr << "new lb " << lower_bound << std::endl;
//        if (lower_bound > path.alpha + epsilon()){
//            if (lower_bound > upper_bound) {
//                break;
//            }
////            std::cerr << "Result from lb ";
//            return n.g.alpha;
//        }
//
//    }
////    std::cerr << "Result from ub ";
//    return upper_bound;
//}

double update_reference_time(const EdgeATF& path, rePEAT::Open& open_list){
    intervalTime_t upper_bound = path.beta;
    intervalTime_t lower_bound = path.alpha;
    std::cerr << "Starting update tref with alpha " << lower_bound << " beta " << upper_bound << " delta " << path.delta << std::endl;
    // return upper_bound;
     while(lower_bound < upper_bound){
         if(open_list.empty()){
             return upper_bound;
         }
         auto n = open_list.top();
         open_list.pop();
         std::cerr << "popped " << n.g << std::endl;
         std::cerr << "f: " << n.f << std::endl;
         lower_bound = n.f - path.delta;
         std::cerr << ", new lb " << lower_bound << std::endl;
         if (n.g.alpha > lower_bound){
             std::cerr << "Result from lb ";
             return std::min(upper_bound, lower_bound);
         }
     }
    std::cerr << "Result from ub ";
    return upper_bound;
}

CompoundATF<std::vector<GraphContainer>> rePEAT::search(GraphNode * source, const Location& dest, MetaData & m,
                                                     double start_time, gamma_t gamma, intervalTime_t search_duration,
                                                     bool optimize_total_delay){
    double t_ref = start_time;
    std::vector<GraphContainer> path;
    CompoundATF solutions(path);
    m.init();
    while((t_ref < end(source->state.interval) + std::get<4>(source->state.interval)) && (t_ref < start_time + search_duration)){
        std::cerr << "tref: " << t_ref << "\n";
        Open open_list;
        open_list.optimize_total_delay = optimize_total_delay;
        open_list.emplace(EdgeATF(-std::numeric_limits<double>::infinity(), t_ref, std::numeric_limits<double>::infinity(), 0.0, gamma), 0, source, nullptr, nullptr);
        auto res = asipp::search_core(open_list, dest, m);
        if(res.first.size() == 0){
            break;
        }
        solutions.add(res.second, res.first);
        if (optimize_total_delay) {
            break;
        }
        t_ref = update_reference_time(res.second, open_list);
    }
    std::cerr << "At end of safe interval at start node at " << t_ref << "source int " << std::get<4>(source->state.interval) << std::endl;
    return solutions;
}